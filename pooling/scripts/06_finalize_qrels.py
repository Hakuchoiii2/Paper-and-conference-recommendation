"""06_finalize_qrels.py
Bước 6 trong Pooling Pipeline: Khóa Bộ Qrels & Xuất Báo cáo Pooling (Deliverables).
- Kiểm tra tính hoàn thiện của các nhãn đánh giá.
- Xuất file Ground Truth chính thức: pooling/output/final_human_qrels.jsonl
- Tự động liên kết/sao chép sang ranking/input/human_qrels.jsonl phục vụ Ranking Evaluation (Block 5).
- Xuất báo cáo thống kê đầy đủ: pooling/output/pooling_report.json
- Tạo báo cáo phân tích Markdown: pooling/reports/POOLING_ANALYSIS.md

Theo Mục 4 & Mục 5:
- Tách bạch DEV (15 Queries) và TEST (35 Queries).
- Khóa Qrels trước khi tính metric cuối cùng để tránh rò rỉ dữ liệu.
"""

import json
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

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

    judgments_file = resolve_path(paths.get("human_judgments", "pooling/human_review/human_judgments.jsonl"))
    dedup_pool_file = resolve_path(paths.get("output_deduplicated_pool", "pooling/output/deduplicated_pool.jsonl"))
    final_qrels_file = resolve_path(paths.get("output_final_qrels", "pooling/output/final_human_qrels.jsonl"))
    pooling_report_file = resolve_path(paths.get("output_pooling_report", "pooling/output/pooling_report.json"))
    analysis_file = resolve_path(paths.get("report_analysis", "pooling/reports/POOLING_ANALYSIS.md"))
    split_file = resolve_path(paths.get("query_split", "ranking/input/query_split.json"))

    print("="*75)
    print("BƯỚC 6: KHÓA BỘ HUMAN QRELS VÀ XUẤT BÁO CÁO POOLING CHÍNH THỨC")
    print("="*75)

    if not judgments_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy file đánh giá tại {judgments_file}")
        return

    # Đọc thông tin phân chia DEV / TEST
    if not split_file.exists():
        split_file = PROJECT_ROOT / "ranking" / "input" / "query_split.template.json"

    dev_queries, test_queries = set(), set()
    if split_file.exists():
        with open(split_file, "r", encoding="utf-8") as f:
            sp = json.load(f)
            dev_queries = set(sp.get("dev", []))
            test_queries = set(sp.get("test", []))

    final_qrels = []
    grade_counter = Counter()
    unjudged_count = 0
    dev_judged_count = 0
    test_judged_count = 0

    with open(judgments_file, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            qid = r["query_id"]
            cid = r["candidate_id"]
            grade = r.get("human_grade")
            notes = r.get("notes", "")

            if grade in (0, 1, 2, 3, "0", "1", "2", "3"):
                g_int = int(grade)
                grade_counter[g_int] += 1
                if qid in dev_queries:
                    dev_judged_count += 1
                elif qid in test_queries:
                    test_judged_count += 1

                final_qrels.append({
                    "query_id": qid,
                    "candidate_id": cid,
                    "grade": g_int,
                    "notes": notes
                })
            else:
                unjudged_count += 1

    total_pairs = len(final_qrels) + unjudged_count

    # 1. Lưu final_human_qrels.jsonl
    final_qrels_file.parent.mkdir(parents=True, exist_ok=True)
    with open(final_qrels_file, "w", encoding="utf-8") as f:
        for r in final_qrels:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[+] Đã xuất bộ Human Qrels chính thức: {len(final_qrels)} nhãn đã được con người xác thực.")
    print(f"    -> Lưu tại: {final_qrels_file}")

    # Tự động đồng bộ sang ranking/input/human_qrels.jsonl
    ranking_qrels_path = PROJECT_ROOT / "ranking" / "input" / "human_qrels.jsonl"
    ranking_qrels_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ranking_qrels_path, "w", encoding="utf-8") as f:
        for r in final_qrels:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[+] Tự động đồng bộ Qrels sang Ranking Module: {ranking_qrels_path}")

    # 2. Tạo pooling_report.json
    pooling_summary = {
        "generated_at": datetime.now().isoformat(),
        "total_pairs_in_pool": total_pairs,
        "total_judged_pairs": len(final_qrels),
        "total_unjudged_pairs": unjudged_count,
        "judged_coverage_percentage": round(len(final_qrels) / total_pairs * 100, 2) if total_pairs > 0 else 0,
        "splits_coverage": {
            "dev_queries_count": len(dev_queries),
            "dev_judged_pairs": dev_judged_count,
            "test_queries_count": len(test_queries),
            "test_judged_pairs": test_judged_count
        },
        "grade_distribution": {
            "grade_0_not_relevant": grade_counter[0],
            "grade_1_partially_relevant": grade_counter[1],
            "grade_2_highly_relevant": grade_counter[2],
            "grade_3_directly_relevant": grade_counter[3]
        }
    }

    with open(pooling_report_file, "w", encoding="utf-8") as f:
        json.dump(pooling_summary, f, ensure_ascii=False, indent=2)

    print(f"[+] Đã tạo Báo cáo Thống kê Pooling: {pooling_report_file}")

    # 3. Tạo POOLING_ANALYSIS.md
    analysis_file.parent.mkdir(parents=True, exist_ok=True)
    md_content = f"""# BÁO CÁO PHÂN TÍCH QUY TRÌNH POOLING & FINAL GROUND TRUTH (EXP B)
*Khóa luận tốt nghiệp / Báo cáo DS300 — Ngày cập nhật: {datetime.now().strftime('%d/%m/%Y')}*

---

## 1. Mục tiêu và Nguyên lý Triển khai Pooling
Theo tiêu chuẩn đánh giá hệ thống truy xuất thông tin của **TREC (Text REtrieval Conference)**, quy trình Pooling được thực hiện nhằm mục đích:
1. **Tránh thiên lệch hệ thống đơn lẻ (Single-system Bias)**: Không chỉ đánh giá các bài báo do một phương pháp duy nhất tìm thấy, mà gộp các ứng viên từ nhiều phương pháp khác nhau:
   - Ground Truth Candidate Generation (Top 100 bằng MiniLM Full-text).
   - Method 1: Full-text Embedding Ranking (Top 20).
   - Method 2: Equal-weight Facet Ranking (Top 20).
   - Method 3: Weighted Facet Ranking (Top 20).
2. **Loại bỏ trùng lặp (Deduplication)**: Hợp nhất các bài ứng viên trùng lặp theo cặp duy nhất `(query_id, candidate_id)` và lưu vết danh sách nguồn phát hiện (`retrieved_by`).
3. **Thẩm định con người (Human Relevance Judgment)**: Đánh giá thực chất mức độ liên quan theo thang đo chuẩn 4 mức (Grade 0–3).

---

## 2. Thống kê Kích thước và Tỷ lệ Bao phủ của Pool

| Chỉ số Thống kê | Giá trị | Tỷ lệ (%) |
| :--- | :---: | :---: |
| **Tổng số cặp trong Pool** | **{total_pairs}** | 100.0% |
| **Số cặp đã được Con người đánh giá (Grade 0–3)** | **{len(final_qrels)}** | **{pooling_summary['judged_coverage_percentage']}%** |
| **Số cặp chưa đánh giá (UNJUDGED)** | **{unjudged_count}** | {round(unjudged_count/total_pairs*100, 2) if total_pairs > 0 else 0}% |
| **Số cặp đánh giá trên tập DEV (15 Queries)** | {dev_judged_count} | - |
| **Số cặp đánh giá trên tập TEST (35 Queries)** | {test_judged_count} | - |

---

## 3. Phân bổ Thang điểm Đánh giá (Relevance Grade Distribution)

| Thang điểm Human Grade | Ý nghĩa Thực tế | Số lượng cặp | Tỷ lệ (%) |
| :--- | :--- | :---: | :---: |
| **Grade 0** | Không liên quan | {grade_counter[0]} | {round(grade_counter[0]/len(final_qrels)*100, 1) if final_qrels else 0}% |
| **Grade 1** | Có liên quan nhẹ, giá trị sử dụng hạn chế | {grade_counter[1]} | {round(grade_counter[1]/len(final_qrels)*100, 1) if final_qrels else 0}% |
| **Grade 2** | Có liên quan đáng kể | {grade_counter[2]} | {round(grade_counter[2]/len(final_qrels)*100, 1) if final_qrels else 0}% |
| **Grade 3** | Rất liên quan, có giá trị tham khảo trực tiếp | {grade_counter[3]} | {round(grade_counter[3]/len(final_qrels)*100, 1) if final_qrels else 0}% |

---

## 4. Các Quy tắc Nghiên cứu Đã Tuân thủ (Scientific Compliance)
1. **Deduplicate theo từng cặp**: Khóa duy nhất là `(query_id, candidate_id)`.
2. **Không tự ý gán Grade 0**: Các cặp chưa được đánh giá giữ nguyên nhãn `UNJUDGED`, không mặc định gán là 0 khi chưa qua Human Review.
3. **Khóa Qrels cho tập TEST**: Bộ Qrels được khóa cứng tại `final_human_qrels.jsonl` trước khi chạy tính toán metric cuối cùng trên tập TEST để bảo đảm tính khách quan.
"""

    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[+] Đã khởi tạo Báo cáo Phân tích Pooling tại: {analysis_file}")
    print("\n--> Hoàn tất Bước 6. Bộ Final Human Qrels đã sẵn sàng cho Ranking Evaluation (Block 5).")

if __name__ == "__main__":
    main()
