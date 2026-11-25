"""Policy/contrastive-example ablation using the existing five-facet extract/review path."""
import argparse
import csv
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import matrix as shared

base, v3, evaluator, FACETS = shared.base, shared.v3, shared.evaluator, shared.FACETS
ARMS = ('original', 'policy', 'policy_examples')
POLICY = 'data/exp_a/prompts/facet_policy_v1.md'
EXAMPLES = 'data/exp_a/prompts/policy_examples_v1.json'
AUDIT = 'data/exp_a/prompts/policy_audit_v1.json'


def validate_split(scored_ids, audit_ids, example_ids):
    base.require(len(scored_ids) == len(set(scored_ids)) and len(audit_ids) == len(set(audit_ids)), 'Duplicate split IDs')
    base.require(not set(scored_ids) & (set(audit_ids) | set(example_ids)), 'Policy/example papers overlap scored papers')


def instruction(root, arm, config):
    if arm == 'original':
        return '\n\n'.join((root/config[k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    text = (root/POLICY).read_text(encoding='utf-8')
    if arm == 'policy_examples':
        text += '\nSynthetic contrasting examples; these are OTHER sources, never labels for the current paper.\n'
        for example in json.loads((root/EXAMPLES).read_text(encoding='utf-8')):
            source = dict(paper_id=example['paper_id'], evidence_options={k:v['evidence']
                          for k,v in base.evidence_options(example['source']).items()})
            text += '\nSOURCE: '+json.dumps(source,ensure_ascii=False)+'\nOUTPUT: '+json.dumps(example['output'],ensure_ascii=False)
            text += '\nWHY: '+example['contrast']+'\n'
    return text


def annotate_paper(paper, text, config, runtime, generate, directory):
    value, audit = v3.annotate(paper,text,config,runtime,generate,directory/'last_failure.json')
    return dict(paper_id=paper['paper_id'],facets=dict(paper_id=paper['paper_id'],
        **{f:[x['concept'] for x in value[f]] for f in FACETS}),audit=audit,usage=audit['usage'],
        generation_seconds=audit['generation_seconds'],fallback_used=audit['fallback_used'])


def build(destination=None, *, model_keys=('8b',), paper_ids=None, local=False):
    import build_matrix
    destination = Path(destination or HERE/'build_policy')
    audit = json.loads((ROOT/AUDIT).read_text(encoding='utf-8'))
    examples = json.loads((ROOT/EXAMPLES).read_text(encoding='utf-8'))
    sources = base.read_jsonl(ROOT/audit['source'])
    by_id = {p['paper_id']:p for p in sources}
    audit_ids = [c['paper_id'] for c in audit['cases']]
    base.require(len(audit_ids) == 20 and set(audit_ids) <= by_id.keys(), 'Expected 20 source-inspected policy papers')
    for case in audit['cases']:
        for item in case['accepted']:
            response = dict(paper_id=case['paper_id'], **{f:[] for f in FACETS})
            response[item['facet']] = [dict(concept=item['concept'],evidence_id=item['evidence_id'])]
            v3.validate_response(v3.ground_response(response,by_id[case['paper_id']]),by_id[case['paper_id']],policy='3.1')
    for example in examples:
        base.require(set(example['derived_from']) <= set(audit_ids), 'Example uses an unaudited development paper')
        v3.validate_response(v3.ground_response(example['output'],example['source']),example['source'],policy='3.1')
    ids = sorted(paper_ids or (by_id.keys()-set(audit_ids)))
    validate_split(ids,audit_ids,[x['paper_id'] for x in examples])
    base.require(ids and set(ids) <= by_id.keys(), 'Unknown/empty evaluation subset')
    with tempfile.TemporaryDirectory() as staging:
        build_matrix.build(Path(staging))
        with zipfile.ZipFile(Path(staging)/'input-dataset/matrix_bundle.zip.bin') as archive:
            files = {n:archive.read(n) for n in archive.namelist()}
    old = json.loads(files.pop('matrix_settings.json'))
    files.pop('model_inputs/baseline_records.jsonl')
    files.pop('model_inputs/completed_4b_source_first.jsonl',None)
    def json_bytes(value):
        return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    def jsonl_bytes(rows):
        return ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows).encode('utf-8')
    files['model_inputs/papers.jsonl'] = jsonl_bytes([by_id[pid] for pid in ids])
    references = [r for r in base.read_jsonl(ROOT/'data/exp_a/pilot50/ai_reference_v1/review_annotations.jsonl') if r['paper_id'] in ids]
    base.require({r['paper_id'] for r in references} == set(ids), 'Reference IDs differ')
    files['evaluation_only/review_annotations.jsonl'] = jsonl_bytes(references)
    files['policy_development/source_papers.jsonl'] = jsonl_bytes([by_id[pid] for pid in audit_ids])
    previous = ROOT/'data/exp_a/evaluation/facet_matrix_v2'
    manifest = json.loads((previous/'manifest.json').read_text(encoding='utf-8'))
    base.require(manifest['status'] == 'complete', 'Cached matrix baseline is incomplete')
    for key in model_keys:
        records = []
        for pid in ids:
            name = f'{key}_original/records/{pid}.json'
            base.require(base.sha256(previous/name) == manifest['files'][name], 'Cached baseline checksum differs')
            record = shared.load_record(previous/name,manifest['generation_signature'])
            record = dict(record,reused_from=dict(kernel=build_matrix.KERNEL,version=2,arm=f'{key}_original',
                signature=manifest['generation_signature']))
            records.append(record)
        files[f'model_inputs/baseline_{key}.jsonl'] = jsonl_bytes(records)
    for name in (POLICY,EXAMPLES,AUDIT,'data/exp_a/.kaggle/matrix/policy_matrix.py'):
        files[name] = (ROOT/name).read_bytes()
    settings = dict(experiment_version='policy_matrix_v1',arms=list(ARMS),paper_ids=ids,audit_paper_ids=audit_ids,
        generation=old['generation'],models={k:old['models'][k] for k in model_keys},workers=1 if local else 2,
        local=local,local_cache=str(ROOT/'models/huggingface') if local else None,
        reference_kind='ai',sample_kind='reused_dev_subset_excluding_policy_development20',
        parent_reference_sha256=base.sha256(ROOT/'data/exp_a/pilot50/ai_reference_v1/review_annotations.jsonl'),
        review_profile='3.7 unchanged; prompt content varies by arm; ordered-source validation policy 3.1',
        schema='concept + evidence_id for every arm; no generated span/kind',
        limitations=['AI-reviewed policy cases and frozen AI reference, not human gold',
            'Evaluation papers were previously used in development; not a fresh held-out test',
            'Original records reused; their generation cost is historical',
            'Synthetic examples teach roles; their effect is not proven before evaluation'],
        files={name:hashlib.sha256(data).hexdigest() for name,data in files.items()})
    settings['generation_signature'] = shared.digest(settings)
    files['policy_settings.json'] = json_bytes(settings)
    dataset, kernel = destination/'input-dataset',destination/'kernel'
    dataset.mkdir(parents=True,exist_ok=True)
    kernel.mkdir(parents=True,exist_ok=True)
    archive_path = dataset/'matrix_bundle.zip.bin'
    with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):
            archive.writestr(name,data)
    base.write_json(dataset/'dataset-metadata.json',dict(id=build_matrix.DATASET,title='Exp A Qwen Facet Matrix Inputs',licenses=[dict(name='other')]))
    code = (HERE/'kernel_matrix.template.py').read_text(encoding='utf-8').replace('__BUNDLE_SHA256__',base.sha256(archive_path))
    code = code.replace('exp_a_matrix','exp_a_policy').replace('matrix_settings.json','policy_settings.json').replace('import matrix','import policy_matrix as matrix')
    compile(code,'run_policy.py','exec')
    (kernel/'run_policy.py').write_text(code,encoding='utf-8')
    base.write_json(kernel/'kernel-metadata.json',dict(id=build_matrix.KERNEL,title='Exp A Qwen Facet Matrix',
        code_file='run_policy.py',language='python',kernel_type='script',is_private=True,enable_gpu=True,
        enable_internet=True,machine_shape='NvidiaTeslaT4',dataset_sources=[build_matrix.DATASET],
        competition_sources=[],kernel_sources=[],model_sources=[]))
    result = dict(kernel=build_matrix.KERNEL,dataset=build_matrix.DATASET,arms=list(ARMS),models=list(model_keys),
        sample_size=len(ids),policy_cases=len(audit_ids),generation_signature=settings['generation_signature'],
        bundle_sha256=base.sha256(archive_path),settings=settings)
    base.write_json(destination/'build_manifest.json',result)
    return result


def worker(root, model_key, gpu):
    settings = json.loads((root/'policy_settings.json').read_text(encoding='utf-8'))
    papers = base.read_jsonl(root/'model_inputs/papers.jsonl')[gpu::settings['workers']]
    signature = settings['generation_signature']
    config = dict(settings['generation'],**settings['models'][model_key])
    config['cache_dir'] = settings['local_cache'] if settings['local'] else '/tmp/exp_a_huggingface'
    config['offline'] = settings['local']
    paths = [root/f'results/{model_key}_{arm}/records/{p["paper_id"]}.json' for p in papers for arm in ARMS[1:]]
    if all(path.exists() for path in paths):
        for path in paths:
            shared.load_record(path,signature)
        return
    texts = {arm:instruction(root,arm,config) for arm in ARMS[1:]}
    generate, runtime = shared.load_generator(config)
    for paper in papers:
        for arm in ARMS[1:]:
            directory = root/f'results/{model_key}_{arm}'
            path = directory/f'records/{paper["paper_id"]}.json'
            if path.exists():
                shared.load_record(path,signature)
                continue
            result = annotate_paper(paper,texts[arm],config,runtime,generate,directory)
            result.update(prompt_arm=arm,instruction_sha256=hashlib.sha256(texts[arm].encode('utf-8')).hexdigest())
            shared.save_record(path,result,signature)
            print(f'{model_key} GPU {gpu}: {arm} completed {paper["paper_id"]}',flush=True)


def evaluate(root):
    settings = json.loads((root/'policy_settings.json').read_text(encoding='utf-8'))
    papers = base.read_jsonl(root/'model_inputs/papers.jsonl')
    refs = base.read_jsonl(root/'evaluation_only/review_annotations.jsonl')
    records = {f'{key}_{arm}':[shared.load_record(root/f'results/{key}_{arm}/records/{p["paper_id"]}.json',
        settings['generation_signature']) for p in papers] for key in settings['models'] for arm in ARMS}
    labels = sorted({v for rows in records.values() for r in rows for f in FACETS for v in r['facets'][f]}
                    | {v for r in refs for f in FACETS for v in r['facets'][f]})
    vectors, embedding = evaluator.encode_labels(ROOT if settings['local'] else root,labels)
    table = []
    for arm,rows in records.items():
        report = shared.score_rows(papers,rows,refs,vectors)
        base.write_json(root/f'results/{arm}/evaluation.json',report)
        base.write_jsonl(root/f'results/{arm}/facets_silver.jsonl',[r['facets'] for r in rows])
        table.append(dict(arm=arm,**{k:report['micro'][k] for k in ('precision','recall','tp','fp','fn')},
            micro_f1=report['micro']['f1'],macro_f1=report['macro_f1'],target_f1=report['target_micro']['f1'],
            **{f'{f}_f1':report['by_facet'][f]['f1'] for f in FACETS},
            fallback_count=sum(r['fallback_used'] for r in rows),output_tokens=sum(r['usage'].get('output_tokens',0) for r in rows),
            generation_seconds=sum(r['generation_seconds'] for r in rows),reused=arm.endswith('_original')))
    destination = root/'results'
    with (destination/'experiment_table.csv').open('w',encoding='utf-8',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    columns = ('micro_f1','macro_f1','problem_f1','task_f1','method_f1','dataset_f1','contribution_f1','target_f1')
    lines = [f'# Policy matrix: {len(papers)} reused development papers','',
        '20 source-inspected policy-development papers excluded. Frozen AI reference, not human gold.',
        'Same minimal schema and 3.7 extract/review budget for every arm. Original cost is historical.',
        '| Arm | Micro | Macro | Problem | Task | Method | Dataset | Contribution | Target |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in table:
        lines.append('| '+row['arm']+' | '+' | '.join('N/A' if row[k] is None else f'{100*row[k]:.2f}' for k in columns)+' |')
    (destination/'experiment_table.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    base.write_json(destination/'experiment_summary.json',dict(status='complete',table=table,settings=settings,
        threshold=0.85,reference_kind='ai',embedding=embedding,reference_sha256=base.sha256(root/'evaluation_only/review_annotations.jsonl')))
    print('\n'.join(lines),flush=True)
    return table


def run(root):
    import torch
    settings = json.loads((root/'policy_settings.json').read_text(encoding='utf-8'))
    workers = settings['workers']
    base.require(torch.cuda.device_count() == workers, 'GPU count differs from experiment settings')
    for key in settings['models']:
        for record in base.read_jsonl(root/f'model_inputs/baseline_{key}.jsonl'):
            shared.save_record(root/f'results/{key}_original/records/{record["paper_id"]}.json',record,settings['generation_signature'])
        if workers == 1:
            worker(root,key,0)
        else:
            processes = []
            try:
                for gpu in range(workers):
                    env = dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
                    processes.append(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),
                        '--root',str(root),'--worker',key,'--gpu',str(gpu)],env=env))
                for process in processes:
                    base.require(process.wait() == 0, 'Policy worker failed; checkpoints retained')
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                        process.wait()
        gc.collect()
        torch.cuda.empty_cache()
    return evaluate(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',action='store_true')
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--root',type=Path)
    parser.add_argument('--worker',choices=('4b','8b'))
    parser.add_argument('--gpu',type=int,default=0)
    args = parser.parse_args()
    if args.build:
        result = build(args.destination)
        print(json.dumps({k:v for k,v in result.items() if k != 'settings'},indent=2))
    elif args.worker:
        worker(args.root,args.worker,args.gpu)
    else:
        run(args.root)
