"""Private, bounded first-draft probe: base/adapter x old/new policy x three papers."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')
PAPERS = ('P000962', 'P001892', 'P000151')
POLICIES = ('old_v3_7', 'new_v2_2')
BUNDLE_SHA256 = '38e77ec72990909c9dfe9dae3be4421af4e1c2313adb0d8904a6964399032b35'
LIMITS = dict(max_new_tokens=1024, seconds_per_call=90, worker_seconds=1500)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def duplicate_item(text):
    """Recognize identical complete objects within one facet, even before JSON closes."""
    decoder = json.JSONDecoder()
    def space(index):
        while index < len(text) and text[index].isspace():
            index += 1
        return index
    try:
        index = space(0)
        if text[index] != '{':
            return None
        index += 1
        while True:
            key, index = decoder.raw_decode(text, space(index))
            index = space(index)
            if not isinstance(key, str) or text[index] != ':':
                return None
            index = space(index + 1)
            if key in FACETS and text[index] == '[':
                seen = Counter()
                index = space(index + 1)
                while text[index] != ']':
                    item, index = decoder.raw_decode(text, index)
                    if isinstance(item, dict) and 'concept' in item:
                        fingerprint = digest(item)
                        seen[fingerprint] += 1
                        if seen[fingerprint] >= 2:
                            return dict(facet=key, count=seen[fingerprint])
                    index = space(index)
                    if text[index] == ',':
                        index = space(index + 1)
                    elif text[index] != ']':
                        return None
                index += 1
            else:
                _, index = decoder.raw_decode(text, index)
            index = space(index)
            if text[index] != ',':
                return None
            index = space(index + 1)
    except (ValueError, IndexError, TypeError):
        return None


class BudgetStop:
    def __init__(self, tokenizer, input_length, seconds):
        self.tokenizer, self.input_length = tokenizer, input_length
        self.seconds, self.started = seconds, time.monotonic()
        self.reason, self.duplicate, self.checked_tokens = None, None, 0

    def __call__(self, input_ids, scores, **kwargs):
        if time.monotonic() - self.started >= self.seconds:
            self.reason = 'time_budget'
            return True
        count = input_ids.shape[-1] - self.input_length
        if count - self.checked_tokens >= 16:
            self.checked_tokens = count
            text = self.tokenizer.decode(input_ids[0, self.input_length:], skip_special_tokens=True)
            self.duplicate = duplicate_item(text)
            if self.duplicate:
                self.reason = 'duplicate_item'
                return True
        return False


def get_runner(root):
    sys.path.insert(0, str(root / 'data/exp_a/finetuning/policy_ab'))
    import runner
    return runner


def first_messages(runner, paper, instruction, policy):
    source = dict(paper_id=paper['paper_id'], evidence_options={
        key: value['evidence'] for key, value in runner.shared.base.evidence_options(paper).items()})
    schema = runner.multi.SCHEMA if policy == 'new_v2_2' else runner.shared.base.SCHEMA
    encoded_schema = json.dumps(schema, separators=(',', ':')) if policy == 'new_v2_2' else json.dumps(schema)
    return [dict(role='system', content=instruction + '\nReturn JSON only. Schema: ' + encoded_schema),
            dict(role='user', content=json.dumps(source, ensure_ascii=False))]


def prepare_project():
    root = Path('/kaggle/working/policy_probe/source')
    candidates = list(Path('/kaggle/input').rglob('policy_ab_bundle.zip.bin'))
    if len(candidates) != 1 or hashlib.sha256(candidates[0].read_bytes()).hexdigest() != BUNDLE_SHA256:
        raise ValueError('Frozen A/B bundle missing or changed')
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(candidates[0]) as archive:
        if any(root.resolve() not in (root / name).resolve().parents for name in archive.namelist()):
            raise ValueError('Unsafe bundle path')
        archive.extractall(root)
    settings = json.loads((root / 'settings.json').read_text(encoding='utf-8'))
    adapters = [p.parent for p in Path('/kaggle/input').rglob('adapter_manifest.json')
                if hashlib.sha256(p.read_bytes()).hexdigest() == settings['adapter_manifest_sha256']]
    if len(adapters) != 1:
        raise ValueError('Expected the exact sealed v1 adapter')
    os.environ.update(HF_HOME='/tmp/exp_a_huggingface', TOKENIZERS_PARALLELISM='false',
        PYTHONDONTWRITEBYTECODE='1', USE_TF='0')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'transformers==4.57.6',
        'accelerate==1.15.0', 'bitsandbytes==0.50.2', 'peft==0.18.1'], check=True)
    return root, adapters[0]


def worker(root, adapter, arm):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, StoppingCriteriaList
    runner = get_runner(root)
    settings = json.loads((root / 'settings.json').read_text(encoding='utf-8'))
    papers = {p['paper_id']: p for p in runner.verify_inputs(root, settings, adapter)}
    probe = json.loads((root.parent / 'probe_settings.json').read_text(encoding='utf-8'))
    assert torch.cuda.device_count() == 1
    model_settings = settings['model']
    options = dict(revision=model_settings['revision'], cache_dir='/tmp/exp_a_huggingface',
                   token=False, trust_remote_code=False)
    tokenizer = AutoTokenizer.from_pretrained(model_settings['model'], **options)
    attention = runner.shared.install_attention()
    model = AutoModelForCausalLM.from_pretrained(model_settings['model'], **options,
        use_safetensors=True, torch_dtype=torch.float16, device_map={'': 0},
        attn_implementation=attention, quantization_config=BitsAndBytesConfig(load_in_4bit=True,
        bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)).eval()
    assert model.config._commit_hash == model_settings['revision']
    if arm == 'adapter':
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter, is_trainable=False).eval()
    runtime = dict(gpu=torch.cuda.get_device_name(0), torch=torch.__version__,
        transformers=transformers.__version__, model=model_settings['model'],
        revision=model_settings['revision'], adapter_enabled=arm == 'adapter',
        quantization='nf4_double_fp16', attention=attention)
    print(json.dumps(dict(event='model_ready', arm=arm, runtime=runtime)), flush=True)
    for pid in PAPERS:
        for policy in POLICIES:
            instruction_path = root / ('instruction_old.txt' if policy == 'old_v3_7' else 'instruction_new.txt')
            messages = first_messages(runner, papers[pid], instruction_path.read_text(encoding='utf-8'), policy)
            seed = settings['generation']['seed'] + int(pid[1:]) * settings['generation']['max_attempts']
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            encoded = tokenizer(text, return_tensors='pt').to(model.device)
            length = encoded['input_ids'].shape[-1]
            assert length + LIMITS['max_new_tokens'] <= model.config.max_position_embeddings
            path = root.parent / 'results' / arm / policy / (pid + '.json')
            entry = dict(arm=arm, policy=policy, paper_id=pid, seed=seed, stage='draft', runtime=runtime,
                probe_signature=probe['signature'], source_signature=settings['signature'],
                adapter_manifest_sha256=settings['adapter_manifest_sha256'],
                instruction_sha256=hashlib.sha256(instruction_path.read_bytes()).hexdigest(),
                messages_sha256=digest(messages), limits=LIMITS)
            print(json.dumps(dict(event='call_start', arm=arm, policy=policy, paper_id=pid)), flush=True)
            started = time.monotonic()
            guard = BudgetStop(tokenizer, length, LIMITS['seconds_per_call'])
            try:
                with torch.inference_mode():
                    output = model.generate(**encoded, max_new_tokens=LIMITS['max_new_tokens'],
                        do_sample=False, pad_token_id=tokenizer.eos_token_id,
                        stopping_criteria=StoppingCriteriaList([guard]))[0, length:]
                raw = tokenizer.decode(output, skip_special_tokens=True).strip()
                reason = guard.reason or ('token_limit' if len(output) == LIMITS['max_new_tokens'] else 'eos')
                if policy == 'new_v2_2':
                    assessment = runner.assess_new(raw, papers[pid])
                else:
                    _, _, assessment, _ = runner.shared.v3.assess_attempt(raw, papers[pid], '3.1',
                        prompt_version='3.7', dataset_resource_filter=True)
                entry.update(status='measured', raw_output=raw, stop_reason=reason,
                    duplicate=guard.duplicate, generation_seconds=time.monotonic() - started,
                    usage=dict(input_tokens=length, output_tokens=len(output)),
                    schema_valid=assessment['schema_valid'], validation_errors=assessment['validation_errors'],
                    bounded_stop=reason in ('time_budget', 'duplicate_item', 'token_limit'))
            except Exception as error:
                entry.update(status='error', error_type=type(error).__name__, error_message=str(error)[:500],
                             generation_seconds=time.monotonic() - started)
            write_json(path, dict(record=entry, record_sha256=digest(entry)))
            print(json.dumps({k: entry[k] for k in ('arm', 'policy', 'paper_id', 'status',
                'stop_reason', 'generation_seconds', 'usage', 'schema_valid') if k in entry}), flush=True)
            if entry['status'] == 'error':
                raise RuntimeError('GPU probe call failed; error record retained')


def run(root, adapter):
    import torch
    runner = get_runner(root)
    settings = json.loads((root / 'settings.json').read_text(encoding='utf-8'))
    papers = runner.verify_inputs(root, settings, adapter)
    assert set(PAPERS) <= {p['paper_id'] for p in papers}
    assert torch.cuda.device_count() == 2
    probe = dict(version='loop_probe_v1_2026_10_18', papers=PAPERS, policies=POLICIES,
        arms=('base', 'adapter'), limits=LIMITS, source_signature=settings['signature'],
        probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        purpose='format/repetition diagnosis only; no reference labels or F1', training_performed=False)
    probe['signature'] = digest(probe)
    write_json(root.parent / 'probe_settings.json', probe)
    print(json.dumps(dict(event='probe_started', signature=probe['signature'], calls=12, limits=LIMITS)), flush=True)
    processes = []
    started = time.monotonic()
    try:
        for gpu, arm in enumerate(('base', 'adapter')):
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
            processes.append(subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                '--root', str(root), '--adapter', str(adapter), '--worker', arm], env=env))
        while any(process.poll() is None for process in processes):
            if time.monotonic() - started > LIMITS['worker_seconds']:
                break
            time.sleep(1)
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait()
    files = sorted((root.parent / 'results').rglob('P*.json'))
    records = []
    for path in files:
        envelope = json.loads(path.read_text(encoding='utf-8'))
        assert digest(envelope['record']) == envelope['record_sha256']
        records.append(envelope['record'])
    summary = dict(status='complete' if len(records) == 12 and all(p.returncode == 0 for p in processes)
        else 'incomplete', signature=probe['signature'], expected_calls=12, saved_calls=len(records),
        worker_exit_codes=[p.returncode for p in processes],
        results=[{k: r[k] for k in ('arm', 'policy', 'paper_id', 'status', 'stop_reason',
            'generation_seconds', 'usage', 'schema_valid', 'bounded_stop') if k in r} for r in records])
    write_json(root.parent / 'run_summary.json', summary)
    print(json.dumps(summary), flush=True)
    if summary['status'] != 'complete':
        raise RuntimeError('Probe incomplete; partial records and summary retained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--worker', choices=('base', 'adapter'))
    args = parser.parse_args()
    root, adapter = (args.root, args.adapter) if args.root else prepare_project()
    if args.worker:
        worker(root, adapter, args.worker)
    else:
        run(root, adapter)
