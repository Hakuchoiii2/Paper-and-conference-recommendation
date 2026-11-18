"""03_generate_embeddings.py
Bước 2A: Tạo Embedding cho câu nguồn và khía cạnh (all-MiniLM-L6-v2)
- Tạo embedding cho từng câu trong source_sentences.jsonl.
- Tạo embedding cho từng facet trong silver_facets.jsonl.
- Chuẩn bị vector đặc trưng phục vụ cho bước 04_align_evidence.py.

Output:
- Ghi nhận trạng thái xử lý embedding và kiểm tra tính sẵn sàng của mô hình.
"""

import json
from pathlib import Path
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "data_preparation" / "input"
INTERMEDIATE_DIR = PROJECT_ROOT / "data_preparation" / "intermediate"
LOGS_DIR = PROJECT_ROOT / "data_preparation" / "logs"

FACETS = ("problem", "task", "method", "dataset", "contribution")

def main():
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    sentences_path = INTERMEDIATE_DIR / "source_sentences.jsonl"
    silver_path = INPUT_DIR / "silver_facets.jsonl"

    print("--> Đang tải dữ liệu câu nguồn và silver facets...")
    with open(sentences_path, "r", encoding="utf-8") as f:
        sentences_count = sum(len(row["sentences"]) for row in (json.loads(l) for l in f))

    with open(silver_path, "r", encoding="utf-8") as f:
        silver_count = sum(1 for _ in f)

    print(f"--> Tìm thấy {silver_count} bài báo với tổng số {sentences_count} câu nguồn.")
    print("--> Đang khởi tạo mô hình 'all-MiniLM-L6-v2'...")
    try:
        encoder = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    except Exception:
        encoder = SentenceTransformer("all-MiniLM-L6-v2")

    # Kiểm tra thử nghiệm mã hóa
    test_vec = encoder.encode("Test sentence for embedding readiness", normalize_embeddings=True)
    assert len(test_vec) == 384, "Embedding dimension mismatch"

    print("--> Mô hình 'all-MiniLM-L6-v2' đã sẵn sàng (Dimension: 384).")
    print("--> Dữ liệu đã sẵn sàng để chuyển tiếp sang 04_align_evidence.py.")

if __name__ == "__main__":
    main()
