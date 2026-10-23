"""Freeze source-grounded AI references into a deterministic 70/15/15 SFT split."""
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import re

_MATRIX_PATH = Path(__file__).resolve().parents[3] / 'data/exp_a/.kaggle/matrix/matrix.py'
_SPEC = importlib.util.spec_from_file_location('_qlora_preparation_matrix', _MATRIX_PATH)
_MATRIX = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MATRIX)
ROOT, base, v3 = _MATRIX.ROOT, _MATRIX.base, _MATRIX.v3
FACETS = base.FACET_NAMES
RATIOS = dict(train=0.70, dev=0.15, test=0.15)


def _digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _json_digest(value):
    return _digest(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _normalized(text):
    return ' '.join(text.casefold().split())


def _source_key(paper):
    return _digest(_normalized(paper['title']) + '\n' + _normalized(paper['abstract']))


def _keyed(path):
    rows = base.read_jsonl(path)
    result = {row['paper_id']: row for row in rows}
    base.require(len(result) == len(rows), f'Duplicate paper_id in {path.name}')
    return result


def _quota(count):
    quotas = {split: math.floor(count * ratio) for split, ratio in RATIOS.items()}
    order = sorted(RATIOS, key=lambda split: -(count * RATIOS[split] - quotas[split]))
    for split in order[:count - sum(quotas.values())]:
        quotas[split] += 1
    return quotas


def _features(record, length_cutoffs):
    target = record['target']
    features = {f'present:{facet}' for facet in FACETS if target[facet]}
    features |= {f'multiple:{facet}' for facet in FACETS if len(target[facet]) >= 2}
    if not any(target[facet] for facet in FACETS):
        features.add('all_empty')
    length = len(record['paper']['abstract'].split())
    bucket = sum(length > cutoff for cutoff in length_cutoffs)
    features.add(f'length:{bucket}')
    features.add('origin:' + record['provenance']['annotation_group'])
    return features


def _split(records, seed):
    """Iterative multilabel allocation: rare remaining features receive slots first."""
    quotas = _quota(len(records))
    lengths = sorted(len(record['paper']['abstract'].split()) for record in records)
    cutoffs = [lengths[min(len(lengths) - 1, int(len(lengths) * part / 3))] for part in (1, 2)]
    features = {record['paper']['paper_id']: _features(record, cutoffs) for record in records}
    totals = Counter(feature for labels in features.values() for feature in labels)
    desired = {split: {feature: total * RATIOS[split] for feature, total in totals.items()} for split in RATIOS}
    rng = random.Random(seed)
    ids = sorted(features)
    rng.shuffle(ids)
    rank = {pid: index for index, pid in enumerate(ids)}
    remaining, result = set(ids), {split: [] for split in RATIOS}
    while remaining:
        counts = Counter(feature for pid in remaining for feature in features[pid])
        rarest = min(counts, key=lambda feature: (counts[feature], feature))
        candidates = sorted((pid for pid in remaining if rarest in features[pid]), key=rank.get)
        for pid in candidates:
            choices = [split for split in RATIOS if len(result[split]) < quotas[split]]
            split = max(choices, key=lambda name: (desired[name][rarest], quotas[name] - len(result[name])))
            result[split].append(pid)
            for feature in features[pid]:
                desired[split][feature] -= 1
            remaining.remove(pid)
    return {split: sorted(ids) for split, ids in result.items()}, features


def _token_lengths(tokenizer, messages):
    prefix = tokenizer.apply_chat_template(messages[:2], tokenize=True, add_generation_prompt=True, enable_thinking=False)
    full = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False, enable_thinking=False)
    base.require(full[:len(prefix)] == prefix, 'Chat template does not preserve the assistant prompt prefix')
    base.require(len(full) <= 4096, f'Complete document exceeds 4096 tokens ({len(full)})')
    completion = len(full) - len(prefix)
    base.require(0 < completion <= 2048, f'Assistant target exceeds 2048 tokens ({completion})')
    return dict(sequence=len(full), assistant=completion)


def _distribution(ids, records, features):
    rows = [records[pid] for pid in ids]
    return dict(count=len(ids),
        facet_presence={facet: sum(bool(row['target'][facet]) for row in rows) for facet in FACETS},
        facet_multiple={facet: sum(len(row['target'][facet]) >= 2 for row in rows) for facet in FACETS},
        concept_counts={facet: sum(len(row['target'][facet]) for row in rows) for facet in FACETS},
        all_empty=sum(not any(row['target'][facet] for facet in FACETS) for row in rows),
        length_buckets=dict(Counter(feature for pid in ids for feature in features[pid] if feature.startswith('length:'))),
        annotation_groups=dict(Counter(row['provenance']['annotation_group'] for row in rows)))


