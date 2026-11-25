# MODULE KHUYẾN NGHỊ HỘI NGHỊ KHOA HỌC DỰA TRÊN 5 FACETS (CONFERENCE RECOMMENDATION)

Module độc lập chuyên trách bài toán **Khuyến nghị Hội nghị Khoa học (Conference Recommendation)** cho dự án DS300.  
Toàn bộ mã nguồn được đóng gói biệt lập trong thư mục `scripts/conference_recommendation/` và `configs/conference_recommendation/`, **tuyệt đối không can thiệp hay gây conflict với các thư mục `exp_a` đến `exp_e`**.

---

## 1. Kiến Trúc & Cấu Trúc Tệp Tin Sau Chuẩn Hóa

```
scripts/conference_recommendation/
├── __init__.py           # Khai báo package và export các lớp chính
├── data_loader.py        # [1] Nạp Train (602) & Test (186), ghép với 5 Facets của Exp A theo paper_id
├── feature_loader.py     # [2] Module nhúng đa mô hình: TF-IDF, SPECTER2, SciBERT, Precomputed vectors
├── reranker.py           # [3] Thuật toán Gated 5-Facet k-NN Reranker (Phương pháp đề xuất chính)
├── baselines.py          # [4] Các baseline đối chứng: Whole-Text k-NN, Flat 5-Facet k-NN, Random
├── metrics.py            # [5] Thư viện tính Hit@1, Hit@3, Hit@5, MRR, Macro-Hit@K, Macro-MRR
├── evaluate.py           # [6] Runner đánh giá mô hình trên 186 bài Test
├── run_benchmark.py      # [7] Runner tự động hóa so sánh nhiều LLM Extractor (Exp A -> Conference)
└── README.md             # Tài liệu hướng dẫn sử dụng toàn diện
```

---

## 2. Hướng Dẫn Sử Dụng Với Các File Dataset Từ Nhiều LLM Khác Nhau (Exp A)

Một trong các mục tiêu cốt lõi của đề tài là: **Đo lường mức độ ảnh hưởng của chất lượng trích xuất 5 facets từ các LLM khác nhau đến độ chính xác của hệ thống khuyến nghị hội nghị**.

### 2.1. Định dạng Tệp Dữ Liệu 5 Facets Yêu Cầu
Mọi tệp trích xuất 5 facets từ Exp A khi đưa vào nhánh hội nghị cần tuân theo định dạng chuẩn **JSONL** (mỗi dòng là một JSON object) và chia sẻ chung khóa định danh `paper_id`:

```json
{
  "paper_id": "P000001",
  "problem": ["Neural Machine Translation with low resource languages"],
  "task": ["Language translation", "Domain adaptation"],
  "method": ["Adversarial training", "Data augmentation"],
  "dataset": ["IWSLT 2014", "WMT 14"],
  "contribution": ["Outperformed standard baseline by 1.5 BLEU score"]
}
```
*(Ghi chú: Trường `problem`, `task`, `method`, `dataset`, `contribution` có thể là danh sách các chuỗi `List[str]` hoặc chuỗi văn bản `str`).*

### 2.2. Cách Chạy Đánh Giá Trên Một File LLM Cụ Thể
Bạn có thể sử dụng cờ `--facets-path` trong lệnh gọi `evaluate.py` để trỏ trực tiếp tới tệp 5 facets của mô hình mong muốn mà không cần sửa file code hay cấu hình:

```bash
# 1. Chạy với kết quả trích xuất của Qwen-Local (Silver):
python scripts/conference_recommendation/evaluate.py --facets-path data/exp_a/generated/facets_silver.jsonl

# 2. Chạy với kết quả trích xuất của Gemini 1.5 Flash:
python scripts/conference_recommendation/evaluate.py --facets-path data/exp_a/generated/facets_gemini.jsonl

# 3. Chạy với kết quả trích xuất của Regex Heuristic Baseline:
python scripts/conference_recommendation/evaluate.py --facets-path data/exp_a/generated/facets_regex.jsonl
```

