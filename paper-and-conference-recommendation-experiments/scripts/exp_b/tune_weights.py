"""Grid-search masked facet weights on Exp B train and select on dev."""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from exp_b.facet_ranker import FACETS, MODEL_NAME, FacetRanker
from experiment_io import concept_sets, load_silver
from experiment_runner import evaluation_cases
from validate_experiments import validate_experiment


def weight_grid(step):
    if not math.isfinite(step) or step <= 0:
        raise ValueError('Grid step must be positive and finite')
    units = round(1.0 / step)
    if not math.isclose(units * step, 1.0, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError('Grid step must divide 1 exactly, for example 0.05 or 0.1')

    def compositions(total, size):
        if size == 1:
            yield (total,)
            return
        for value in range(total + 1):
            for remainder in compositions(total - value, size - 1):
                yield (value, *remainder)

    return [
        dict(zip(FACETS, (value / units for value in values)))
        for values in compositions(units, len(FACETS))
    ]


def mean_ndcg(cases, labels, score_rows, weights):
    values = []
    for case in cases:
        whole, similarities, active = score_rows[case['case_id']]
        scores = FacetRanker.weighted_scores(whole, similarities, active, weights)
        candidate_ids = case['candidate_ids']
        ranking = sorted(
            range(len(candidate_ids)),
            key=lambda index: (-scores[index], candidate_ids[index]),
        )
        relevance = labels[case['case_id']]
        grades = [relevance[candidate_ids[index]] for index in ranking[:10]]
        ideal = sorted(relevance.values(), reverse=True)[:10]
        idcg = sum((2 ** grade - 1) / math.log2(rank + 2)
                   for rank, grade in enumerate(ideal))
        if idcg:
            dcg = sum((2 ** grade - 1) / math.log2(rank + 2)
                      for rank, grade in enumerate(grades))
            values.append(dcg / idcg)
    if not values:
        raise ValueError('nDCG@10 is undefined for every case in this split')
    return sum(values) / len(values)


def prepare_scores(cases, ranker):
    rows = {}
    for case in cases:
        rows[case['case_id']] = ranker.score_components(
            case['query_paper_id'], case['candidate_ids']
        )
    return rows


def optimize(root, config_path, grid_step, shortlist_size):
    config_relative_path = Path(config_path).resolve().relative_to(root).as_posix()
    dataset = validate_experiment(root, 'b', config_relative_path)
    config = dataset['config']
    papers, raw_facets, metadata, _ = load_silver(
        root, Path(config['facets_path']).parent
    )
    facets = concept_sets(raw_facets, metadata)
    train_cases, train_labels, _, _ = evaluation_cases(root, 'b', config, 'train')
    dev_cases, dev_labels, _, _ = evaluation_cases(root, 'b', config, 'dev')
    required_ids = {
        paper_id
        for case in train_cases + dev_cases
        for paper_id in [case['query_paper_id'], *case['candidate_ids']]
    }
    ranker = FacetRanker(model_name=MODEL_NAME)
    ranker.encode(
        {paper_id: papers[paper_id] for paper_id in sorted(required_ids)},
        {paper_id: facets[paper_id] for paper_id in required_ids if paper_id in facets},
    )
    train = (train_cases, train_labels, prepare_scores(train_cases, ranker))
    dev = (dev_cases, dev_labels, prepare_scores(dev_cases, ranker))

    candidates = []
    for weights in weight_grid(grid_step):
        train_score = mean_ndcg(*train, weights)
        candidates.append((train_score, weights))
    candidates.sort(key=lambda item: (-item[0], tuple(item[1][facet] for facet in FACETS)))
    candidates = candidates[:shortlist_size]

    evaluated = [
        (mean_ndcg(*dev, weights), train_score, weights)
        for train_score, weights in candidates
    ]
    evaluated.sort(key=lambda item: (
        -item[0], -item[1], tuple(item[2][facet] for facet in FACETS)
    ))
    dev_score, train_score, weights = evaluated[0]
    return {
        'format_version': '1.0',
        'experiment': 'b',
        'encoder': MODEL_NAME,
        'weights': weights,
        'scoring': {
            'similarity': 'cosine',
            'normalization': 'L2-normalized embeddings',
            'missing_facet_policy': 'mask missing facets; normalize by active weight; fallback to whole-text cosine when none are shared',
        },
        'selection': {
            'status': 'frozen',
            'objective': 'mean nDCG@10',
            'train_split': 'train',
            'dev_split': 'dev',
            'grid_step': grid_step,
            'train_grid_candidates': len(weight_grid(grid_step)),
            'dev_shortlist_size': len(candidates),
            'train_ndcg_at_10': train_score,
            'dev_ndcg_at_10': dev_score,
            'test_used_for_selection': False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/exp_b_curated.json')
    parser.add_argument('--output', default='configs/exp_b_frozen.json')
    parser.add_argument('--grid-step', type=float, default=0.05)
    parser.add_argument('--dev-shortlist-size', type=int, default=100)
    args = parser.parse_args()
    if args.dev_shortlist_size < 1:
        parser.error('--dev-shortlist-size must be positive')

    config_path = (ROOT / args.config).resolve()
    output_path = (ROOT / args.output).resolve()
    if ROOT not in config_path.parents or ROOT not in output_path.parents:
        parser.error('Config and output paths must stay inside the project')
    result = optimize(ROOT, config_path, args.grid_step, args.dev_shortlist_size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8',
    )
    print(
        f"Frozen {MODEL_NAME}: nDCG@10 train={result['selection']['train_ndcg_at_10']:.4f}, "
        f"dev={result['selection']['dev_ndcg_at_10']:.4f}; weights={result['weights']}"
    )


if __name__ == '__main__':
    main()
