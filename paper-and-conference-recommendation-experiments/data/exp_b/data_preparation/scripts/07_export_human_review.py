"""Step 5: Export every unresolved facet and a stratified AUTO_ACCEPT QC sample."""

import json
import math
from pathlib import Path
import random
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_preparation.pipeline_scope import get_scope_ids

INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
HUMAN_REVIEW_DIR = PROJECT_ROOT / "data_preparation" / "human_review"
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"

FACETS = ("problem", "task", "method", "dataset", "contribution")
QC_SAMPLE_RATE = 0.05


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as file:
        return [json.loads(line) for line in file]


def main():
    HUMAN_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    decisions = read_jsonl(INTERMEDIATE_DIR / "automated_decisions.jsonl")
    scope_ids = get_scope_ids()
    if scope_ids is not None:
        decisions = [row for row in decisions if row.get("paper_id") in scope_ids]
    papers_by_id = {row["paper_id"]: row for row in read_jsonl(INPUT_DIR / "papers.jsonl")}
    silver_by_id = {row["paper_id"]: row for row in read_jsonl(INPUT_DIR / "silver_facets.jsonl")}
    sentences_by_id = {
        row["paper_id"]: row["sentences"]
        for row in read_jsonl(INTERMEDIATE_DIR / "source_sentences.jsonl")
    }

    review_queue = []
    auto_accept_cases = {}
    for decision in decisions:
        paper_id = decision["paper_id"]
        paper = papers_by_id.get(paper_id, {})
        silver = silver_by_id.get(paper_id, {})
        sentences = sentences_by_id.get(paper_id, [])
        qwen_facets = decision.get("qwen_audit", {})
        evidence = decision.get("evidence", {})

        for facet in FACETS:
            audit_decision = decision["audit_decision"][facet]
            facet_status = decision["facet_status"][facet]
            qwen = qwen_facets.get(facet, {})
            evidence_ids = evidence.get(facet, [])
            evidence_texts = [
                sentence["text"]
                for sentence in sentences
                if sentence["sentence_id"] in evidence_ids
            ]
            item = {
                "paper_id": paper_id,
                "facet": facet,
                "current_concepts": silver.get(facet, []),
                "facet_status": facet_status,
                "audit_decision": audit_decision,
                "evidence_sentence_ids": evidence_ids,
                "evidence_texts": evidence_texts,
                "qwen_relevant_sentence_ids": qwen.get("relevant_sentences", []),
                "qwen_support_status": qwen.get("support_status"),
                "qwen_detected_issues": qwen.get("detected_issues"),
                "qwen_proposed_revision": qwen.get("proposed_revision"),
                "qwen_explanation": qwen.get("explanation"),
                "qwen_provenance": decision.get("qwen_provenance", {}),
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", ""),
            }
            if audit_decision in ("NEEDS_REVIEW", "REJECTED"):
                review_queue.append(item)
            elif audit_decision == "AUTO_ACCEPT":
                auto_accept_cases.setdefault((facet, facet_status), []).append(item)

    rng = random.Random(42)
    qc_sample = []
    for items in auto_accept_cases.values():
        sample_size = min(len(items), math.ceil(len(items) * QC_SAMPLE_RATE))
        qc_sample.extend(rng.sample(items, sample_size))
    for item in qc_sample:
        item["audit_decision"] = "AUTO_ACCEPT_QC_SAMPLE"
        review_queue.append(item)

    priority = {"REJECTED": 0, "NEEDS_REVIEW": 1, "AUTO_ACCEPT_QC_SAMPLE": 2}
    review_queue.sort(
        key=lambda item: (
            priority.get(item["audit_decision"], 3),
            item["paper_id"],
            item["facet"],
        )
    )

    queue_path = HUMAN_REVIEW_DIR / "review_queue.jsonl"
    with open(queue_path, "w", encoding="utf-8") as output:
        for item in review_queue:
            output.write(json.dumps(item, ensure_ascii=False) + "\n")

    corrections_path = HUMAN_REVIEW_DIR / "human_corrections.jsonl"
    existing_corrections = {}
    if corrections_path.exists():
        for line_no, row in enumerate(read_jsonl(corrections_path), 1):
            key = (row.get("paper_id"), row.get("facet"))
            if not all(key):
                raise ValueError(f"{corrections_path}:{line_no}: missing paper_id or facet")
            existing_corrections[key] = row

    corrections = dict(existing_corrections)
    for item in review_queue:
        key = (item["paper_id"], item["facet"])
        if key in corrections:
            continue
        proposal = item.get("qwen_proposed_revision")
        initial_revision = [proposal] if isinstance(proposal, str) and proposal else item["current_concepts"]
        corrections[key] = {
            "paper_id": item["paper_id"],
            "facet": item["facet"],
            "human_decision": "PENDING",
            "human_revised_facet": initial_revision,
            "human_notes": "",
        }

    with open(corrections_path, "w", encoding="utf-8") as output:
        for correction in corrections.values():
            output.write(json.dumps(correction, ensure_ascii=False) + "\n")

    print(f"Review queue contains {len(review_queue)} items, including {len(qc_sample)} QC samples.")
    print(f"Saved review queue to {queue_path}")
    print(f"Saved/preserved correction templates to {corrections_path}")


if __name__ == "__main__":
    main()
