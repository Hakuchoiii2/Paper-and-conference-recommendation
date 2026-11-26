"""05_weighted_ranking.py
Method 3 – Weighted Facet: Weighted Facet Ranking
- So sánh từng facet tương ứng giữa Query và Candidate với cấu hình trọng số ưu tiên:
    | Facet        | Trọng số w_f |
    | Problem      | 0.4          |
    | Task         | 0.2          |
    | Method       | 0.2          |
    | Dataset      | 0.1          |
    | Contribution | 0.1          |
- Công thức chuẩn hóa theo Mục 4.1:
    S_weighted(q, c) = [sum_{f in V(q,c)} w_f * s_f(q, c)] / [sum_{f in V(q,c)} w_f]
- Xử lý thiếu facet (Mục 4.1):
    Nếu Dataset bị thiếu ở Query hoặc Candidate thì tổng trọng số mẫu số chỉ còn 0.9.
    Điểm cuối cùng được chia cho 0.9 thay vì 1.0.
- Xếp hạng trên cùng tập Candidate Corpus (Mục 4.2).

Output:
- ranking/output/weighted_ranking.jsonl
- ranking/output/final_ranking_results.jsonl (Hợp nhất kết quả 3 phương pháp)
"""

import json
import argparse
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RANKING_DIR = PROJECT_ROOT / "ranking"
CONFIG_PATH = RANKING_DIR / "config" / "ranking_config.json"

FACETS = ["problem", "task", "method", "dataset", "contribution"]
DEFAULT_WEIGHTS = {
    "problem": 0.4,
    "task": 0.2,
    "method": 0.2,
    "dataset": 0.1,
    "contribution": 0.1
}

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_path(p_str):
    p = Path(p_str)
    return p if p.is_absolute() else PROJECT_ROOT / p

def main():
    parser = argparse.ArgumentParser(description="Method 3: Weighted Facet Ranking")
    parser.add_argument("--top-k", type=int, default=100, help="Số lượng ứng viên lưu lại cho mỗi query (mặc định: 100)")
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all", help="Chạy cho tập queries nào (all/dev/test)")
    args = parser.parse_args()

    config = load_config()
    paths = config.get("paths", {})
    weights_cfg = config.get("weight_configurations", {}).get("method_3_weighted", {}).get("weights", DEFAULT_WEIGHTS)

    facet_emb_dir = resolve_path(paths.get("intermediate_facet_emb", "ranking/intermediate/facet_embeddings"))
    ids_file = facet_emb_dir / "paper_ids.json"
    output_file = resolve_path(paths.get("output_weighted", "ranking/output/weighted_ranking.jsonl"))
    final_output_file = resolve_path(paths.get("output_final", "ranking/output/final_ranking_results.jsonl"))
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("="*75)
    print("METHOD 3: WEIGHTED FACET RANKING (PRIORITIZE PROBLEM 0.4)")
    print("="*75)

    if not ids_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy Facet Embeddings tại {facet_emb_dir}")
        print("    Vui lòng chạy Bước 2: python ranking/scripts/02_prepare_embeddings.py trước.")
        return

    with open(ids_file, "r", encoding="utf-8") as f:
        paper_ids = json.load(f)
    id_to_idx = {pid: i for i, pid in enumerate(paper_ids)}
    N = len(paper_ids)

    print("--> Đang nạp Embeddings và Masks của 5 khía cạnh...")
    facet_embs = {}
    facet_masks = {}
    for f in FACETS:
        emb_path = facet_emb_dir / f"facet_{f}_embeddings.npy"
        mask_path = facet_emb_dir / f"facet_{f}_mask.npy"
        if not (emb_path.exists() and mask_path.exists()):
            print(f"[!] Lỗi: Thiếu dữ liệu của facet '{f}' tại {facet_emb_dir}")
            return
        facet_embs[f] = np.load(emb_path)
        facet_masks[f] = np.load(mask_path)

    split_path = resolve_path(paths.get("query_split", "ranking/input/query_split.json"))
    if not split_path.exists():
        split_path = RANKING_DIR / "input" / "query_split.template.json"

    query_list = []
    dev_queries, test_queries = [], []
    if split_path.exists():
        with open(split_path, "r", encoding="utf-8") as f:
            split_data = json.load(f)
            dev_queries = split_data.get("dev", [])
            test_queries = split_data.get("test", [])

        if args.split == "dev":
            query_list = dev_queries
        elif args.split == "test":
            query_list = test_queries
        else:
            query_list = dev_queries + test_queries
    else:
        query_list = paper_ids[:50]

    print(f"[+] Số lượng Queries cần xếp hạng: {len(query_list)} (Chế độ: {args.split.upper()})")
    print(f"[+] Bảng trọng số cấu hình: {weights_cfg}")

    ranked_records = []

    for q_idx, q_id in enumerate(query_list):
        if q_id not in id_to_idx:
            continue

        q_vec_idx = id_to_idx[q_id]

        numerator = np.zeros(N, dtype=np.float32)
        denominator = np.zeros(N, dtype=np.float32)

        for f in FACETS:
            w_f = float(weights_cfg.get(f, 0.2))

            # Nếu Query thiếu facet này -> Bỏ qua
            if not facet_masks[f][q_vec_idx]:
                continue

            q_f_vec = facet_embs[f][q_vec_idx]
            f_sims = np.dot(facet_embs[f], q_f_vec)

            c_has_facet = facet_masks[f]

            numerator += np.where(c_has_facet, w_f * f_sims, 0.0)
            denominator += np.where(c_has_facet, w_f, 0.0)

        valid_pairs = denominator > 0
        valid_pairs[q_vec_idx] = False
        eligible_indices = np.flatnonzero(valid_pairs)
        scores = numerator[eligible_indices] / denominator[eligible_indices]
        order = np.argsort(-scores, kind="stable")
        if args.top_k > 0:
            order = order[:args.top_k]

        candidates_ranked = []
        for rank, position in enumerate(order, start=1):
            c_idx = eligible_indices[position]
            candidates_ranked.append({
                "candidate_id": paper_ids[c_idx],
                "rank": rank,
                "score": float(scores[position])
            })

        ranked_records.append({
            "query_id": q_id,
            "method": "weighted_facet",
            "weights": weights_cfg,
            "split": "dev" if q_id in dev_queries else "test",
            "candidate_count": len(candidates_ranked),
            "ranking": candidates_ranked
        })

    with open(output_file, "w", encoding="utf-8") as f:
        for r in ranked_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[+] Đã hoàn thành xếp hạng cho {len(ranked_records)} queries.")
    print(f"[+] Kết quả Method 3 lưu tại: {output_file}")

    # Hợp nhất kết quả 3 phương pháp vào final_ranking_results.jsonl (nếu các file kia đã chạy)
    out_full = resolve_path(paths.get("output_fulltext", "ranking/output/fulltext_ranking.jsonl"))
    out_equal = resolve_path(paths.get("output_equal_weight", "ranking/output/equal_weight_ranking.jsonl"))

    all_methods_records = []
    if out_full.exists():
        all_methods_records.extend(json.loads(line) for line in open(out_full, encoding="utf-8"))
    if out_equal.exists():
        all_methods_records.extend(json.loads(line) for line in open(out_equal, encoding="utf-8"))
    all_methods_records.extend(ranked_records)

    with open(final_output_file, "w", encoding="utf-8") as f:
        for r in all_methods_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[+] Đã hợp nhất kết quả các phương pháp vào: {final_output_file}")
    print("--> Hoàn tất Method 3.")

if __name__ == "__main__":
    main()
