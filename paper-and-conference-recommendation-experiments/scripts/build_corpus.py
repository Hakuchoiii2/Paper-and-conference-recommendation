"""Merge the IT-scoped corpus; leave native labels and splits unchanged in raw/."""
import collections
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from download_sources import ROOT, sha256, write_json


def read_jsonl(path):
    rows = []
    with Path(path).open(encoding='utf-8') as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError('expected object')
                rows.append(row)
            except (ValueError, TypeError) as error:
                raise ValueError(f'{path}:{line_number}: {error}') from error
    return rows


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    temporary.replace(path)


def normalize(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold()))


def term_present(term, text):
    return re.search(r'(?<!\w)' + re.escape(term) + r's?(?!\w)', text) is not None


def classify(source, title, abstract, policy):
    # ponytail: phrase-based scope misses synonyms; review scope_audit and add versioned overrides before freeze.
    if source in policy['trusted_cs_sources']:
        return True, 'source_cs_scope', [policy['trusted_scope_evidence']]
    title_text = normalize(title)
    title_terms = [term for term in policy['terms'] if term_present(term, title_text)]
    if title_terms:
        return True, 'it_term_in_title', title_terms
    hits = []
    for sentence in re.split(r'(?<=[.!?])\s+', abstract):
        text = normalize(sentence)
        terms = [term for term in policy['terms'] if term_present(term, text)]
        hits.extend(terms)
        if terms and any(term_present(marker, text) for marker in policy['method_markers']):
            return True, 'it_method_in_abstract', sorted(set(terms))
    return False, 'review_pending' if hits else 'no_explicit_it_evidence', sorted(set(hits))


def adapt(source, row):
    source_id = row['paper_id'] if source == 'csfcube' else row['doc_id']
    if isinstance(source_id, bool) or not isinstance(source_id, (int, str)):
        raise ValueError('invalid source ID')
    title, sentences = row.get('title'), row.get('abstract')
    if not isinstance(title, str) or not isinstance(sentences, (str, list)):
        raise ValueError(f'{source}:{source_id}: title/abstract type invalid')
    if isinstance(sentences, list) and not all(isinstance(s, str) for s in sentences):
        raise ValueError(f'{source}:{source_id}: abstract sentences must be strings')
    abstract = ' '.join(sentences) if isinstance(sentences, list) else sentences
    metadata = row.get('metadata') or {}
    year = metadata.get('year')
    year = int(year) if str(year).isdigit() else None
    if year is not None and not 1000 <= year <= 2100:
        year = None
    identifiers = {'s2orc': str(source_id)}
    for key in ('doi', 'arxiv_id', 'acl_id', 'pubmed_id', 'pmc_id'):
        if metadata.get(key):
            value = str(metadata[key]).strip().casefold()
            if key == 'doi':
                value = re.sub(r'^(https?://(dx\.)?doi\.org/|doi:\s*)', '', value)
            identifiers[key] = value
    return dict(source=source, source_id=str(source_id), title=' '.join(title.split()), abstract=' '.join(abstract.split()), year=year, identifiers=identifiers)


def fingerprint(row):
    content = {key: value for key, value in row.items() if key != 'scope_evidence'}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def check_override(override, key):
    if not isinstance(override, dict) or type(override.get('include')) is not bool:
        raise ValueError(f'{key}: override requires boolean include')
    for field in ('reviewer', 'reason'):
        if not isinstance(override.get(field), str) or not override[field].strip():
            raise ValueError(f'{key}: override requires nonempty string {field}')
    return override


