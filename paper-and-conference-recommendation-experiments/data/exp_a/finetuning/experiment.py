"""Train once, then compare fresh base/adapter predictions on the frozen test set."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'data/exp_a/.kaggle/matrix'))
import matrix as shared

ARMS = ('original','qlora')
ADAPTER = 'adapters/qwen3-8b-facets-qlora-v1'


def verify_adapter(directory, settings):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/'adapter_manifest.json').read_text(encoding='utf-8'))
    shared.base.require(manifest['status'] == 'complete', 'Adapter training incomplete')
    shared.base.require(manifest['base_model'] == settings['model']['model']
        and manifest['base_revision'] == settings['model']['revision'], 'Adapter base model or revision differs')
    shared.base.require(manifest['experiment_signature'] == settings['experiment_signature'], 'Adapter experiment signature differs')
    for name, expected in manifest['files'].items():
        path = (directory/name).resolve()
        shared.base.require(directory in path.parents and path.is_file(), 'Unsafe/missing adapter file')
        shared.base.require(shared.base.sha256(path) == expected, 'Adapter checksum differs: '+name)
    return manifest


def seal_adapter(root, settings):
    from safetensors import safe_open
    import torch
    directory = root/ADAPTER
    required = ('adapter_config.json','adapter_model.safetensors','training_metadata.json')
    shared.base.require(all((directory/name).is_file() for name in required), 'Training did not produce a complete adapter')
    config = json.loads((directory/'adapter_config.json').read_text(encoding='utf-8'))
    shared.base.require(config['base_model_name_or_path'] == settings['model']['model'], 'Adapter targets another base model')
    shared.base.require(config['r'] == 16 and config['lora_alpha'] == 32, 'LoRA configuration differs')
    updated = False
    with safe_open(directory/'adapter_model.safetensors',framework='pt',device='cpu') as archive:
        keys = list(archive.keys())
        shared.base.require(keys and all('lora_A' in k or 'lora_B' in k for k in keys), 'File is not a LoRA-only adapter')
        for key in keys:
            value = archive.get_tensor(key)
            shared.base.require(bool(torch.isfinite(value).all()), 'Nonfinite adapter weights')
            updated |= 'lora_B' in key and bool(torch.count_nonzero(value))
    shared.base.require(updated, 'Adapter has no learned LoRA-B weights')
    manifest = dict(status='complete',base_model=settings['model']['model'],base_revision=settings['model']['revision'],
        experiment_signature=settings['experiment_signature'],prompt_sha256=settings['training']['prompt_sha256'],
        schema_sha256=settings['training']['schema_sha256'],data_signature=settings['data_signature'],
        files={p.name:shared.base.sha256(p) for p in directory.iterdir() if p.is_file() and p.name!='adapter_manifest.json'})
    shared.base.write_json(directory/'adapter_manifest.json',manifest)
    verify_adapter(directory,settings)
    return manifest


def predict(root, settings, arm, *, generate=None, runtime=None):
    shared.base.require(arm in ARMS, 'Unknown prediction arm')
    papers = shared.base.read_jsonl(root/'model_inputs/test_papers.jsonl')
    shared.base.require([p['paper_id'] for p in papers] == settings['test_ids'], 'Test inputs changed or incomplete')
    signature = settings['experiment_signature']
    directory = root/f'results/{arm}'
    directory.mkdir(parents=True,exist_ok=True)
    paths = [directory/f'records/{p["paper_id"]}.json' for p in papers]
    if all(path.exists() for path in paths):
        for path in paths:
            shared.load_record(path,signature)
        return
    config = dict(settings['generation'],**settings.get('model',{}),cache_dir='/tmp/exp_a_huggingface')
    adapter = None
    if arm == 'qlora':
        adapter = verify_adapter(root/ADAPTER,settings)
        config['adapter_path'] = str(root/ADAPTER)
    if generate is None:
        generate,runtime = shared.load_generator(config)
    instruction = (root/'instruction.txt').read_text(encoding='utf-8')
    for paper,path in zip(papers,paths):
        if path.exists():
            shared.load_record(path,signature)
            continue
        value,audit = shared.v3.annotate(paper,instruction,config,runtime or {},generate,directory/'last_failure.json')
        record = dict(paper_id=paper['paper_id'],facets=dict(paper_id=paper['paper_id'],
            **{f:[x['concept'] for x in value[f]] for f in shared.FACETS}),audit=audit,
            usage=audit['usage'],generation_seconds=audit['generation_seconds'],fallback_used=audit['fallback_used'],
            arm=arm,instruction_sha256=hashlib.sha256(instruction.encode()).hexdigest(),
            adapter_manifest_sha256=shared.base.sha256(root/ADAPTER/'adapter_manifest.json') if adapter else None)
        shared.save_record(path,record,signature)
        print(f'{arm}: completed {paper["paper_id"]}',flush=True)


def embedding_vectors(root, labels):
    from huggingface_hub import hf_hub_download
    import shutil
    cache_root = Path('/tmp/exp_a_qlora_embedding')
    relative = shared.evaluator.MODEL_DIRECTORY
    source = root/relative
    directory = cache_root/relative
    directory.mkdir(parents=True,exist_ok=True)
    manifest = json.loads((source/'download_manifest.json').read_text(encoding='utf-8'))
    for name,info in manifest['files'].items():
        path = directory/name
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            if (source/name).is_file():
                shutil.copy2(source/name,path)
            else:
                hf_hub_download(shared.evaluator.MODEL_ID,filename=name,revision=shared.evaluator.MODEL_REVISION,
                    local_dir=str(directory),token=False)
        shared.base.require(shared.base.sha256(path) == info['sha256'], 'Embedding checksum differs')
    shutil.copy2(source/'download_manifest.json',directory/'download_manifest.json')
    return shared.evaluator.encode_labels(cache_root,labels)


def evaluate(root, settings):
    papers = shared.base.read_jsonl(root/'model_inputs/test_papers.jsonl')
    references = shared.base.read_jsonl(root/'evaluation_only/test_references.jsonl')
    shared.base.require(len(papers) == len(references) == 100, 'Evaluation requires exactly 100 test papers')
    records = {arm:[shared.load_record(root/f'results/{arm}/records/{p["paper_id"]}.json',
        settings['experiment_signature']) for p in papers] for arm in ARMS}
    labels = sorted({v for rows in records.values() for r in rows for f in shared.FACETS for v in r['facets'][f]}
        | {v for r in references for f in shared.FACETS for v in r['facets'][f]})
    vectors,embedding = embedding_vectors(root,labels)
    table = []
    for arm,rows in records.items():
        report = shared.score_rows(papers,rows,references,vectors)
        shared.base.write_json(root/f'results/{arm}/evaluation.json',report)
        shared.base.write_jsonl(root/f'results/{arm}/facets_silver.jsonl',[r['facets'] for r in rows])
        table.append(dict(arm=arm,**{k:report['micro'][k] for k in ('tp','fp','fn','precision','recall')},
            micro_f1=report['micro']['f1'],macro_f1=report['macro_f1'],
            **{f'{f}_f1':report['by_facet'][f]['f1'] for f in shared.FACETS},
            fallback_count=sum(r['fallback_used'] for r in rows),
            output_tokens=sum(r['usage'].get('output_tokens',0) for r in rows),
            generation_seconds=sum(r['generation_seconds'] for r in rows)))
    with (root/'results/experiment_table.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    lines=['# QLoRA paired evaluation: 100 held-out papers','',
        'AI reference; no pilot50 overlap; fresh base and adapter generation.','',
        '| Arm | Micro F1 | Macro F1 | TP | FP | FN |','|---|---:|---:|---:|---:|---:|']
    for row in table:
        lines.append(f'| {row["arm"]} | {100*row["micro_f1"]:.2f} | {100*row["macro_f1"]:.2f} | {row["tp"]} | {row["fp"]} | {row["fn"]} |')
    (root/'results/experiment_table.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    shared.base.write_json(root/'results/experiment_summary.json',dict(status='complete',table=table,settings=settings,
        embedding=embedding,threshold=0.85,reference_kind='ai',
        reference_sha256=shared.base.sha256(root/'evaluation_only/test_references.jsonl')))
    print('\n'.join(lines),flush=True)
    return table


def run(root, settings):
    import torch
    shared.base.require(torch.cuda.device_count() == 2, 'This kernel requires two Tesla T4 GPUs')
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
    subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--root',str(root),'--train'],env=env,check=True)
    seal_adapter(root,settings)
    processes=[]
    try:
        for gpu,arm in enumerate(ARMS):
            env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),
                '--root',str(root),'--worker',arm],env=env))
        for process in processes:
            shared.base.require(process.wait() == 0, 'Prediction worker failed; adapter and checkpoints retained')
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait()
    return evaluate(root,settings)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--train',action='store_true')
    parser.add_argument('--worker',choices=ARMS)
    args=parser.parse_args()
    settings=json.loads((args.root/'qlora_settings.json').read_text(encoding='utf-8'))
    if args.train:
        sys.path.insert(0,str(HERE))
        import train
        train.train(args.root,settings['training'])
    elif args.worker:
        predict(args.root,settings,args.worker)
    else:
        run(args.root,settings)
