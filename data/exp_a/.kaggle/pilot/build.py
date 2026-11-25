"""Build a private, reference-free Kaggle bundle for the reproducible Qwen pilot."""
import hashlib
import json
import random
import re
import sys
import zipfile
import sqlite3
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def select_pilot(papers, excluded, count, seed):
    eligible = sorted({p['paper_id'] for p in papers} - set(excluded))
    if type(count) is not int or not 0 < count <= len(eligible):
        raise ValueError('sample_size must fit the eligible papers')
    return sorted(random.Random(seed).sample(eligible, count))


def resume_files(root, config):
    output = root / config['output_dir']
    checkpoint = output / '.exp_a_checkpoint.sqlite3'
    if not checkpoint.is_file() and not (output / 'manifest.json').is_file():
        return []
    sys.path.insert(0, str(ROOT / 'data/exp_a'))
    import build_exp_a as generator
    if checkpoint.is_file():
        papers, provenance, _ = generator.inputs(root, config)
        catalog = {p['paper_id']: p for p in papers}
        with closing(sqlite3.connect(checkpoint)) as db:
            signatures = db.execute('SELECT signature FROM run').fetchall()
            generator.require(len(signatures) == 1 and generator.compatible_provenance(
                json.loads(signatures[0][0]), provenance, root), 'Checkpoint provenance differs; use a new output_dir')
            for pid, payload in db.execute('SELECT paper_id, payload FROM annotations'):
                record = json.loads(payload)
                generator.require(pid in catalog and pid == record['facets']['paper_id'] == record['metadata']['paper_id'],
                                  'Checkpoint contains unknown or mismatched paper IDs')
                generator.require(record['metadata'].get('extraction_protocol') == 'two_pass_v3'
                                  and generator.validate_annotation(record['metadata']['evidence'], catalog[pid], record['metadata'], config=config)
                                  == record['facets'], 'Checkpoint annotation/evidence differs')
            generator.export(root, config, papers, provenance, db)
    generator.check_outputs(root, config, allow_partial=True)
    return [(output / n).relative_to(root).as_posix()
            for n in ('facets_silver.jsonl', 'annotation_metadata.jsonl', 'manifest.json')]


