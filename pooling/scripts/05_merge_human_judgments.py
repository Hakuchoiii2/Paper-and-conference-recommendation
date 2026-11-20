"""05_merge_human_judgments.py
Bước 5 trong Pooling Pipeline: Hợp nhất và Kiểm tra Nhãn Đánh giá của Con người.
- Đọc kết quả đánh giá từ pooling/human_review/human_judgments.jsonl.
- Xác thực nhãn hợp lệ (0, 1, 2, 3 hoặc UNJUDGED).
- Thống kê tỷ lệ hoàn thành theo từng Query và toàn bộ Pool.
- Phát hiện các cặp Candidate mới phát sinh từ Ranking chưa được đánh giá (Mục 4: Bổ sung vào pool, không bỏ sót).

Output:
- Thống kê phân bố Grade và tiến độ đánh giá.
"""

import json
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POOLING_DIR = PROJECT_ROOT / "pooling"
CONFIG_PATH = POOLING_DIR / "config" / "pooling_config.json"

VALID_GRADES = {0, 1, 2, 3, "0", "1", "2", "3"}

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

    print("="*75)
    print("BƯỚC 5: HỢP NHẤT VÀ KIỂM TRA ĐÁNH GIÁ HUMAN RELEVANCE JUDGMENTS")
    print("="*75)

    if not judgments_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy file đánh giá tại {judgments_file}")
        return

    judgments_map = {}
    grade_counter = Counter()
    unjudged_count = 0
    invalid_count = 0

    with open(judgments_file, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            key = (r["query_id"], r["candidate_id"])
            raw_grade = r.get("human_grade")

            if raw_grade in VALID_GRADES:
                grade_int = int(raw_grade)
                judgments_map[key] = {
                    "query_id": r["query_id"],
                    "candidate_id": r["candidate_id"],
                    "grade": grade_int,
                    "notes": r.get("notes", ""),
                    "status": "JUDGED"
                }
                grade_counter[grade_int] += 1
            elif raw_grade in ("UNJUDGED", None, ""):
                judgments_map[key] = {
                    "query_id": r["query_id"],
                    "candidate_id": r["candidate_id"],
                    "grade": None,
                    "notes": r.get("notes", ""),
                    "status": "UNJUDGED"
                }
                unjudged_count += 1
            else:
                invalid_count += 1
                print(f"[!] Cảnh báo: Nhãn không hợp lệ '{raw_grade}' tại cặp {key}")

    total_judgments = len(judgments_map)
    judged_count = sum(grade_counter.values())

    print("\nThống kê Tiến độ Đánh giá:")
    print(f"  - Tổng số cặp trong hồ sơ đánh giá : {total_judgments}")
    print(f"  - Đã được con người đánh giá (0–3)  : {judged_count} ({judged_count/total_judgments*100:.1f}%)" if total_judgments > 0 else "")
    print(f"  - Chưa được đánh giá (UNJUDGED)     : {unjudged_count}")
    if invalid_count > 0:
        print(f"  - Nhãn lỗi cú pháp (cần kiểm tra lại): {invalid_count}")

    print("\nPhân bổ thang điểm Human Relevance Grade (cho các bài đã chấm):")
    grade_desc = {
        0: "0 (Không liên quan)",
        1: "1 (Liên quan nhẹ, giá trị hạn chế)",
        2: "2 (Có liên quan đáng kể)",
        3: "3 (Rất liên quan, tham khảo trực tiếp)"
    }
    for g in [0, 1, 2, 3]:
        c = grade_counter[g]
        pct = (c / judged_count * 100) if judged_count > 0 else 0
        print(f"  - Grade {grade_desc[g]:40}: {c:5} cặp ({pct:5.1f}%)")

    # Kiểm tra xem có cặp nào trong deduplicated_pool chưa được đưa vào judgments không
    if dedup_pool_file.exists():
        missing_in_judgments = 0
        with open(dedup_pool_file, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                k = (r["query_id"], r["candidate_id"])
                if k not in judgments_map:
                    missing_in_judgments += 1

        if missing_in_judgments > 0:
            print(f"\n[!] Cảnh báo: Phát hiện {missing_in_judgments} cặp Candidate mới từ Ranking chưa có trong file Human Judgments!")
            print("    Vui lòng chạy lại Bước 4: python pooling/scripts/04_export_human_review.py để cập nhật hàng đợi.")
        else:
            print("\n[+] Đồng bộ hoàn hảo: 100% cặp trong Candidate Pool đã có mặt trong tệp đánh giá.")

    print("\n--> Hoàn tất Bước 5.")

if __name__ == "__main__":
    main()
