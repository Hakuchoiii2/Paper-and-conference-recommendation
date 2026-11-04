"""Build a private, reproducible gold400 QLoRA/V-recall trial."""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import unicodedata
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FROZEN = ROOT / 'data/exp_a/.kaggle/v_recall_gold400/release_20261026_v1/preflight_project'
RELEASE = HERE / 'release_20261028_v5'
KERNEL = 'htnkhi/exp-a-v-recall-gold400-qlora'
DATASET = 'htnkhi/exp-a-v-recall-gold400-qlora-inputs'
FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def jsonl(rows):
    return ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode('utf-8')


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def split_papers(papers):
    require(len(papers) == 400 and len({p['paper_id'] for p in papers}) == 400, 'Expected 400 unique papers')
    for key in ('title', 'abstract'):
        values = [' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', p[key]).casefold())) for p in papers]
        require(all(values) and len(set(values)) == 400, 'Duplicate or empty normalized ' + key)
    ids = sorted(p['paper_id'] for p in papers)
    random.Random(42).shuffle(ids)
    return {name: sorted(part) for name, part in (
        ('train', ids[:280]), ('valid', ids[280:340]), ('test', ids[340:]))}


def target(gold, proof, options):
    require(gold['paper_id'] == proof['paper_id'], 'Evidence paper differs')
    answer = dict(paper_id=gold['paper_id'])
    for facet in FACETS:
        items = proof['evidence'][facet]
        require([x['concept'] for x in items] == gold['facets'][facet], 'Evidence concepts differ from gold')
        for item in items:
            require(item['evidence_id'] in options and options[item['evidence_id']]['evidence'] == item['evidence'],
                    'Evidence sentence differs from source')
        answer[facet] = [{k: x[k] for k in ('concept', 'evidence_id')} for x in items]
    return answer


