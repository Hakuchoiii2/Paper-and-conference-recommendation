"""Freeze a new train/dev source-only cohort and deterministic private Kaggle bundle."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import runner

base = runner.shared.base
KERNEL = 'htnkhi/exp-a-qlora-policy-ab-v2'
DATASET = 'htnkhi/exp-a-qlora-policy-ab-v2-inputs'
ADAPTER = 'htnkhi/exp-a-qwen3-8b-facets-qlora-v1'


def build(destination=None):
    destination = Path(destination or HERE / 'build')
    fine = HERE.parent
    frozen = json.loads((fine / 'data/manifest.json').read_text(encoding='utf-8'))
    base.require(base.sha256(ROOT / 'data/processed/papers.jsonl') == frozen['corpus_sha256'], 'Frozen source corpus changed')
    for name in ('train.jsonl', 'dev.jsonl', 'instruction.txt'):
        base.require(base.sha256(fine / 'data' / name) == frozen['output_sha256'][name], 'Frozen v1 file changed: ' + name)
    prior = json.loads((fine / 'label_revision_v2/pilot40/selection.json').read_text(encoding='utf-8'))
    corpus = {p['paper_id']: p for p in base.read_jsonl(ROOT / 'data/processed/papers.jsonl')}
    pilot50 = set(json.loads((ROOT / 'data/exp_a/config_v3_pilot50.json').read_text(encoding='utf-8'))['paper_ids'])
    pilot40 = {p['paper_id'] for p in prior['selection']}
    test = set(frozen['split_ids']['test'])
    exclude = pilot50 | pilot40 | test
    # Only provenance is used from the training records; targets never enter the bundle.
    rng, selection = random.Random(20261019), []
    for split in ('train', 'dev'):
        records = base.read_jsonl(fine / f'data/{split}.jsonl')
        base.require({r['paper_id'] for r in records} == set(frozen['split_ids'][split]), 'Frozen split differs')
        for group in ('existing_ai_reference', 'additional_ai_reference'):
            eligible = sorted(r['paper_id'] for r in records if r['paper_id'] not in exclude
                              and r['provenance']['annotation_group'] == group)
            base.require(len(eligible) >= 10, 'Insufficient fresh papers in stratum')
            for pid in sorted(rng.sample(eligible, 10)):
                selection.append(dict(paper_id=pid, split=split, annotation_group=group,
                                      corpus_source=corpus[pid]['source']))
    ids = [r['paper_id'] for r in selection]
    base.require(len(ids) == len(set(ids)) == 40, 'Duplicate/incomplete cohort')
    papers = [{k: corpus[pid][k] for k in ('paper_id', 'title', 'abstract', 'source')} for pid in ids]
    protected = {pid: corpus[pid] for pid in exclude}
    title = lambda p: base.normalize(p['title']).casefold()
    text = lambda p: base.normalize(p['title'] + ' ' + p['abstract']).casefold()
    base.require(not ({title(p) for p in papers} & {title(p) for p in protected.values()}), 'Protected title overlap')
    base.require(not ({text(p) for p in papers} & {text(p) for p in protected.values()}), 'Protected source overlap')
    payload = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    files = {'model_inputs/papers.jsonl': ('\n'.join(json.dumps(p, ensure_ascii=False) for p in papers) + '\n').encode('utf-8'),
        'instruction_old.txt': (fine / 'data/instruction.txt').read_bytes(),
        'instruction_new.txt': (fine / 'label_revision_v2/prompt_v2_2.md').read_bytes()}
    for name in ('data/exp_a/finetuning/policy_ab/runner.py', 'data/exp_a/finetuning/label_revision_v2/schema.py',
        'data/exp_a/.kaggle/matrix/matrix.py', 'data/exp_a/build_exp_a.py', 'data/exp_a/extraction_v3.py',
        'scripts/exp_a/evaluate_exp_a.py', 'scripts/experiment_io.py', 'scripts/build_corpus.py',
        'scripts/download_sources.py', 'scripts/validate_all.py'):
        files[name] = (ROOT / name).read_bytes()
    original = json.loads((fine / 'build/build_manifest.json').read_text(encoding='utf-8'))['settings']
    generation = dict(original['generation'])
    generation.pop('paper_ids', None)
    settings = dict(version='policy_ab_v2_2_2026_10_18', model=original['model'], generation=generation,
        paper_ids=ids, arms=list(runner.ARMS), adapter_dataset=ADAPTER,
        adapter_manifest_sha256=base.sha256(fine / 'adapter-dataset/adapter_manifest.json'),
        old_policy='v3.7 frozen pipeline', new_policy='v2.2 candidate with v2.1 multi-sentence schema',
        comparison='combined policy/schema/review pipeline intervention; report format and semantic errors separately',
        reference_status='pending source-first seal; no old or student labels supplied to inference',
        files={name: hashlib.sha256(value).hexdigest() for name, value in files.items()})
    settings['signature'] = runner.shared.digest(settings)
    files['settings.json'] = payload(settings)
    dataset, kernel = destination / 'input-dataset', destination / 'kernel'
    dataset.mkdir(parents=True, exist_ok=True)
    kernel.mkdir(parents=True, exist_ok=True)
    bundle = dataset / 'policy_ab_bundle.zip.bin'
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, value)
    base.write_json(dataset / 'dataset-metadata.json', dict(id=DATASET, title='Exp A QLoRA Policy AB v2 Inputs',
                                                         licenses=[dict(name='other')]))
    code = (HERE / 'kernel.template.py').read_text(encoding='utf-8').replace('__BUNDLE_SHA256__', base.sha256(bundle))
    compile(code, 'run_policy_ab.py', 'exec')
    (kernel / 'run_policy_ab.py').write_text(code, encoding='utf-8')
    base.write_json(kernel / 'kernel-metadata.json', dict(id=KERNEL, title='Exp A QLoRA Policy AB v2',
        code_file='run_policy_ab.py', language='python', kernel_type='script', is_private=True, enable_gpu=True,
        enable_internet=True, machine_shape='NvidiaTeslaT4', dataset_sources=[DATASET, ADAPTER],
        competition_sources=[], kernel_sources=[], model_sources=[]))
    report = dict(kernel=KERNEL, dataset=DATASET, adapter=ADAPTER, counts=dict(Counter(r['split'] for r in selection)),
        seed=20261019, selection=selection, source_counts=dict(Counter(p['source'] for p in papers)),
        annotation_groups=dict(Counter(r['annotation_group'] for r in selection)),
        leakage=dict(test=len(set(ids) & test), pilot50=len(set(ids) & pilot50), policy_pilot40=len(set(ids) & pilot40)),
        caveats=['Train/dev diagnostic, not an unseen held-out benchmark.',
            'All three eligible SciFact train/dev papers were in the previous pilot; this fresh sample is CSFCube only.',
            'References must be drafted and sealed from source before viewing model predictions; human review pending.'],
        corpus_sha256=base.sha256(ROOT / 'data/processed/papers.jsonl'),
        split_manifest_sha256=base.sha256(fine / 'data/manifest.json'),
        bundle_sha256=base.sha256(bundle), signature=settings['signature'], settings=settings)
    base.write_json(destination / 'build_manifest.json', report)
    base.write_jsonl(destination / 'source_papers.jsonl', [dict(p, evidence_options=base.evidence_options(p)) for p in papers])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    result = build(args.destination)
    print(json.dumps({k: result[k] for k in ('kernel', 'counts', 'source_counts', 'leakage', 'signature')}, indent=2))
