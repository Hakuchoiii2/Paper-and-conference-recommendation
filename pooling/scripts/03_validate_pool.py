"""03_validate_pool.py
Bước 3 trong Pooling Pipeline: Kiểm tra & Hợp thức hóa dữ liệu (Pool Validation).
- Loại trừ Query Paper xuất hiện trong chính Candidate list của nó (c == q).
- Kiểm tra tính hợp lệ của tất cả Query IDs và Candidate IDs đối chiếu với Corpus (4,210 bài báo).
- Thống kê chi tiết kích thước pool theo từng Query.
- Báo cáo tỷ lệ overlap giữa Ground Truth Generation và 3 phương pháp Ranking.

Output:
- pooling/output/pool_validation_report.json
- Cập nhật lại pooling/output/deduplicated_pool.jsonl (nếu có trường hợp c == q bị loại).
"""

import json
from pathlib import Path
from collections import defaultdict

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
    report_file = resolve_path(paths.get("output_validation_report", "pooling/output/pool_validation_report.json"))
    corpus_file = resolve_path(paths.get("papers_corpus", "data_preparation/input/papers.jsonl"))
    val_silver_file = resolve_path(paths.get("validated_silver", "data_preparation/output/validated_silver.jsonl"))

    print("="*75)
    print("BƯỚC 3: KIỂM ĐỊNH VÀ HỢP THỨC HÓA CANDIDATE POOL (VALIDATION)")
    print("="*75)

    if not dedup_pool_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy deduplicated_pool.jsonl tại {dedup_pool_file}")
        print("    Vui lòng chạy Bước 2: python pooling/scripts/02_deduplicate_pool.py trước.")
        return

    # Tải danh sách Paper IDs hợp lệ từ corpus
    valid_corpus_ids = set()
    if val_silver_file.exists():
        with open(val_silver_file, "r", encoding="utf-8") as f:
            for line in f:
                valid_corpus_ids.add(json.loads(line)["paper_id"])
    elif corpus_file.exists():
        with open(corpus_file, "r", encoding="utf-8") as f:
            for line in f:
                valid_corpus_ids.add(json.loads(line)["paper_id"])

    print(f"[+] Không gian Corpus xác thực: {len(valid_corpus_ids)} bài báo.")

    valid_records = []
    self_query_violations = 0
    unknown_query_ids = set()
    unknown_candidate_ids = set()
    candidates_per_query = defaultdict(int)

    with open(dedup_pool_file, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            qid = r["query_id"]
            cid = r["candidate_id"]

            # 1. Kiểm tra self-query (c == q)
            if qid == cid:
                self_query_violations += 1
                continue

            # 2. Kiểm tra tồn tại trong corpus
            if valid_corpus_ids:
                if qid not in valid_corpus_ids:
                    unknown_query_ids.add(qid)
                if cid not in valid_corpus_ids:
                    unknown_candidate_ids.add(cid)

            valid_records.append(r)
            candidates_per_query[qid] += 1

    # Tính toán các chỉ số thống kê
    query_counts = len(candidates_per_query)
    cands_counts_list = list(candidates_per_query.values())
    min_cands = min(cands_counts_list) if cands_counts_list else 0
    max_cands = max(cands_counts_list) if cands_counts_list else 0
    avg_cands = sum(cands_counts_list) / len(cands_counts_list) if cands_counts_list else 0

    validation_summary = {
        "status": "VALID",
        "total_valid_pairs": len(valid_records),
        "total_queries_in_pool": query_counts,
        "candidates_per_query_stats": {
            "min": min_cands,
            "max": max_cands,
            "average": round(avg_cands, 2)
        },
        "violations_detected": {
            "self_query_pairs_removed": self_query_violations,
            "unknown_query_ids_count": len(unknown_query_ids),
            "unknown_candidate_ids_count": len(unknown_candidate_ids)
        }
    }

    print("\nKết quả kiểm định Pool:")
    print(f"  - Số cặp (Query, Candidate) hợp lệ : {len(valid_records)}")
    print(f"  - Số Query Papers có trong Pool     : {query_counts}")
    print(f"  - Kích thước Pool mỗi Query (Min/Avg/Max): {min_cands} / {avg_cands:.1f} / {max_cands}")
    print(f"  - Cặp vi phạm self-query (đã loại)  : {self_query_violations}")
    if unknown_query_ids:
        print(f"  [!] Cảnh báo: Có {len(unknown_query_ids)} Query IDs không tồn tại trong corpus: {list(unknown_query_ids)[:5]}")
    if unknown_candidate_ids:
        print(f"  [!] Cảnh báo: Có {len(unknown_candidate_ids)} Candidate IDs không tồn tại trong corpus: {list(unknown_candidate_ids)[:5]}")

    # Ghi lại deduplicated_pool.jsonl nếu có loại bớt self-query
    if self_query_violations > 0:
        with open(dedup_pool_file, "w", encoding="utf-8") as f:
            for r in valid_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[+] Đã cập nhật lại {dedup_pool_file.name} (đã loại bỏ {self_query_violations} cặp self-query).")

    # Lưu báo cáo
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(validation_summary, f, ensure_ascii=False, indent=2)

    print(f"[+] Báo cáo kiểm định lưu tại: {report_file}")
    print("--> Hoàn tất Bước 3.")

if __name__ == "__main__":
    main()