def main():
    require(not RELEASE.exists(), 'Release already exists; use a new immutable release')
    frozen = json.loads((FROZEN / 'settings.json').read_text(encoding='utf-8'))
    for name, expected in frozen['files'].items():
        require(sha((FROZEN / name).read_bytes()) == expected, 'Frozen runtime differs: ' + name)
    policy = load('gold400_frozen_policy', FROZEN / 'runner.py')
    shared = policy.load_shared(FROZEN)
    origin = ROOT / 'data/exp_a/ground_truth/gold_review'
    gold = {r['paper_id']: r for r in rows(origin / 'human_gold.jsonl')}
    evidence = {r['paper_id']: r for r in rows(origin / 'gpt_review_evidence.jsonl')}
    papers = {r['paper_id']: {k: r[k] for k in ('paper_id', 'title', 'abstract')} for r in rows(origin / 'review_papers.jsonl')}
    require(len(gold) == len(papers) == len(evidence) == 400 and set(gold) == set(papers) == set(evidence), 'Gold/source/evidence IDs differ')
    require(sha((origin / 'human_gold.jsonl').read_bytes()) == frozen['gold_sha256'], 'Gold differs from accepted release')
    splits = split_papers(list(papers.values()))
    require(sha(jsonl([papers[pid] for pid in sorted(papers)])) == frozen['source_sha256'], 'Sources differ from frozen gold400')
    generation = dict(frozen['generation'])
    generation.pop('paper_ids', None)
    generation['cache_dir'] = '/tmp/exp_a_huggingface'
    generation.update(prompt='data/exp_a/prompts/extraction_gold_v1.md',
                      guideline='data/exp_a/prompts/guideline_gold_v1.md',
                      validator_policy='source_attributed_paraphrase_v1', instruction_revision='gold_paraphrase_v1')
    instruction = '\n\n'.join((HERE / name).read_text(encoding='utf-8') for name in ('guideline.md', 'instruction.md'))
    validator = load('gold400_source_only_validator', HERE / 'validator.py')
    sft = {}
    validation_errors = []
    old_errors = []
    validation_warnings = []
    for pid, paper in papers.items():
        require(gold[pid].get('human_review_status') == 'accepted', 'Unaccepted gold')
        answer = target(gold[pid], evidence[pid], shared.base.evidence_options(paper))
        _, _, old = policy.recall.v.repair.assess(shared, json.dumps(answer, ensure_ascii=False), paper, scoped=True)
        if old['validation_errors']:
            old_errors.append(dict(paper_id=pid, errors=old['validation_errors']))
        with validator.scope(shared):
            _, _, assessment = shared.v3.assess_generation(json.dumps(answer, ensure_ascii=False), paper,
                '3.1', prompt_version='3.7', dataset_resource_filter=True)
        if assessment['validation_errors']:
            validation_errors.append(dict(paper_id=pid, errors=assessment['validation_errors']))
        if assessment['validation_warnings']:
            validation_warnings.append(dict(paper_id=pid, warnings=assessment['validation_warnings']))
        source = dict(paper_id=pid, evidence_options={k: v['evidence'] for k, v in shared.base.evidence_options(paper).items()})
        sft[pid] = dict(paper_id=pid, messages=[
            dict(role='system', content=instruction + '\nReturn JSON only. Schema: ' + json.dumps(shared.base.SCHEMA)),
            dict(role='user', content=json.dumps(source, ensure_ascii=False)),
            dict(role='assistant', content=json.dumps(answer, ensure_ascii=False))],
            provenance=dict(label_source='human_gold', human_review_status='accepted', annotation_author_type='ai',
                            source_sha256=sha(raw_json(paper)), gold_sha256=sha(raw_json(gold[pid]))))
    payloads = {name: (FROZEN / name).read_bytes() for name in frozen['files']
                if not name.startswith(('model_inputs/', 'evaluation_only/')) and name != 'runner.py'}
    payloads['gold_policy.py'] = (FROZEN / 'runner.py').read_bytes()
    payloads['gold_validator.py'] = (HERE / 'validator.py').read_bytes()
    payloads[generation['prompt']] = (HERE / 'instruction.md').read_bytes()
    payloads[generation['guideline']] = (HERE / 'guideline.md').read_bytes()
    repair = payloads['repair.py'].decode('utf-8')
    start, end = repair.index('def validate_scoped('), repair.index('def assess(')
    replacement = '''def validate_scoped(shared, original, value, paper, *, policy='3.1'):
    return gold_validator.validate_response(shared, value, paper)


@contextmanager
def scope_validator(shared, enabled):
    if enabled:
        with gold_validator.scope(shared):
            yield
    else:
        yield


'''
    loader = '''\nimport importlib.util
from pathlib import Path
_gold_spec = importlib.util.spec_from_file_location('gold400_packaged_validator', Path(__file__).with_name('gold_validator.py'))
gold_validator = importlib.util.module_from_spec(_gold_spec)
_gold_spec.loader.exec_module(gold_validator)
'''
    payloads['repair.py'] = (repair[:start] + replacement + repair[end:] + loader).encode('utf-8')
    recall = payloads['recall.py'].decode('utf-8')
    replacements = {
        'Copy concise source words in original order; retain negation, conditions, subject and scope.':
            'Use concise faithful source-supported paraphrases; retain negation, conditions, subject and scope.',
        "'select a different supplied sentence that supports the concept. Copy source words '":
            "'select a different supplied sentence that supports the concept. Faithful paraphrases '",
        "'in order; retain subject, negation, metric, quantities, comparator and conditions. '":
            "'are allowed; retain subject, negation, metric, quantities, comparator and conditions. '",
        "'do not rewrite all lists merely to change the draft. No invented synonyms or '":
            "'do not rewrite all lists merely to change the draft. No unsupported meanings or '",
        'shared.evaluator.label_key(': 'v.repair.gold_validator.concept_key(',
        '    value,post=shared.v3.filter_named_datasets(value,paper)':
            '    with v.repair.scope_validator(shared,True):\n        value,post=shared.v3.filter_named_datasets(value,paper)',
        "    return dict(paper_id=paper['paper_id'],arm='V-recall',facets=":
            "    audit.update(validator_policy=v.repair.gold_validator.VERSION, semantic_entailment_verified=False, validation_warnings=assessment.get('validation_warnings', []))\n    return dict(paper_id=paper['paper_id'],arm='V-recall',facets="}
    for old, new in replacements.items():
        require(old in recall, 'Recall policy patch anchor differs: ' + old)
        recall = recall.replace(old, new)
    payloads['recall.py'] = recall.encode('utf-8')
    # Preserve the original decoder; only add optional PEFT loading before the existing closure.
    matrix = payloads['data/exp_a/.kaggle/matrix.py'].decode('utf-8')
    anchor = '    runtime = dict(model=config[\'model\'], model_revision=model.config._commit_hash,'
    require(matrix.count(anchor) == 1, 'Generator patch anchor differs')
    matrix = matrix.replace(anchor, "    if config.get('adapter_path'):\n        from peft import PeftModel\n        model = PeftModel.from_pretrained(model, config['adapter_path'], is_trainable=False).eval()\n" + anchor)
    payloads['data/exp_a/.kaggle/matrix.py'] = matrix.encode('utf-8')
    trainer = (HERE.parent / 'train.py').read_text(encoding='utf-8')
    replacements = {
        "'data/exp_a/.kaggle/matrix/matrix.py'": "'data/exp_a/.kaggle/matrix.py'",
        'save_total_limit=2,': 'save_total_limit=3,',
        "label_source='ai_generated_reference'": "label_source='human_gold'"}
    for old, new in replacements.items():
        require(trainer.count(old) == 1, 'Trainer patch anchor differs: ' + old)
        trainer = trainer.replace(old, new)
    payloads['train.py'] = trainer.encode('utf-8')
    payloads['runtime.py'] = (HERE / 'runtime.py').read_bytes()
    payloads['splits.json'] = raw_json(splits)
    for split, ids in splits.items():
        payloads[f'model_inputs/{split}.jsonl'] = jsonl([papers[pid] for pid in ids])
        payloads[f'evaluation_only/{split}.jsonl'] = jsonl([gold[pid] for pid in ids]) if split != 'train' else b''
        if split != 'test':
            payloads[f'training_data/{split}.jsonl'] = jsonl([sft[pid] for pid in ids])
    # No duplicate train reference file; gold is present solely as supervised train examples.
    del payloads['evaluation_only/train.jsonl']
    training = dict(model=frozen['model']['model'], revision=frozen['model']['revision'], max_seq_length=4096,
                    epochs=3, learning_rate=1e-4, seed=42, gradient_accumulation_steps=8,
                    train_file='training_data/train.jsonl', dev_file='training_data/valid.jsonl',
                    output_dir='provisional_adapter', checkpoint_dir='train_state', split_manifest_file='splits.json',
                    prompt_sha256=sha(instruction.encode()), schema_sha256=sha(raw_json(shared.base.SCHEMA)))
    # Tokenizer-only preflight, using the exact pinned local snapshot. Never truncate examples.
    from transformers import AutoTokenizer
    tokenizer_path = ROOT / 'models/huggingface/models--Qwen--Qwen3-8B/snapshots' / training['revision']
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path), local_files_only=True, trust_remote_code=False)
    helper = load('gold400_existing_trainer', HERE.parent / 'train.py')
    lengths = {split: [len(helper.encode_example(tokenizer, sft[pid], training['max_seq_length'])['input_ids']) for pid in splits[split]]
               for split in ('train', 'valid')}
    settings = dict(version='v_recall_gold400_qlora_trial_1', kernel=KERNEL, dataset=DATASET,
        splits=splits, training=training, generation=generation, instruction_sha256=sha(instruction.encode()),
        validator_policy=validator.VERSION, instruction_revision='gold_paraphrase_v1',
        gold_sha256=frozen['gold_sha256'], checkpoint_selection='validation_v_recall_micro_f1_then_recall_then_earlier_epoch',
        threshold=.85, metrics=['precision', 'recall', 'f1', 'macro_f1'],
        limitation='Gold400 was purposively selected and previously inspected during pipeline development; this is a new paper-level training split, not an independent external holdout.',
        files={name: sha(raw) for name, raw in payloads.items()})
    require(not validation_errors, 'New validator still rejects reviewed gold; inspect before packaging')
    settings['signature'] = policy.digest(settings)
    payloads['settings.json'] = raw_json(settings)
    work = RELEASE / 'project'
    for name, raw in payloads.items():
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    dataset = RELEASE / 'input-dataset'
    dataset.mkdir()
    bundle = dataset / 'gold400_qlora_bundle.zip.bin'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    (dataset / 'dataset-metadata.json').write_bytes(raw_json(dict(id=DATASET, title='Exp A V Recall Gold400 QLoRA Inputs', is_private=True, licenses=[dict(name='other')])))
    (dataset / 'README.md').write_text('Private gold400 QLoRA trial. Existing CSFCube/SciFact provenance and license metadata are retained in the frozen payload. AI-assisted labels explicitly accepted by the user. Split 280/60/60, seed42. Never use test labels for training or checkpoint selection.\n', encoding='utf-8')
    kernel = RELEASE / 'kernel'
    kernel.mkdir()
    code = (HERE / 'bootstrap.py').read_text(encoding='utf-8').replace('__BUNDLE_SHA256__', sha(bundle.read_bytes()))
    compile(code, 'run_trial.py', 'exec')
    (kernel / 'run_trial.py').write_text(code, encoding='utf-8')
    (kernel / 'kernel-metadata.json').write_bytes(raw_json(dict(id=KERNEL, title='Exp A V Recall Gold400 QLoRA', code_file='run_trial.py', language='python', kernel_type='script', is_private=True, enable_gpu=True, enable_internet=True, machine_shape='NvidiaTeslaT4', dataset_sources=[DATASET], kernel_sources=[], competition_sources=[], model_sources=[])))
    report = dict(status='passed', counts={k: len(v) for k, v in splits.items()}, max_tokens={k: max(v) for k, v in lengths.items()},
                  signature=settings['signature'], gold_sha256=settings['gold_sha256'], bundle_sha256=sha(bundle.read_bytes()),
                  validator_gold_disagreements=validation_errors, old_validator_gold_disagreements=old_errors,
                  validator_gold_warnings=validation_warnings, validator_policy=validator.VERSION,
                  kernel_sha256=sha((kernel / 'run_trial.py').read_bytes()),
                  test_in_sft=False, private=True, original_artifacts_changed=False)
    (RELEASE / 'preflight.json').write_bytes(raw_json(report))
    print(json.dumps({k: v for k, v in report.items() if k not in ('validator_gold_disagreements', 'old_validator_gold_disagreements', 'validator_gold_warnings')}, ensure_ascii=False, indent=2))
    print('Gold/validator disagreement papers:', len(validation_errors), '(full evidence in preflight.json)')


if __name__ == '__main__':
    main()
