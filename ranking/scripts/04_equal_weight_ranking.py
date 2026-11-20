"""04_equal_weight_ranking.py
Method 2 – Facet baseline: Equal-weight Facet Ranking
- So sánh từng facet tương ứng giữa Query và Candidate:
    problem vs problem, task vs task, method vs method, dataset vs dataset, contribution vs contribution.
- Mỗi facet có trọng số bằng nhau: w_f = 0.2.
- Công thức chuẩn hóa theo Mục 4.1:
    S_equal(q, c) = [sum_{f in V(q,c)} 0.2 * s_f(q, c)] / [sum_{f in V(q,c)} 0.2]
  Trong đó V(q,c) là tập các facet có mặt hợp lệ (PRESENT) ở CẢ Query và Candidate.
- QUY TẮC BẮT BUỘC (Mục 4.1):
    KHÔNG được cho similarity bằng 0 chỉ vì một bên thiếu thông tin.
    Nếu facet bị thiếu ở Query hoặc Candidate thì bỏ qua facet đó và chia cho tổng trọng số thực tế sử dụng.
- Loại trừ chính Query Paper khỏi danh sách Candidate (c != q).

Output:
- ranking/output/equal_weight_ranking.jsonl
"""

import json
import argparse
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RANKING_DIR = PROJECT_ROOT / "ranking"
CONFIG_PATH = RANKING_DIR / "config" / "ranking_config.json"

FACETS = ["problem", "task", "method", "dataset", "contribution"]

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_path(p_str):
    p = Path(p_str)
    return p if p.is_absolute() else PROJECT_ROOT / p

def main():
    parser = argparse.ArgumentParser(description="Method 2: Equal-weight Facet Ranking")
    parser.add_argument("--top-k", type=int, default=100, help="Số lượng ứng viên lưu lại cho mỗi query (mặc định: 100)")
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all", help="Chạy cho tập queries nào (all/dev/test)")
    args = parser.parse_args()

    config = load_config()
    paths = config.get("paths", {})

    facet_emb_dir = resolve_path(paths.get("intermediate_facet_emb", "ranking/intermediate/facet_embeddings"))
    ids_file = facet_emb_dir / "paper_ids.json"
    output_file = resolve_path(paths.get("output_equal_weight", "ranking/output/equal_weight_ranking.jsonl"))
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("="*75)
    print("METHOD 2: EQUAL-WEIGHT FACET RANKING (BASELINE 5 FACETS)")
    print("="*75)

    if not ids_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy Facet Embeddings tại {facet_emb_dir}")
        print("    Vui lòng chạy Bước 2: python ranking/scripts/02_prepare_embeddings.py trước.")
        return

    with open(ids_file, "r", encoding="utf-8") as f:
        paper_ids = json.load(f)
    id_to_idx = {pid: i for i, pid in enumerate(paper_ids)}
    N = len(paper_ids)

    # Tải embeddings và masks của 5 facets
    print("--> Đang nạp Embeddings và Masks của 5 khía cạnh...")
    facet_embs = {}
    facet_masks = {}
    for f in FACETS:
        emb_path = facet_emb_dir / f"facet_{f}_embeddings.npy"
        mask_path = facet_emb_dir / f"facet_{f}_mask.npy"
        if not (emb_path.exists() and mask_path.exists()):
            print(f"[!] Lỗi: Thiếu dữ liệu của facet '{f}' tại {facet_emb_dir}")
            return
        facet_embs[f] = np.load(emb_path)    # Shape (N, 384)
        facet_masks[f] = np.load(mask_path)  # Shape (N,) bool

    # Đọc danh sách queries từ query_split.json
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
    print(f"[+] Trọng số mỗi facet: w_f = 0.2")

    WEIGHT = 0.2
    ranked_records = []

    for q_idx, q_id in enumerate(query_list):
        if q_id not in id_to_idx:
            continue

        q_vec_idx = id_to_idx[q_id]

        # Khởi tạo tử số và mẫu số cho tất cả N ứng viên
        numerator = np.zeros(N, dtype=np.float32)
        denominator = np.zeros(N, dtype=np.float32)

        # Duyệt qua từng facet
        for f in FACETS:
            # Query có facet này không?
            if not facet_masks[f][q_vec_idx]:
                continue  # Bỏ qua facet nếu Query không có (Mục 4.1)

            q_f_vec = facet_embs[f][q_vec_idx]  # Shape (384,)
            
            # Tính similarity với tất cả các ứng viên
            f_sims = np.dot(facet_embs[f], q_f_vec)  # Shape (N,)

            # Chỉ xét ứng viên nào cũng CÓ facet này (Candidate mask == True)
            c_has_facet = facet_masks[f]

            # Cộng vào tử số và mẫu số theo công thức chuẩn hóa
            numerator += np.where(c_has_facet, WEIGHT * f_sims, 0.0)
            denominator += np.where(c_has_facet, WEIGHT, 0.0)

        # Điểm cuối cùng = numerator / denominator (nếu denominator == 0 thì score = 0)
        final_scores = np.zeros(N, dtype=np.float32)
        valid_pairs = denominator > 0
        final_scores[valid_pairs] = numerator[valid_pairs] / denominator[valid_pairs]

        # Loại trừ chính query khỏi candidate list (Mục 4.2)
        final_scores[q_vec_idx] = -1e9

        # Lấy Top-K ứng viên
        top_k = min(args.top_k, N - 1) if args.top_k > 0 else N - 1
        top_indices = np.argpartition(final_scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(-final_scores[top_indices])]

        candidates_ranked = []
        for rank, c_idx in enumerate(top_indices, start=1):
            candidates_ranked.append({
                "candidate_id": paper_ids[c_idx],
                "rank": rank,
                "score": float(final_scores[c_idx])
            })

        ranked_records.append({
            "query_id": q_id,
            "method": "equal_weight_facet",
            "split": "dev" if q_id in dev_queries else "test",
            "candidate_count": len(candidates_ranked),
            "ranking": candidates_ranked
        })

    with open(output_file, "w", encoding="utf-8") as f:
        for r in ranked_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[+] Đã hoàn thành xếp hạng cho {len(ranked_records)} queries.")
    print(f"[+] Kết quả lưu tại: {output_file}")
    print("--> Hoàn tất Method 2.")

if __name__ == "__main__":
    main()
