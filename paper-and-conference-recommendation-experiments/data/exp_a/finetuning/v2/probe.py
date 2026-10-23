"""Twelve bounded draft calls: base/adapter x greedy/sampling x three fixed papers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import generation
import legacy_probe as legacy

DECODERS = ('greedy', 'sampling')


def worker(root, adapter, arm):
    runner = legacy.get_runner(root)
    settings = json.loads((root/'settings.json').read_text(encoding='utf-8'))
    papers = {p['paper_id']: p for p in runner.verify_inputs(root, settings, adapter)}
    output = root.parent.parent/'policy_probe_v2'
    probe = json.loads((output/'probe_settings.json').read_text(encoding='utf-8'))
    config = dict(settings['model'])
    if arm == 'adapter':
        config['adapter_path'] = str(adapter)
    model, tokenizer, runtime = generation.load_model(config, runner.shared)
    instruction = (root/'instruction_new.txt').read_text(encoding='utf-8')
    generators = {name: generation.build_generator(model, tokenizer,
        dict(do_sample=name == 'sampling', **probe['limits'])) for name in DECODERS}
    for pid in legacy.PAPERS:
        messages = legacy.first_messages(runner, papers[pid], instruction, 'new_v2_2')
        seed = settings['generation']['seed'] + int(pid[1:])*settings['generation']['max_attempts']
        for decoder in DECODERS:
            print(json.dumps(dict(event='call_start', arm=arm, decoder=decoder, paper_id=pid)), flush=True)
            raw, stats = generators[decoder](messages, seed)
            assessed = runner.assess_new(raw, papers[pid])
            errors = list(assessed['validation_errors'])
            if stats['bounded_stop']:
                errors.append('Generation stopped: ' + stats['stop_reason'])
            entry = dict(arm=arm, decoder=decoder, policy='new_v2_2', paper_id=pid, seed=seed,
                stage='draft', status='measured', runtime=runtime, probe_signature=probe['signature'],
                messages_sha256=legacy.digest(messages), instruction_sha256=hashlib.sha256(
                    (root/'instruction_new.txt').read_bytes()).hexdigest(),
                adapter_manifest_sha256=settings['adapter_manifest_sha256'],
                source_signature=settings['signature'], raw_output=raw,
                schema_valid=assessed['schema_valid'], validation_errors=errors, **stats)
            legacy.write_json(output/f'results/{arm}/{decoder}/{pid}.json',
                dict(record=entry, record_sha256=legacy.digest(entry)))
            print(json.dumps({k: entry[k] for k in ('arm', 'decoder', 'paper_id', 'stop_reason',
                'generation_seconds', 'usage', 'schema_valid', 'validation_errors')}), flush=True)


def run(root, adapter):
    import torch
    runner = legacy.get_runner(root)
    settings = json.loads((root/'settings.json').read_text(encoding='utf-8'))
    runner.verify_inputs(root, settings, adapter)
    if torch.cuda.device_count() != 2:
        raise ValueError('Expected two T4 GPUs')
    output = root.parent.parent/'policy_probe_v2'
    probe = dict(version='exp_a_v2_decoding_probe_1', papers=legacy.PAPERS,
        decoders=DECODERS, limits=dict(max_new_tokens=1024, seconds_per_call=90),
        source_signature=settings['signature'], training_performed=False,
        sampling=dict(temperature=0.7, top_p=0.8, top_k=20),
        files={name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
               for name in ('probe.py', 'generation.py', 'legacy_probe.py')},
        purpose='format/repetition diagnosis, not semantic/F1 evaluation')
    probe['signature'] = legacy.digest(probe)
    legacy.write_json(output/'probe_settings.json', probe)
    processes = []
    started = time.monotonic()
    try:
        for gpu, arm in enumerate(('base', 'adapter')):
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                '--root', str(root), '--adapter', str(adapter), '--worker', arm], env=env))
        while any(p.poll() is None for p in processes):
            if time.monotonic() - started > 1500:
                break
            time.sleep(1)
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
                p.wait()
    records = []
    for path in sorted((output/'results').rglob('P*.json')):
        envelope = json.loads(path.read_text(encoding='utf-8'))
        if envelope['record_sha256'] != legacy.digest(envelope['record']):
            raise ValueError('Changed diagnostic record')
        records.append(envelope['record'])
    complete = len(records) == 12 and all(p.returncode == 0 for p in processes)
    summary = dict(status='complete' if complete else 'incomplete', signature=probe['signature'],
        saved_calls=len(records), expected_calls=12, worker_exit_codes=[p.returncode for p in processes],
        results=[{k: r[k] for k in ('arm', 'decoder', 'paper_id', 'stop_reason', 'generation_seconds',
            'usage', 'schema_valid', 'validation_errors', 'bounded_stop')} for r in records])
    legacy.write_json(output/'run_summary.json', summary)
    print(json.dumps(summary), flush=True)
    if not complete:
        raise RuntimeError('Probe incomplete; preserve partial results')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--worker', choices=('base', 'adapter'))
    args = parser.parse_args()
    root, adapter = (args.root, args.adapter) if args.root else legacy.prepare_project()
    (worker(root, adapter, args.worker) if args.worker else run(root, adapter))
