"""01_validate_structure.py
Bước 1: Structural Validation (Python thuần)
Kiểm tra cấu trúc, ID, kiểu dữ liệu, facet rỗng, lỗi trích xuất và dấu hiệu cắt cụt.
Output: data_preparation/intermediate/structural_report.jsonl
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_preparation.pipeline_scope import get_scope_ids

INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
LOGS_DIR = PROJECT_ROOT / "data_preparation" / "logs"

FACETS = ("problem", "task", "method", "dataset", "contribution")

def load_records(path):
    records = {}
    with open(path, "r", encoding="utf-8") as file:
        for line_no, line in enumerate(file, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected a JSON object")
            paper_id = row.get("paper_id")
            if not isinstance(paper_id, str) or not paper_id.strip():
                raise ValueError(f"{path}:{line_no}: paper_id must be a non-empty string")
            if paper_id in records:
                raise ValueError(f"{path}:{line_no}: duplicate paper_id {paper_id}")
            records[paper_id] = row
    return records


def main():
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    papers_path = INPUT_DIR / "papers.jsonl"
    silver_path = INPUT_DIR / "silver_facets.jsonl"

    if not papers_path.exists() or not silver_path.exists():
        print(f"Error: Missing input files in {INPUT_DIR}")
        sys.exit(1)

    print("--> Đang tải dữ liệu papers.jsonl...")
    papers = load_records(papers_path)
    scope_ids = get_scope_ids()
    if scope_ids is not None:
        papers = {pid: row for pid, row in papers.items() if pid in scope_ids}

    print(f"--> Đã tải {len(papers)} bài báo từ corpus.")

    print("--> Đang tải và kiểm tra silver_facets.jsonl...")
    silver = load_records(silver_path)
    if scope_ids is not None:
        silver = {pid: row for pid, row in silver.items() if pid in scope_ids}

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

    all_pids = sorted(set(papers.keys()) | set(silver.keys()) | (scope_ids or set()))

    for pid in all_pids:
        p_row = papers.get(pid)
        s_row = silver.get(pid)
        issues = []
        warnings = []
        extraction_provenance_status = "UNAVAILABLE"

        if not p_row:
            issues.append("PAPER_NOT_IN_CORPUS")
            stats["missing_in_corpus"] += 1
        if not s_row:
            issues.append("PAPER_NOT_IN_SILVER")
            stats["missing_in_silver"] += 1

        title = p_row.get("title", "") if p_row else ""
        abstract = p_row.get("abstract", "") if p_row else ""

        if p_row:
            if not isinstance(title, str):
                issues.append("INVALID_TITLE_TYPE")
                title = ""
            if not isinstance(abstract, str):
                issues.append("INVALID_ABSTRACT_TYPE")
                abstract = ""
            if not title.strip():
                issues.append("EMPTY_TITLE")
            if not abstract.strip():
                issues.append("EMPTY_ABSTRACT")
            elif len(abstract) < 50:
                issues.append("VERY_SHORT_ABSTRACT")
            if abstract.rstrip().endswith(("...", "…", "[truncated]")):
                issues.append("TRUNCATED_ABSTRACT")

        empty_facets = []
        present_facets = []

        if s_row:
            metadata = s_row.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            provenance_keys = (
                "fallback_used",
                "used_fallback",
                "fallback",
                "error",
                "extraction_error",
                "extraction_status",
            )
            provenance_values = {
                key: s_row[key] if key in s_row else metadata[key]
                for key in provenance_keys
                if key in s_row or key in metadata
            }
            if provenance_values:
                has_failure = any(
                    (isinstance(value, bool) and value)
                    or (
                        isinstance(value, str)
                        and value.strip().lower() in {"fallback", "failed", "error", "true"}
                    )
                    or (key in ("error", "extraction_error") and value not in (None, "", False))
                    for key, value in provenance_values.items()
                )
                extraction_provenance_status = "FALLBACK_OR_ERROR" if has_failure else "AVAILABLE"
                if has_failure:
                    issues.append("EXP_A_FALLBACK_OR_ERROR")
            else:
                warnings.append("EXP_A_PROVENANCE_UNAVAILABLE")

            for f in FACETS:
                val = s_row.get(f)
                if val is None or not isinstance(val, list):
                    issues.append(f"INVALID_FACET_TYPE_{f.upper()}")
                    empty_facets.append(f)
                    stats["facet_empty_counts"][f] += 1
                elif any(not isinstance(item, str) for item in val):
                    issues.append(f"INVALID_FACET_VALUE_TYPE_{f.upper()}")
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
                        if isinstance(item, str) and item.rstrip().endswith(("...", "…", "[truncated]")):
                            issues.append(f"TRUNCATED_CONCEPT_{f.upper()}")

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
            "warnings": warnings,
            "extraction_provenance_status": extraction_provenance_status,
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
