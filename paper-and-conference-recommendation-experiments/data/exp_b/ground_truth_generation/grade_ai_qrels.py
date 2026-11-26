"""Publish provisional AI relevance grades for the EXP-B initial pool."""

from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEIGHTS = {"problem": 0.40, "task": 0.35, "method": 0.15,
           "dataset": 0.04, "contribution": 0.06}
METHOD = "minilm_facet_rubric_v1"


def grade_pair(scores):
    score = sum(WEIGHTS[name] * value for name, value in scores.items()) / sum(
        WEIGHTS[name] for name in scores
    )
    problem = scores.get("problem", 0.0)
    task = scores.get("task", 0.0)
    if score >= 0.51 and min(problem, task) >= 0.55:
        return 3, score
    if score >= 0.33 and min(problem, task) >= 0.33:
        return 2, score
    if score >= 0.14 or max(problem, task, scores.get("method", 0.0)) >= 0.33:
        return 1, score
    return 0, score


def main():
    with (ROOT / "output/ground_truth_candidates.jsonl").open(encoding="utf-8") as file:
        candidates = list(map(json.loads, file))
    keys = {(row["query_id"], row["candidate_id"]) for row in candidates}
    counts = Counter(row["query_id"] for row in candidates)
    if len(keys) != len(candidates) or len(counts) != 50 or set(counts.values()) != {100}:
        raise ValueError("Expected 100 unique candidate pairs for each of 50 queries")
    rows = []
    for candidate in candidates:
        query_id, candidate_id = candidate["query_id"], candidate["candidate_id"]
        grade, score = grade_pair(candidate["facet_similarities"])
        rows.append({
            "pair_id": f"{query_id}:{candidate_id}",
            "query_id": query_id, "candidate_id": candidate_id, "split": candidate["split"],
            "grade": grade, "label_source": "AI", "judgment_method": METHOD,
            "model": candidate["model"], "judgment_score": round(score, 6),
        })
    paths = [
        ROOT / "human_review/ai_judgments.jsonl",
        ROOT / "human_review/initial_human_qrels.jsonl",
        ROOT.parent / "ranking/input/human_qrels.jsonl",
    ]
    for path in paths:
        if path.exists():
            with path.open(encoding="utf-8") as file:
                if any(json.loads(line).get("label_source") != "AI" for line in file if line.strip()):
                    raise ValueError(f"Refusing to replace existing non-AI judgments in {path}")
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    for path in paths:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    grades = Counter(row["grade"] for row in rows)
    report = {
        "judged_pairs": len(rows), "queries": len(counts), "label_source": "AI",
        "method": METHOD, "facet_weights": WEIGHTS, "grade_counts": dict(sorted(grades.items())),
        "human_verified": False,
        "limitation": "Grades use the MiniLM scores also used in retrieval. Evaluation against them is a proxy, not independent human validation.",
    }
    (ROOT / "evaluation/ai_judgment_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(report)


if __name__ == "__main__":
    main()
