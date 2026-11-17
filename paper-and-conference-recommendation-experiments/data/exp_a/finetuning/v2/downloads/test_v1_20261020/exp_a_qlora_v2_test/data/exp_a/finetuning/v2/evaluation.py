"""Frozen 100-paper paired test: base versus the dev-selected v2 adapter."""
import argparse
import base64
from collections import Counter
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
KERNEL = 'htnkhi/exp-a-qwen-qlora-v2-test'
DATASET = 'htnkhi/exp-a-qwen-qlora-inputs'
ARMS = ('base', 'qlora_v2')
GENERATION = dict(seed=42, max_attempts=2, max_new_tokens=2048, seconds_per_call=180,
                  do_sample=False, temperature=0.7, top_p=0.8, top_k=20)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load('v2_test_policy_runner', HERE.parent/'policy_ab/runner.py')
generation = load('v2_test_generation', HERE/'generation.py')
shared = runner.shared
read = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
sha256 = shared.base.sha256
write_json = shared.base.write_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_adapter(adapter, settings):
    metadata = read(adapter/'training_metadata.json')
    require(sha256(adapter/'training_metadata.json') == settings['adapter_metadata_sha256'],
            'Adapter metadata differs from the verified training output')
    require(metadata['status'] == 'complete' and metadata['best_checkpoint'] == 'checkpoint-118'
            and metadata['base_model'] == settings['model']['model']
            and metadata['base_revision'] == settings['model']['revision'], 'Wrong adapter/model/checkpoint')
    for name, expected in metadata['files'].items():
        path = (adapter/name).resolve()
        require(adapter.resolve() in path.parents and path.is_file() and sha256(path) == expected,
                'Missing or changed adapter file: '+name)
    require(metadata['files']['adapter_model.safetensors'] == settings['adapter_sha256'], 'Wrong adapter weights')
    return metadata


def verify(root, settings):
    require(shared.digest({k:v for k,v in settings.items() if k != 'signature'}) == settings['signature'],
            'Test settings signature differs')
    require(settings['version'] == 'exp_a_qlora_v2_test_1'
            and settings['generation'] == GENERATION, 'Unexpected evaluation protocol')
    require(set(settings['test_files']) == {'model_inputs/test_papers.jsonl',
            'evaluation_only/test_references.jsonl'}, 'Unexpected external test inputs')
    for name, expected in {**settings['files'], **settings['test_files'], **settings.get('embedding_files',{})}.items():
        path = (root/name).resolve()
        require(root.resolve() in path.parents and path.is_file() and sha256(path) == expected,
                'Changed or unsafe test payload: '+name)
    papers = shared.base.read_jsonl(root/'model_inputs/test_papers.jsonl')
    ids = [p['paper_id'] for p in papers]
    require(len(ids) == len(set(ids)) == 100 and ids == settings['test_ids'], 'Changed test cohort')
    require(not set(ids) & set(settings['train_dev_ids']), 'Test overlaps training/development')
    return papers


def load_record(root, settings, arm, pid):
    record = shared.load_record(root/f'results/{arm}/records/{pid}.json', settings['signature'])
    require(record['paper_id'] == pid and record['arm'] == arm
            and record['adapter_sha256'] == settings['adapter_sha256']
            and record['instruction_sha256'] == settings['files']['instruction.txt'], 'Record pairing differs')
    return record


def worker(root, settings, adapter, arm, *, generate=None, runtime=None):
    require(arm in ARMS, 'Unknown arm')
    papers = verify(root, settings)
    verify_adapter(adapter, settings)
    config = dict(settings['generation'], **settings['model'])
    if arm == 'qlora_v2':
        config['adapter_path'] = str(adapter)
    if generate is None:
        model, tokenizer, runtime = generation.load_model(config, shared)
        generate = generation.build_generator(model, tokenizer, config)
    require(runtime['adapter_enabled'] is (arm == 'qlora_v2'), 'Runtime arm differs')
    instruction = (root/'instruction.txt').read_text(encoding='utf-8')
    for paper in papers:
        pid = paper['paper_id']
        path = root/f'results/{arm}/records/{pid}.json'
        if path.exists():
            load_record(root, settings, arm, pid)
            continue
        # This shared pipeline receives only source and instruction, never reference labels.
        record = runner.annotate_new(paper, instruction, config, generate)
        record.update(arm=arm, runtime=runtime, adapter_sha256=settings['adapter_sha256'],
                      instruction_sha256=settings['files']['instruction.txt'])
        shared.save_record(path, record, settings['signature'])
        print(f'{arm}: {pid} saved; fallback={record["fallback_used"]}', flush=True)