def merge(rows, previous):
    old = {(r['source'], r['source_id']): r for r in previous}
    if len(old) != len(previous):
        raise ValueError('duplicate source keys in existing ID map')
    next_id = max((int(r['paper_id'][1:]) for r in previous), default=0) + 1
    groups, identifiers, titles, mapping, conflicts = {}, {}, collections.defaultdict(list), [], []
    seen = set()
    # Existing records first preserve issued IDs even when new sources sort earlier.
    for row in sorted(rows, key=lambda r: ((r['source'], r['source_id']) not in old, not old.get((r['source'],r['source_id']),{}).get('primary',False), r['source'], r['source_id'])):
        key = row['source'], row['source_id']
        if key in seen:
            raise ValueError(f'duplicate source record: {key}')
        seen.add(key)
        content_hash = fingerprint(row)
        if key in old and old[key].get('content_sha256', content_hash) != content_hash:
            raise ValueError(f'source content changed for {key}; version the release explicitly')
        matches = {identifiers[(kind, value)] for kind, value in row['identifiers'].items() if (kind, value) in identifiers}
        if len(matches) > 1:
            raise ValueError(f'identifier conflict requires human review: {key}')
        normalized_title = normalize(row['title'])
        equivalent = [pid for pid in titles[normalized_title] if normalize(groups[pid]['abstract']) == normalize(row['abstract'])]
        pid = next(iter(matches), None) or (equivalent[0] if equivalent else None)
        if key in old:
            issued = old[key]['paper_id']
            if pid and pid != issued:
                raise ValueError(f'dedup would change issued ID for {key}; review required')
            pid = issued
        if pid is None:
            if next_id > 999999:
                raise ValueError('paper ID capacity exceeded')
            pid = f'P{next_id:06d}'
            next_id += 1
        if not matches and not equivalent and titles[normalized_title] and pid not in titles[normalized_title]:
            conflicts.append(dict(source=row['source'], source_id=row['source_id'], paper_id=pid, conflicting_paper_ids=list(titles[normalized_title]), reason='same normalized title, different abstract; kept separate'))
        if pid not in groups:
            groups[pid] = {k: row[k] for k in ('source','source_id','title','abstract','year')}
            groups[pid].update(paper_id=pid, domain='information_technology', scope_evidence=row['scope_evidence'])
        for kind, value in row['identifiers'].items():
            identifiers[kind, value] = pid
        if pid not in titles[normalized_title]:
            titles[normalized_title].append(pid)
        mapping.append(dict(source=row['source'], source_id=row['source_id'], paper_id=pid, identifiers=row['identifiers'], content_sha256=content_hash))
    # Retain historical mappings to reserve IDs; active=false records cannot be labels' active corpus refs.
    mapping = [dict(r, active=True, primary=(r['source'],r['source_id']) == (groups[r['paper_id']]['source'],groups[r['paper_id']]['source_id'])) for r in mapping] + [dict(r, active=False, primary=False) for key,r in old.items() if key not in seen]
    return sorted(groups.values(), key=lambda r:r['paper_id']), sorted(mapping, key=lambda r:(r['source'],r['source_id'])), dict(title_conflicts=conflicts, duplicate_records_merged=len(rows)-len(groups))


