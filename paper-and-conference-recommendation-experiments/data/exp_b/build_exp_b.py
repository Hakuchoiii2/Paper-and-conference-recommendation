"""Generate dataset B; paths are relative to the project root."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

import collections
from data.experiment_common import (FACETS, candidate_sample, facet_index, facet_relevance,
                                    grouped_splits, overlapping, validate_sampling)
from validate_all import require


def build_b(facets, config, rng):
    validate_sampling(config, 'num_queries', 'candidates_per_query')
    targets = config['target_facets']
    require(targets and len(targets) == len(set(targets)) and set(targets) <= set(FACETS),
            'Invalid target facets')
    index = facet_index(facets)
    queries, labels, provenance = [], [], []
    requested, actual, skipped = {}, {}, {}
    for nfacet, facet in enumerate(targets):
        quota = config['num_queries'] // len(targets) + (nfacet < config['num_queries'] % len(targets))
        requested[facet] = quota
        eligible = {pid for pid in facets if facets[pid][facet]}
        anchors = sorted(eligible)
        rng.shuffle(anchors)
        actual[facet], reasons = 0, collections.Counter()
        for anchor in anchors:
            if actual[facet] == quota:
                break
            positive = overlapping(index, facet, facets[anchor][facet]) - {anchor}
            negative = eligible - positive - {anchor}
            hard = set()
            for other in FACETS:
                if other != facet:
                    hard.update(overlapping(index, other, facets[anchor][other]))
            hard &= negative
            candidates = candidate_sample(positive, negative, hard, config['candidates_per_query'], config, rng)
            if candidates is None:
                reason = 'no_positive' if not positive else 'no_negative' if not negative else 'insufficient_candidates'
                reasons[reason] += 1
                continue
            qid = f'Q{len(queries)+1:04}'
            queries.append(dict(query_id=qid, query_paper_id=anchor, target_facet=facet, candidate_ids=candidates))
            for pid in candidates:
                relevance = facet_relevance(facets[anchor][facet], facets[pid][facet])
                labels.append(dict(query_id=qid, candidate_id=pid, relevance=relevance))
                provenance.append(dict(query_id=qid, candidate_id=pid, label_source='synthetic_rule',
                                       rule_version=config['label_rule_version'], target_facet=facet,
                                       anchor_concepts=sorted(facets[anchor][facet]),
                                       candidate_concepts=sorted(facets[pid][facet]),
                                       candidate_role='positive' if relevance else 'hard_negative' if pid in hard else 'easy_negative'))
            actual[facet] += 1
        skipped[facet] = dict(reasons)
    report = dict(requested_by_facet=requested, actual_by_facet=actual, skipped=skipped,
                  shortfall=config['num_queries']-len(queries), actual_pairs=len(labels),
                  label_counts=dict(collections.Counter(str(row['relevance']) for row in labels)))
    return ({'retrieval_queries.jsonl': queries, 'splits.json': grouped_splits(queries, 'query_id', config['seed'])},
            {'retrieval_labels.jsonl': labels, 'label_provenance.jsonl': provenance}, report)

if __name__ == '__main__':
    from data.build_experiments import run
    run('b')
