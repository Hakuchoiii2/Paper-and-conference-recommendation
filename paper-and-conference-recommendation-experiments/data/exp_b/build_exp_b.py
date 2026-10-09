"""B: controlled whole-document versus five-facet retrieval."""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT_ROOT))
sys.path.insert(0,str(PROJECT_ROOT / 'scripts'))
import collections
from data.experiment_common import (FACETS, candidate_sample, grouped_splits, normalized_weights,
                                    retrieval_grade, validate_sampling)
from validate_all import require

def build_b(facets, config, rng):
    validate_sampling(config,'num_queries','candidates_per_query')
    require(config['label_rule_version'] == 'weighted_overlap_v2','Unsupported B label rule')
    weights = normalized_weights(config['fixed_weights'])
    anchors = sorted(pid for pid,row in facets.items() if sum(bool(row[f]) for f in FACETS) >= 2)
    rng.shuffle(anchors)
    queries, labels, provenance = [], [], []
    skipped = collections.Counter()
    for anchor in anchors:
        if len(queries) == config['num_queries']:
            break
        grades = {pid: retrieval_grade(facets[anchor],row,weights)
                  for pid,row in sorted(facets.items()) if pid != anchor and any(row.values())}
        positives = {pid for pid,v in grades.items() if v >= config['positive_grade']}
        negatives = set(grades) - positives
        hard = {pid for pid in negatives if grades[pid] > 0}
        candidates = candidate_sample(positives,negatives,hard,config['candidates_per_query'],config,rng)
        if candidates is None:
            skipped['insufficient_positive_or_negative_pool'] += 1
            continue
        qid = f'Q{len(queries)+1:04}'
        queries.append(dict(query_id=qid,query_paper_id=anchor,candidate_ids=candidates))
        for pid in candidates:
            labels.append(dict(query_id=qid,candidate_id=pid,relevance=grades[pid]))
            provenance.append(dict(query_id=qid,candidate_id=pid,label_source='synthetic_rule',
                                   rule_version=config['label_rule_version']))
    report = dict(shortfall=config['num_queries'] - len(queries),actual_pairs=len(labels),skipped=dict(skipped))
    return ({'retrieval_queries.jsonl':queries,'splits.json':grouped_splits(queries,'query_id',config['seed'])},
            {'retrieval_labels.jsonl':labels,'label_provenance.jsonl':provenance},report)

if __name__ == '__main__':
    from data.build_experiments import run
    run('b')
