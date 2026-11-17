"""04_align_evidence.py
Bước 2: Evidence Alignment (all-MiniLM-L6-v2)
So sánh từng facet Silver với các câu trong title và abstract để tìm câu bằng chứng hỗ trợ.
Output:
- data_preparation/intermediate/evidence_candidates.jsonl
- data_preparation/intermediate/embedding_audit.jsonl
"""

import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"

FACETS = ("problem", "task", "method", "dataset", "contribution")
MIN_ALIGNMENT_THRESHOLD = 0.35  # Ngưỡng cosine tối thiểu để coi một câu là có hỗ trợ

def main():
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    sentences_path = INTERMEDIATE_DIR / "source_sentences.jsonl"
    silver_path = INPUT_DIR / "silver_facets.jsonl"

    print("--> Đang tải dữ liệu câu nguồn và silver facets...")
    with open(sentences_path, "r", encoding="utf-8") as f:
        sentences_by_paper = {row["paper_id"]: row["sentences"] for row in (json.loads(line) for line in f)}

    with open(silver_path, "r", encoding="utf-8") as f:
        silver_by_paper = {row["paper_id"]: row for row in (json.loads(line) for line in f)}

    print(f"--> Đã nạp {len(sentences_by_paper)} bài báo.")

    print("--> Đang khởi tạo SentenceTransformer('all-MiniLM-L6-v2')...")
    try:
        encoder = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    except Exception:
        encoder = SentenceTransformer("all-MiniLM-L6-v2")

    # Gom toàn bộ câu và facet text cần mã hóa theo từng paper
    print("--> Đang tiến hành Evidence Alignment trên từng bài báo...")
    evidence_records = []
    audit_records = []

    total_papers = len(sentences_by_paper)
    matched_facets_count = 0
    total_present_facets = 0

    paper_ids = sorted(sentences_by_paper.keys())
    
    # Để tối ưu tốc độ CPU, xử lý theo từng batch bài báo
    BATCH_SIZE = 100
    for b_start in range(0, total_papers, BATCH_SIZE):
        batch_pids = paper_ids[b_start: b_start + BATCH_SIZE]
        
        for pid in batch_pids:
            sents = sentences_by_paper[pid]
            s_row = silver_by_paper.get(pid, {})
            
            if not sents:
                evidence_records.append({"paper_id": pid, "evidence": {f: [] for f in FACETS}})
                audit_records.append({"paper_id": pid, "similarities": {f: 0.0 for f in FACETS}, "status": "NO_SENTENCES"})
                continue

            sent_texts = [s["text"] for s in sents]
            # Mã hóa các câu của bài báo
            sent_embs = encoder.encode(sent_texts, normalize_embeddings=True, show_progress_bar=False)

            paper_evidence = {}
            paper_sims = {}
            paper_audit = {}

            for f in FACETS:
                concepts = s_row.get(f, [])
                if not concepts:
                    paper_evidence[f] = []
                    paper_sims[f] = 0.0
                    paper_audit[f] = "EMPTY"
                    continue

                total_present_facets += 1
                facet_text = " ".join(concepts)
                f_emb = encoder.encode(facet_text, normalize_embeddings=True, show_progress_bar=False)

                # Tính cosine similarity với tất cả các câu trong bài
                sims = np.dot(sent_embs, f_emb)
                best_idx = int(np.argmax(sims))
                best_sim = float(sims[best_idx])
                best_sent_id = sents[best_idx]["sentence_id"]

                paper_sims[f] = round(best_sim, 4)

                if best_sim >= MIN_ALIGNMENT_THRESHOLD:
                    paper_evidence[f] = [best_sent_id]
                    paper_audit[f] = "ALIGNED"
                    matched_facets_count += 1
                else:
                    paper_evidence[f] = []
                    paper_audit[f] = "WEAK_EVIDENCE"

            evidence_records.append({
                "paper_id": pid,
                "evidence": paper_evidence
            })

            audit_records.append({
                "paper_id": pid,
                "similarities": paper_sims,
                "audit_flags": paper_audit
            })

        if (b_start + BATCH_SIZE) % 500 == 0 or (b_start + BATCH_SIZE) >= total_papers:
            processed = min(b_start + BATCH_SIZE, total_papers)
            print(f"    Đã xử lý {processed}/{total_papers} bài ({processed/total_papers*100:.1f}%)...")

    # Lưu kết quả
    ev_path = INTERMEDIATE_DIR / "evidence_candidates.jsonl"
    with open(ev_path, "w", encoding="utf-8") as f:
        for r in evidence_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    audit_path = INTERMEDIATE_DIR / "embedding_audit.jsonl"
    with open(audit_path, "w", encoding="utf-8") as f:
        for r in audit_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("\n==================== KẾT QUẢ EVIDENCE ALIGNMENT ====================")
    print(f"Tổng số facet có mặt: {total_present_facets}")
    print(f"Số facet tìm thấy câu bằng chứng hỗ trợ tốt (Cosine >= {MIN_ALIGNMENT_THRESHOLD}): {matched_facets_count} ({matched_facets_count/total_present_facets*100:.1f}%)")
    print(f"Số facet bằng chứng yếu hoặc nghi ngờ: {total_present_facets - matched_facets_count} ({(total_present_facets - matched_facets_count)/total_present_facets*100:.1f}%)")
    print(f"-> Đã lưu danh sách bằng chứng tại: {ev_path}")
    print(f"-> Đã lưu báo cáo tương đồng tại: {audit_path}")

if __name__ == "__main__":
    main()
