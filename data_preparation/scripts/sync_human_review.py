"""sync_human_review.py
Công cụ đồng bộ 2 chiều giữa Human Review Queue / Corrections và file CSV (Excel / Google Sheets).

Sử dụng:
1. Xuất ra file CSV để mở bằng Excel hoặc đưa lên Google Sheets cho nhóm cùng duyệt:
   python data_preparation/scripts/sync_human_review.py --to-csv

2. Cập nhật các quyết định từ file CSV đã duyệt trở lại pipeline:
   python data_preparation/scripts/sync_human_review.py --from-csv
"""

import csv
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HUMAN_DIR = PROJECT_ROOT / "data_preparation" / "human_review"
QUEUE_PATH = HUMAN_DIR / "review_queue.jsonl"
CORR_PATH = HUMAN_DIR / "human_corrections.jsonl"
CSV_PATH = HUMAN_DIR / "human_review_spreadsheet.csv"

def export_to_csv():
    if not QUEUE_PATH.exists():
        print(f"Lỗi: Không tìm thấy {QUEUE_PATH}")
        return

    queue = [json.loads(line) for line in open(QUEUE_PATH, encoding="utf-8")]
    corrections = {}
    if CORR_PATH.exists():
        for line in open(CORR_PATH, encoding="utf-8"):
            try:
                r = json.loads(line)
                corrections[(r["paper_id"], r["facet"])] = r
            except Exception:
                pass

    fieldnames = [
        "paper_id",
        "facet",
        "audit_decision",
        "human_decision",         # Người duyệt điền: ACCEPT, REJECT, hoặc REVISE
        "human_revised_facet",    # Nội dung sửa (nếu chọn REVISE)
        "human_notes",            # Ghi chú của người duyệt
        "current_concepts",
        "qwen_support_status",
        "qwen_detected_issues",
        "qwen_proposed_revision",
        "qwen_explanation",
        "evidence_texts",
        "title",
        "abstract"
    ]

    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in queue:
            pid = item["paper_id"]
            facet = item["facet"]
            corr = corrections.get((pid, facet), {})

            row = {
                "paper_id": pid,
                "facet": facet,
                "audit_decision": item.get("audit_decision", ""),
                "human_decision": corr.get("human_decision", "PENDING"),
                "human_revised_facet": "; ".join(corr.get("human_revised_facet", [])) if isinstance(corr.get("human_revised_facet"), list) else corr.get("human_revised_facet", ""),
                "human_notes": corr.get("human_notes", ""),
                "current_concepts": "; ".join(item.get("current_concepts", [])) if isinstance(item.get("current_concepts"), list) else str(item.get("current_concepts", "")),
                "qwen_support_status": item.get("qwen_support_status", ""),
                "qwen_detected_issues": item.get("qwen_detected_issues", ""),
                "qwen_proposed_revision": item.get("qwen_proposed_revision", "") or "",
                "qwen_explanation": item.get("qwen_explanation", ""),
                "evidence_texts": " | ".join(item.get("evidence_texts", [])),
                "title": item.get("title", ""),
                "abstract": item.get("abstract", item.get("abstract_snippet", ""))
            }
            writer.writerow(row)

    print(f"--> Đã xuất thành công {len(queue)} dòng sang file CSV:")
    print(f"    {CSV_PATH}")
    print("Bạn có thể mở file này bằng Microsoft Excel hoặc tải lên Google Sheets để chia việc cho các thành viên trong nhóm.")
    print("Các giá trị hợp lệ cho cột 'human_decision': ACCEPT, REJECT, REVISE, PENDING.")

def import_from_csv():
    if not CSV_PATH.exists():
        print(f"Lỗi: Không tìm thấy file {CSV_PATH}")
        return

    # Tải các quyết định hiện có
    corrections = {}
    if CORR_PATH.exists():
        for line in open(CORR_PATH, encoding="utf-8"):
            try:
                r = json.loads(line)
                corrections[(r["paper_id"], r["facet"])] = r
            except Exception:
                pass

    updated_count = 0
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["paper_id"].strip()
            facet = row["facet"].strip()
            decision = row["human_decision"].strip().upper()
            notes = row.get("human_notes", "").strip()
            revised_raw = row.get("human_revised_facet", "").strip()

            if decision in ("ACCEPT", "REJECT", "REVISE"):
                if revised_raw:
                    # Tách dấu ; hoặc dấu , thành danh sách các concept
                    revised = [c.strip() for c in revised_raw.replace(";", ",").split(",") if c.strip()]
                else:
                    revised = []

                corrections[(pid, facet)] = {
                    "paper_id": pid,
                    "facet": facet,
                    "human_decision": decision,
                    "human_revised_facet": revised,
                    "human_notes": notes
                }
                updated_count += 1

    # Ghi lại file human_corrections.jsonl
    with open(CORR_PATH, "w", encoding="utf-8") as f:
        for r in corrections.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"--> Đã nhập thành công {updated_count} quyết định từ CSV vào {CORR_PATH}")
    print("Tiếp theo, hãy chạy: python data_preparation/scripts/08_merge_validated_silver.py để cập nhật Validated Silver!")

def main():
    parser = argparse.ArgumentParser(description="Đồng bộ Human Quality Control giữa JSONL và CSV")
    parser.add_argument("--to-csv", action="store_true", help="Xuất hàng đợi ra file CSV để mở bằng Excel/Google Sheets")
    parser.add_argument("--from-csv", action="store_true", help="Nhập các quyết định từ file CSV vào human_corrections.jsonl")

    args = parser.parse_args()
    if args.to_csv:
        export_to_csv()
    elif args.from_csv:
        import_from_csv()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
