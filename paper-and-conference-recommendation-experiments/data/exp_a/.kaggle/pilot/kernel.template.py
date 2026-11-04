"""Kaggle entrypoint; credentials and reference labels are not required."""
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from collections import Counter

BUNDLE_SHA256 = '__BUNDLE_SHA256__'
PROJECT = Path('/kaggle/working/exp_a_run')


def main():
    bundles = list(Path('/kaggle/input').rglob('input_bundle.zip.bin'))
    if len(bundles) != 1 or hashlib.sha256(bundles[0].read_bytes()).hexdigest() != BUNDLE_SHA256:
        raise RuntimeError('Kaggle input bundle missing, ambiguous or has the wrong hash')
    PROJECT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundles[0]) as archive:
        for member in archive.infolist():
            target = (PROJECT / member.filename).resolve()
            if PROJECT.resolve() not in target.parents or member.filename.startswith('/'):
                raise RuntimeError('Unsafe archive member')
        archive.extractall(PROJECT)
    os.environ['HF_HOME'] = '/tmp/exp_a_huggingface'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'transformers==4.57.6',
                    'accelerate==1.15.0', 'bitsandbytes==0.50.2'], check=True)
    sys.path.insert(0, str(PROJECT / 'data/exp_a'))
    import build_exp_a
    config = json.loads((PROJECT / 'data/exp_a/config_v3_pilot50.json').read_text(encoding='utf-8'))
    selection = json.loads((PROJECT / 'data/exp_a/pilot50/selection.json').read_text(encoding='utf-8'))
    if config['paper_ids'] != selection['paper_ids'] or len(config['paper_ids']) != 50:
        raise RuntimeError('Pilot selection/config mismatch')
    print(json.dumps(dict(pilot_size=50, seed=selection['seed'], protocol=config['extraction_protocol'],
                          prompt_version=config['prompt_version'], model=config['model'],
                          revision=config['revision'], do_sample=config['do_sample'],
                          gpu_workers=config['gpu_workers']), indent=2), flush=True)
    import torch
    gpu_names = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    if config['gpu_workers'] != 2 or len(gpu_names) != 2 or any('T4' not in name for name in gpu_names):
        raise RuntimeError(f'This run requires T4 x2; available GPUs: {gpu_names}')
    print(json.dumps(dict(parallelism='one model per GPU, disjoint paper ranges',
                          gpu_count=len(gpu_names), gpu_names=gpu_names)), flush=True)
    sys.path.insert(0, str(PROJECT / 'data/exp_a/.kaggle/pilot'))
    from dual_t4 import run_workers
    started = time.monotonic()
    manifest = run_workers(PROJECT, config, gpu_count=len(gpu_names))
    build_exp_a.check_outputs(PROJECT, config)
    annotations = build_exp_a.read_jsonl(PROJECT / config['output_dir'] / 'annotation_metadata.jsonl')
    source_counts = Counter(row['source_quality']['status'] for row in annotations)
    report = dict(status=manifest['status'], count=manifest['count'], expected=50, seed=selection['seed'],
                  prompt_version=config['prompt_version'],
                  gpu_workers=config['gpu_workers'], gpu_count=len(gpu_names), gpu_names=gpu_names,
                  source_parts=manifest.get('source_parts', []),
                  dataset_resource_filter=config.get('dataset_resource_filter', False),
                  filtered_dataset_item_count=sum(len(row.get('postprocessing', {}).get('removed', [])) for row in annotations),
                  validation_passed_count=sum(row['validation_passed'] for row in annotations),
                  fallback_count=sum(row['fallback_used'] for row in annotations),
                  source_quality_counts=dict(source_counts),
                  source_flagged_count=sum(bool(row['source_quality']['issues']) for row in annotations),
                  failed_annotations=manifest['failed_annotations'], missing_ids=manifest['missing_ids'],
                  seconds=round(time.monotonic()-started, 2), semantic_evaluation='not run in Kaggle; evaluate locally with frozen reference after completion')
    (Path('/kaggle/working') / 'pilot_run_summary.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
    if manifest['count'] != 50 or manifest['status'] != 'complete':
        raise RuntimeError('Pilot incomplete; completed papers are checkpointed, failed papers remain missing')


if __name__ == '__main__':
    main()
