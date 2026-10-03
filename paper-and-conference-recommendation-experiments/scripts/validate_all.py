"""Validate the delivered main real corpus; absent experiments never silent-pass."""
import argparse
import datetime
import json
import re
from pathlib import Path
from build_corpus import adapt, fingerprint, read_jsonl
from download_sources import ROOT, sha256

FACETS = {'problem', 'task', 'method', 'dataset', 'contribution'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_papers(rows):
    seen = set()
    fields = {'paper_id','source','source_id','title','abstract','year','domain','scope_evidence'}
    for line, row in enumerate(rows, 1):
        where = f'papers.jsonl:{line}'
        require(fields <= row.keys(), f'{where}: missing fields {fields - row.keys()}')
        require(set(row)==fields, f'{where}: unexpected fields outside the paper schema')
        pid = row['paper_id']
        require(isinstance(pid,str) and re.fullmatch(r'P[0-9]{6}', pid), f'{where}: invalid paper_id')
        require(pid not in seen, f'{where}: duplicate {pid}')
        seen.add(pid)
        require(row['source'] in {'csfcube','scifact'}, f'{where}: non-real source')
        require(isinstance(row['source_id'],str) and row['source_id'], f'{where}: missing source_id')
        for field in ('title','abstract'):
            require(isinstance(row[field],str) and row[field].strip(), f'{where}: empty/invalid {field}')
        require(row['year'] is None or type(row['year']) is int and 1000 <= row['year'] <= 2100, f'{where}: invalid year')
        require(row['domain']=='information_technology', f'{where}: unexpected domain')
        require(isinstance(row['scope_evidence'],list) and row['scope_evidence'] and all(isinstance(x,str) and x for x in row['scope_evidence']), f'{where}: missing IT evidence')
        require(not (row.keys() & {'relevance','satisfies_intent','latent_preferences','constraints','split'}), f'{where}: labels or experiment split leaked into corpus')
    require(rows, 'papers.jsonl: empty catalog')
    return seen


def validate_refs(rows, ids, filename):
    for line,row in enumerate(rows,1):
        require(row.get('paper_id') in ids, f'{filename}:{line}: unknown paper ref {row.get("paper_id")}')


def validate_facets(rows, ids):
    validate_refs(rows, ids, 'facets.jsonl')
    seen = set()
    for line,row in enumerate(rows,1):
        require(set(row)==FACETS | {'paper_id'}, f'facets.jsonl:{line}: wrong facet keys')
        require(row['paper_id'] not in seen, f'facets.jsonl:{line}: duplicate paper')
        seen.add(row['paper_id'])
        for facet in FACETS:
            values = row[facet]
            require(isinstance(values,list) and all(isinstance(x,str) and x.strip() for x in values), f'facets.jsonl:{line}: {facet} must be list of nonempty strings')
            require(len(set(values)) == len(values), f'facets.jsonl:{line}: duplicate facet value')


def validate_time(value):
    require(isinstance(value,str), 'timestamp must be a string')
    try:
        parsed = datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as error:
        raise ValueError(f'invalid timestamp: {value}') from error
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, f'timestamp missing timezone: {value}')
    return parsed


def validate_temporal(train, test):
    history, holdout = {}, {}
    for rows,result in ((train,history),(test,holdout)):
        for row in rows:
            result.setdefault(row['user_id'],[]).append(validate_time(row['timestamp']))
    require(history.keys()==holdout.keys() and history, 'each user requires history and holdout')
    for user in history:
        require(max(history[user]) < min(holdout[user]), f'{user}: temporal train/test overlap')


def checked_manifest(directory):
    path = directory / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    require(manifest['contract_version']=='1.0' and manifest['dataset_kind']=='real', f'{path}: wrong version/kind')
    for filename,expected in manifest['files'].items():
        file = directory / filename
        require(file.is_file(), f'missing required file: {file}')
        require(sha256(file)==expected, f'checksum mismatch: {file}')
    return manifest


