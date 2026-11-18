"""01_validate_structure.py
Bước 1: Structural Validation (Python thuần)
Kiểm tra cấu trúc, ID, kiểu dữ liệu, facet rỗng, lỗi trích xuất và dấu hiệu cắt cụt.
Output: data_preparation/intermediate/structural_report.jsonl
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
LOGS_DIR = PROJECT_ROOT / "data_preparation" / "logs"

FACETS = ("problem", "task", "method", "dataset", "contribution")

def main():
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    papers_path = INPUT_DIR / "papers.jsonl"
    silver_path = INPUT_DIR / "silver_facets.jsonl"

    if not papers_path.exists() or not silver_path.exists():
        print(f"Error: Missing input files in {INPUT_DIR}")
        sys.exit(1)

    print("--> Đang tải dữ liệu papers.jsonl...")
    papers = {}
    with open(papers_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            try:
                row = json.loads(line)
                pid = row.get("paper_id")
                if not pid:
                    print(f"Warning: Line {line_no} in papers.jsonl has no paper_id")
                    continue
                papers[pid] = row
            except Exception as e:
                print(f"Error parsing line {line_no} in papers.jsonl: {e}")

    print(f"--> Đã tải {len(papers)} bài báo từ corpus.")

    print("--> Đang tải và kiểm tra silver_facets.jsonl...")
    silver = {}
    with open(silver_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            try:
                row = json.loads(line)
                pid = row.get("paper_id")
                if not pid:
                    print(f"Warning: Line {line_no} in silver_facets has no paper_id")
                    continue
                silver[pid] = row
            except Exception as e:
                print(f"Error parsing line {line_no} in silver_facets: {e}")

    print(f"--> Đã tải {len(silver)} bản ghi silver facets.")

    # Kiểm tra liên kết và cấu trúc
    report_records = []
    stats = {
        "total_corpus": len(papers),
        "total_silver": len(silver),
        "missing_in_silver": 0,
        "missing_in_corpus": 0,
        "clean_papers": 0,
        "sparse_papers": 0,  # < 2 facets
        "facet_empty_counts": {f: 0 for f in FACETS},
        "truncation_warnings": 0,
    }

    all_pids = sorted(set(papers.keys()) | set(silver.keys()))

    for pid in all_pids:
        p_row = papers.get(pid)
        s_row = silver.get(pid)
        issues = []

        if not p_row:
            issues.append("PAPER_NOT_IN_CORPUS")
            stats["missing_in_corpus"] += 1
        if not s_row:
            issues.append("PAPER_NOT_IN_SILVER")
            stats["missing_in_silver"] += 1

        title = p_row.get("title", "") if p_row else ""
        abstract = p_row.get("abstract", "") if p_row else ""

        if p_row:
            if not title.strip():
                issues.append("EMPTY_TITLE")
            if not abstract.strip():
                issues.append("EMPTY_ABSTRACT")
            elif len(abstract) < 50:
                issues.append("VERY_SHORT_ABSTRACT")

        empty_facets = []
        present_facets = []

        if s_row:
            for f in FACETS:
                val = s_row.get(f)
                if val is None or not isinstance(val, list):
                    issues.append(f"INVALID_FACET_TYPE_{f.upper()}")
                    empty_facets.append(f)
                    stats["facet_empty_counts"][f] += 1
                elif len(val) == 0:
                    empty_facets.append(f)
                    stats["facet_empty_counts"][f] += 1
                else:
                    present_facets.append(f)
                    for item in val:
                        if isinstance(item, str) and (item.endswith("...") or len(item) < 3):
                            issues.append(f"SUSPICIOUS_CONCEPT_{f.upper()}")
                            stats["truncation_warnings"] += 1

        num_present = len(present_facets)
        if num_present >= 2 and not issues:
            status = "CLEAN"
            stats["clean_papers"] += 1
        elif num_present < 2:
            status = "SPARSE"
            stats["sparse_papers"] += 1
        else:
            status = "HAS_ISSUES"

        report_records.append({
            "paper_id": pid,
            "status": status,
            "num_present_facets": num_present,
            "present_facets": present_facets,
            "empty_facets": empty_facets,
            "issues": issues,
            "title_len": len(title),
            "abstract_len": len(abstract)
        })

    # Ghi output
    out_path = INTERMEDIATE_DIR / "structural_report.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in report_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n==================== KẾT QUẢ STRUCTURAL VALIDATION ====================")
    print(f"Tổng bài trong corpus: {stats['total_corpus']}")
    print(f"Tổng bài trong silver: {stats['total_silver']}")
    print(f"Bài sạch (Clean, >= 2 facets): {stats['clean_papers']} ({stats['clean_papers']/stats['total_corpus']*100:.1f}%)")
    print(f"Bài thưa (Sparse, < 2 facets): {stats['sparse_papers']} ({stats['sparse_papers']/stats['total_corpus']*100:.1f}%)")
    print(f"Cảnh báo cắt cụt / concept bất thường: {stats['truncation_warnings']}")
    print("\nThống kê số bài BỊ KHUYẾT từng facet:")
    for f, cnt in stats["facet_empty_counts"].items():
        print(f"  - {f:12s}: {cnt:4d} bài khuyết ({cnt/stats['total_corpus']*100:.1f}%)")
    print(f"\n-> Đã lưu báo cáo chi tiết tại: {out_path}")

if __name__ == "__main__":
    main()
