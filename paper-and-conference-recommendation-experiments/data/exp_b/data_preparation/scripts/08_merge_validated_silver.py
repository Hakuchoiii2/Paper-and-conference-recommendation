"""Merge accepted facets and retain pending facet text for review."""

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_preparation.pipeline_scope import get_scope_ids

INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
OUTPUT_DIR = PROJECT_ROOT / "data_preparation" / "output"
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
HUMAN_DIR = PROJECT_ROOT / "data_preparation" / "human_review"

FACETS = ("problem", "task", "method", "dataset", "contribution")
FACET_STATUSES = {
    "PRESENT",
    "NOT_MENTIONED",
    "SOURCE_MISSING",
    "TRUNCATED",
    "EXTRACTION_FAILED",
    "NOT_REVIEWED",
}
HUMAN_REVIEW_SOURCES = {"cli", "web_ui", "spreadsheet_import"}


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as file:
        rows = []
        for line_no, line in enumerate(file, 1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def normalize_revised_facet(value, paper_id, facet):
    if isinstance(value, str):
        concepts = [value.strip()] if value.strip() else []
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        concepts = [item.strip() for item in value if item.strip()]
    else:
        raise ValueError(f"Invalid human_revised_facet for {paper_id}/{facet}")
    return concepts


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    silver_by_id = {row["paper_id"]: row for row in load_jsonl(INPUT_DIR / "silver_facets.jsonl")}
    decisions_by_id = {
        row["paper_id"]: row for row in load_jsonl(INTERMEDIATE_DIR / "automated_decisions.jsonl")
    }
    scope_ids = get_scope_ids()
    if scope_ids is not None:
        decisions_by_id = {
            paper_id: row for paper_id, row in decisions_by_id.items() if paper_id in scope_ids
        }
    audit_by_id = {
        row["paper_id"]: row for row in load_jsonl(INTERMEDIATE_DIR / "qwen_audit.jsonl")
    }
    corrections_path = HUMAN_DIR / "human_corrections.jsonl"
    correction_by_key = {}
    if corrections_path.exists():
        for correction in load_jsonl(corrections_path):
            key = (correction.get("paper_id"), correction.get("facet"))
            if not all(key):
                raise ValueError(f"Invalid correction record without paper_id/facet: {correction}")
            if correction.get("review_source") not in HUMAN_REVIEW_SOURCES:
                continue
            if correction.get("human_decision") in ("ACCEPT", "REJECT", "REVISE"):
                correction_by_key[key] = correction

    generated_at = datetime.now(timezone.utc).isoformat()
    validated_records = []
    rejected_records = []
    needs_review_records = []
    stats = {
        "generated_at": generated_at,
        "total_records": len(decisions_by_id),
        "validated_papers": 0,
        "needs_review_papers": 0,
        "rejected_papers": 0,
        "human_reviewed_papers": 0,
        "ignored_unverified_corrections": 0,
        "facet_coverage": {
            facet: {
                "present": 0,
                "not_mentioned": 0,
                "source_missing": 0,
                "not_reviewed": 0,
                "evidence_grounded": 0,
                "rejected": 0,
            }
            for facet in FACETS
        },
    }

    if corrections_path.exists():
        for correction in load_jsonl(corrections_path):
            if (
                correction.get("human_decision") in ("ACCEPT", "REJECT", "REVISE")
                and correction.get("review_source") not in HUMAN_REVIEW_SOURCES
            ):
                stats["ignored_unverified_corrections"] += 1

    for paper_id in sorted(decisions_by_id):
        decision = decisions_by_id[paper_id]
        silver = silver_by_id.get(paper_id, {})
        model_provenance = decision.get("qwen_provenance", {})
        audit_record = audit_by_id.get(paper_id, {})
        if audit_record.get("provenance") != model_provenance:
            raise ValueError(f"Qwen audit provenance mismatch for {paper_id}")

        facet_status = dict(decision["facet_status"])
        audit_decision = dict(decision["audit_decision"])
        if audit_record.get("audit_status") in (
            "SKIPPED_SOURCE_MISSING",
            "SKIPPED_SOURCE_TRUNCATED",
        ):
            expected_status = (
                "SOURCE_MISSING"
                if audit_record["audit_status"] == "SKIPPED_SOURCE_MISSING"
                else "TRUNCATED"
            )
            if (
                model_provenance.get("engine") != "not_run"
                or model_provenance.get("model") is not None
                or any(status != expected_status for status in facet_status.values())
            ):
                raise ValueError(f"Invalid skipped-audit provenance for {paper_id}")
        elif (
            audit_record.get("audit_status") != "COMPLETED"
            or model_provenance.get("engine") != "ollama"
            or model_provenance.get("model") != "qwen3:4b"
        ):
            raise ValueError(f"Missing mandatory Qwen provenance for {paper_id}")
        qwen_facets = decision.get("qwen_audit", {})
        evidence = dict(decision.get("evidence", {}))
        final_facets = {}
        human_reviewed_facets = []

        for facet in FACETS:
            concepts = silver.get(facet, [])
            original_concepts = list(concepts) if isinstance(concepts, list) else []
            correction = correction_by_key.get((paper_id, facet))
            accepted_concepts = None

            if correction:
                human_reviewed_facets.append(facet)
                human_status = correction.get("human_facet_status")
                if human_status is not None and human_status not in FACET_STATUSES:
                    raise ValueError(f"Invalid human_facet_status for {paper_id}/{facet}: {human_status}")
                human_decision = correction["human_decision"]
                if human_decision == "ACCEPT":
                    if (
                        facet == "problem"
                        and not any(
                            isinstance(concept, str) and concept.strip()
                            for concept in original_concepts
                        )
                        and audit_record.get("audit_status") == "COMPLETED"
                    ):
                        raise ValueError(
                            f"An empty problem facet cannot be ACCEPTed for {paper_id}; "
                            "provide a source-grounded revision."
                        )
                    if human_status is not None and human_status not in ("PRESENT", "NOT_MENTIONED"):
                        raise ValueError(
                            f"ACCEPT requires PRESENT or NOT_MENTIONED status for {paper_id}/{facet}"
                        )
                    if original_concepts and human_status in (
                        "NOT_MENTIONED",
                        "SOURCE_MISSING",
                        "TRUNCATED",
                        "EXTRACTION_FAILED",
                    ):
                        raise ValueError(
                            f"ACCEPT conflicts with human_facet_status for {paper_id}/{facet}"
                        )
                    if not original_concepts and human_status == "PRESENT":
                        raise ValueError(f"Empty facet cannot be PRESENT for {paper_id}/{facet}")
                    accepted_concepts = original_concepts
                    if human_status:
                        facet_status[facet] = human_status
                    elif original_concepts:
                        facet_status[facet] = "PRESENT"
                    elif qwen_facets.get(facet, {}).get("support_status") == "NOT_MENTIONED":
                        facet_status[facet] = "NOT_MENTIONED"
                    else:
                        facet_status[facet] = "NOT_REVIEWED"
                        audit_decision[facet] = "NEEDS_REVIEW"
                    if facet_status[facet] in ("PRESENT", "NOT_MENTIONED"):
                        audit_decision[facet] = "AUTO_ACCEPT"
                elif human_decision == "REVISE":
                    accepted_concepts = normalize_revised_facet(
                        correction.get("human_revised_facet"), paper_id, facet
                    )
                    if not accepted_concepts:
                        raise ValueError(f"REVISE must provide facet content for {paper_id}/{facet}")
                    facet_status[facet] = "PRESENT"
                    audit_decision[facet] = "AUTO_ACCEPT"
                elif human_decision == "REJECT":
                    if (
                        facet == "problem"
                        and not any(
                            isinstance(concept, str) and concept.strip()
                            for concept in original_concepts
                        )
                        and audit_record.get("audit_status") == "COMPLETED"
                    ):
                        raise ValueError(
                            f"An empty problem facet cannot be REJECTed for {paper_id}; "
                            "provide a source-grounded revision."
                        )
                    if human_status == "PRESENT":
                        raise ValueError(f"REJECT conflicts with PRESENT status for {paper_id}/{facet}")
                    accepted_concepts = []
                    if human_status:
                        facet_status[facet] = human_status
                    elif qwen_facets.get(facet, {}).get("support_status") == "NOT_MENTIONED":
                        facet_status[facet] = "NOT_MENTIONED"
                    else:
                        facet_status[facet] = "NOT_REVIEWED"
                    audit_decision[facet] = "REJECTED"
            elif audit_decision[facet] == "AUTO_ACCEPT":
                if facet == "problem" and not any(
                    isinstance(concept, str) and concept.strip()
                    for concept in original_concepts
                ):
                    qwen = qwen_facets.get(facet, {})
                    cited_ids = qwen.get("relevant_sentences")
                    if (
                        audit_record.get("problem_requery", {}).get("auto_accept_eligible") is not True
                        or qwen.get("support_status") not in ("SUPPORTED", "PARTIALLY_SUPPORTED")
                        or qwen.get("detected_issues") != "missing"
                        or not isinstance(cited_ids, list)
                        or not cited_ids
                    ):
                        raise ValueError(
                            f"Empty problem facet lacks a grounded Qwen requery for {paper_id}"
                        )
                    accepted_concepts = normalize_revised_facet(
                        qwen.get("proposed_revision"), paper_id, facet
                    )
                    evidence[facet] = cited_ids
                else:
                    accepted_concepts = original_concepts
            elif audit_decision[facet] == "NEEDS_REVIEW":
                qwen = qwen_facets.get(facet, {})
                proposal = qwen.get("proposed_revision")
                if isinstance(proposal, str) and proposal.strip():
                    accepted_concepts = [proposal.strip()]
                    evidence[facet] = qwen.get("relevant_sentences", [])
                else:
                    usable_original = [
                        concept.strip() for concept in original_concepts
                        if isinstance(concept, str) and concept.strip()
                    ]
                    if (
                        usable_original
                        and facet_status[facet] == "PRESENT"
                        and qwen.get("support_status") == "SUPPORTED"
                        and qwen.get("detected_issues") == "none"
                    ):
                        accepted_concepts = usable_original
                    else:
                        accepted_concepts = []
                        evidence[facet] = []
                        needs_review_records.append({
                            "paper_id": paper_id,
                            "facet": facet,
                            "current_concepts": original_concepts,
                            "facet_status": facet_status[facet],
                            "audit_decision": "NEEDS_REVIEW",
                            "qwen_proposed_revision": None,
                            "qwen_support_status": qwen.get("support_status"),
                            "qwen_detected_issues": qwen.get("detected_issues"),
                            "qwen_relevant_sentence_ids": qwen.get("relevant_sentences", []),
                            "qwen_explanation": qwen.get("explanation"),
                        })
            else:
                accepted_concepts = []
                if audit_decision[facet] == "REJECTED":
                    qwen = qwen_facets.get(facet, {})
                    rejected_records.append({
                        "paper_id": paper_id,
                        "facet": facet,
                        "rejected_concepts": original_concepts,
                        "reason": qwen.get("explanation", "Rejected by semantic audit; awaiting human review"),
                        "human_reviewed": False,
                    })
                    if facet_status[facet] not in ("NOT_MENTIONED", "SOURCE_MISSING"):
                        facet_status[facet] = "NOT_REVIEWED"

            if audit_decision[facet] == "REJECTED":
                if correction:
                    rejected_records.append({
                        "paper_id": paper_id,
                        "facet": facet,
                        "rejected_concepts": original_concepts,
                        "reason": correction.get("human_notes", "Rejected by human reviewer"),
                        "human_reviewed": True,
                    })
                evidence[facet] = []

            final_facets[facet] = "; ".join(accepted_concepts or [])
            coverage = stats["facet_coverage"][facet]
            if audit_decision[facet] == "NEEDS_REVIEW" and facet_status[facet] == "PRESENT":
                coverage["not_reviewed"] += 1
            elif facet_status[facet] == "PRESENT" and final_facets[facet]:
                coverage["present"] += 1
                if evidence.get(facet):
                    coverage["evidence_grounded"] += 1
            elif facet_status[facet] == "NOT_MENTIONED":
                coverage["not_mentioned"] += 1
            elif facet_status[facet] == "SOURCE_MISSING":
                coverage["source_missing"] += 1
            else:
                coverage["not_reviewed"] += 1
            if audit_decision[facet] == "REJECTED":
                coverage["rejected"] += 1

        unresolved = [
            facet for facet in FACETS
            if audit_decision[facet] != "AUTO_ACCEPT"
            and (paper_id, facet) not in correction_by_key
        ]
        unresolved_statuses = {"SOURCE_MISSING", "TRUNCATED", "EXTRACTION_FAILED", "NOT_REVIEWED"}
        if unresolved or any(status in unresolved_statuses for status in facet_status.values()):
            paper_status = (
                "REJECTED"
                if all(audit_decision[facet] == "REJECTED" for facet in FACETS)
                else "NEEDS_REVIEW"
            )
        elif any(audit_decision[facet] == "NEEDS_REVIEW" for facet in FACETS):
            paper_status = "NEEDS_REVIEW"
        else:
            paper_status = "VALIDATED"
        if paper_status == "VALIDATED" and not final_facets.get("problem", "").strip():
            raise ValueError(
                f"Validated paper {paper_id} has an empty problem facet; refusing to merge."
            )

        stats_key = {
            "VALIDATED": "validated_papers",
            "NEEDS_REVIEW": "needs_review_papers",
            "REJECTED": "rejected_papers",
        }[paper_status]
        stats[stats_key] += 1
        if human_reviewed_facets:
            stats["human_reviewed_papers"] += 1

        validated_records.append({
            "paper_id": paper_id,
            "facets": final_facets,
            "facet_status": facet_status,
            "audit_decision": audit_decision,
            "evidence": evidence,
            "paper_validation_status": paper_status,
            "provenance": {
                "source": "exp_a_silver",
                "embedding_model": "all-MiniLM-L6-v2",
                "audit_engine": model_provenance["engine"],
                "audit_model": model_provenance["model"],
                "audit_prompt_version": model_provenance.get("prompt_version"),
                "human_reviewed": bool(human_reviewed_facets),
                "human_reviewed_facets": human_reviewed_facets,
                "review_version": "data_preparation_v2",
                "timestamp": generated_at,
            },
        })

    output_path = OUTPUT_DIR / "validated_silver.jsonl"
    with open(output_path, "w", encoding="utf-8") as output:
        for record in validated_records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    rejected_path = OUTPUT_DIR / "rejected_facets.jsonl"
    with open(rejected_path, "w", encoding="utf-8") as output:
        for record in rejected_records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    needs_review_path = OUTPUT_DIR / "needs_review.jsonl"
    with open(needs_review_path, "w", encoding="utf-8") as output:
        for record in needs_review_records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    report_path = OUTPUT_DIR / "data_quality_report.json"
    with open(report_path, "w", encoding="utf-8") as output:
        json.dump(stats, output, indent=2, ensure_ascii=False)

    print(f"Merge report: {stats}")
    print(f"Saved validated Silver to {output_path}")
    print(f"Saved rejected facet history to {rejected_path}")
    print(f"Saved {len(needs_review_records)} unresolved facets to {needs_review_path}")
    print(f"Saved quality report to {report_path}")


if __name__ == "__main__":
    main()
