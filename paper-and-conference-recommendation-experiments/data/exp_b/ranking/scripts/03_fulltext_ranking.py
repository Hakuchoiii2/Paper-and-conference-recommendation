"""03_fulltext_ranking.py
Method 1 – Baseline: Full-text Embedding Ranking
- Sử dụng toàn bộ title + abstract của Query Paper và Candidate Paper.
- Lấy embedding từ intermediate/paper_embeddings/fulltext_embeddings.npy.
- Tính cosine similarity giữa hai embedding: S_full(q, c) = cos(E(Tq + Aq), E(Tc + Ac)).
- Sắp xếp Candidate theo similarity giảm dần.
- Loại trừ chính Query Paper khỏi danh sách Candidate (c != q).
- Tất cả phương pháp đều xếp hạng trên cùng tập Candidate Corpus để bảo đảm công bằng (Mục 4.2).

Output:
- ranking/output/fulltext_ranking.jsonl
"""

import json
import argparse
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RANKING_DIR = PROJECT_ROOT / "ranking"
CONFIG_PATH = RANKING_DIR / "config" / "ranking_config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_path(p_str):
    p = Path(p_str)
    return p if p.is_absolute() else PROJECT_ROOT / p

def main():
    parser = argparse.ArgumentParser(description="Method 1: Full-text Embedding Ranking")
    parser.add_argument("--top-k", type=int, default=100, help="Số lượng ứng viên lưu lại cho mỗi query (mặc định: 100)")
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all", help="Chạy cho tập queries nào (all/dev/test)")
    args = parser.parse_args()

    config = load_config()
    paths = config.get("paths", {})

    paper_emb_dir = resolve_path(paths.get("intermediate_paper_emb", "ranking/intermediate/paper_embeddings"))
    emb_file = paper_emb_dir / "fulltext_embeddings.npy"
    ids_file = paper_emb_dir / "paper_ids.json"
    output_file = resolve_path(paths.get("output_fulltext", "ranking/output/fulltext_ranking.jsonl"))
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("="*75)
    print("METHOD 1: FULL-TEXT EMBEDDING RANKING (BASELINE)")
    print("="*75)

    if not (emb_file.exists() and ids_file.exists()):
        print(f"[!] Lỗi: Chưa tìm thấy Fulltext Embeddings tại {emb_file}")
        print("    Vui lòng chạy Bước 2: python ranking/scripts/02_prepare_embeddings.py trước.")
        return

    # Tải embeddings
    print(f"--> Đang tải Full-text Embeddings từ {emb_file.name}...")
    full_embs = np.load(emb_file)  # Shape (N, 384)
    with open(ids_file, "r", encoding="utf-8") as f:
        paper_ids = json.load(f)

    id_to_idx = {pid: i for i, pid in enumerate(paper_ids)}
    N = len(paper_ids)

    # Đọc danh sách queries từ query_split.json
    split_path = resolve_path(paths.get("query_split", "ranking/input/query_split.json"))
    if not split_path.exists():
        split_path = RANKING_DIR / "input" / "query_split.template.json"

    query_list = []
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
        # Nếu chưa có split, lấy 50 bài đầu tiên làm mẫu kiểm thử
        query_list = paper_ids[:50]

    print(f"[+] Số lượng Queries cần xếp hạng: {len(query_list)} (Chế độ: {args.split.upper()})")
    print(f"[+] Không gian ứng viên cho mỗi query: {N - 1} bài báo (loại trừ chính Query Paper)")

    ranked_records = []
    for q_idx, q_id in enumerate(query_list):
        if q_id not in id_to_idx:
            print(f"[!] Bỏ qua {q_id}: không tìm thấy trong embeddings")
            continue

        q_vec_idx = id_to_idx[q_id]
        q_vec = full_embs[q_vec_idx]  # Shape (384,)

        # Tính dot product (vì vectors đã được L2 normalized nên dot product == cosine similarity)
        scores = np.dot(full_embs, q_vec)  # Shape (N,)

        # Loại trừ chính query khỏi candidate list (Mục 4.2)
        scores[q_vec_idx] = -1e9

        # Lấy Top-K ứng viên có điểm cao nhất
        top_k = min(args.top_k, N - 1) if args.top_k > 0 else N - 1
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        # Sắp xếp giảm dần theo điểm
        top_indices = top_indices[np.argsort(-scores[top_indices])]

        candidates_ranked = []
        for rank, c_idx in enumerate(top_indices, start=1):
            candidates_ranked.append({
                "candidate_id": paper_ids[c_idx],
                "rank": rank,
                "score": float(scores[c_idx])
            })

        ranked_records.append({
            "query_id": q_id,
            "method": "fulltext_embedding",
            "split": "dev" if q_id in dev_queries else "test",
            "candidate_count": len(candidates_ranked),
            "ranking": candidates_ranked
        })

    # Lưu kết quả
    with open(output_file, "w", encoding="utf-8") as f:
        for r in ranked_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[+] Đã hoàn thành xếp hạng cho {len(ranked_records)} queries.")
    print(f"[+] Kết quả lưu tại: {output_file}")
    print("--> Hoàn tất Method 1.")

if __name__ == "__main__":
    main()
