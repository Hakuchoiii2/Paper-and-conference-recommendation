"""Evaluate audit signals against a held-out subset of the independently reviewed Gold set."""

import json
import hashlib
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_preparation.pipeline_scope import split_gold_ids

INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
EVAL_DIR = PROJECT_ROOT / "data_preparation" / "evaluation"

FACETS = ("problem", "task", "method", "dataset", "contribution")


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as file:
        return [json.loads(line) for line in file]


def facet_text(value):
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    if isinstance(value, str):
        return value
    return ""


def normalize_tokens(text):
    return set(text.lower().replace(";", " ").split())


def main():
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    gold_path = INPUT_DIR / "gold_facets_400.jsonl"
    silver_path = INPUT_DIR / "silver_facets.jsonl"
    decisions_path = INTERMEDIATE_DIR / "automated_decisions.jsonl"
    if not all(path.exists() for path in (gold_path, silver_path, decisions_path)):
        raise FileNotFoundError("Gold, Silver, and automated_decisions.jsonl are required for evaluation.")

    gold_records = read_jsonl(gold_path)
    silver_by_id = {row["paper_id"]: row for row in read_jsonl(silver_path)}
    decisions_by_id = {
        row["paper_id"]: row for row in read_jsonl(decisions_path)
    }

    sorted_gold = sorted(gold_records, key=lambda row: row["paper_id"])
    calibration_ids, heldout_ids = split_gold_ids(
        [row["paper_id"] for row in sorted_gold]
    )
    calibration_records = [
        row for row in sorted_gold if row["paper_id"] in calibration_ids
    ]
    heldout_records = [row for row in sorted_gold if row["paper_id"] in heldout_ids]
    evaluation_phase = os.environ.get("DATA_PREPARATION_EVAL_PHASE", "calibration")
    if evaluation_phase not in ("calibration", "heldout", "full"):
        raise ValueError(f"Unknown DATA_PREPARATION_EVAL_PHASE: {evaluation_phase}")
    evaluation_records = (
        calibration_records if evaluation_phase == "calibration" else heldout_records
    )
    gold_ids_hash = hashlib.sha256(
        "\n".join(sorted(row["paper_id"] for row in gold_records)).encode("utf-8")
    ).hexdigest()

    for name, records in (
        ("gold_calibration.jsonl", calibration_records),
        ("gold_heldout.jsonl", heldout_records),
    ):
        with open(EVAL_DIR / name, "w", encoding="utf-8") as output:
            for record in records:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

    results = {
        "gold_total": len(gold_records),
        "gold_paper_ids_sha256": gold_ids_hash,
        "evaluation_phase": evaluation_phase,
        "calibration_papers": len(calibration_records),
        "heldout_papers": len(heldout_records),
        "evaluated_papers": len(evaluation_records),
        "evaluated_matched_papers": sum(
            row["paper_id"] in silver_by_id and row["paper_id"] in decisions_by_id
            for row in evaluation_records
        ),
        "heldout_matched_papers": (
            sum(row["paper_id"] in silver_by_id and row["paper_id"] in decisions_by_id for row in heldout_records)
            if evaluation_phase in ("heldout", "full")
            else 0
        ),
        "calibration_requires_manual_rule_review": True,
        "calibration_review_confirmed": (
            os.environ.get("DATA_PREPARATION_CALIBRATION_REVIEW_CONFIRMED") == "1"
        ),
        "facet_metrics": {},
    }

    for facet in FACETS:
        missing_tp = missing_fp = missing_fn = 0
        unsupported_tp = unsupported_fp = unsupported_fn = 0
        jaccard_scores = []
        matched_papers = 0

        for gold in evaluation_records:
            paper_id = gold["paper_id"]
            silver = silver_by_id.get(paper_id)
            decision = decisions_by_id.get(paper_id)
            if silver is None or decision is None:
                continue
            matched_papers += 1
            gold_facets = gold.get("facets", {})
            gold_present = bool(facet_text(gold_facets.get(facet, "" )).strip())
            silver_text = facet_text(silver.get(facet, ""))
            silver_present = bool(silver_text.strip())
            qwen = decision.get("qwen_audit", {}).get(facet, {})
            audit_decision = decision.get("audit_decision", {}).get(facet)

            expected_missing = gold_present and not silver_present
            detected_missing = (
                not silver_present
                and qwen.get("detected_issues") == "missing"
                and bool(qwen.get("relevant_sentences"))
                and (
                    audit_decision == "NEEDS_REVIEW"
                    or (
                        facet == "problem"
                        and audit_decision == "AUTO_ACCEPT"
                        and decision.get("qwen_problem_requery", {}).get(
                            "auto_accept_eligible"
                        ) is True
                    )
                )
            )
            if expected_missing and detected_missing:
                missing_tp += 1
            elif detected_missing and not expected_missing:
                missing_fp += 1
            elif expected_missing:
                missing_fn += 1

            expected_unsupported = silver_present and not gold_present
            detected_unsupported = (
                silver_present
                and audit_decision == "REJECTED"
                and qwen.get("support_status") in ("UNSUPPORTED", "NOT_MENTIONED")
            )
            if expected_unsupported and detected_unsupported:
                unsupported_tp += 1
            elif detected_unsupported and not expected_unsupported:
                unsupported_fp += 1
            elif expected_unsupported:
                unsupported_fn += 1

            if gold_present and silver_present:
                gold_text = facet_text(gold_facets.get(facet, ""))
                gold_tokens = normalize_tokens(gold_text)
                silver_tokens = normalize_tokens(silver_text)
                union = gold_tokens | silver_tokens
                jaccard_scores.append(len(gold_tokens & silver_tokens) / len(union) if union else 1.0)

        def summarize(tp, fp, fn):
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            return {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }

        results["facet_metrics"][facet] = {
            "matched_papers": matched_papers,
            "silver_missing_detection": summarize(missing_tp, missing_fp, missing_fn),
            "unsupported_silver_detection": summarize(
                unsupported_tp, unsupported_fp, unsupported_fn
            ),
            "silver_gold_token_jaccard": round(
                sum(jaccard_scores) / len(jaccard_scores), 4
            ) if jaccard_scores else 0.0,
            "jaccard_pairs": len(jaccard_scores),
        }

    exploratory_heldout = (
        evaluation_phase == "heldout"
        and os.environ.get("DATA_PREPARATION_EXPLORATORY_HELDOUT") == "1"
    )
    report_name = (
        "exploratory_heldout_audit_evaluation_report.json"
        if exploratory_heldout
        else "audit_evaluation_report.json"
    )
    report_path = EVAL_DIR / report_name
    with open(report_path, "w", encoding="utf-8") as output:
        json.dump(results, output, indent=2, ensure_ascii=False)
    print(
        f"Gold split: {len(calibration_records)} calibration / "
        f"{len(heldout_records)} held-out papers; evaluated phase={evaluation_phase} "
        f"({results['evaluated_matched_papers']}/{results['evaluated_papers']} matched)."
    )
    if exploratory_heldout:
        print(
            "Exploratory heldout metrics are diagnostic only. Tuning from these results "
            "means they are no longer an independent final evaluation."
        )
    else:
        print("Calibration metrics are diagnostic only; review prompts and rules manually before full-corpus use.")
    print(f"Saved held-out audit evaluation to {report_path}")


if __name__ == "__main__":
    main()
