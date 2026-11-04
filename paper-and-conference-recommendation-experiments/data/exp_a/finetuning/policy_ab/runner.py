"""Inference only: frozen QLoRA v1 with old pipeline versus v2.2 policy/schema."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'data/exp_a/.kaggle/matrix'))
sys.path.insert(0, str(ROOT / 'data/exp_a/finetuning/label_revision_v2'))
import matrix as shared
import schema as multi

ARMS = ('old_v3_7', 'new_v2_2')


def assess_new(raw, paper):
    empty = dict(paper_id=paper['paper_id'], **{f: [] for f in shared.FACETS})
    selected = dict(paper_id=paper['paper_id'], **{f: [] for f in shared.FACETS})
    errors, schema_valid = [], True
    try:
        value = json.loads(raw)
        shared.base.require(isinstance(value, dict) and set(value) == set(empty)
                            and value['paper_id'] == paper['paper_id'], 'Wrong paper_id/facet keys')
        shared.base.require(all(isinstance(value[f], list) for f in shared.FACETS), 'Facets must be lists')
    except (ValueError, TypeError, KeyError) as error:
        return dict(selection=selected, evidence=multi.ground_response(selected, paper),
                    validation_errors=[str(error)], schema_valid=False)
    for facet in shared.FACETS:
        for index, item in enumerate(value[facet]):
            trial = dict(selected, **{facet: selected[facet] + [item]})
            try:
                multi.ground_response(trial, paper)
                selected = trial
            except (ValueError, TypeError, KeyError) as error:
                message = str(error)
                schema_valid &= message == 'Concept must use selected source words in source order'
                errors.append(f'{facet}[{index}]: {message}')
    return dict(selection=selected, evidence=multi.ground_response(selected, paper),
                validation_errors=errors, schema_valid=bool(schema_valid))


def annotate_new(paper, instruction, config, generate):
    source = dict(paper_id=paper['paper_id'], evidence_options={
        k: v['evidence'] for k, v in shared.base.evidence_options(paper).items()})
    original = [dict(role='system', content=instruction + '\nReturn JSON only. Schema: '
                     + json.dumps(multi.SCHEMA, separators=(',', ':'))),
                dict(role='user', content=json.dumps(source, ensure_ascii=False))]
    attempts, results, usage = [], [], Counter()
    shared.base.require(config['max_attempts'] >= 2, 'A draft and mandatory review are required')
    for index in range(config['max_attempts']):
        messages = list(original)
        if attempts:
            messages += [dict(role='assistant', content=attempts[-1]['raw_output']),
                dict(role='user', content='Review the draft against ALL original source sentences and the system policy. '
                    'Preserve supported labels; recover missing objectives, actually used methods, named resources, '
                    'introduced artifacts and findings. Check roles, independent concepts, antecedents, comparisons, '
                    'conditions, quantities, negation and caveats. Use evidence_ids arrays in source order. '
                    'Return the complete corrected JSON only. Validation feedback:\n'
                    + '\n'.join(attempts[-1]['validation_errors']))]
        seed = config['seed'] + int(paper['paper_id'][1:]) * config['max_attempts'] + index
        raw, stats = generate(messages, seed)
        assessed = assess_new(raw, paper)
        attempts.append(dict(attempt=index + 1, stage='extract' if index == 0 else 'review',
            seed=seed, raw_output=raw, schema_valid=assessed['schema_valid'],
            validation_errors=assessed['validation_errors'], **stats))
        results.append(assessed)
        usage.update(stats.get('usage', {}))
        if index > 0 and not assessed['validation_errors']:
            break
    valid_reviews = [i for i in range(1, len(results)) if not results[i]['validation_errors']]
    chosen = valid_reviews[-1] if valid_reviews else min(range(len(results)), key=lambda i: (
        -sum(len(results[i]['selection'][f]) for f in shared.FACETS),
        not results[i]['schema_valid'], len(results[i]['validation_errors']), -i))
    selected = results[chosen]
    return dict(paper_id=paper['paper_id'], selection=selected['selection'], evidence=selected['evidence'],
        facets=dict(paper_id=paper['paper_id'], **{f: [x['concept'] for x in selected['selection'][f]] for f in shared.FACETS}),
        audit=dict(attempts=attempts, selected_attempt=chosen + 1, validation_errors=selected['validation_errors']),
        fallback_used=not bool(valid_reviews), usage=dict(usage),
        generation_seconds=sum(a.get('generation_seconds', 0) for a in attempts))


def verify_inputs(root, settings, adapter):
    unsigned = dict(settings)
    signature = unsigned.pop('signature')
    shared.base.require(shared.digest(unsigned) == signature, 'Changed experiment settings')
    for name, expected in settings['files'].items():
        path = (root / name).resolve()
        shared.base.require(root.resolve() in path.parents and shared.base.sha256(path) == expected,
                            'Changed/unsafe input: ' + name)
    shared.base.require(shared.base.sha256(adapter / 'adapter_manifest.json') == settings['adapter_manifest_sha256'],
                        'Different adapter manifest')
    manifest = json.loads((adapter / 'adapter_manifest.json').read_text(encoding='utf-8'))
    shared.base.require(manifest['status'] == 'complete' and manifest['base_model'] == settings['model']['model']
        and manifest['base_revision'] == settings['model']['revision'], 'Adapter/model identity differs')
    for name, expected in manifest['files'].items():
        path = (adapter / name).resolve()
        shared.base.require(adapter.resolve() in path.parents and shared.base.sha256(path) == expected,
                            'Changed adapter payload: ' + name)
    papers = shared.base.read_jsonl(root / 'model_inputs/papers.jsonl')
    shared.base.require([p['paper_id'] for p in papers] == settings['paper_ids'], 'Changed paper cohort')
    return papers


def load_checkpoint(root, settings, arm, paper_id):
    path = root / 'results' / arm / 'records' / (paper_id + '.json')
    record = shared.load_record(path, settings['signature'])
    instruction = 'instruction_old.txt' if arm == ARMS[0] else 'instruction_new.txt'
    shared.base.require(record.get('paper_id') == paper_id and record.get('arm') == arm,
                        'Checkpoint arm/paper identity differs')
    shared.base.require(record.get('adapter_manifest_sha256') == settings['adapter_manifest_sha256']
        and record.get('instruction_sha256') == settings['files'][instruction], 'Checkpoint adapter/prompt identity differs')
    return record


def worker(root, settings, adapter, arm):
    papers = verify_inputs(root, settings, adapter)
    directory = root / 'results' / arm
    directory.mkdir(parents=True, exist_ok=True)
    config = dict(settings['generation'], **settings['model'], adapter_path=str(adapter))
    generate, runtime = shared.load_generator(config)
    instruction = (root / ('instruction_old.txt' if arm == ARMS[0] else 'instruction_new.txt')).read_text(encoding='utf-8')
    for paper in papers:
        path = directory / 'records' / (paper['paper_id'] + '.json')
        if path.exists():
            load_checkpoint(root, settings, arm, paper['paper_id'])
            continue
        if arm == ARMS[0]:
            evidence, audit = shared.v3.annotate(paper, instruction, config, runtime, generate, directory / 'last_failure.json')
            record = dict(paper_id=paper['paper_id'], evidence=evidence, audit=audit,
                facets=dict(paper_id=paper['paper_id'], **{f: [x['concept'] for x in evidence[f]] for f in shared.FACETS}),
                usage=audit['usage'], generation_seconds=audit['generation_seconds'], fallback_used=audit['fallback_used'])
        else:
            record = annotate_new(paper, instruction, config, generate)
        record.update(arm=arm, runtime=runtime, adapter_manifest_sha256=settings['adapter_manifest_sha256'],
                      instruction_sha256=shared.base.sha256(root / ('instruction_old.txt' if arm == ARMS[0] else 'instruction_new.txt')))
        shared.save_record(path, record, settings['signature'])
        print(f'{arm}: completed {paper["paper_id"]}', flush=True)


def run(root, settings, adapter):
    import torch
    verify_inputs(root, settings, adapter)
    shared.base.require(torch.cuda.device_count() == 2, 'Expected two T4 GPUs')
    processes = []
    try:
        for gpu, arm in enumerate(ARMS):
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                '--root', str(root), '--adapter', str(adapter), '--worker', arm], env=env))
        for process in processes:
            shared.base.require(process.wait() == 0, 'Inference worker failed; checkpoints retained')
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait()
    summary = dict(status='complete', signature=settings['signature'], paper_count=len(settings['paper_ids']),
        training_performed=False, reference_status='not_loaded; source-first reference sealing required before opening predictions',
        arms={})
    for arm in ARMS:
        rows = [load_checkpoint(root, settings, arm, pid)
                for pid in settings['paper_ids']]
        summary['arms'][arm] = dict(papers=len(rows), fallback=sum(r['fallback_used'] for r in rows),
            input_tokens=sum(r['usage'].get('input_tokens', 0) for r in rows),
            output_tokens=sum(r['usage'].get('output_tokens', 0) for r in rows),
            generation_seconds=sum(r['generation_seconds'] for r in rows))
    shared.base.write_json(root / 'run_summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--adapter', type=Path, required=True)
    parser.add_argument('--worker', choices=ARMS)
    args = parser.parse_args()
    settings = json.loads((args.root / 'settings.json').read_text(encoding='utf-8'))
    if args.worker:
        worker(args.root, settings, args.adapter, args.worker)
    else:
        run(args.root, settings, args.adapter)