def main():
    config = json.loads((ROOT / 'configs/data.json').read_text(encoding='utf-8'))
    policy_path = ROOT / config['scope_policy']
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    overrides = policy['overrides']
    selected, audit, source_counts, input_hashes = [], [], {}, {}
    for source, filename in [('csfcube','abstracts-csfcube-preds.jsonl'), ('scifact','corpus.jsonl')]:
        path = ROOT / 'data/raw' / source / filename
        manifest_path = path.parent / 'source_manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        for name, expected in manifest['files'].items():
            raw_file = path.parent / name
            if sha256(raw_file) != expected:
                raise ValueError(f'raw checksum mismatch: {raw_file}')
        input_hashes[source] = dict(corpus_sha256=sha256(path), source_manifest_sha256=sha256(manifest_path))
        rows = read_jsonl(path)
        counts = collections.Counter(total=len(rows), missing_abstract=0, missing_title=0, missing_year=0, invalid_year=0)
        for line, raw in enumerate(rows, 1):
            row = adapt(source, raw)
            counts['missing_abstract'] += not bool(row['abstract'])
            counts['missing_title'] += not bool(row['title'])
            raw_year = (raw.get('metadata') or {}).get('year')
            counts['missing_year'] += raw_year is None or str(raw_year).strip() == ''
            counts['invalid_year'] += raw_year is not None and str(raw_year).strip() != '' and row['year'] is None
            key = f"{source}:{row['source_id']}"
            keep, reason, evidence = classify(source, row['title'], row['abstract'], policy)
            reviewer = None
            if key in overrides:
                override = check_override(overrides[key],key)
                keep, reason, evidence = override['include'], 'scope_override', [override['reason']]
                reviewer = override['reviewer']
            if not row['title'] or not row['abstract']:
                keep, reason = False, 'missing_title_or_abstract'
            counts['included' if keep else 'excluded'] += 1
            counts[reason] += 1
            audit.append(dict(source=source, source_id=row['source_id'], title=row['title'], raw_line=line, included=keep, reason=reason, evidence=evidence, reviewer=reviewer))
            if keep:
                selected.append(dict(row, scope_evidence=evidence))
        source_counts[source] = dict(counts)
    known_keys = {f"{r['source']}:{r['source_id']}" for r in audit}
    if set(overrides) - known_keys:
        raise ValueError(f'overrides reference unknown papers: {sorted(set(overrides)-known_keys)}')
    output = ROOT / 'data/processed'
    map_path = output / 'id_map.jsonl'
    previous = read_jsonl(map_path) if map_path.exists() else []
    # Upgrade the initial bootstrap map using the already-issued canonical primary.
    if previous and any('primary' not in row for row in previous):
        existing_papers = read_jsonl(output / 'papers.jsonl')
        primary_keys = {(row['source'],row['source_id']) for row in existing_papers}
        previous = [dict(row,primary=(row['source'],row['source_id']) in primary_keys) for row in previous]
    papers, mapping, dedup = merge(selected, previous)
    if not papers:
        raise ValueError('scope filter produced an empty corpus')
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / 'papers.jsonl', papers)
    write_jsonl(map_path, mapping)
    write_jsonl(output / 'scope_audit.jsonl', audit)
    by_paper = collections.defaultdict(set)
    for record in mapping:
        if record['active']:
            by_paper[record['paper_id']].add(record['source'])
    unique_by_source = {source:sum(source in values for values in by_paper.values()) for source in source_counts}
    write_json(output / 'corpus_report.json', dict(source_counts=source_counts, canonical_papers_by_source=unique_by_source, cross_source_overlap=sum(len(values)>1 for values in by_paper.values()), domains={'information_technology':len(papers)}, unique_papers=len(papers), active_source_records=len(selected), **dedup, scope_status='provisional; human audit and title-conflict review required before freeze', minimum_target=3000, working_target=6000, gap_to_minimum=max(0,3000-len(papers)), gap_to_working_target=max(0,6000-len(papers))))
    write_json(output / 'native_split_policy.json', dict(policy='Preserve native source splits in raw; no new training split assigned in this ingestion phase.', csfcube='data/raw/csfcube/evaluation_splits.json', scifact=['data/raw/scifact/claims_train.jsonl','data/raw/scifact/claims_dev.jsonl','data/raw/scifact/claims_test.jsonl'], warning='Source splits concern queries/claims, not a universal paper train/test split. Never map SciFact evidence labels directly to recommendation relevance.'))
    files = {p.name:sha256(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != 'manifest.json'}
    write_json(output / 'manifest.json', dict(contract_version=config['contract_version'], dataset_kind='real', seed=config['seed'], generator_version='1.0', generator_sha256=sha256(Path(__file__)), input_hashes=input_hashes, scope_policy_version=policy['version'], scope_policy_sha256=sha256(policy_path), record_counts=dict(papers=len(papers), id_map=len(mapping), scope_audit=len(audit)), files=files, status='provisional IT corpus; no reviewed five-facet annotations'))
    print(json.dumps(dict(unique_papers=len(papers), source_counts=source_counts, **dedup), indent=2))


if __name__ == '__main__':
    main()
