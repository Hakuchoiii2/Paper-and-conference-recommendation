"""02_deduplicate_pool.py
Bước 2 trong Pooling Pipeline: Deduplication (Loại bỏ trùng lặp).
- Nhóm và loại bỏ các Candidate trùng lặp trong cùng một Query Paper.
- Quy tắc bắt buộc (Mục 4):
    * Khóa duy nhất là cặp: (query_id, candidate_id).
    * Candidate xuất hiện ở nhiều Query khác nhau vẫn là các cặp độc lập.
    * Lưu nguồn phát hiện (retrieved_by): Biết được phương pháp nào đã tìm thấy Candidate này.
    * Lưu chi tiết rank và score từ từng phương pháp phát hiện.

Output:
- pooling/output/deduplicated_pool.jsonl
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

    input_pool_file = resolve_path(paths.get("output_candidate_pool", "pooling/output/candidate_pool.jsonl"))
    output_dedup_file = resolve_path(paths.get("output_deduplicated_pool", "pooling/output/deduplicated_pool.jsonl"))

    print("="*75)
    print("BƯỚC 2: DEDUPLICATION - LOẠI BỎ TRÙNG LẶP THEO TỪNG CẶP (QUERY, CANDIDATE)")
    print("="*75)

    if not input_pool_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy candidate_pool.jsonl tại {input_pool_file}")
        print("    Vui lòng chạy Bước 1: python pooling/scripts/01_merge_candidates.py trước.")
        return

    # Gom nhóm theo (query_id, candidate_id)
    pool_by_pair = defaultdict(lambda: {
        "retrieved_by": set(),
        "method_details": {}
    })

    total_records = 0
    with open(input_pool_file, "r", encoding="utf-8") as f:
        for line in f:
            total_records += 1
            r = json.loads(line)
            qid = r["query_id"]
            cid = r["candidate_id"]
            src = r["source"]
            rank = r.get("rank_in_source")
            score = r.get("score_in_source")

            key = (qid, cid)
            pool_by_pair[key]["retrieved_by"].add(src)
            pool_by_pair[key]["method_details"][src] = {
                "rank": rank,
                "score": score
            }

    unique_pairs_count = len(pool_by_pair)
    overlap_count = total_records - unique_pairs_count

    print(f"[+] Tổng số bản ghi ban đầu          : {total_records}")
    print(f"[+] Số cặp (Query, Candidate) duy nhất : {unique_pairs_count}")
    print(f"[+] Số cặp trùng lặp đã gộp (Overlap)  : {overlap_count} ({overlap_count/total_records*100:.1f}%)" if total_records > 0 else "")

    dedup_records = []
    # Thống kê phân bố nguồn phát hiện
    overlap_distribution = defaultdict(int)

    for (qid, cid), data in sorted(pool_by_pair.items()):
        sources_list = sorted(list(data["retrieved_by"]))
        overlap_distribution[len(sources_list)] += 1

        dedup_records.append({
            "query_id": qid,
            "candidate_id": cid,
            "source_count": len(sources_list),
            "retrieved_by": sources_list,
            "method_details": data["method_details"]
        })

    print("\nThống kê số lượng phương pháp cùng tìm thấy Candidate:")
    for num_src, count in sorted(overlap_distribution.items()):
        print(f"  - Tìm thấy bởi {num_src} phương pháp : {count} cặp ({count/unique_pairs_count*100:.1f}%)")

    with open(output_dedup_file, "w", encoding="utf-8") as f:
        for r in dedup_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n[+] Đã lưu Deduplicated Candidate Pool vào: {output_dedup_file}")
    print("--> Hoàn tất Bước 2.")

if __name__ == "__main__":
    main()