def evaluate(root, settings, *, vectors=None, embedding=None):
    papers = verify(root, settings)
    records = {arm:[load_record(root,settings,arm,p['paper_id']) for p in papers] for arm in ARMS}
    # References are opened only after both complete prediction sets have been sealed.
    refs = shared.base.read_jsonl(root/'evaluation_only/test_references.jsonl')
    require([r['paper_id'] for r in refs] == settings['test_ids'], 'Reference cohort differs')
    labels = sorted({v for rows in records.values() for r in rows for f in shared.FACETS for v in r['facets'][f]}
                    | {v for r in refs for f in shared.FACETS for v in r['facets'][f]})
    if vectors is None:
        experiment = load('v2_test_embedding', HERE.parent/'experiment.py')
        vectors, embedding = experiment.embedding_vectors(root, labels)
    table = []
    for arm, rows in records.items():
        report = shared.score_rows(papers, rows, refs, vectors, threshold=0.85)
        write_json(root/f'results/{arm}/evaluation.json', report)
        shared.base.write_jsonl(root/f'results/{arm}/facets_silver.jsonl', [r['facets'] for r in rows])
        attempts = [a for r in rows for a in r['audit']['attempts']]
        stops = Counter(a.get('stop_reason','unknown') for a in attempts)
        row = dict(arm=arm, precision=report['micro']['precision'], recall=report['micro']['recall'],
                   micro_f1=report['micro']['f1'], macro_f1=report['macro_f1'],
                   **{f'{f}_f1':report['by_facet'][f]['f1'] for f in shared.FACETS},
                   fallback_count=sum(r['fallback_used'] for r in rows),
                   draft_schema_valid=sum(r['audit']['attempts'][0]['schema_valid'] for r in rows),
                   draft_validator_valid=sum(not r['audit']['attempts'][0]['validation_errors'] for r in rows),
                   selected_schema_valid=sum(r['audit']['attempts'][r['audit']['selected_attempt']-1]['schema_valid'] for r in rows),
                   selected_validator_valid=sum(not r['audit']['validation_errors'] for r in rows),
                   bounded_calls=sum(a.get('bounded_stop',False) for a in attempts),
                   duplicate_stops=stops['duplicate_concept'], time_stops=stops['time_budget'],
                   token_stops=stops['token_limit'], total_calls=len(attempts),
                   output_tokens=sum(r['usage'].get('output_tokens',0) for r in rows),
                   generation_seconds=sum(r['generation_seconds'] for r in rows))
        table.append(row)
    with (root/'results/experiment_table.csv').open('w',encoding='utf-8',newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    lines = ['# QLoRA v2 paired test: 100 papers','',
             'Frozen existing AI references (pre-v2 label policy); human review pending.',
             'Same v2.2 instruction, schema, greedy decoder and mandatory source-only review for both arms.',
             'Failed papers remain in the denominator; grounded fallback concepts are scored and flagged.', '',
             '| Arm | Micro F1 | Macro F1 | Precision | Recall | Fallback papers |',
             '|---|---:|---:|---:|---:|---:|']
    for row in table:
        percent = lambda key: f'{100*row[key]:.2f}' if row[key] is not None else 'n/a'
        lines.append(f'| {row["arm"]} | {percent("micro_f1")} | {percent("macro_f1")} | '
                     f'{percent("precision")} | {percent("recall")} | {row["fallback_count"]} |')
    (root/'results/experiment_table.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    result = dict(status='complete', settings=settings, signature=settings['signature'], table=table,
                  embedding=embedding, threshold=0.85, paper_count=100, training_performed=False,
                  reference_kind='frozen_existing_ai_reference_pre_v2_policy', human_review_status='pending',
                  reference_sha256=settings['test_files']['evaluation_only/test_references.jsonl'])
    write_json(root/'results/experiment_summary.json',result)
    print('\n'.join(lines),flush=True)
    return result


def run(root, settings, adapter):
    import torch
    verify(root,settings);verify_adapter(adapter,settings)
    require(torch.cuda.device_count() == 2, 'This paired kernel requires two Tesla T4 GPUs')
    processes = []
    try:
        for gpu,arm in enumerate(ARMS):
            env = dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),
                '--root',str(root),'--adapter',str(adapter),'--worker',arm],env=env))
        for process in processes:
            require(process.wait() == 0, 'Inference failed; per-paper checkpoints retained')
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate();process.wait()
    return evaluate(root,settings)


