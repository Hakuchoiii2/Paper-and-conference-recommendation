"""03_generate_embeddings.py
Bước 2A: Tạo Embedding cho câu nguồn và khía cạnh (all-MiniLM-L6-v2)
- Tạo embedding cho từng câu trong source_sentences.jsonl.
- Tạo embedding cho từng facet trong silver_facets.jsonl.
- Chuẩn bị vector đặc trưng phục vụ cho bước 04_align_evidence.py.

This step checks that the locally cached model is ready. Step 04 creates and
uses the source/facet embeddings for evidence alignment.
"""

import json
import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from data_preparation.pipeline_scope import filter_by_scope

try:
    from sentence_transformers import SentenceTransformer
except ImportError as exc:
    raise RuntimeError(
        "sentence-transformers is required. Run data_preparation\\setup_semantic_models.ps1."
    ) from exc
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
LOGS_DIR = PROJECT_ROOT / "data_preparation" / "logs"

FACETS = ("problem", "task", "method", "dataset", "contribution")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="Verify local embedding model readiness")
    args = parser.parse_args()

    sentences_path = INTERMEDIATE_DIR / "source_sentences.jsonl"
    silver_path = INPUT_DIR / "silver_facets.jsonl"

    print("--> Đang khởi tạo mô hình 'all-MiniLM-L6-v2'...")
    try:
        encoder = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    except Exception as exc:
        raise RuntimeError(
            "The all-MiniLM-L6-v2 embedding model is not available locally. "
            "Run data_preparation\\setup_semantic_models.ps1 to prepare the models."
        ) from exc

    # Kiểm tra thử nghiệm mã hóa
    test_vec = encoder.encode("Test sentence for embedding readiness", normalize_embeddings=True)
    assert len(test_vec) == 384, "Embedding dimension mismatch"

    print("--> Mô hình 'all-MiniLM-L6-v2' đã sẵn sàng (Dimension: 384).")
    if args.check_only:
        return

    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    print("--> Đang tải dữ liệu câu nguồn và silver facets...")
    with open(sentences_path, "r", encoding="utf-8") as f:
        sentences_count = sum(len(row["sentences"]) for row in (json.loads(l) for l in f))

    with open(silver_path, "r", encoding="utf-8") as f:
        silver_count = len(filter_by_scope([json.loads(line) for line in f]))

    print(f"--> Tìm thấy {silver_count} bài báo với tổng số {sentences_count} câu nguồn.")
    print("--> Dữ liệu đã sẵn sàng để chuyển tiếp sang 04_align_evidence.py.")

if __name__ == "__main__":
    main()