def prepare(root: Path, destination: Path, *, seed=42, tokenizer=None, extra_source_dir=None):
    root, destination = Path(root), Path(destination)
    config_path = root / 'data/exp_a/config_v3_pilot50.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    prompt_paths = [root / config[key] for key in ('guideline', 'prompt')]
    instruction = '\n\n'.join(path.read_text(encoding='utf-8') for path in prompt_paths)
    schema = json.dumps(base.SCHEMA)
    system = instruction + '\nReturn JSON only. Schema: ' + schema
    pilot = _keyed(root / 'data/exp_a/pilot50/ai_reference_v1/source_papers.jsonl')
    frozen_ids = set(pilot) | set(re.findall(r'\bP\d{6}\b', instruction))
    frozen_titles = {_normalized(paper['title']) for paper in pilot.values()}
    frozen_sources = {_source_key(paper) for paper in pilot.values()}
    corpus_path = root / config['corpus']
    corpus = _keyed(corpus_path)
    review_dir = root / 'data/exp_a/ground_truth/gold_review'
    groups = [(review_dir, 'review_papers.jsonl', 'gpt_review_evidence.jsonl',
               'gpt_review_manifest.json', 'existing_ai_reference')]
    if extra_source_dir is not None:
        groups.append((Path(extra_source_dir), 'source_papers.jsonl', 'review_evidence.jsonl',
                       'manifest.json', 'additional_ai_reference'))
    records, rejected, files, seen = [], [], {}, set()
    for directory, paper_name, evidence_name, manifest_name, group in groups:
        paths = [directory / paper_name, directory / 'review_annotations.jsonl', directory / evidence_name]
        papers, references, evidence = (_keyed(path) for path in paths)
        base.require(set(papers) == set(references) == set(evidence), 'Source/reference/evidence IDs differ')
        base.require(not seen & set(papers), 'Reference groups overlap by paper_id')
        seen.update(papers)
        group_manifest_path = directory / manifest_name
        group_manifest = json.loads(group_manifest_path.read_text(encoding='utf-8')) if group_manifest_path.exists() else {}
        pending = set(group_manifest.get('source_confirmation_pending_ids', []))
        for path in paths + ([group_manifest_path] if group_manifest_path.exists() else []):
            files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        for pid in sorted(papers):
            paper, reference, proof = papers[pid], references[pid], evidence[pid]
            base.require(_json_digest(paper) == proof['source_sha256'], f'{pid}: source hash mismatch')
            base.require(pid in corpus and all(paper[key] == corpus[pid][key] for key in ('title', 'abstract')),
                         f'{pid}: source differs from current corpus')
            try:
                base.require(pid not in pending, 'Source confirmation pending')
                base.require(pid not in frozen_ids and _normalized(paper['title']) not in frozen_titles
                             and _source_key(paper) not in frozen_sources, 'Frozen pilot or prompt example')
                base.require(reference.get('reviewer_type') == 'ai' and reference.get('review_status') == 'reviewed',
                             'Reference is not a reviewed AI annotation')
                base.require(reference.get('human_review_status') == 'pending', 'Unexpected human review provenance')
                base.require(set(reference['facets']) == set(FACETS) == set(proof['evidence']), 'Wrong evidence/facet keys')
                target, remapped = dict(paper_id=pid), []
                options = base.evidence_options(paper)
                for facet in FACETS:
                    items = proof['evidence'][facet]
                    base.require([item['concept'] for item in items] == reference['facets'][facet],
                                 f'{facet}: annotation and evidence concepts differ')
                    target[facet] = []
                    for item in items:
                        matches = [eid for eid, option in options.items()
                                   if option['source'] == item['source'] and option['evidence'] == item['evidence']]
                        base.require(matches, f'{facet}: evidence is not one exact current source sentence')
                        eid = item['evidence_id'] if item['evidence_id'] in matches else matches[0]
                        if eid != item['evidence_id']:
                            remapped.append(dict(facet=facet, concept=item['concept'], before=item['evidence_id'], after=eid))
                        target[facet].append(dict(concept=item['concept'], evidence_id=eid))
                v3.validate_response(v3.ground_response(target, paper), paper, policy='3.1')
                source = dict(paper_id=pid, evidence_options={eid: value['evidence'] for eid, value in options.items()})
                messages = [dict(role='system', content=system), dict(role='user', content=json.dumps(source, ensure_ascii=False)),
                            dict(role='assistant', content=json.dumps(target, ensure_ascii=False))]
                provenance = dict(annotation_group=group, annotation_origin=proof['annotation_origin'],
                    reviewer_type='ai', human_review_status='pending', review_status='reviewed',
                    source_sha256=proof['source_sha256'], reference_sha256=_json_digest(reference),
                    evidence_id_remapping=remapped)
                record = dict(paper=paper, reference=reference, target=target, messages=messages, provenance=provenance)
                if tokenizer is not None:
                    record['token_lengths'] = _token_lengths(tokenizer, messages)
                records.append(record)
            except (ValueError, TypeError, KeyError) as error:
                rejected.append(dict(paper_id=pid, annotation_group=group, reason=str(error)))
    base.require(records, 'No complete source-grounded references are eligible')
    split_ids, features = _split(records, seed)
    records = {row['paper']['paper_id']: row for row in records}
    leakage = {}
    for name, key in [('paper_id', lambda row: row['paper']['paper_id']),
                      ('title', lambda row: _normalized(row['paper']['title'])),
                      ('source', lambda row: _source_key(row['paper']))]:
        keys = {split: {key(records[pid]) for pid in ids} for split, ids in split_ids.items()}
        overlap = sum(len(keys[a] & keys[b]) for a, b in [('train', 'dev'), ('train', 'test'), ('dev', 'test')])
        base.require(overlap == 0, f'Cross-split {name} leakage')
        leakage[name + '_cross_split_overlap'] = overlap
    base.require(not frozen_ids & set(records), 'Frozen pilot/prompt paper leaked into eligible cohort')
    leakage['frozen_pilot_or_prompt_id_overlap'] = 0
    distributions = {split: _distribution(ids, records, features) for split, ids in split_ids.items()}
    notes = ['Labels are AI references with human review pending, not independently human-validated gold.',
             'The existing 400-paper cohort favors richer prior silver annotations and is not a random corpus sample.',
             'Iterative multilabel allocation balances facet presence, multiple concepts, empty papers, length and annotation group; exact joint balance is not guaranteed.']
    total_features = Counter(feature for labels in features.values() for feature in labels)
    notes.extend(f'{feature}: only {count} papers; representation in all three splits may be impossible.'
                 for feature, count in sorted(total_features.items()) if count < 3)
    manifest = dict(version='1.0', seed=seed, ratios=RATIOS, input_papers=len(seen), eligible_papers=len(records),
        counts={split: len(ids) for split, ids in split_ids.items()}, split_ids=split_ids,
        rejected_papers=rejected, distributions=distributions, imbalance_notes=notes, leakage=leakage,
        prompt_sha256=_digest(instruction), schema_sha256=_digest(schema), system_prompt_sha256=_digest(system),
        input_sha256=files, corpus_sha256=hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        prompt_version=config.get('prompt_version'), guideline_version=config.get('guideline_version'),
        token_limits=dict(max_sequence_tokens=4096, max_assistant_tokens=2048, verified=tokenizer is not None),
        annotation_kind='ai_reference', human_review_status='pending',
        distribution_table=[dict(facet=facet, **{split: dict(present=distributions[split]['facet_presence'][facet],
            multiple=distributions[split]['facet_multiple'][facet], concepts=distributions[split]['concept_counts'][facet])
            for split in RATIOS}) for facet in FACETS])
    destination.mkdir(parents=True, exist_ok=True)
    def write_jsonl(name, rows):
        (destination / name).write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    for split in ('train', 'dev'):
        write_jsonl(split + '.jsonl', [dict(paper_id=pid, messages=records[pid]['messages'],
            provenance=records[pid]['provenance'], **({'token_lengths': records[pid]['token_lengths']}
                if 'token_lengths' in records[pid] else {})) for pid in split_ids[split]])
    write_jsonl('test_papers.jsonl', [records[pid]['paper'] for pid in split_ids['test']])
    write_jsonl('test_references.jsonl', [dict(records[pid]['reference'], provenance=records[pid]['provenance'])
                                      for pid in split_ids['test']])
    (destination / 'instruction.txt').write_text(instruction, encoding='utf-8')
    manifest['output_sha256'] = {name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
        for name in ('train.jsonl', 'dev.jsonl', 'test_papers.jsonl', 'test_references.jsonl', 'instruction.txt')}
    (destination / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest
