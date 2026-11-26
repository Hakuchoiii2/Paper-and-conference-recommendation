"""Tune facet weights on DEV and evaluate the locked methods on TEST."""

import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RANKING = ROOT / "ranking"
CONFIG = RANKING / "config/ranking_config.json"
OUTPUT = ROOT / json.loads(CONFIG.read_text(encoding="utf-8"))["paths"]["dev_test_reports"]
GROUND_TRUTH = ROOT / "ground_truth_generation"
FACETS = ("problem", "task", "method", "dataset", "contribution")
WEIGHTS = {
    "equal_weight": dict.fromkeys(FACETS, 0.2),
    "weighted_a": dict(zip(FACETS, (0.4, 0.2, 0.2, 0.1, 0.1))),
    "weighted_b": dict(zip(FACETS, (0.3, 0.25, 0.25, 0.1, 0.1))),
}


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_rows(path):
    with path.open(encoding="utf-8") as file:
        yield from map(json.loads, file)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run_rankers(split, folder, config, variants):
    scripts = RANKING / "scripts"
    config["paths"].update({
        "output_fulltext": str(folder / "fulltext.jsonl"),
        "output_equal_weight": str(folder / "equal_weight.jsonl"),
        "output_final": str(folder / "combined.jsonl"),
    })
    jobs = [
        ("fulltext", "03_fulltext_ranking.py"),
        ("equal_weight", "04_equal_weight_ranking.py"),
        *((name, "05_weighted_ranking.py") for name in variants),
    ]
    rankings = {}
    previous_argv = sys.argv
    try:
        for name, script in jobs:
            ranker = load_module(scripts / script)
            ranker.load_config = lambda: config
            if name in variants:
                config["paths"]["output_weighted"] = str(folder / f"{name}.jsonl")
                config["weight_configurations"]["method_3_weighted"]["weights"] = variants[name]
            sys.argv = [script, "--split", split, "--top-k", "100"]
            ranker.main()
            rankings[name] = {
                row["query_id"]: row["ranking"]
                for row in read_rows(folder / f"{name}.jsonl")
            }
    finally:
        sys.argv = previous_argv
    return rankings


def pool_and_evaluate(query_ids, rankings, folder):
    wanted = set(query_ids)
    for name, ranks in rankings.items():
        if set(ranks) != wanted or any(len(items) < 20 for items in ranks.values()):
            raise ValueError(f"Incomplete ranking for {name}")
    initial = {
        (row["query_id"], row["candidate_id"]): row["grade"]
        for row in read_rows(GROUND_TRUTH / "human_review/initial_human_qrels.jsonl")
        if row["query_id"] in wanted
    }
    if any(sum(key[0] == qid for key in initial) != 100 for qid in query_ids):
        raise ValueError("Expected 100 initial qrels per query")
    pool = set(initial)
    for ranks in rankings.values():
        pool.update((qid, item["candidate_id"]) for qid, items in ranks.items() for item in items[:20])
    added = pool - initial.keys()
    similarities = {
        (row["query_id"], row["candidate_id"]): row["facet_similarities"]
        for row in read_rows(GROUND_TRUTH / "intermediate/facet_similarity_results.jsonl")
        if (row["query_id"], row["candidate_id"]) in added
    } if added else {}
    grader = load_module(GROUND_TRUTH / "grade_ai_qrels.py")
    qrels = defaultdict(dict)
    with (folder / "qrels.jsonl").open("w", encoding="utf-8") as file:
        for qid, cid in sorted(pool):
            key = (qid, cid)
            scores = similarities.get(key)
            grade = initial[key] if key in initial else grader.grade_pair(scores)[0] if scores else 0
            qrels[qid][cid] = grade
            file.write(json.dumps({
                "query_id": qid, "candidate_id": cid, "grade": grade, "label_source": "AI",
                "judgment_method": grader.METHOD,
                "no_shared_facet_scores": key in added and not scores,
            }) + "\n")
    evaluator = load_module(RANKING / "scripts/06_evaluate_ranking.py")
    metrics = {
        name: evaluator.evaluate_method_for_split(ranks, qrels, query_ids)
        for name, ranks in rankings.items()
    }
    write_json(folder / "metrics.json", metrics)
    print(json.dumps({name: values["nDCG@10"] for name, values in metrics.items()}))
    print(f"{len(pool)} pooled pairs, including {len(added)} newly graded by AI")
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", choices=("dev", "test"))
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    split = json.loads((ROOT / config["paths"]["query_split"]).read_text(encoding="utf-8"))
    if len(set(split["dev"])) != 15 or len(set(split["test"])) != 35 or set(split["dev"]) & set(split["test"]):
        raise ValueError("Expected disjoint splits with 15 DEV and 35 TEST queries")
    folder = OUTPUT / args.split
    folder.mkdir(parents=True, exist_ok=True)
    lock_path = OUTPUT / "locked_weights.json"
    if args.split == "dev":
        variants = {name: WEIGHTS[name] for name in ("weighted_a", "weighted_b")}
    else:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        variants = {"weighted": lock["weights"]}
    rankings = run_rankers(args.split, folder, config, variants)
    metrics = pool_and_evaluate(split[args.split], rankings, folder)
    if args.split == "dev":
        # Keep the equal-weight baseline as a separate TEST method.
        winner = max(variants, key=lambda name: metrics[name]["nDCG@10"])
        write_json(lock_path, {
            "selected": winner, "weights": variants[winner],
            "selection_metric": "DEV nDCG@10",
            "dev_scores": {name: metrics[name]["nDCG@10"] for name in WEIGHTS},
        })
        print(f"Locked {winner} for TEST")


if __name__ == "__main__":
    main()