### 2.3. Cấu Hình Mặc Định Trong File `config.json`
Nếu muốn cố định một file facets làm mặc định cho toàn bộ pipeline, mở file `configs/conference_recommendation/config.json` và sửa trường `facets_path`:

```json
{
  "dataset_split_dir": "data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019",
  "facets_path": "data/exp_a/generated/facets_gemini.jsonl",
  "algorithm": "gated_knn"
}
```

### 2.4. Chạy Tự Động So Sánh Đồng Loạt Các LLM (`run_benchmark.py`)
File `run_benchmark.py` được lập trình sẵn để tự động duyệt qua danh sách các file trích xuất và xuất bảng ma trận so sánh.

1. Mở file `scripts/conference_recommendation/run_benchmark.py` và kiểm tra danh sách `extractors`:
```python
extractors = [
    {
        "name": "Qwen-Local (Silver)",
        "path": repo_root / "data/exp_a/generated/facets_silver.jsonl",
    },
    {
        "name": "Gemini-1.5-Flash",
        "path": repo_root / "data/exp_a/generated/facets_gemini.jsonl",
    },
    {
        "name": "Regex-Rule-Baseline",
        "path": repo_root / "data/exp_a/generated/facets_regex.jsonl",
    },
    # Thêm mô hình mới tại đây (ví dụ Llama-3-8B):
    # {
    #     "name": "Llama-3-8B-Instruct",
    #     "path": repo_root / "data/exp_a/generated/facets_llama3.jsonl",
    # },
]
```

2. Thực thi lệnh chạy benchmark:
```bash
python scripts/conference_recommendation/run_benchmark.py
```

3. Kết quả sẽ được tổng hợp tự động ra file:
`results/conference_recommendation/multi_extractor_benchmark.csv`

---

## 3. Khái Quát Hóa Vector Hóa (`feature_loader.py`): Hỗ Trợ Đa Dạng Embedding

Mã nguồn trong `feature_loader.py` đã được tái cấu trúc theo mô hình **Pluggable Embedding Backend**, hỗ trợ 4 chế độ nhúng:

| Backend | Tên cấu hình | Đặc điểm & Yêu cầu | Trường hợp sử dụng |
|---|:---:|---|---|
| **TF-IDF (Mặc định)** | `tfidf` | Thuần CPU, chạy trong 1-2 giây, 0 thư viện ngoài | Chạy nhanh, kiểm tra luồng, đồng bộ với Exp B |
| **SPECTER2** | `specter2` | Dense Transformer chuyên sâu cho bài báo khoa học (`allenai/specter2_base`) | Tăng độ chính xác ngữ nghĩa sâu, hiểu từ đồng nghĩa |
| **SentenceTransformer**| `sentence_transformers` | Bất kỳ mô hình HuggingFace nào (`scibert`, `bge-small-en`...) | Tùy biến các mô hình ngôn ngữ học sâu khác |
| **Precomputed Vectors**| `precomputed` | Nạp trực tiếp vector tính sẵn từ file `.npz` hoặc `.jsonl` | Tiết kiệm 100% thời gian encode khi chạy lặp lại |

### 3.1. Chạy với TF-IDF Mặc Định (Nhanh, Nhẹ)
```bash
python scripts/conference_recommendation/evaluate.py --embedding-backend tfidf
```

### 3.2. Chạy với Dense Embedding (SPECTER2)
Yêu cầu cài đặt: `pip install sentence-transformers torch`
```bash
# Chạy với mô hình mặc định allenai/specter2_base:
python scripts/conference_recommendation/evaluate.py --embedding-backend specter2

# Hoặc tùy biến tên mô hình bất kỳ trên HuggingFace:
python scripts/conference_recommendation/evaluate.py --embedding-backend sentence_transformers --embedding-model allenai/scibert_scivocab_uncased
```

