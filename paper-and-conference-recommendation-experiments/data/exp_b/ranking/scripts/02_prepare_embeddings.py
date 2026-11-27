"""02_prepare_embeddings.py
Bước 2: Chuẩn bị và cache embeddings cho Full-text và 5 facet bằng encoder trong cấu hình.
- Mã hóa toàn văn bài báo (Title + Abstract) -> lưu vào intermediate/paper_embeddings/
- Mã hóa riêng từng facet (cho các bài có facet_status == 'PRESENT') -> lưu vào intermediate/facet_embeddings/
- Lưu mảng boolean mask để đánh dấu facet có hợp lệ/hiện diện hay không.
- Hỗ trợ cơ chế Cache: Bỏ qua tính lại nếu file .npy đã tồn tại (dùng --force để ép tính lại).
- Hỗ trợ --check-only để kiểm tra tính sẵn sàng mà không cần chạy mô hình nặng.
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

REPO_ROOT = PROJECT_ROOT.parents[1]

def resolve_path(p_str):
    p = Path(p_str)
    if p.is_absolute():
        return p
    if (REPO_ROOT / p).exists():
        return REPO_ROOT / p
    return PROJECT_ROOT / p

def get_sentence_transformer(model_name, pooling=None):
    from sentence_transformers import SentenceTransformer, models
    print(f"--> Đang tải mô hình Encoder: {model_name}...")
    if pooling == "mean":
        encoder = models.Transformer(model_name)
        pool = models.Pooling(encoder.get_word_embedding_dimension(), pooling_mode="mean")
        return SentenceTransformer(modules=[encoder, pool])
    model = SentenceTransformer(model_name)
    return model

def main():
    parser = argparse.ArgumentParser(description="Tạo và cache embeddings cho Ranking")
    parser.add_argument("--force", action="store_true", help="Bắt buộc tính toán lại dù đã có cache")
    parser.add_argument("--check-only", action="store_true", help="Chỉ kiểm tra cấu trúc dữ liệu và cache, không chạy model")
    args = parser.parse_args()

    config = load_config()
    paths = config.get("paths", {})
    model_cfg = config.get("model", {})
    model_name = model_cfg.get("name", "sentence-transformers/all-MiniLM-L6-v2")

    paper_emb_dir = resolve_path(paths.get("intermediate_paper_emb", "ranking/intermediate/paper_embeddings"))
    facet_emb_dir = resolve_path(paths.get("intermediate_facet_emb", "ranking/intermediate/facet_embeddings"))
    paper_emb_dir.mkdir(parents=True, exist_ok=True)
    facet_emb_dir.mkdir(parents=True, exist_ok=True)

    val_silver_path = resolve_path(paths.get("validated_silver", "ranking/input/validated_silver.jsonl"))
    if not val_silver_path.exists():
        fallback_path = PROJECT_ROOT / "data_preparation" / "output" / "validated_silver.jsonl"
        if fallback_path.exists():
            val_silver_path = fallback_path

    papers_raw_path = resolve_path(paths.get("papers", "data_preparation/input/papers.jsonl"))

    print("="*75)
    print("BƯỚC 2: CHUẨN BỊ VÀ CACHE EMBEDDINGS (FULLTEXT & FACETS)")
    print("="*75)

    if not val_silver_path.exists():
        raise FileNotFoundError(f"Missing Validated Silver: {val_silver_path}")

    # Kiểm tra cache hiện có
    fulltext_emb_file = paper_emb_dir / "fulltext_embeddings.npy"
    fulltext_ids_file = paper_emb_dir / "paper_ids.json"
    cache_complete = all(path.exists() for path in (
        fulltext_emb_file, fulltext_ids_file, facet_emb_dir / "paper_ids.json",
    ))

    for f in FACETS:
        f_emb_file = facet_emb_dir / f"facet_{f}_embeddings.npy"
        f_mask_file = facet_emb_dir / f"facet_{f}_mask.npy"
        if not (f_emb_file.exists() and f_mask_file.exists()):
            cache_complete = False
            break

    if cache_complete and not args.force:
        print("[+] Đã tìm thấy toàn bộ Embeddings Cache hợp lệ:")
        print(f"    - Fulltext Cache : {fulltext_emb_file}")
        print(f"    - Facet Cache    : {facet_emb_dir} (5 facets)")
        print("--> Bỏ qua tính toán. (Dùng cờ --force nếu muốn tạo lại từ đầu).")
        return

    if args.check_only:
        print("[*] Chế độ --check-only: Cache chưa hoàn chỉnh hoặc chưa được tạo.")
        print(f"    - validated_silver: {val_silver_path} (Sẵn sàng)")
        print(f"    - papers_raw      : {papers_raw_path} (Sẵn sàng)")
        print("--> Pipeline hợp lệ, sẵn sàng tạo embeddings khi chạy chính thức.")
        return

    # Tải dữ liệu
    print("--> Đang tải dữ liệu bài báo và validated silver...")
    silver_data = {}
    with open(val_silver_path, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            silver_data[r["paper_id"]] = r

    raw_texts = {}
    if papers_raw_path.exists():
        with open(papers_raw_path, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                pid = r["paper_id"]
                title = r.get("title", "").strip()
                abstract = r.get("abstract", "").strip()
                raw_texts[pid] = f"{title}. {abstract}".strip()

    paper_ids = sorted(silver_data.keys())
    N = len(paper_ids)
    print(f"Tổng số bài báo cần encode: {N}")

    model = get_sentence_transformer(model_name, model_cfg.get("pooling"))
    dim = model.get_sentence_embedding_dimension()
    if dim != model_cfg.get("embedding_dim", dim):
        raise ValueError(f"Encoder {model_name} returned an unexpected dimension: {dim}")

    # 1. Encode Full-text (Title + Abstract)
    print("--> Đang mã hóa Full-text (Title + Abstract)...")
    fulltexts = [raw_texts.get(pid, "") for pid in paper_ids]
    # L2 normalize để tích vô hướng = cosine similarity
    full_embs = model.encode(fulltexts, batch_size=model_cfg.get("batch_size", 64), 
                             show_progress_bar=True, normalize_embeddings=True)
    np.save(fulltext_emb_file, full_embs.astype(np.float32))
    with open(fulltext_ids_file, "w", encoding="utf-8") as f:
        json.dump(paper_ids, f)
    print(f"[+] Đã lưu Fulltext Embeddings: {fulltext_emb_file} (Shape: {full_embs.shape})")

    # 2. Encode 5 Facets
    print("--> Đang mã hóa từng khía cạnh (5 Facets)...")
    (facet_emb_dir / "paper_ids.json").unlink(missing_ok=True)
    for f in FACETS:
        facet_texts = []
        mask = np.zeros(N, dtype=bool)

        for i, pid in enumerate(paper_ids):
            row = silver_data[pid]
            status = row.get("facet_status", {}).get(f, "NOT_MENTIONED")
            text = row.get("facets", {}).get(f, "").strip()

            if status == "PRESENT" and text:
                facet_texts.append(text)
                mask[i] = True
            else:
                facet_texts.append("")  # Placeholder
                mask[i] = False

        # Encode chỉ các bài có facet hợp lệ để tiết kiệm thời gian
        valid_indices = np.where(mask)[0]
        facet_embs = np.zeros((N, dim), dtype=np.float32)

        if len(valid_indices) > 0:
            texts_to_encode = [facet_texts[idx] for idx in valid_indices]
            encoded = model.encode(texts_to_encode, batch_size=model_cfg.get("batch_size", 64),
                                   show_progress_bar=False, normalize_embeddings=True)
            facet_embs[valid_indices] = encoded.astype(np.float32)

        f_emb_file = facet_emb_dir / f"facet_{f}_embeddings.npy"
        f_mask_file = facet_emb_dir / f"facet_{f}_mask.npy"
        np.save(f_emb_file, facet_embs)
        np.save(f_mask_file, mask)
        print(f"[+] Khía cạnh '{f:12}': {len(valid_indices)}/{N} bài có mặt ({len(valid_indices)/N*100:.1f}%) -> Lưu tại {f_emb_file.name}")

    with open(facet_emb_dir / "paper_ids.json", "w", encoding="utf-8") as f:
        json.dump(paper_ids, f)
    print("\n--> Hoàn tất Bước 2. Toàn bộ Embeddings đã được lưu vào Cache.")

if __name__ == "__main__":
    main()
