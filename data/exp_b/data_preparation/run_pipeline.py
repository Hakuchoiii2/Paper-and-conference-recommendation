"""Run the Gold audit/calibration phase first, then explicitly approve full-corpus use."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_DIR.parent
SCRIPTS_DIR = PIPELINE_DIR / "scripts"
INPUT_DIR = PIPELINE_DIR / "input"
EVALUATION_DIR = PIPELINE_DIR / "evaluation"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_preparation.pipeline_scope import split_gold_ids

STEPS = [
    ("01_validate_structure.py", "Structural Validation"),
    ("02_split_source_sentences.py", "Split Source Sentences"),
    ("03_generate_embeddings.py", "Embedding Model Readiness"),
    ("04_align_evidence.py", "MiniLM Evidence Candidate Retrieval"),
    ("05_qwen_semantic_audit.py", "Required Qwen Semantic Audit via Ollama"),
    ("06_make_decisions.py", "Automated Decisions"),
    ("07_export_human_review.py", "Human Review Queue and Stratified QC Sample"),
    ("08_merge_validated_silver.py", "Merge Validated Silver"),
    ("09_evaluate_audit.py", "Held-out Gold Evaluation"),
]


def load_gold_ids():
    gold_path = INPUT_DIR / "gold_facets_400.jsonl"
    if not gold_path.exists():
        raise FileNotFoundError(f"Gold calibration input is missing: {gold_path}")
    paper_ids = []
    seen = set()
    with open(gold_path, "r", encoding="utf-8") as file:
        for line_no, line in enumerate(file, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{gold_path}:{line_no}: invalid JSON: {exc}") from exc
            paper_id = row.get("paper_id") if isinstance(row, dict) else None
            if not isinstance(paper_id, str) or not paper_id:
                raise ValueError(f"{gold_path}:{line_no}: missing paper_id")
            if paper_id in seen:
                raise ValueError(f"{gold_path}:{line_no}: duplicate paper_id {paper_id}")
            seen.add(paper_id)
            paper_ids.append(paper_id)
    if not paper_ids:
        raise ValueError(f"Gold calibration input is empty: {gold_path}")
    return paper_ids


def load_evaluation_report():
    report_path = EVALUATION_DIR / "audit_evaluation_report.json"
    if not report_path.exists():
        raise RuntimeError(
            "The required Gold evaluation report is missing. Run the prior Gold phase first."
        )
    with open(report_path, "r", encoding="utf-8") as report_file:
        return json.load(report_file)


def verify_calibration_report(paper_ids, calibration_count):
    report = load_evaluation_report()
    expected_hash = hashlib.sha256("\n".join(sorted(paper_ids)).encode("utf-8")).hexdigest()
    if report.get("gold_paper_ids_sha256") != expected_hash:
        raise RuntimeError("The calibration report does not match the current Gold paper IDs.")
    if report.get("evaluation_phase") != "calibration":
        raise RuntimeError("Run the calibration phase before the held-out phase.")
    if report.get("evaluated_matched_papers") != calibration_count:
        raise RuntimeError("The Gold calibration evaluation is incomplete.")


def verify_gold_evaluation(paper_ids, heldout_count):
    report = load_evaluation_report()
    expected_hash = hashlib.sha256("\n".join(sorted(paper_ids)).encode("utf-8")).hexdigest()
    if report.get("gold_paper_ids_sha256") != expected_hash:
        raise RuntimeError("The Gold evaluation report does not match the current Gold paper IDs.")
    if report.get("evaluation_phase") != "heldout":
        raise RuntimeError("Run the held-out evaluation after manual calibration before full mode.")
    if report.get("evaluated_matched_papers") != heldout_count:
        raise RuntimeError("The Gold held-out evaluation is incomplete; full-corpus mode is blocked.")
    if report.get("calibration_review_confirmed") is not True:
        raise RuntimeError("The report does not record confirmation of the manual calibration review.")


def run_preflight(environment):
    for script_name, description in (
        ("03_generate_embeddings.py", "Embedding model preflight"),
        ("05_qwen_semantic_audit.py", "Qwen semantic audit preflight"),
    ):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script_name), "--check-only"],
            env=environment,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"{description} failed; no data-preparation steps were run.")


def main():
    parser = argparse.ArgumentParser(description="Run Silver data preparation using Qwen semantic audit.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Audit the full corpus after the calibration and held-out phases.",
    )
    parser.add_argument(
        "--phase",
        choices=("calibration", "heldout"),
        default="calibration",
        help="Gold subset phase; calibration uses 70%%, heldout uses 30%%.",
    )
    parser.add_argument(
        "--confirm-calibration-review",
        action="store_true",
        help="Confirm that calibration results and rule/prompt changes were reviewed before heldout.",
    )
    parser.add_argument(
        "--exploratory-heldout",
        action="store_true",
        help=(
            "Run heldout diagnostically before calibration review; keeps review confirmation "
            "false and writes a separate report."
        ),
    )
    parser.add_argument(
        "--confirm-gold-review",
        action="store_true",
        help="Confirm that Gold independence and held-out results were reviewed before full mode.",
    )
    args = parser.parse_args()

    if args.full and args.phase != "calibration":
        parser.error("--phase cannot be combined with --full.")
    if args.full and args.confirm_calibration_review:
        parser.error("--confirm-calibration-review cannot be combined with --full.")
    if args.exploratory_heldout and (args.full or args.phase != "heldout"):
        parser.error("--exploratory-heldout requires --phase heldout and cannot be combined with --full.")
    if args.exploratory_heldout and args.confirm_calibration_review:
        parser.error("--exploratory-heldout cannot be combined with --confirm-calibration-review.")
    gold_ids = load_gold_ids()
    calibration_ids, heldout_ids = split_gold_ids(gold_ids)
    environment = os.environ.copy()
    if args.full:
        if not args.confirm_gold_review:
            parser.error("--full requires --confirm-gold-review after inspecting Gold evaluation.")
        verify_gold_evaluation(gold_ids, len(heldout_ids))
        environment.pop("DATA_PREPARATION_SCOPE_IDS", None)
        environment.pop("DATA_PREPARATION_EXPLORATORY_HELDOUT", None)
        environment["DATA_PREPARATION_EVAL_PHASE"] = "full"
        environment["DATA_PREPARATION_CALIBRATION_REVIEW_CONFIRMED"] = "1"
        print("Full-corpus mode enabled after Gold evaluation verification.")
    else:
        if args.confirm_gold_review:
            parser.error("--confirm-gold-review is only valid with --full.")
        if args.phase == "calibration":
            if args.confirm_calibration_review:
                parser.error("--confirm-calibration-review is only valid with --phase heldout.")
            selected_ids = calibration_ids
            environment["DATA_PREPARATION_EVAL_PHASE"] = "calibration"
            environment.pop("DATA_PREPARATION_CALIBRATION_REVIEW_CONFIRMED", None)
            environment.pop("DATA_PREPARATION_EXPLORATORY_HELDOUT", None)
        else:
            if not args.confirm_calibration_review and not args.exploratory_heldout:
                parser.error("--phase heldout requires --confirm-calibration-review.")
            verify_calibration_report(gold_ids, len(calibration_ids))
            selected_ids = heldout_ids
            environment["DATA_PREPARATION_EVAL_PHASE"] = "heldout"
            if args.exploratory_heldout:
                environment.pop("DATA_PREPARATION_CALIBRATION_REVIEW_CONFIRMED", None)
                environment["DATA_PREPARATION_EXPLORATORY_HELDOUT"] = "1"
                print(
                    "Running exploratory heldout without calibration review confirmation. "
                    "These results are diagnostic, not final."
                )
            else:
                environment.pop("DATA_PREPARATION_EXPLORATORY_HELDOUT", None)
                environment["DATA_PREPARATION_CALIBRATION_REVIEW_CONFIRMED"] = "1"
        environment["DATA_PREPARATION_SCOPE_IDS"] = ",".join(sorted(selected_ids))
        print(
            f"Running Gold {args.phase} phase for {len(selected_ids)} papers. "
            "The remaining corpus will not be processed in this phase."
        )

    run_preflight(environment)
    print("Qwen is mandatory. The pipeline will stop on any model, response, or schema error.")

    for script_name, description in STEPS:
        print(f"\n>>> {description}: {script_name}")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script_name)],
            env=environment,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"{script_name} failed with exit code {result.returncode}; pipeline stopped.")

    if args.full:
        print("Full-corpus audit completed. Review the generated output and quality report.")
    elif args.phase == "calibration":
        print(
            "Calibration phase completed. Review calibration metrics, then manually adjust the prompt/rules "
            "before running --phase heldout --confirm-calibration-review or "
            "--phase heldout --exploratory-heldout."
        )
    elif args.exploratory_heldout:
        print(
            "Exploratory heldout completed. Review evaluation/exploratory_heldout_audit_evaluation_report.json. "
            "The calibration report is preserved; tune calibration before a final heldout run."
        )
    else:
        print(
            "Held-out evaluation completed. Inspect evaluation/audit_evaluation_report.json before "
            "running --full --confirm-gold-review."
        )


if __name__ == "__main__":
    main()
