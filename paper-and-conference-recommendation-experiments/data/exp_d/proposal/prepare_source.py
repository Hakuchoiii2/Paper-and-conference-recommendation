"""Prepare a verified, read-only A/C source bundle inside D; no experiment runner."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

HERE = Path(__file__).resolve().parent
# The new preparation pipeline lives in data/exp_d/proposal, separate from baseline.
PROJECT = HERE.parents[2]
FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalize(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold()))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def write_rows(path, values):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True) + '\n' for x in values), encoding='utf-8')


def inside(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    require(path.is_relative_to(root), f'Path escapes source: {name}')
    return path


def checked_hash(root, name, expected):
    path = inside(root, name)
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    operation = 'exact_bytes'
    if actual != expected:
        # These two known checkout files differ only in line endings. Never rewrite them.
        require(name in ('data/processed/papers.jsonl', 'scripts/build_corpus.py')
                and hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest() == expected,
                f'Upstream checksum mismatch: {name}')
        operation = 'verified_CRLF_to_LF_equivalence_read_only'
    return dict(path=name, observed_sha256=actual, manifest_sha256=expected, operation=operation)


def load_bundle(directory):
    directory = Path(directory).resolve()
    manifest = read_json(directory / 'manifest.json')
    require(manifest.get('protocol') == 'd_source_v1' and manifest.get('status') == 'verified', 'Invalid D source bundle')
    for name, expected in manifest['files'].items():
        require(sha(inside(directory, name)) == expected, f'Source bundle changed: {name}')
    papers = {r['paper_id']: r for r in read_rows(directory / 'papers.jsonl')}
    facets = {r['paper_id']: {f:set(r[f]) for f in FACETS} for r in read_rows(directory / 'facets.jsonl')}
    history = {name:read_rows(directory / 'history' / name) for name in
               ('users.jsonl', 'interactions_train.jsonl', 'search_events.jsonl', 'exposures.jsonl')}
    return dict(papers=papers, facets=facets, history=history, manifest=manifest,
                directory=directory, manifest_sha256=sha(directory / 'manifest.json'))


def prepare(source_root, output):
    root, output = Path(source_root).resolve(), Path(output).resolve()
    require(output.is_relative_to(HERE) and output != HERE and 'backup' not in output.relative_to(HERE).parts,
            'Source output must be a new directory inside data/exp_d, outside backup')
    require(not output.exists(), 'Source bundle exists; choose a new output')
    cm_path = root / 'data/exp_c/generated/manifest.json'
    cm = read_json(cm_path)
    require(cm.get('experiment') == 'c' and cm.get('status') == 'complete'
            and cm.get('contract_version') == '2.0', 'Complete C 2.0 handoff required')
    checks = []
    expected_all = {}
    for section in ('input_hashes', 'files', 'generator_hashes'):
        for name, expected in cm[section].items():
            require(name not in expected_all or expected_all[name] == expected, 'Conflicting C checksums')
            expected_all[name] = expected
    for name, expected in sorted(expected_all.items()):
        checks.append(checked_hash(root, name, expected))
    config = cm['config']
    am_path = inside(root, Path(config['facets_path']).parent / 'manifest.json')
    am = read_json(am_path)
    require(am.get('status') == 'complete' and am.get('dataset_kind') == 'real'
            and not am.get('missing_ids'), 'Complete real A handoff required')
    for name, expected in am['files'].items():
        checks.append(checked_hash(root, (am_path.parent.relative_to(root) / name).as_posix(), expected))
    for key, expected in am['provenance']['input_hashes'].items():
        checks.append(checked_hash(root, am['provenance']['config'][key], expected))
    papers = read_rows(inside(root, config['corpus_path']))
    raw = read_rows(inside(root, config['facets_path']))
    metadata = read_rows(am_path.parent / 'annotation_metadata.jsonl')
    pids = {r['paper_id'] for r in papers}
    require(len(pids) == len(papers), 'Duplicate canonical paper IDs')
    require({r['paper_id'] for r in raw} == pids and len(raw) == len(pids), 'A coverage differs from corpus')
    meta = {r['paper_id']:r for r in metadata}
    require(set(meta) == pids and len(meta) == len(metadata), 'A metadata coverage differs')
    facets = []
    for row in sorted(raw, key=lambda x:x['paper_id']):
        if meta[row['paper_id']].get('fallback_used') or meta[row['paper_id']].get('validation_errors'):
            continue
        require(all(isinstance(row[f], list) and all(isinstance(v, str) for v in row[f]) for f in FACETS), 'Invalid A facets')
        facets.append(dict(paper_id=row['paper_id'], **{f:sorted(set(filter(None, map(normalize, row[f])))) for f in FACETS}))
    histories = {name:read_rows(cm_path.parent / name) for name in
                 ('users.jsonl', 'interactions_train.jsonl', 'search_events.jsonl', 'exposures.jsonl')}
    users = {r['user_id'] for r in histories['users.jsonl']}
    require(len(users) == len(histories['users.jsonl']) and users, 'Invalid C users')
    for name in ('interactions_train.jsonl', 'search_events.jsonl', 'exposures.jsonl'):
        require(all(r['user_id'] in users for r in histories[name]), 'Unknown user in C prefix')
    # All checks finish before any new directory is written.
    write_rows(output / 'papers.jsonl', sorted(papers, key=lambda x:x['paper_id']))
    write_rows(output / 'facets.jsonl', facets)
    for name, values in histories.items():
        write_rows(output / 'history' / name, values)
    receipt = dict(source_root=str(root), checks=checks, A_manifest_sha256=sha(am_path), C_manifest_sha256=sha(cm_path),
                   quality_filtered=len(papers)-len(facets), public_C_prefix_only=True,
                   note='No hidden C profiles or future C logs are exported; source files are never modified.')
    write_json(output / 'source_receipt.json', receipt)
    for check in checks:
        require(sha(root / check['path']) == check['observed_sha256'], 'Source changed during preparation')
    files = {p.relative_to(output).as_posix():sha(p) for p in output.rglob('*') if p.is_file()}
    write_json(output / 'manifest.json', dict(protocol='d_source_v1', status='verified', files=files,
               papers=len(papers), approved_facets=len(facets), users=len(users), canonical_modified=False))
    return load_bundle(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=PROJECT)
    parser.add_argument('--output', type=Path, default=HERE / 'inputs/base_v1')
    args = parser.parse_args()
    result = prepare(args.source_root, args.output)
    print(json.dumps({k:result['manifest'][k] for k in ('papers', 'approved_facets', 'users')}, indent=2))


if __name__ == '__main__':
    main()