def validate_corpus():
    directory = ROOT / 'data/processed'
    manifest = checked_manifest(directory)
    config = json.loads((ROOT / 'configs/data.json').read_text(encoding='utf-8'))
    require(manifest['seed']==config['seed'], 'manifest seed differs from config')
    require(manifest['generator_sha256']==sha256(ROOT / 'scripts/build_corpus.py'), 'corpus generator changed; rebuild required')
    require(manifest['scope_policy_sha256']==sha256(ROOT / config['scope_policy']), 'scope policy changed; rebuild required')
    papers = read_jsonl(directory / 'papers.jsonl')
    ids = validate_papers(papers)
    mapping = read_jsonl(directory / 'id_map.jsonl')
    active = [r for r in mapping if r['active']]
    validate_refs(active, ids, 'id_map.jsonl')
    require({r['paper_id'] for r in active} == ids, 'corpus papers missing active provenance')
    keys = [(r['source'],r['source_id']) for r in mapping]
    require(len(keys)==len(set(keys)), 'id_map.jsonl: duplicate source key')
    require(all(type(r['active']) is bool and re.fullmatch(r'P[0-9]{6}',r['paper_id']) for r in mapping), 'invalid ID map active flag or paper ID')
    require(all(type(r['primary']) is bool and (not r['primary'] or r['active']) for r in mapping), 'invalid ID map primary flag')
    primaries = [r for r in active if r['primary']]
    require(len(primaries)==len(ids) and {r['paper_id'] for r in primaries}==ids, 'each paper requires exactly one active primary source')
    by_source_key = {(r['source'],r['source_id']):r for r in active}
    raw_records = {}
    for source,filename in [('csfcube','abstracts-csfcube-preds.jsonl'),('scifact','corpus.jsonl')]:
        raw_directory = ROOT / 'data/raw' / source
        source_manifest_path = raw_directory / 'source_manifest.json'
        source_manifest = json.loads(source_manifest_path.read_text(encoding='utf-8'))
        require(sha256(source_manifest_path)==manifest['input_hashes'][source]['source_manifest_sha256'], f'{source}: input manifest changed')
        for name,expected in source_manifest['files'].items():
            require(sha256(raw_directory / name)==expected, f'{source}: raw file changed: {name}')
        for raw in read_jsonl(raw_directory / filename):
            record = adapt(source,raw)
            key = source, record['source_id']
            require(key not in raw_records, f'{source}: duplicate raw source ID')
            raw_records[key] = record
    for key,row in by_source_key.items():
        require(key in raw_records, f'ID map ref absent from raw: {key}')
        require(fingerprint(raw_records[key])==row['content_sha256'], f'ID map fingerprint mismatch: {key}')
    for row in papers:
        key = row['source'], row['source_id']
        require(key in by_source_key and by_source_key[key]['paper_id']==row['paper_id'], f'{row["paper_id"]}: primary source mismatch')
        require(by_source_key[key]['primary'], f'{row["paper_id"]}: canonical source not marked primary')
        require(row['abstract']==raw_records[key]['abstract'] and row['title']==raw_records[key]['title'], f'{row["paper_id"]}: corrupted canonical text')
    audit = read_jsonl(directory / 'scope_audit.jsonl')
    audit_keys = [(r['source'],r['source_id']) for r in audit]
    require(all(type(r['included']) is bool and type(r['raw_line']) is int and r['raw_line']>0 for r in audit), 'scope audit: invalid decision or line type')
    require(all(isinstance(r['reviewer'],str) and r['reviewer'].strip() if r['reason']=='scope_override' else r['reviewer'] is None for r in audit), 'scope audit: missing override reviewer attribution')
    require(len(audit_keys)==len(set(audit_keys)) and set(audit_keys)==set(raw_records), 'scope audit does not cover each raw record exactly once')
    included = {(r['source'],r['source_id']) for r in audit if r['included']}
    require(included == set(by_source_key), 'scope decisions do not match active ID map')
    counts = dict(papers=len(papers), id_map=len(mapping), scope_audit=len(audit))
    require(manifest['record_counts']==counts, 'manifest record counts incorrect')
    report = json.loads((directory / 'corpus_report.json').read_text(encoding='utf-8'))
    require(report['unique_papers']==len(papers) and report['active_source_records']==len(active), 'report counts incorrect')
    for source,counts in report['source_counts'].items():
        source_audit = [r for r in audit if r['source']==source]
        require(counts['total']==len(source_audit) and counts['included']==sum(r['included'] for r in source_audit), f'{source}: report scope counts incorrect')
    print(f'PASS: {len(papers)} real IT-scoped papers, {len(active)} active source refs, {len(audit)} audited records')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-kind', choices=['real','mock'], default='real')
    parser.add_argument('--phase', choices=['corpus','experiments'], default='corpus')
    args = parser.parse_args()
    try:
        require(args.dataset_kind=='real', 'Mock datasets are not built in this real-data ingestion phase.')
        require(args.phase=='corpus', 'Experiments A-E are not built yet; full experiment validation is unavailable, not passed.')
        validate_corpus()
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'VALIDATION FAILED: {error}\n')


if __name__ == '__main__':
    main()