def build():
    settings = json.loads((HERE / 'settings.json').read_text(encoding='utf-8'))
    if settings.get('gpu_workers') != 2 or settings['accelerator'] != 'NvidiaTeslaT4':
        raise ValueError('This pilot requires two T4 workers on NvidiaTeslaT4')
    username = settings['username']
    if not re.fullmatch(r'[a-z0-9_-]+', username):
        raise ValueError('Invalid Kaggle username')
    title_slug = re.sub(r'[^a-z0-9]+', '-', settings['kernel_title'].lower()).strip('-')
    if settings['kernel_slug'] != title_slug or not re.fullmatch(r'[a-z0-9-]+', settings['dataset_slug']):
        raise ValueError('Invalid kernel title/slug or dataset slug')
    corpus = ROOT / 'data/processed/papers.jsonl'
    reference = ROOT / 'data/exp_a/ground_truth/gold_review/review_annotations.jsonl'
    read_rows = lambda p: [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()]
    papers, reviewed = read_rows(corpus), read_rows(reference)
    excluded = {p['paper_id'] for p in reviewed}
    ids = select_pilot(papers, excluded, settings['sample_size'], settings['sample_seed'])
    config = json.loads((ROOT / 'data/exp_a/config.json').read_text(encoding='utf-8'))
    config.update(paper_range=[1, None], paper_ids=ids, output_dir='data/exp_a/generated_v3_7_pilot50',
                  cache_dir='/tmp/exp_a_huggingface', prompt='data/exp_a/prompts/extraction_v3_7.md',
                  guideline='data/exp_a/prompts/facet_guideline_v3.md', prompt_version='3.7', guideline_version='3.1',
                  extraction_protocol='two_pass_v3', do_sample=False, max_attempts=3,
                  dataset_resource_filter=True, gpu_workers=settings['gpu_workers'])
    write_json(ROOT / 'data/exp_a/config_v3_pilot50.json', config)
    baseline = [r for r in read_rows(ROOT / 'data/exp_a/generated/facets_silver.jsonl') if r['paper_id'] in set(ids)]
    if {r['paper_id'] for r in baseline} != set(ids):
        raise ValueError('Baseline is missing selected papers')
    baseline_path = ROOT / 'data/exp_a/pilot50/baseline_silver.jsonl'
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in baseline), encoding='utf-8')
    baseline_manifest = json.loads((ROOT / 'data/exp_a/generated/manifest.json').read_text(encoding='utf-8'))
    flagged = sorted(set(baseline_manifest.get('fallback_annotations', {})) & set(ids))
    selection = dict(sample_size=len(ids), seed=settings['sample_seed'], algorithm='random.Random(seed).sample(sorted(eligible_ids), size); then sort',
                     eligible_count=len(papers)-len(excluded), excluded_reference_count=len(excluded), paper_ids=ids,
                     corpus_sha256=sha(corpus), excluded_reference_sha256=sha(reference), baseline_sha256=sha(baseline_path),
                     baseline_flagged_count=len(flagged), baseline_flagged_ids=flagged,
                     reference_in_model_input=False, reference_preparation='pending; must be source-only and independent of new Qwen outputs')
    write_json(ROOT / 'data/exp_a/pilot50/selection.json', selection)
    files = ['data/processed/papers.jsonl', 'data/exp_a/config_v3_pilot50.json',
             'data/exp_a/build_exp_a.py', 'data/exp_a/extraction_v3.py',
             'data/exp_a/merge_exp_a.py', 'data/exp_a/.kaggle/pilot/dual_t4.py', 'scripts/experiment_io.py',
             config['prompt'], config['guideline'],
             'data/exp_a/pilot50/selection.json',
             'scripts/build_corpus.py', 'scripts/download_sources.py', 'scripts/validate_all.py']
    files += resume_files(ROOT, config)
    from dual_t4 import worker_configs
    for worker in worker_configs(config):
        files += resume_files(ROOT, worker)
    dataset = HERE / 'build/input-dataset'
    dataset.mkdir(parents=True, exist_ok=True)
    archive_path = dataset / 'input_bundle.zip.bin'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (ROOT / name).read_bytes())
    write_json(dataset / 'dataset-metadata.json', dict(id=username+'/'+settings['dataset_slug'],
                                                     title=settings['dataset_title'], licenses=[dict(name='other')]))
    archive_sha = sha(archive_path)
    kernel = HERE / 'build/kernel'
    kernel.mkdir(parents=True, exist_ok=True)
    code = (HERE / 'kernel.template.py').read_text(encoding='utf-8').replace('__BUNDLE_SHA256__', archive_sha)
    compile(code, 'run_exp_a.py', 'exec')
    (kernel / 'run_exp_a.py').write_text(code, encoding='utf-8')
    write_json(kernel / 'kernel-metadata.json', dict(id=username+'/'+settings['kernel_slug'], title=settings['kernel_title'],
               code_file='run_exp_a.py', language='python', kernel_type='script', is_private=True,
               enable_gpu=True, enable_internet=True, machine_shape=settings['accelerator'],
               dataset_sources=[username+'/'+settings['dataset_slug']], competition_sources=[], kernel_sources=[], model_sources=[]))
    manifest = dict(kernel=username+'/'+settings['kernel_slug'], dataset=username+'/'+settings['dataset_slug'],
                    sample=selection, bundle_sha256=archive_sha, bundle_files={name: sha(ROOT/name) for name in files},
                    kernel_sha256=sha(kernel/'run_exp_a.py'), generator_config_sha256=sha(ROOT/'data/exp_a/config_v3_pilot50.json'))
    write_json(HERE / 'build/build_manifest.json', manifest)
    print(json.dumps(dict(kernel=manifest['kernel'], dataset=manifest['dataset'], sample_size=len(ids),
                          excluded_overlap=len(set(ids)&excluded), bundle_sha256=archive_sha), ensure_ascii=False))
    return manifest


if __name__ == '__main__':
    build()
