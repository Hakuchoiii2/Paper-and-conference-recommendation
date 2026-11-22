"""Step 4: Combine structure, MiniLM retrieval, and mandatory Qwen audit signals."""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_preparation.pipeline_scope import get_scope_ids

INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"

FACETS = ("problem", "task", "method", "dataset", "contribution")
MODEL_NAME = "qwen3:4b"


def load_by_paper(path, value_key=None):
    records = {}
    with open(path, "r", encoding="utf-8") as file:
        for line_no, line in enumerate(file, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            paper_id = row.get("paper_id")
            if not paper_id:
                raise ValueError(f"{path}:{line_no}: missing paper_id")
            if paper_id in records:
                raise ValueError(f"{path}:{line_no}: duplicate paper_id {paper_id}")
            records[paper_id] = row[value_key] if value_key else row
    return records


def main():
    structure_by_id = load_by_paper(INTERMEDIATE_DIR / "structural_report.jsonl")
    evidence_by_id = load_by_paper(INTERMEDIATE_DIR / "evidence_candidates.jsonl", "evidence")
    audit_by_id = load_by_paper(INTERMEDIATE_DIR / "qwen_audit.jsonl")
    silver_by_id = load_by_paper(INPUT_DIR / "silver_facets.jsonl")
    scope_ids = get_scope_ids()
    if scope_ids is not None:
        structure_by_id = {
            paper_id: row for paper_id, row in structure_by_id.items() if paper_id in scope_ids
        }

    decisions = []
    stats = {
        "facet_status": {},
        "audit_decision": {"AUTO_ACCEPT": 0, "NEEDS_REVIEW": 0, "REJECTED": 0},
        "paper_status": {"VALIDATED": 0, "NEEDS_REVIEW": 0, "REJECTED": 0},
    }

    for paper_id in sorted(structure_by_id):
        structural = structure_by_id[paper_id]
        structural_issues = set(structural.get("issues", []))
        silver_row = silver_by_id.get(paper_id, {})
        qwen_record = audit_by_id.get(paper_id)
        if not qwen_record:
            raise ValueError(f"Missing Qwen audit record for {paper_id}")
        provenance = qwen_record.get("provenance", {})

        source_missing = (
            "PAPER_NOT_IN_CORPUS" in structural_issues
            or "EMPTY_ABSTRACT" in structural_issues
        )
        source_truncated = "TRUNCATED_ABSTRACT" in structural_issues
        silver_missing = "PAPER_NOT_IN_SILVER" in structural_issues
        if source_missing or source_truncated:
            expected_audit_status = (
                "SKIPPED_SOURCE_MISSING" if source_missing else "SKIPPED_SOURCE_TRUNCATED"
            )
            if (
                qwen_record.get("audit_status") != expected_audit_status
                or provenance.get("engine") != "not_run"
                or provenance.get("model") is not None
            ):
                raise ValueError(f"Expected Qwen audit status {expected_audit_status} for {paper_id}")
            qwen_facets = {}
        else:
            if (
                qwen_record.get("audit_status") != "COMPLETED"
                or provenance.get("engine") != "ollama"
                or provenance.get("model") != MODEL_NAME
            ):
                raise ValueError(f"Qwen audit did not complete for {paper_id}")
            qwen_facets = qwen_record.get("semantic_audit", {})
            if set(qwen_facets) != set(FACETS):
                raise ValueError(f"Incomplete Qwen facet audit for {paper_id}")

        evidence = evidence_by_id.get(paper_id, {})
        facet_status = {}
        audit_decision = {}
        proposals = {}
        has_review = False

        for facet in FACETS:
            concepts = silver_row.get(facet, [])
            qwen = qwen_facets.get(facet, {}) if not source_missing else {}
            proposal = qwen.get("proposed_revision")
            if proposal:
                proposals[facet] = proposal
            if not isinstance(concepts, list) or any(not isinstance(value, str) for value in concepts):
                concepts = []
                facet_status[facet] = "EXTRACTION_FAILED"
                audit_decision[facet] = "NEEDS_REVIEW"
                has_review = True
            elif source_missing:
                facet_status[facet] = "SOURCE_MISSING"
                audit_decision[facet] = "NEEDS_REVIEW"
                has_review = True
            elif source_truncated:
                facet_status[facet] = "TRUNCATED"
                audit_decision[facet] = "NEEDS_REVIEW"
                has_review = True
            elif (
                silver_missing
                or "EXP_A_FALLBACK_OR_ERROR" in structural_issues
                or f"INVALID_FACET_TYPE_{facet.upper()}" in structural_issues
                or f"INVALID_FACET_VALUE_TYPE_{facet.upper()}" in structural_issues
            ):
                facet_status[facet] = "EXTRACTION_FAILED"
                audit_decision[facet] = "NEEDS_REVIEW"
                has_review = True
            elif f"TRUNCATED_CONCEPT_{facet.upper()}" in structural_issues:
                facet_status[facet] = "TRUNCATED"
                audit_decision[facet] = "NEEDS_REVIEW"
                has_review = True
            elif facet == "problem" and not any(value.strip() for value in concepts):
                problem_requery = qwen_record.get("problem_requery", {})
                cited_ids = qwen.get("relevant_sentences")
                if (
                    problem_requery.get("auto_accept_eligible") is True
                    and qwen.get("support_status") in ("SUPPORTED", "PARTIALLY_SUPPORTED")
                    and qwen.get("detected_issues") == "missing"
                    and isinstance(cited_ids, list)
                    and cited_ids
                    and isinstance(proposal, str)
                    and proposal.strip()
                ):
                    facet_status[facet] = "PRESENT"
                    audit_decision[facet] = "AUTO_ACCEPT"
                    evidence[facet] = cited_ids
                else:
                    facet_status[facet] = "NOT_REVIEWED"
                    audit_decision[facet] = "NEEDS_REVIEW"
                    has_review = True
            else:
                support = qwen["support_status"]
                issue = qwen["detected_issues"]

                if not concepts and support == "NOT_MENTIONED" and issue == "none":
                    facet_status[facet] = "NOT_MENTIONED"
                    audit_decision[facet] = "AUTO_ACCEPT"
                elif not concepts:
                    facet_status[facet] = "NOT_REVIEWED"
                    audit_decision[facet] = "NEEDS_REVIEW"
                    has_review = True
                elif support == "NOT_MENTIONED":
                    facet_status[facet] = "NOT_MENTIONED"
                    audit_decision[facet] = "REJECTED"
                    has_review = True
                elif support == "UNSUPPORTED" and issue in ("hallucination", "none"):
                    facet_status[facet] = "NOT_REVIEWED"
                    audit_decision[facet] = "REJECTED"
                    has_review = True
                elif issue == "truncated":
                    facet_status[facet] = "TRUNCATED"
                    audit_decision[facet] = "NEEDS_REVIEW"
                    has_review = True
                elif (
                    support != "SUPPORTED"
                    or issue != "none"
                ):
                    facet_status[facet] = "PRESENT"
                    audit_decision[facet] = "NEEDS_REVIEW"
                    has_review = True
                else:
                    cited_ids = set(qwen["relevant_sentences"])
                    candidate_ids = set(evidence.get(facet, []))
                    if not cited_ids or not cited_ids.intersection(candidate_ids):
                        facet_status[facet] = "PRESENT"
                        audit_decision[facet] = "NEEDS_REVIEW"
                        has_review = True
                    else:
                        facet_status[facet] = "PRESENT"
                        audit_decision[facet] = "AUTO_ACCEPT"

            decision = audit_decision[facet]
            stats["audit_decision"][decision] += 1
            stats["facet_status"][facet_status[facet]] = (
                stats["facet_status"].get(facet_status[facet], 0) + 1
            )

        rejected_count = sum(value == "REJECTED" for value in audit_decision.values())
        if rejected_count == len(FACETS):
            paper_status = "REJECTED"
        elif has_review or rejected_count:
            paper_status = "NEEDS_REVIEW"
        else:
            paper_status = "VALIDATED"
        stats["paper_status"][paper_status] += 1

        decisions.append({
            "paper_id": paper_id,
            "facet_status": facet_status,
            "audit_decision": audit_decision,
            "evidence": evidence,
            "qwen_proposals": proposals,
            "qwen_audit": qwen_facets,
            "qwen_problem_requery": qwen_record.get("problem_requery", {}),
            "qwen_provenance": provenance,
            "paper_validation_status": paper_status,
        })

    output_path = INTERMEDIATE_DIR / "automated_decisions.jsonl"
    with open(output_path, "w", encoding="utf-8") as output:
        for record in decisions:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Paper validation statuses: {stats['paper_status']}")
    print(f"Facet audit decisions: {stats['audit_decision']}")
    print(f"Facet content statuses: {stats['facet_status']}")
    print(f"Saved automated decisions to {output_path}")


if __name__ == "__main__":
    main()
