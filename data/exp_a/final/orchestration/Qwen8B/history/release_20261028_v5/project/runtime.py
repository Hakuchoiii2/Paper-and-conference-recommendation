"""Train first; select by validation V-recall F1; then perform paired test."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify(root):
    settings = read(root / 'settings.json')
    unsigned = {k: v for k, v in settings.items() if k != 'signature'}
    require(hashlib.sha256(json.dumps(unsigned, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == settings['signature'], 'Settings signature differs')
    for name, expected in settings['files'].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root.resolve()) and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Changed input: ' + name)
    splits = read(root / 'splits.json')
    require(splits == settings['splits'] and [len(splits[s]) for s in ('train', 'valid', 'test')] == [280, 60, 60], 'Wrong split sizes')
    require(len(set(sum(splits.values(), []))) == 400, 'Overlapping split IDs')
    for split in ('train', 'valid'):
        examples = rows(root / f'training_data/{split}.jsonl')
        require([x['paper_id'] for x in examples] == splits[split], 'SFT split differs')
    require(not (root / 'training_data/test.jsonl').exists(), 'Test SFT is forbidden')
    return settings


def policy(root):
    return load('gold400_trial_frozen_policy', root / 'gold_policy.py')


def instruction(root, settings):
    result = '\n\n'.join((root / settings['generation'][k]).read_text(encoding='utf-8') for k in ('guideline', 'prompt'))
    require(hashlib.sha256(result.encode()).hexdigest() == settings['instruction_sha256'], 'Instruction differs')
    return result


def prediction_signature(p, settings, split, arm, adapter):
    weights = hashlib.sha256((adapter / 'adapter_model.safetensors').read_bytes()).hexdigest() if adapter else None
    return p.digest(dict(settings=settings['signature'], split=split, arm=arm, adapter_sha256=weights))


def worker(root, settings, split, arm, adapter, index):
    p = policy(root)
    shared = p.load_shared(root)
    papers = rows(root / f'model_inputs/{split}.jsonl')
    require([x['paper_id'] for x in papers] == settings['splits'][split], 'Prediction cohort differs')
    require(all(set(x) == {'paper_id', 'title', 'abstract'} for x in papers), 'Unexpected model input fields')
    config = dict(settings['generation'])
    if adapter:
        config['adapter_path'] = str(adapter)
    signature = prediction_signature(p, settings, split, arm, adapter)
    work = root / f'results/{split}/{arm}'
    todo = papers[index::2]
    missing = [x for x in todo if not (work / 'records' / (x['paper_id'] + '.json')).exists()]
    generate, runtime = shared.load_generator(config) if missing else (None, None)
    if runtime is not None:
        runtime.update(adapter_enabled=bool(adapter), adapter_sha256=hashlib.sha256((adapter / 'adapter_model.safetensors').read_bytes()).hexdigest() if adapter else None)
    text = instruction(root, settings)
    for paper in todo:
        path = work / 'records' / (paper['paper_id'] + '.json')
        if path.exists():
            record = shared.load_record(path, signature)
            require(record['paper_id'] == paper['paper_id'] and record['source_sha256'] == p.digest(paper), 'Cached prediction identity differs')
            continue
        result = p.annotate_fresh(shared, paper, text, config, runtime, generate, work, signature=signature)
        result.update(training_performed=bool(adapter), arm=arm, adapter_enabled=bool(adapter),
                      adapter_sha256=runtime['adapter_sha256'])
        shared.save_record(path, result, signature)
        print(f'{split}/{arm}/gpu{index}: {paper["paper_id"]}, fallback={result["fallback_used"]}', flush=True)


def score(root, settings, split, arm, adapter):
    p = policy(root)
    shared = p.load_shared(root)
    papers = rows(root / f'model_inputs/{split}.jsonl')
    signature = prediction_signature(p, settings, split, arm, adapter)
    work = root / f'results/{split}/{arm}'
    predictions = [shared.load_record(work / 'records' / (paper['paper_id'] + '.json'), signature) for paper in papers]
    require([r['paper_id'] for r in predictions] == settings['splits'][split], 'Missing/unpaired predictions')
    write(work / 'prediction_seal.json', dict(signature=signature, records={paper['paper_id']: hashlib.sha256((work / 'records' / (paper['paper_id'] + '.json')).read_bytes()).hexdigest() for paper in papers}))
    # Test references are parsed only here, after the final test predictions are sealed.
    references = rows(root / f'evaluation_only/{split}.jsonl')
    require({r['paper_id'] for r in references} == set(settings['splits'][split]), 'Reference cohort differs')
    labels = sorted({v for r in predictions + references for f in shared.FACETS for v in r['facets'][f]})
    vectors, embedding = shared.evaluator.encode_labels(root, labels)
    result = shared.score_rows(papers, predictions, references, vectors, threshold=settings['threshold'])
    result.update(split=split, arm=arm, signature=signature, embedding=embedding,
                  paper_count=len(papers), fallback=sum(r['fallback_used'] for r in predictions),
                  fresh_calls=sum(r['new_cost']['calls'] for r in predictions),
                  input_tokens=sum(r['usage']['input_tokens'] for r in predictions),
                  output_tokens=sum(r['usage']['output_tokens'] for r in predictions))
    write(work / 'evaluation.json', result)
    print(json.dumps(dict(split=split, arm=arm, **result['micro'])), flush=True)
    return result


def command(root, *args, gpu='0'):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, WORLD_SIZE='1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    return subprocess.Popen([sys.executable, '-B', str(root / 'runtime.py'), *map(str, args)], cwd=root, env=env)


def predict_and_score(root, settings, split, arm, adapter):
    args = ['--split', split, '--arm', arm]
    if adapter:
        args += ['--adapter', adapter]
    processes = [command(root, '--worker', index, *args, gpu=str(index)) for index in (0, 1)]
    try:
        while any(p.poll() is None for p in processes):
            require(all(p.poll() in (None, 0) for p in processes), 'Prediction worker failed')
            time.sleep(1)
        require(all(p.returncode == 0 for p in processes), 'Prediction worker failed')
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
                p.wait()
    require(command(root, '--score', *args).wait() == 0, 'Scoring failed')
    return read(root / f'results/{split}/{arm}/evaluation.json')


def choose_checkpoint(evaluations):
    require(bool(evaluations), 'No validation checkpoints')
    require(all(r['split'] == 'valid' for r in evaluations), 'Checkpoint selection must use validation only')
    return max(evaluations, key=lambda r: (r['micro']['f1'], r['micro']['recall'], -int(r['arm'].split('-')[-1])))


def train(root, settings):
    helper = load('gold400_trial_existing_trainer', root / 'train.py')
    # The legacy helper exports a provisional lowest-loss adapter. Final selection below uses F1.
    metadata = helper.train(root, settings['training'])
    write(root / 'results/training_summary.json', metadata)


def run(root, settings):
    started = time.monotonic()
    write(root / 'results/run_status.json', dict(status='training', signature=settings['signature']))
    require(command(root, '--train').wait() == 0, 'Training failed; checkpoints retained')
    checkpoints = sorted((root / 'train_state').glob('checkpoint-*'), key=lambda x: int(x.name.split('-')[-1]))
    require(len(checkpoints) == 3, 'Expected all three epoch checkpoints')
    validation = []
    for checkpoint in checkpoints:
        write(root / 'results/run_status.json', dict(status='validation', checkpoint=checkpoint.name, signature=settings['signature']))
        validation.append(predict_and_score(root, settings, 'valid', checkpoint.name, checkpoint))
    chosen = choose_checkpoint(validation)
    selection = dict(status='selected', split='valid', checkpoint=chosen['arm'], micro=chosen['micro'],
                     criterion=settings['checkpoint_selection'], signature=settings['signature'])
    write(root / 'results/checkpoint_selection.json', selection)
    destination = root / 'adapter'
    destination.mkdir(exist_ok=False)
    for path in (root / 'provisional_adapter').iterdir():
        if path.is_file() and path.name != 'training_metadata.json':
            shutil.copyfile(path, destination / path.name)
    for name in ('adapter_model.safetensors', 'adapter_config.json'):
        shutil.copyfile(root / 'train_state' / chosen['arm'] / name, destination / name)
    metadata = read(root / 'results/training_summary.json')
    metadata['provisional_best_dev_loss'] = metadata.pop('best_dev_loss')
    metadata.update(checkpoint_selection=settings['checkpoint_selection'], best_checkpoint=chosen['arm'],
                    validation_micro=chosen['micro'], human_review_status='accepted', label_source='human_gold')
    metadata['files'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir() if p.is_file()}
    write(destination / 'training_metadata.json', metadata)
    write(root / 'results/run_status.json', dict(status='test', selected_checkpoint=chosen['arm'], signature=settings['signature']))
    table = []
    for arm, adapter in (('base-V-recall', None), ('gold400-QLoRA-V-recall', destination)):
        result = predict_and_score(root, settings, 'test', arm, adapter)
        table.append(dict(arm=arm, **result['micro'], macro_f1=result['macro_f1'],
                          by_facet=result['by_facet'], fallback=result['fallback'], fresh_calls=result['fresh_calls']))
    summary = dict(status='complete', signature=settings['signature'], counts={k: len(v) for k, v in settings['splits'].items()},
                   selected_checkpoint=chosen['arm'], validation=selection, table=table,
                   training_performed=True, gold_sha256=settings['gold_sha256'], wall_seconds=time.monotonic() - started,
                   limitation=settings['limitation'])
    write(root / 'results/experiment_summary.json', summary)
    lines = ['# Gold400 QLoRA: paired V-recall test', '', settings['limitation'], '',
             '| Arm | Precision | Recall | F1 | Macro F1 | Fallback |', '|---|---:|---:|---:|---:|---:|']
    for row in table:
        lines.append(f'| {row["arm"]} | {100*row["precision"]:.4f} | {100*row["recall"]:.4f} | {100*row["f1"]:.4f} | {100*row["macro_f1"]:.4f} | {row["fallback"]} |')
    (root / 'results/experiment_table.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    write(root / 'results/run_status.json', dict(status='complete', signature=settings['signature']))
    print('\n'.join(lines), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', action='store_true')
    parser.add_argument('--worker', type=int, choices=(0, 1))
    parser.add_argument('--score', action='store_true')
    parser.add_argument('--split', choices=('valid', 'test'))
    parser.add_argument('--arm')
    parser.add_argument('--adapter', type=Path)
    args = parser.parse_args()
    settings = verify(ROOT)
    if args.train:
        train(ROOT, settings)
    elif args.worker is not None:
        worker(ROOT, settings, args.split, args.arm, args.adapter, args.worker)
    elif args.score:
        score(ROOT, settings, args.split, args.arm, args.adapter)
    else:
        run(ROOT, settings)
