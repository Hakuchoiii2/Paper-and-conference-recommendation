"""Verify the exact diagnostic payload and replay validation before reporting telemetry."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LEGACY = HERE.parent/'policy_ab/build/diagnostics/kaggle_probe_2026-10-18/probe.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('v2_collect_legacy', LEGACY)
generation = load('v2_collect_generation', HERE/'generation.py')
runner = legacy.get_runner(ROOT)
PAPERS = legacy.PAPERS
digest = legacy.digest


def code_paths():
    return {'probe.py': HERE/'probe.py', 'generation.py': HERE/'generation.py', 'legacy_probe.py': LEGACY}


def sources():
    return {p['paper_id']: p for p in runner.shared.base.read_jsonl(HERE.parent/'policy_ab/build/source_papers.jsonl')}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def collect(directory):
    directory = Path(directory)
    if not (directory/'probe_settings.json').is_file():
        directory = directory/'policy_probe_v2'
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    probe = read(directory/'probe_settings.json')
    unsigned = {k:v for k,v in probe.items() if k != 'signature'}
    require(digest(unsigned) == probe['signature'], 'Probe settings checksum differs')
    require(probe['version'] == 'exp_a_v2_decoding_probe_1'
        and probe['papers'] == list(PAPERS) and probe['decoders'] == ['greedy','sampling']
        and probe['training_performed'] is False
        and probe['limits'] == dict(max_new_tokens=1024,seconds_per_call=90)
        and probe['sampling'] == dict(temperature=0.7,top_p=0.8,top_k=20), 'Unexpected diagnostic configuration')
    require(probe['files'] == {name:hashlib.sha256(path.read_bytes()).hexdigest()
        for name,path in code_paths().items()}, 'Probe code differs from reviewed source')
    summary = read(directory/'run_summary.json')
    require(summary['status'] == 'complete' and summary['signature'] == probe['signature']
        and summary['worker_exit_codes'] == [0,0] and summary['saved_calls'] == summary['expected_calls'] == 12,
        'Expected complete 12-call probe')
    paths = sorted((directory/'results').rglob('P*.json'))
    require(len(paths) == 12, 'Expected exactly 12 diagnostic records')
    papers, records = sources(), {}
    with zipfile.ZipFile(HERE.parent/'policy_ab/build/input-dataset/policy_ab_bundle.zip.bin') as archive:
        frozen = json.loads(archive.read('settings.json'))
        require(probe['source_signature'] == frozen['signature'], 'Source signature differs')
        instruction_bytes = archive.read('instruction_new.txt')
        instruction = instruction_bytes.decode('utf-8').replace('\r\n','\n')
        for path in paths:
            envelope = read(path)
            r = envelope['record']
            require(digest(r) == envelope['record_sha256'], 'Record checksum differs: ' + str(path))
            key = (r['arm'], r['decoder'], r['paper_id'])
            require(key not in records and key[0] in ('base','adapter')
                and key[1] in ('greedy','sampling') and key[2] in PAPERS, 'Unexpected/duplicate record identity')
            require(r['probe_signature'] == probe['signature'] and r['source_signature'] == frozen['signature']
                and r['adapter_manifest_sha256'] == frozen['adapter_manifest_sha256'], 'Record run/adapter pairing differs')
            require(r['status'] == 'measured' and r['policy'] == 'new_v2_2', 'Unexpected record status/policy')
            expected_seed = frozen['generation']['seed'] + int(r['paper_id'][1:])*frozen['generation']['max_attempts']
            require(type(r.get('seed')) is int and r['seed'] == expected_seed, 'Record seed differs')
            require(r.get('stage') == 'draft', 'Record stage differs')
            runtime = r['runtime']
            require(runtime['model'] == frozen['model']['model'] and runtime['revision'] == frozen['model']['revision']
                and runtime['transformers'] == '4.57.6' and runtime['adapter_enabled'] is (r['arm'] == 'adapter')
                and runtime.get('quantization') == 'nf4_double_fp16'
                and runtime.get('enable_thinking') is False and runtime.get('use_cache') is True,
                'Runtime/model pairing differs')
            messages = legacy.first_messages(runner,papers[r['paper_id']],instruction,'new_v2_2')
            require(r['messages_sha256'] == digest(messages), 'Source/messages pairing differs')
            require(r['instruction_sha256'] == hashlib.sha256(instruction_bytes).hexdigest(), 'Instruction checksum differs')
            raw = r['raw_output_untrimmed'].strip()
            require(r['raw_output'] == (generation.json_prefix(raw) or raw), 'Raw prefix differs')
            stop = r['stop_reason']
            require(stop in ('eos','json_complete','duplicate_concept','time_budget','token_limit'), 'Unknown stop reason')
            bounded = stop in ('duplicate_concept','time_budget','token_limit')
            require(r['bounded_stop'] is bounded, 'Bounded stop was misreported')
            assessed = runner.assess_new(r['raw_output'], papers[r['paper_id']])
            errors = assessed['validation_errors'] + (['Generation stopped: ' + stop] if bounded else [])
            require(r['schema_valid'] is assessed['schema_valid'] and r['validation_errors'] == errors,
                'Replayed validation differs')
            require(type(r['generation_seconds']) in (int,float) and math.isfinite(r['generation_seconds'])
                and r['generation_seconds'] >= 0, 'Invalid generation time')
            require(all(type(r['usage'][k]) is int and r['usage'][k] > 0 for k in ('input_tokens','output_tokens')),
                'Invalid token usage')
            require(r['usage']['output_tokens'] <= probe['limits']['max_new_tokens'], 'Output token budget exceeded')
            records[key] = r
    groups = []
    for arm in ('base','adapter'):
        for decoder in ('greedy','sampling'):
            rows = [r for (a,d,p),r in records.items() if (a,d)==(arm,decoder)]
            require(len(rows)==3, 'Missing paired paper')
            groups.append(dict(arm=arm,decoder=decoder,papers=len(rows),
                schema_valid=sum(r['schema_valid'] for r in rows),
                error_free=sum(not r['validation_errors'] for r in rows),
                stop_reasons=dict(Counter(r['stop_reason'] for r in rows)),
                output_tokens=sum(r['usage']['output_tokens'] for r in rows),
                mean_seconds=round(statistics.mean(r['generation_seconds'] for r in rows),3),
                median_seconds=round(statistics.median(r['generation_seconds'] for r in rows),3)))
    return dict(verified_records=len(records),signature=probe['signature'],groups=groups,
        limitations='Three first-draft diagnostic papers, one seed; no semantic/F1 evaluation or trained v2 adapter')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = collect(args.directory)
    if args.output:
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
