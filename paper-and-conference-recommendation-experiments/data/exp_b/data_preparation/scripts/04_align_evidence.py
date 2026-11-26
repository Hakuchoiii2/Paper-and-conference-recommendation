"""Step 2: Retrieve sentence-level evidence candidates with all-MiniLM-L6-v2.

Cosine similarity ranks candidates only; it is not used as a correctness
threshold. Qwen performs the semantic support judgment in step 05.
"""

import json
from pathlib import Path
import sys

import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_preparation.pipeline_scope import filter_by_scope

INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"

FACETS = ("problem", "task", "method", "dataset", "contribution")
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K_CANDIDATES = 3


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as file:
        return [json.loads(line) for line in file]


def index_by_paper(rows, path):
        indexed = {}
        for line_no, row in enumerate(rows, 1):
            paper_id = row.get("paper_id")
            if not paper_id:
                raise ValueError(f"{path}:{line_no}: missing paper_id")
            if paper_id in indexed:
                raise ValueError(f"{path}:{line_no}: duplicate paper_id {paper_id}")
            indexed[paper_id] = row
        return indexed


def main():
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    sentences_path = INTERMEDIATE_DIR / "source_sentences.jsonl"
    silver_path = INPUT_DIR / "silver_facets.jsonl"

    sentences_by_paper = {
        paper_id: row["sentences"]
        for paper_id, row in index_by_paper(
            filter_by_scope(read_jsonl(sentences_path)), sentences_path
        ).items()
    }
    silver_by_paper = index_by_paper(filter_by_scope(read_jsonl(silver_path)), silver_path)
    print(f"Loaded source sentences for {len(sentences_by_paper)} papers.")

    try:
        encoder = SentenceTransformer(MODEL_NAME, local_files_only=True)
    except Exception as exc:
        raise RuntimeError(
            f"The {MODEL_NAME} embedding model is not available locally. "
            "Run data_preparation\\setup_semantic_models.ps1 to prepare the models."
        ) from exc

    evidence_records = []
    audit_records = []
    paper_ids = sorted(sentences_by_paper)
    for index, paper_id in enumerate(paper_ids, 1):
        sentences = sentences_by_paper[paper_id]
        silver_row = silver_by_paper.get(paper_id, {})
        evidence = {}
        max_similarities = {}
        candidate_details = {}
        audit_flags = {}

        if not sentences:
            for facet in FACETS:
                evidence[facet] = []
                max_similarities[facet] = None
                candidate_details[facet] = []
                audit_flags[facet] = "NO_SENTENCES"
        else:
            sentence_texts = [row["text"] for row in sentences]
            sentence_embeddings = encoder.encode(
                sentence_texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            populated_facets = []
            facet_texts = []
            for facet in FACETS:
                concepts = silver_row.get(facet, [])
                if not isinstance(concepts, list) or any(not isinstance(item, str) for item in concepts):
                    raise ValueError(f"Silver facet {paper_id}/{facet} must be a list of strings")
                if concepts:
                    populated_facets.append(facet)
                    facet_texts.append(" ".join(concepts))
                else:
                    evidence[facet] = []
                    max_similarities[facet] = None
                    candidate_details[facet] = []
                    audit_flags[facet] = "EMPTY_FACET"

            facet_embeddings = encoder.encode(
                facet_texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            ) if facet_texts else []

            for facet, facet_embedding in zip(populated_facets, facet_embeddings):
                similarities = np.dot(sentence_embeddings, facet_embedding)
                ranked_indices = np.argsort(similarities)[::-1][:TOP_K_CANDIDATES]
                candidates = [
                    {
                        "sentence_id": sentences[int(sentence_index)]["sentence_id"],
                        "text": sentences[int(sentence_index)]["text"],
                        "similarity": round(float(similarities[sentence_index]), 4),
                    }
                    for sentence_index in ranked_indices
                ]
                evidence[facet] = [candidate["sentence_id"] for candidate in candidates]
                max_similarities[facet] = candidates[0]["similarity"] if candidates else None
                candidate_details[facet] = candidates
                audit_flags[facet] = "CANDIDATES_AVAILABLE" if candidates else "NO_SENTENCES"

        evidence_records.append({"paper_id": paper_id, "evidence": evidence})
        audit_records.append({
            "paper_id": paper_id,
            "model": MODEL_NAME,
            "similarities": max_similarities,
            "candidate_details": candidate_details,
            "audit_flags": audit_flags,
        })
        if index % 500 == 0 or index == len(paper_ids):
            print(f"Aligned {index}/{len(paper_ids)} papers.")

    evidence_path = INTERMEDIATE_DIR / "evidence_candidates.jsonl"
    with open(evidence_path, "w", encoding="utf-8") as output:
        for record in evidence_records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    audit_path = INTERMEDIATE_DIR / "embedding_audit.jsonl"
    with open(audit_path, "w", encoding="utf-8") as output:
        for record in audit_records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Saved top-{TOP_K_CANDIDATES} evidence candidates to {evidence_path}")
    print(f"Saved embedding similarities and candidate details to {audit_path}")


if __name__ == "__main__":
    main()
