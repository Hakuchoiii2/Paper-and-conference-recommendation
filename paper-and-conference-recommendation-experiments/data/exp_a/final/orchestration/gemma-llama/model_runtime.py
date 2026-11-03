"""One-model QLoRA run around the accepted gold400 runtime."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import time


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen(root):
    old = load('comparison_frozen_runtime', root/'frozen_runtime.py')
    compat = load('comparison_compat', root/'compat.py')
    original_policy = old.policy
    def policy(directory):
        p = original_policy(directory)
        original_shared = p.load_shared
        def shared(source):
            value = original_shared(source)
            value.load_generator = lambda config: compat.load_generator(config, value.install_attention)
            return value
        p.load_shared = shared
        return p
    old.policy = policy
    return old, compat


def recover_run_directory(root, check, state_dir, signature, adapter_dir, resume=None, reuse_completed=False):
    state_dir, adapter_dir = Path(state_dir), Path(adapter_dir)
    marker = state_dir/'run_manifest.json'
    if marker.is_file():
        value = json.loads(marker.read_text(encoding='utf-8'))
        if value.get('status') == 'running' and value.get('signature') == signature:
            def preserve(path):
                # Only rename the two owned output directories inside this model project.
                if path.resolve().parent != root.resolve() or path.name not in ('train_state', 'provisional_adapter'):
                    raise ValueError('Recovery path escapes model project')
                index = 1
                while path.with_name(path.name+f'.interrupted-{index}').exists():
                    index += 1
                path.rename(path.with_name(path.name+f'.interrupted-{index}'))
            if resume is not None:
                # Verify checkpoint identity and all hashes before moving any partial export.
                check(state_dir, signature, root/'_no_adapter_for_resume_check', resume, False)
            else:
                preserve(state_dir)
            if adapter_dir.exists() and any(adapter_dir.iterdir()):
                preserve(adapter_dir)
    return check(state_dir, signature, adapter_dir, resume, reuse_completed)


def train(root, settings, old, compat):
    helper = old.load('comparison_trainer', root/'train.py')
    helper.encode_example = compat.encode_example
    config = dict(settings['training'], reuse_completed=True)
    state = root/config['checkpoint_dir']
    if (state/'run_manifest.json').is_file():
        manifest = old.read(state/'run_manifest.json')
        if manifest.get('status') != 'complete':
            checkpoints = sorted(state.glob('checkpoint-*'), key=lambda p: int(p.name.split('-')[-1]), reverse=True)
            complete = [p for p in checkpoints if all((p/name).is_file() for name in (*helper.RESUME_FILES, 'checkpoint_manifest.json'))]
            if complete:
                config['resume_from_checkpoint'] = str(complete[0].relative_to(root))
    original_check = helper.check_run_directory
    def check(state_dir, signature, adapter_dir, resume=None, reuse_completed=False):
        return recover_run_directory(root, original_check, state_dir, signature, adapter_dir, resume, reuse_completed)
    helper.check_run_directory = check
    metadata = helper.train(root, config)
    old.write(root/'results/training_summary.json', metadata)


def select_adapter(root, settings, chosen, old):
    destination = root/'adapter'
    checkpoint = root/'train_state'/chosen['arm']
    metadata = old.read(root/'results/training_summary.json')
    metadata['provisional_best_dev_loss'] = metadata.pop('best_dev_loss')
    metadata.update(checkpoint_selection=settings['checkpoint_selection'], best_checkpoint=chosen['arm'],
                    validation_micro=chosen['micro'], human_review_status='accepted', label_source='human_gold')
    if destination.exists():
        saved = old.read(destination/'training_metadata.json')
        old.require(saved['best_checkpoint'] == chosen['arm'] and saved['signature'] == metadata['signature'], 'Selected adapter identity differs')
        for name, expected in saved['files'].items():
            old.require(hashlib.sha256((destination/name).read_bytes()).hexdigest() == expected, 'Selected adapter checksum differs')
        return destination
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        stage = Path(temporary)/'adapter'
        shutil.copytree(root/'provisional_adapter', stage)
        for name in ('adapter_model.safetensors', 'adapter_config.json'):
            shutil.copyfile(checkpoint/name, stage/name)
        metadata['files'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in stage.iterdir() if p.is_file() and p.name != 'training_metadata.json'}
        old.write(stage/'training_metadata.json', metadata)
        stage.rename(destination)
    return destination


def run(root, settings, old):
    started = time.monotonic()
    old.write(root/'results/run_status.json', dict(status='training', signature=settings['signature']))
    old.require(old.command(root, '--train').wait() == 0, 'Training failed; checkpoints retained')
    checkpoints = sorted((root/'train_state').glob('checkpoint-*'), key=lambda p: int(p.name.split('-')[-1]))
    old.require(len(checkpoints) == 3, 'Expected all three epoch checkpoints')
    validation = []
    for checkpoint in checkpoints:
        old.write(root/'results/run_status.json', dict(status='validation', checkpoint=checkpoint.name, signature=settings['signature']))
        validation.append(old.predict_and_score(root, settings, 'valid', checkpoint.name, checkpoint))
    chosen = old.choose_checkpoint(validation)
    selection = dict(status='selected', split='valid', checkpoint=chosen['arm'], micro=chosen['micro'],
                     criterion=settings['checkpoint_selection'], signature=settings['signature'])
    old.write(root/'results/checkpoint_selection.json', selection)
    adapter = select_adapter(root, settings, chosen, old)
    old.write(root/'results/run_status.json', dict(status='test', signature=settings['signature']))
    result = old.predict_and_score(root, settings, 'test', 'QLoRA-V-recall', adapter)
    p = old.policy(root)
    shared = p.load_shared(root)
    signature = old.prediction_signature(p, settings, 'test', 'QLoRA-V-recall', adapter)
    work = root/'results/test/QLoRA-V-recall'
    records = [shared.load_record(work/'records'/(pid+'.json'), signature) for pid in settings['splits']['test']]
    shared.base.write_jsonl(work/'facets_silver.jsonl', [r['facets'] for r in records])
    table = [dict(arm='QLoRA-V-recall', **result['micro'], macro_f1=result['macro_f1'],
                  by_facet=result['by_facet'], fallback=result['fallback'], fresh_calls=result['fresh_calls'])]
    summary = dict(status='complete', signature=settings['signature'], model=settings['training']['model'],
        revision=settings['training']['revision'], counts={k: len(v) for k,v in settings['splits'].items()},
        selected_checkpoint=chosen['arm'], validation=selection, table=table, training_performed=True,
        gold_sha256=settings['gold_sha256'], wall_seconds_this_invocation=time.monotonic()-started,
        limitation=settings['limitation'])
    old.write(root/'results/experiment_summary.json', summary)
    (root/'results/experiment_table.md').write_text(
        '| Model | Precision | Recall | F1 | Macro F1 |\n|---|---:|---:|---:|---:|\n'
        + f'| {root.name} | {result["micro"]["precision"]:.6f} | {result["micro"]["recall"]:.6f} | {result["micro"]["f1"]:.6f} | {result["macro_f1"]:.6f} |\n', encoding='utf-8')
    old.write(root/'results/run_status.json', dict(status='complete', signature=settings['signature']))


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', action='store_true')
    parser.add_argument('--worker', type=int, choices=(0, 1))
    parser.add_argument('--score', action='store_true')
    parser.add_argument('--split', choices=('valid', 'test'))
    parser.add_argument('--arm')
    parser.add_argument('--adapter', type=Path)
    args = parser.parse_args()
    old, compat = frozen(root)
    settings = old.verify(root)
    if args.train:
        train(root, settings, old, compat)
    elif args.worker is not None:
        old.worker(root, settings, args.split, args.arm, args.adapter, args.worker)
    elif args.score:
        old.score(root, settings, args.split, args.arm, args.adapter)
    else:
        import torch
        old.require(torch.cuda.device_count() == 2, 'Generation requires exactly two CUDA GPUs')
        run(root, settings, old)


if __name__ == '__main__':
    main()