def build(destination):
    destination = Path(destination)
    require(not destination.exists(), 'Refusing to overwrite an evaluation build')
    old_data = HERE.parent/'data'
    frozen = read(old_data/'manifest.json')
    train = read(HERE/'training_data/manifest.json')
    result = read(HERE/'build/training_result_summary_2026-10-19.json')
    adapter = ROOT/result['download_directory']/'exp_a_qlora_v2/adapters/qwen3-8b-facets-qlora-v2'
    metadata = read(adapter/'training_metadata.json')
    require(result['status'] == 'verified_training_complete', 'Training not verified')
    require(train['split_ids']['train'] == frozen['split_ids']['train']
            and train['split_ids']['dev'] == frozen['split_ids']['dev'], 'Training split changed')
    files, test_files = {}, {}
    for name,target in [('test_papers.jsonl','model_inputs/test_papers.jsonl'),
                        ('test_references.jsonl','evaluation_only/test_references.jsonl')]:
        require(sha256(old_data/name) == frozen['output_sha256'][name], 'Sealed test changed')
        test_files[target] = frozen['output_sha256'][name]
    prior_launch = read(HERE.parent/'build/push_report.json')
    require(prior_launch['dataset'] == DATASET and prior_launch['visibility'] == 'private'
            and sha256(HERE.parent/'build/input-dataset/qlora_bundle.zip.bin') == prior_launch['bundle_sha256'],
            'Existing private Kaggle test bundle provenance differs')
    files['instruction.txt'] = (HERE/'training_data/instruction.txt').read_bytes()
    require(hashlib.sha256(files['instruction.txt']).hexdigest() == train['instruction_sha256'], 'Instruction changed')
    code_files = ['data/exp_a/finetuning/v2/evaluation.py','data/exp_a/finetuning/v2/generation.py',
        'data/exp_a/finetuning/policy_ab/runner.py','data/exp_a/finetuning/label_revision_v2/schema.py',
        'data/exp_a/finetuning/experiment.py','data/exp_a/.kaggle/matrix/matrix.py',
        'data/exp_a/build_exp_a.py','data/exp_a/extraction_v3.py','scripts/exp_a/evaluate_exp_a.py',
        'scripts/experiment_io.py','scripts/build_corpus.py','scripts/download_sources.py','scripts/validate_all.py']
    for name in code_files:
        files[name] = (ROOT/name).read_bytes();compile(files[name],name,'exec')
    relative = shared.evaluator.MODEL_DIRECTORY
    download = read(ROOT/relative/'download_manifest.json')
    embedding_files = {relative+'/download_manifest.json': sha256(ROOT/relative/'download_manifest.json')}
    for name,info in download['files'].items():
        if name != 'model.safetensors':
            require(sha256(ROOT/relative/name) == info['sha256'], 'Embedding metadata changed')
            embedding_files[relative+'/'+name] = info['sha256']
    settings = dict(version='exp_a_qlora_v2_test_1', kernel=KERNEL, dataset=DATASET,
        model=dict(model=metadata['base_model'],revision=metadata['base_revision']), generation=GENERATION,
        training_signature=result['signature'],adapter_metadata_sha256=sha256(adapter/'training_metadata.json'),
        adapter_sha256=result['adapter_sha256'],test_ids=frozen['split_ids']['test'],
        train_dev_ids=frozen['split_ids']['train']+frozen['split_ids']['dev'],
        test_files=test_files,embedding_files=embedding_files,source_bundle_sha256=prior_launch['bundle_sha256'],
        reference_kind='frozen_existing_ai_reference_pre_v2_policy',human_review_status='pending',
        files={name:hashlib.sha256(value).hexdigest() for name,value in files.items()})
    settings['signature'] = shared.digest(settings)
    verify_adapter(adapter,settings)
    files['v2_settings.json'] = (json.dumps(settings,ensure_ascii=False,indent=2)+'\n').encode()
    kernel = destination/'kernel'
    kernel.mkdir(parents=True)
    bundle = destination/'v2_test_code.zip'
    with zipfile.ZipFile(bundle,'w') as archive:
        for name,payload in sorted(files.items()):
            entry = zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
            entry.external_attr=0o100644<<16;archive.writestr(entry,payload)
    # Reuse the checked bootstrap extractor rather than another ZIP extraction implementation.
    bootstrap = (HERE/'training_kernel.template.py').read_text(encoding='utf-8').split('\ndef main():')[0]
    bootstrap = bootstrap.replace('__BUNDLE_SHA256__',sha256(bundle)).replace('/exp_a_qlora_v2\'', '/exp_a_qlora_v2_test\'')
    code = bootstrap + '\nCODE_B64 = '+repr(base64.b64encode(bundle.read_bytes()).decode('ascii'))+'\n'
    code += (HERE/'evaluation_kernel.template.py').read_text(encoding='utf-8')
    compile(code,'run_test.py','exec')
    require(len(code.encode('utf-8')) < 1_000_000, 'Kaggle kernel source exceeds 1 MB')
    (kernel/'run_test.py').write_text(code,encoding='utf-8')
    write_json(kernel/'kernel-metadata.json',dict(id=KERNEL,title='Exp A Qwen QLoRA V2 Test',code_file='run_test.py',
        language='python',kernel_type='script',is_private=True,enable_gpu=True,enable_internet=True,
        machine_shape='NvidiaTeslaT4',dataset_sources=[DATASET],kernel_sources=['htnkhi/exp-a-qwen-qlora-v2'],
        competition_sources=[],model_sources=[]))
    result = dict(kernel=KERNEL,existing_private_dataset=DATASET,new_upload_contains_test_content=False,
        signature=settings['signature'],settings=settings,
        bundle_sha256=sha256(bundle),kernel_sha256=sha256(kernel/'run_test.py'))
    write_json(destination/'build_manifest.json',result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path)
    parser.add_argument('--root',type=Path)
    parser.add_argument('--adapter',type=Path)
    parser.add_argument('--worker',choices=ARMS)
    args = parser.parse_args()
    if args.build:
        result = build(args.build)
        print(json.dumps({k:v for k,v in result.items() if k != 'settings'},indent=2))
    else:
        settings = read(args.root/'v2_settings.json')
        if args.worker:
            worker(args.root,settings,args.adapter,args.worker)
        else:
            run(args.root,settings,args.adapter)
