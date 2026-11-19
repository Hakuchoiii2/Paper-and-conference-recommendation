"""sync_pooling_review.py
Công cụ đồng bộ 2 chiều giữa Pooling Review Queue / Judgments và file CSV (Excel / Google Sheets).

Sử dụng:
1. Xuất ra file CSV để mở bằng Excel hoặc đưa lên Google Sheets cho nhóm cùng đánh giá:
   python pooling/scripts/sync_pooling_review.py --to-csv

2. Cập nhật các đánh giá từ file CSV vào human_judgments.jsonl:
   python pooling/scripts/sync_pooling_review.py --from-csv
"""

import csv
import json
import argparse
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

def export_to_csv():
    config = load_config()
    paths = config.get("paths", {})

    queue_file = resolve_path(paths.get("human_review_queue", "pooling/human_review/review_queue.jsonl"))
    judgments_file = resolve_path(paths.get("human_judgments", "pooling/human_review/human_judgments.jsonl"))
    csv_file = POOLING_DIR / "human_review" / "pooling_review_spreadsheet.csv"

    if not queue_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy file review queue tại {queue_file}")
        return

    judgments_map = {}
    if judgments_file.exists():
        with open(judgments_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    judgments_map[(r["query_id"], r["candidate_id"])] = r
                except Exception:
                    pass

    fieldnames = [
        "query_id",
        "candidate_id",
        "human_grade",       # Người đánh giá điền: 0, 1, 2, hoặc 3
        "notes",             # Ghi chú nhận xét
        "retrieved_by",      # Các phương pháp phát hiện
        "query_title",
        "candidate_title",
        "query_abstract",
        "candidate_abstract",
        "query_facets",
        "candidate_facets"
    ]

    count = 0
    with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        with open(queue_file, "r", encoding="utf-8") as qf:
            for line in qf:
                item = json.loads(line)
                qid = item["query_id"]
                cid = item["candidate_id"]
                key = (qid, cid)
                j = judgments_map.get(key, {})

                writer.writerow({
                    "query_id": qid,
                    "candidate_id": cid,
                    "human_grade": j.get("human_grade", "UNJUDGED"),
                    "notes": j.get("notes", ""),
                    "retrieved_by": "; ".join(item.get("retrieved_by", [])),
                    "query_title": item.get("query_title", ""),
                    "candidate_title": item.get("candidate_title", ""),
                    "query_abstract": item.get("query_abstract", ""),
                    "candidate_abstract": item.get("candidate_abstract", ""),
                    "query_facets": json.dumps(item.get("query_facets", {}), ensure_ascii=False),
                    "candidate_facets": json.dumps(item.get("candidate_facets", {}), ensure_ascii=False)
                })
                count += 1

    print(f"[+] Đã xuất thành công {count} cặp sang file CSV:")
    print(f"    {csv_file}")
    print("Mở file này bằng Excel hoặc tải lên Google Sheets. Điền số 0, 1, 2, 3 vào cột 'human_grade'.")

def import_from_csv():
    config = load_config()
    paths = config.get("paths", {})

    judgments_file = resolve_path(paths.get("human_judgments", "pooling/human_review/human_judgments.jsonl"))
    csv_file = POOLING_DIR / "human_review" / "pooling_review_spreadsheet.csv"

    if not csv_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy file CSV tại {csv_file}")
        return

    updated_count = 0
    records = []
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row["query_id"].strip()
            cid = row["candidate_id"].strip()
            raw_grade = row["human_grade"].strip().upper()
            notes = row.get("notes", "").strip()

            if raw_grade in ("0", "1", "2", "3"):
                grade_val = int(raw_grade)
                updated_count += 1
            else:
                grade_val = "UNJUDGED"

            records.append({
                "query_id": qid,
                "candidate_id": cid,
                "human_grade": grade_val,
                "notes": notes
            })

    with open(judgments_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[+] Đã cập nhật thành công {len(records)} dòng ({updated_count} đã chấm) vào {judgments_file.name}")
    print("Tiếp theo, hãy chạy: python pooling/scripts/06_finalize_qrels.py để hoàn tất bộ Qrels!")

def main():
    parser = argparse.ArgumentParser(description="Đồng bộ Pooling Human Review giữa JSONL và CSV")
    parser.add_argument("--to-csv", action="store_true", help="Xuất sang file CSV để mở bằng Excel/Google Sheets")
    parser.add_argument("--from-csv", action="store_true", help="Nhập lại các đánh giá từ file CSV vào human_judgments.jsonl")

    args = parser.parse_args()
    if args.to_csv:
        export_to_csv()
    elif args.from_csv:
        import_from_csv()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