### 3.3. Chạy với Precomputed Vectors (File Vector Đã Sinh Sẵn)
Nếu nhóm đã chạy GPU sinh trước vector cho các bài báo và lưu dưới dạng `.npz` hoặc `.jsonl`:
```bash
python scripts/conference_recommendation/evaluate.py --embedding-backend precomputed --embedding-path path/to/precomputed_vectors.npz
```

**Quy ước định dạng file Precomputed:**
- **File `.npz`**: Chứa các mảng numpy 1D với key có dạng: `{paper_id}__{field_name}` (ví dụ: `P000012__problem`, `P000012__method`...).
- **File `.jsonl`**: Mỗi dòng là một JSON:
  ```json
  {"paper_id": "P000012", "whole_text": [0.02, ...], "problem": [0.15, ...], "task": [...], "method": [...], "dataset": [...], "contribution": [...]}
  ```

---

## 4. Hướng Dẫn So Sánh Baselines & Phân Tích Kết Quả

### 4.1. Chạy Toàn Bộ Bảng So Sánh (Proposed vs Baselines)
```bash
python scripts/conference_recommendation/evaluate.py --model all
```

Bảng kết quả in ra sẽ so sánh 4 mô hình:
1. **`Proposed: Gated 5-Facet k-NN`**: Tái xếp hạng kết hợp Cổng Ngữ Cảnh $\mathcal{G}_{\text{problem}}$ và 4 facets giải pháp.
2. **`Baseline: Flat 5-Facet k-NN`**: Cộng phẳng 5 facets không có cổng ngữ cảnh.
3. **`Baseline: Whole-Text k-NN`**: Chỉ dùng toàn văn Title + Abstract.
4. **`Baseline: Random`**: Mốc sàn ngẫu nhiên.

### 4.2. Ý Nghĩa Của Các Chỉ Số Đánh Giá
* **`Hit@1`**: Tỷ lệ bài báo được hệ thống dự đoán **chính xác 100% ở vị trí số 1**.
* **`Hit@3`**: Tỷ lệ hội nghị đúng xuất hiện trong **Top-3 gợi ý** của hệ thống (chỉ số thực tế quan trọng nhất).
* **`Hit@5`**: Tỷ lệ hội nghị đúng nằm trong Top-5.
* **`MRR (Mean Reciprocal Rank)`**: Điểm trung bình nghịch đảo thứ hạng của hội nghị đúng.
* **`Macro-Hit@3` & `Macro-MRR`**: Điểm trung bình được tính đồng đều trên cả 30 hội nghị ($1/30$ cho mỗi hội nghị). Thước đo này triệt tiêu hoàn toàn sự thiên lệch dữ liệu, bảo đảm hội nghị ít bài (như ICLR, WSDM) có tiếng nói bình đẳng với hội nghị nhiều bài (ACL, EMNLP).

---

## 5. Bảng Tóm Tắt Các Lệnh Thường Dùng

```bash
# 1. Đánh giá nhanh bằng TF-IDF trên toàn bộ baselines:
python scripts/conference_recommendation/evaluate.py --model all

# 2. Đánh giá riêng thuật toán đề xuất với file facets của Gemini:
python scripts/conference_recommendation/evaluate.py --model gated_knn --facets-path data/exp_a/generated/facets_gemini.jsonl

# 3. Tinh chỉnh siêu tham số k láng giềng và ngưỡng Cổng tau:
python scripts/conference_recommendation/evaluate.py --k 15 --tau 0.50

# 4. Đánh giá với mô hình nhúng học sâu SPECTER2:
python scripts/conference_recommendation/evaluate.py --embedding-backend specter2

# 5. Chạy benchmark so sánh đồng loạt tất cả LLM Extractor:
python scripts/conference_recommendation/run_benchmark.py
```
