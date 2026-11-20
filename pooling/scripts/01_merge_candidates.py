"""01_merge_candidates.py
Bước 1 trong Pooling Pipeline: Thu thập Candidate từ các nguồn.
- Nguồn 1: Top 100 từ Ground Truth Candidate Generation (ground_truth_candidates.jsonl)
- Nguồn 2: Top 20 từ Method 1 Full-text Ranking (fulltext_ranking.jsonl)
- Nguồn 3: Top 20 từ Method 2 Equal-weight Facet Ranking (equal_weight_ranking.jsonl)
- Nguồn 4: Top 20 từ Method 3 Weighted Facet Ranking (weighted_ranking.jsonl)

Gộp tất cả Candidate theo từng Query Paper và lưu nguồn phát hiện.
Output:
- pooling/output/candidate_pool.jsonl
"""

import json
import argparse
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

def parse_ranking_file(file_path, source_name, top_k):
    """Đọc file ranking dạng jsonl và trích xuất top_k candidates cho từng query."""
    if not file_path.exists():
        return []

    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            qid = r.get("query_id")
            # Hỗ trợ cả trường 'ranking' và 'candidates'
            cand_list = r.get("ranking") or r.get("candidates") or []

            for item in cand_list[:top_k]:
                cid = item.get("candidate_id")
                rank = item.get("rank")
                score = item.get("score")
                records.append({
                    "query_id": qid,
                    "candidate_id": cid,
                    "source": source_name,
                    "rank_in_source": rank,
                    "score_in_source": score
                })
    return records

def main():
    parser = argparse.ArgumentParser(description="Bước 1 Pooling: Thu thập Candidate từ các nguồn")
    parser.add_argument("--gt-top-k", type=int, default=100, help="Số lượng ứng viên lấy từ Ground Truth Generation (mặc định: 100)")
    parser.add_argument("--rank-top-k", type=int, default=20, help="Số lượng ứng viên lấy từ mỗi phương pháp Ranking (mặc định: 20)")
    args = parser.parse_args()

    config = load_config()
    paths = config.get("paths", {})

    output_pool_file = resolve_path(paths.get("output_candidate_pool", "pooling/output/candidate_pool.jsonl"))
    output_pool_file.parent.mkdir(parents=True, exist_ok=True)

    print("="*75)
    print("BƯỚC 1: THU THẬP CANDIDATES TỪ CÁC NGUỒN VÀO CANDIDATE POOL")
    print("="*75)

    # 1. Nguồn Ground Truth Candidate Generation
    gt_file = resolve_path(paths.get("input_gt_candidates", "pooling/input/ground_truth_candidates.jsonl"))
    if not gt_file.exists():
        template_file = POOLING_DIR / "input" / "ground_truth_candidates.template.jsonl"
        if template_file.exists():
            print(f"[*] Chưa có {gt_file.name}, đang dùng template {template_file.name} để kiểm tra schema.")
            gt_file = template_file

    # 2. Ba nguồn từ Ranking (tự động fallback từ ranking/output nếu chưa copy vào pooling/input)
    ft_file = resolve_path(paths.get("input_fulltext_ranking", "pooling/input/fulltext_ranking.jsonl"))
    if not ft_file.exists():
        fallback_ft = PROJECT_ROOT / "ranking" / "output" / "fulltext_ranking.jsonl"
        if fallback_ft.exists():
            ft_file = fallback_ft

    eq_file = resolve_path(paths.get("input_equal_weight_ranking", "pooling/input/equal_weight_ranking.jsonl"))
    if not eq_file.exists():
        fallback_eq = PROJECT_ROOT / "ranking" / "output" / "equal_weight_ranking.jsonl"
        if fallback_eq.exists():
            eq_file = fallback_eq

    wt_file = resolve_path(paths.get("input_weighted_ranking", "pooling/input/weighted_ranking.jsonl"))
    if not wt_file.exists():
        fallback_wt = PROJECT_ROOT / "ranking" / "output" / "weighted_ranking.jsonl"
        if fallback_wt.exists():
            wt_file = fallback_wt

    sources = [
        ("Ground Truth Candidate Generation", gt_file, args.gt_top_k),
        ("Method 1: Full-text Ranking", ft_file, args.rank_top_k),
        ("Method 2: Equal-weight Facet Ranking", eq_file, args.rank_top_k),
        ("Method 3: Weighted Facet Ranking", wt_file, args.rank_top_k)
    ]

    all_raw_candidates = []
    source_stats = {}

    for source_name, fpath, top_k in sources:
        if fpath.exists():
            items = parse_ranking_file(fpath, source_name, top_k)
            all_raw_candidates.extend(items)
            source_stats[source_name] = len(items)
            print(f"[+] {source_name:36} (Top {top_k:3}): Thu thập được {len(items):5} cặp từ {fpath.name}")
        else:
            print(f"[!] {source_name:36}: Chưa tìm thấy tệp tại {fpath.name}")
            source_stats[source_name] = 0

    print(f"\n--> Tổng số bản ghi Candidate thu thập được từ tất cả các nguồn: {len(all_raw_candidates)}")

    with open(output_pool_file, "w", encoding="utf-8") as f:
        for r in all_raw_candidates:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[+] Đã lưu toàn bộ Candidate Pool ban đầu vào: {output_pool_file}")
    print("--> Hoàn tất Bước 1.")

if __name__ == "__main__":
    main()
