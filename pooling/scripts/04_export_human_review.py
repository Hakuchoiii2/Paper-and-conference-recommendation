"""04_export_human_review.py
Bước 4 trong Pooling Pipeline: Chuẩn bị Hàng đợi Đánh giá cho Con người (Human Review Queue).
- Ghép nối Query Paper và Candidate Paper với metadata đầy đủ:
    * Title và Abstract của Query
    * Title và Abstract của Candidate
    * Các Facet (Problem, Task, Method, Dataset, Contribution) đã được audit
    * Danh sách các phương pháp đã phát hiện ra Candidate này (retrieved_by)
- Khởi tạo file xác nhận đánh giá: pooling/human_review/human_judgments.jsonl
    với trạng thái mặc định: UNJUDGED (Mục 4: Tuyệt đối không tự ý gán 0).
- Thang điểm đánh giá:
    0: Không liên quan
    1: Có liên quan nhẹ, giá trị sử dụng hạn chế
    2: Có liên quan đáng kể
    3: Rất liên quan, có giá trị tham khảo trực tiếp

Output:
- pooling/human_review/review_queue.jsonl
- pooling/human_review/human_judgments.jsonl
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POOLING_DIR = PROJECT_ROOT / "pooling"
CONFIG_PATH = POOLING_DIR / "config" / "pooling_config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_path(p_str):
    p = Path(p_str)
    return p if p.is_absolute() else PROJECT_ROOT / p

def main():
    config = load_config()
    paths = config.get("paths", {})

    dedup_pool_file = resolve_path(paths.get("output_deduplicated_pool", "pooling/output/deduplicated_pool.jsonl"))
    queue_file = resolve_path(paths.get("human_review_queue", "pooling/human_review/review_queue.jsonl"))
    judgments_file = resolve_path(paths.get("human_judgments", "pooling/human_review/human_judgments.jsonl"))
    corpus_file = resolve_path(paths.get("papers_corpus", "data_preparation/input/papers.jsonl"))
    val_silver_file = resolve_path(paths.get("validated_silver", "data_preparation/output/validated_silver.jsonl"))

    queue_file.parent.mkdir(parents=True, exist_ok=True)

    print("="*75)
    print("BƯỚC 4: CHUẨN BỊ HÀNG ĐỢI ĐÁNH GIÁ HUMAN RELEVANCE REVIEW")
    print("="*75)

    if not dedup_pool_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy deduplicated_pool.jsonl tại {dedup_pool_file}")
        print("    Vui lòng chạy Bước 2 và Bước 3 trước.")
        return

    # Tải thông tin văn bản gốc
    print("--> Đang tải dữ liệu văn bản (Title & Abstract)...")
    papers_raw = {}
    if corpus_file.exists():
        with open(corpus_file, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                papers_raw[r["paper_id"]] = {
                    "title": r.get("title", ""),
                    "abstract": r.get("abstract", "")
                }

    # Tải thông tin facets
    silver_facets = {}
    if val_silver_file.exists():
        with open(val_silver_file, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                silver_facets[r["paper_id"]] = r.get("facets", {})

    # Tải lại các đánh giá đã có từ trước (nếu đang chạy bổ sung)
    existing_judgments = {}
    if judgments_file.exists():
        with open(judgments_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    existing_judgments[(r["query_id"], r["candidate_id"])] = r
                except Exception:
                    pass
        print(f"[+] Đã tìm thấy {len(existing_judgments)} đánh giá sẵn có từ trước. Sẽ bảo tồn các đánh giá này.")

    print("--> Đang ghép nối thông tin Query và Candidate...")
    review_queue = []
    template_judgments = []

    with open(dedup_pool_file, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            qid = r["query_id"]
            cid = r["candidate_id"]
            retrieved_by = r.get("retrieved_by", [])
            method_details = r.get("method_details", {})

            q_info = papers_raw.get(qid, {})
            c_info = papers_raw.get(cid, {})

            q_facets = silver_facets.get(qid, {})
            c_facets = silver_facets.get(cid, {})

            key = (qid, cid)
            prev_judgment = existing_judgments.get(key)

            review_item = {
                "query_id": qid,
                "candidate_id": cid,
                "retrieved_by": retrieved_by,
                "source_count": len(retrieved_by),
                "method_details": method_details,
                "query_title": q_info.get("title", ""),
                "query_abstract": q_info.get("abstract", ""),
                "query_facets": q_facets,
                "candidate_title": c_info.get("title", ""),
                "candidate_abstract": c_info.get("abstract", ""),
                "candidate_facets": c_facets,
                "current_judgment": prev_judgment.get("human_grade", "UNJUDGED") if prev_judgment else "UNJUDGED"
            }
            review_queue.append(review_item)

            if prev_judgment and prev_judgment.get("human_grade") not in ("UNJUDGED", None):
                template_judgments.append(prev_judgment)
            else:
                template_judgments.append({
                    "query_id": qid,
                    "candidate_id": cid,
                    "human_grade": "UNJUDGED",  # Người đánh giá điền: 0, 1, 2, hoặc 3
                    "notes": "",
                    "retrieved_by": retrieved_by
                })

    with open(queue_file, "w", encoding="utf-8") as f:
        for item in review_queue:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(judgments_file, "w", encoding="utf-8") as f:
        for item in template_judgments:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n[+] Đã xuất {len(review_queue)} cặp vào Hàng đợi Đánh giá:")
    print(f"    - Review Queue: {queue_file}")
    print(f"    - Judgments Template: {judgments_file}")
    print("--> Hoàn tất Bước 4. Sẵn sàng cho người thẩm định đánh giá Grade 0–3.")

if __name__ == "__main__":
    main()
