"""Generate dataset C; paths are relative to the project root."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

import collections
from data.experiment_common import (FACETS, candidate_sample, facet_index, grouped_splits,
                                    overlapping, validate_sampling)
from validate_all import require


def validate_templates(templates, num_cases):
    require(templates['version'] == 'concept_overlap_v1', 'Unsupported template version')
    rows = templates['templates']
    require(rows and len({row['intent_type'] for row in rows}) == len(rows), 'Duplicate or empty intent templates')
    for row in rows:
        require(type(row['quota']) is int and row['quota'] > 0, 'Invalid template quota')
        require(set(row['constraints']) == set(FACETS)
                and set(row['constraints'].values()) <= {'similar','different','ignore'}
                and any(value != 'ignore' for value in row['constraints'].values()), 'Invalid intent constraints')
    require(sum(row['quota'] for row in rows) == num_cases, 'Intent quotas must sum to num_cases')


def build_c(facets, config, templates, rng):
    validate_sampling(config, 'num_cases', 'candidates_per_case')
    validate_templates(templates, config['num_cases'])
    index = facet_index(facets)
    intents, labels, provenance = [], [], []
    actual, skipped = {}, {}
    for template in templates['templates']:
        kind, directions = template['intent_type'], template['constraints']
        active = [facet for facet in FACETS if directions[facet] != 'ignore']
        eligible = {pid for pid, row in facets.items() if all(row[facet] for facet in active)}
        anchors = sorted(eligible)
        rng.shuffle(anchors)
        actual[kind], reasons = 0, collections.Counter()
        for anchor in anchors:
            if actual[kind] == template['quota']:
                break
            positive = eligible - {anchor}
            overlap = {facet: overlapping(index, facet, facets[anchor][facet]) for facet in active}
            for facet in active:
                positive = positive & overlap[facet] if directions[facet] == 'similar' else positive - overlap[facet]
            negative = eligible - positive - {anchor}
            hard = {pid for pid in negative if sum(
                (pid in overlap[facet]) != (directions[facet] == 'similar') for facet in active) == 1}
            candidates = candidate_sample(positive, negative, hard, config['candidates_per_case'], config, rng)
            if candidates is None:
                reason = 'no_positive' if not positive else 'no_negative' if not negative else 'insufficient_candidates'
                reasons[reason] += 1
                continue
            iid = f'I{len(intents)+1:04}'
            intents.append(dict(intent_id=iid, query_paper_id=anchor, intent_type=kind,
                                constraints=directions, candidate_ids=candidates))
            for pid in candidates:
                labels.append(dict(intent_id=iid, candidate_id=pid, satisfies_intent=pid in positive))
                provenance.append(dict(intent_id=iid, candidate_id=pid, label_source='synthetic_rule',
                                       rule_version=config['label_rule_version'], template_version=templates['version'],
                                       candidate_role='positive' if pid in positive else 'hard_negative' if pid in hard else 'negative'))
            actual[kind] += 1
        skipped[kind] = dict(reasons)
    report = dict(actual_by_type=actual, requested_by_type={row['intent_type']: row['quota'] for row in templates['templates']},
                  skipped=skipped, shortfall=config['num_cases']-len(intents), actual_pairs=len(labels))
    return ({'intents.jsonl': intents, 'splits.json': grouped_splits(intents, 'intent_id', config['seed'])},
            {'intent_labels.jsonl': labels, 'label_provenance.jsonl': provenance}, report)

if __name__ == '__main__':
    from data.build_experiments import run
    run('c')
