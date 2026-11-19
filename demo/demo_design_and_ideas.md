# Thiết kế Chuẩn hóa Dữ liệu Mẫu & Hệ thống Phương pháp Ranking cho Demo DS300

Tài liệu này là bản thiết kế đã được đối chiếu trực tiếp với mã nguồn thực nghiệm (`paper-and-conference-recommendation-experiments`), thư mục artifacts cục bộ (`_local/`), và backend demo (`demo/backend/service.py`).

---

## 1. Kiểm kê Dữ liệu Thật Hiện Có (Đã Xác Minh)

### 1.1. Kho Corpus & Tách Tập Train / Test
| Kho dữ liệu | Đường dẫn nguồn | Số lượng | Trạng thái 5 Facets thật |
| :--- | :--- | :---: | :--- |
| **Corpus tổng (Bài báo)** | `data/processed/papers.jsonl` | **4,210 bài** | **4,210 / 4,210 (100%)** từ `data/exp_a/generated/facets_silver.jsonl` (`Qwen3-4B-Instruct`) + `evidence` gốc trong `annotation_metadata.jsonl` |
| **Tập Train Hội nghị** | `data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019_clean/train.jsonl` | **602 bài** (30 hội nghị) | **602 / 602 (100%)** đã được merge sẵn trường `facets` của **`Qwen3-8B`** ngay trong file `train.jsonl` (và có cả `Qwen3-4B` từ `exp_a`) |
| **Tập Test Hội nghị** | `.../temporal_2015_2016_2019_clean/test.jsonl` | **168 bài** (30 hội nghị) | **168 / 168 (100%)** nằm trong `papers.jsonl`, **0% trùng lặp** với 602 bài Train, đã merge sẵn trường `facets` của **`Qwen3-8B`** ngay trong file `test.jsonl` |

### 1.2. Dữ liệu Precomputed của ĐỦ CẢ 5 LLM Extractor trên 168 Bài Test
Đã xác minh đủ **5 / 5 model LLM thật** phủ **100% (168 / 168 bài Test)**:

| Model Key | LoRA Adapter (`_local/adapter/`) | Nguồn 5 Facets thật trên 168 bài Test | Trạng thái trên Demo |
| :--- | :---: | :--- | :--- |
| **`Qwen3-4B`** | Đã có (`Qwen4B`) | `generated_facets/Qwen4B/facets_silver.jsonl` (**168/168**) + evidence gốc từ `exp_a/generated/annotation_metadata.jsonl` | **Sẵn sàng (Precomputed thật + Live)** |
| **`Qwen3-8B`** | Đã có (`Qwen8B`) | Trường `facets` đã merge trực tiếp trong `temporal_2015_2016_2019_clean/test.jsonl` (**168/168**) và `train.jsonl` (**602/602**) | **Sẵn sàng (Precomputed thật)** |
| **`Qwen3-14B`** | Đã có (`Qwen14B`) | `generated_facets/Qwen14B/facets_silver.jsonl` (**168/168**) | **Sẵn sàng (Precomputed thật)** |
| **`Llama3.1-8B`** | Đã có (`Llama8B`) | `generated_facets/Llama8B/facets_silver.jsonl` (**168/168**) | **Sẵn sàng (Precomputed thật)** |
| **`Gemma2-9B`** | Đã có (`Gemma9B`) | `generated_facets/Gemma9B/facets_silver.jsonl` (**168/168**) | **Sẵn sàng (Precomputed thật)** |

> **Vấn đề cần loại bỏ ở Demo cũ (`service.py` hiện tại):**
> * Hiện tại khi chọn chế độ `Mẫu có sẵn`, `service.py` đang fallback về hàm `_extract_heuristic_facets` (cắt câu 1, câu 2, câu cuối) và gắn mác giả tên model → khiến cả 5 model cho ra kết quả **giống hệt nhau**.
> * **Nguyên tắc mới**: Tuyệt đối **không fallback heuristic** ở chế độ `Mẫu có sẵn` — nạp trực tiếp đầu ra LLM thật của **đủ cả 5 model** cho toàn bộ 168 bài Test!

---

## 2. Thiết kế Lại Bộ Dữ liệu Demo (3 Kho Độc Lập — Không Data Leakage)

Thay vì trộn chung 500 bài CSFCube vừa làm corpus vừa làm bài mẫu như cũ, tách thành **3 kho rõ ràng** tại `_local/demo_artifacts/`:

### Kho 1: `paper_corpus.jsonl` (Kho Ứng viên Khuyến nghị Bài báo)
* **Nguồn**: Toàn bộ **4,210 bài** từ `data/processed/papers.jsonl` ghép 5 facets thật từ `data/exp_a/generated/facets_silver.jsonl`.
* **Quy tắc truy vấn**: Khi chấm điểm cho bài mẫu $q$, tự động loại bỏ chính `paper_id` của $q$ (và kiểm tra trùng tiêu đề chuẩn hóa).

### Kho 2: `conference_train_pool.jsonl` (Kho Tham chiếu Khuyến nghị Hội nghị)
* **Nguồn**: **Chỉ gồm đúng 602 bài Train** từ `temporal_2015_2016_2019_clean/train.jsonl` kèm `conference_id` thật và 5 facets thật.
* **Quy tắc chống leakage**: Tuyệt đối không đưa 168 bài Test vào kho này.
* **Bài báo đại diện (`representative_papers`)**: Lấy trực tiếp từ **những bài trong Top-$k$ láng giềng thuộc kho 602 bài Train này đã bỏ phiếu cho hội nghị được gợi ý** (thay vì lấy cứng vài bài đầu tiên trong corpus như hiện tại).

### Kho 3: `demo_examples.json` (Bộ Bài mẫu Dùng chung cho `InputPage` & `ComparePage`)
* **Nguồn**: Nạp **trọn vẹn 168 bài Test hội nghị** (`temporal_2015_2016_2019_clean/test.jsonl`) làm bộ bài mẫu chính.
  * Vì cả `InputPage` và `ComparePage` đều đã có **ô tìm kiếm/lọc bài mẫu**, người dùng và hội đồng có thể lọc nhanh theo tên hội nghị, từ khóa (NLP, CV, neural, graph...) trong toàn bộ 168 bài.
  * Dùng hợp lệ cho **cả Khuyến nghị Bài báo lẫn Khuyến nghị Hội nghị** mà **không bị data leakage**.
  * Lưu kèm trường `ground_truth_venue` (hội nghị thực tế của bài báo) để giao diện có nút **"Hiện / Ẩn hội nghị thực tế"** phục vụ kiểm chứng trực tiếp khi thuyết trình.
  * Gắn sẵn đường dẫn/bản đồ tới **đủ 5 đầu ra LLM thật** (`Qwen3-4B`, `Qwen3-8B`, `Qwen3-14B`, `Llama3.1-8B`, `Gemma2-9B`).
* **Xử lý Evidence cho 4 model chưa lưu span (`Qwen3-8B`, `Qwen3-14B`, `Llama3.1-8B`, `Gemma2-9B`)**:
  * Riêng `Qwen3-4B` lấy trực tiếp `evidence` gốc từ `exp_a/generated/annotation_metadata.jsonl`.
  * Với `Qwen3-8B`, `Qwen3-14B`, `Llama3.1-8B`, `Gemma2-9B`, khi nạp concept sẽ tự tìm câu chứa cụm từ khớp trong `title` / `abstract` để highlight minh họa (nếu không khớp nguyên văn thì hiển thị concept với cờ `verified=false`, không bịa trích dẫn).

---

## 3. Thiết kế Hệ thống Phương pháp Ranking & Tính điểm (2 Chiều Độc Lập)

Đồng bộ 100% với các phương pháp thực nghiệm của nhóm (`scripts/exp_b/` và `scripts/conference_recommendation/reranker.py`), tách rõ **2 chiều cấu hình**:

### 3.1. Chiều 1 — Bộ Mã hóa / Embedding (`embedding_model`)
1. **`tfidf`** *(Mặc định — CPU siêu nhẹ)*: TF-IDF có IDF chuẩn hóa L2 (đúng công thức Exp B, không dùng đếm tần suất thô không IDF như `service.py` cũ).
2. **`bge-small`**: Dense vector 384 chiều (`BAAI/bge-small-en-v1.5`, đã có sẵn tại `_local/models/bge-small-en-v1.5`).
3. **`specter2`** *(Tùy chọn mở rộng)*: Nạp từ vector precomputed nếu đã sinh sẵn.

> **Pre-compute 6 trường vector cho mỗi bài báo**: `whole_text`, `problem`, `task`, `method`, `dataset`, `contribution`. Nhờ vậy việc tính điểm theo từng facet thật và đổi phương pháp ranking đạt tốc độ **< 50ms**.

### 3.2. Chiều 2 — Phương pháp Ranking / Tính điểm (`paper_ranking_method` & `conference_ranking_method`)

#### A. Khuyến nghị Bài báo (`paper_ranking_method`)
| Mã phương pháp | Tên hiển thị trên UI | Công thức tính điểm | Cần trích 5 Facet? |
| :--- | :--- | :--- | :---: |
| **`whole_text`** | Toàn văn (Whole-Text) | $\cos(q_{\text{full}}, d_{\text{full}})$ trên `Title + Abstract` | **Không** |
| **`equal_facets`** | 5-Facet Trọng số đều (Equal) | $\frac{1}{5}\sum_{f} \cos(q_f, d_f)$ | Có |
| **`weighted_facets`** *(Mặc định)* | **5-Facet Có trọng số (Weighted)** | $0.4\,s_{\text{prob}} + 0.2\,s_{\text{task}} + 0.2\,s_{\text{method}} + 0.1\,s_{\text{data}} + 0.1\,s_{\text{contrib}}$ *(chuẩn `configs/exp_b.json`)* | Có |

#### B. Khuyến nghị Hội nghị (`conference_ranking_method`)
| Mã phương pháp | Tên hiển thị trên UI | Công thức tính điểm (trên 602 bài Train) | Cần trích 5 Facet? |
| :--- | :--- | :--- | :---: |
| **`whole_text_knn`** | Toàn văn k-NN (Whole-Text k-NN) | Tìm Top-$k$ ($k=10$) bài Train gần nhất theo `Title + Abstract` rồi bỏ phiếu hội nghị | **Không** |
| **`flat_facet_knn`** | 5-Facet Phẳng k-NN (Flat k-NN) | Cộng phẳng 5 facets (không cổng ngữ cảnh) → Top-$k$ bài Train bỏ phiếu | Có |
| **`gated_knn`** *(Mặc định — Đề xuất chính)* | **Gated 5-Facet k-NN (Cổng Problem)** | $\text{Sim}(q,p) = \mathcal{G}_{\text{prob}}(q,p) \times \text{WeightedFacets}_{4}(q,p)$ với $\mathcal{G}_{\text{prob}} = \sigma(10 \cdot (\cos_{\text{prob}} - 0.45))$, trọng số `(task 0.3, method 0.3, dataset 0.2, contribution 0.2)` → Top-$k$ ($k=10$) bài Train bỏ phiếu có trọng số | Có |
| **`centroid`** *(Tùy chọn phụ)* | Tâm hồ sơ hội nghị (Centroid) | Cosine giữa query và vector tâm của 30 hội nghị | Không / Có |

### 3.3. Cơ chế Bỏ qua Extractor & Re-rank Tức thì trên Giao diện
1. **Khi chọn thuần `Whole-Text`** (`paper_ranking_method == "whole_text"` và `conference_ranking_method == "whole_text_knn"`):
   * UI tự động làm mờ ô chọn LLM Extractor kèm ghi chú *"Chế độ Toàn văn — Không cần trích xuất 5 Facet"*.
   * Backend bỏ qua hoàn toàn bước LLM Extraction, encode trực tiếp `Title + Abstract` và trả kết quả ngay lập tức.
2. **Khi chọn các phương pháp Facet-based**:
   * Dùng **chính 5 facet đã trích xuất** (từ precomputed LLM thật hoặc chạy live) để tính điểm xếp hạng thật; bảng giải thích `PaperExplanation` & `ConferenceExplanation` hiển thị **đúng điểm từng facet tham gia tính tổng** (không ước lượng ngược từ điểm full-text nữa).
3. **Chuyển đổi nhanh trên trang kết quả (`AnalysisResultPage.tsx`)**:
   * Khi đã có 5 facet của bài báo, cho phép người dùng bấm chuyển trực tiếp giữa `Whole-Text` ↔ `Equal` ↔ `Weighted` (Bài báo) và `Whole-Text k-NN` ↔ `Flat k-NN` ↔ `Gated 5-Facet k-NN` (Hội nghị) để **re-rank tức thì** mà không cần chạy lại LLM Extractor!

---

## 4. Lộ trình Triển khai (4 Bước)

1. **Bước 1 — Script xây dựng Artifacts Demo (`demo/backend/scripts/build_demo_artifacts.py`)**:
   * Đọc `papers.jsonl` (4,210 bài), `exp_a/generated/facets_silver.jsonl` + `annotation_metadata.jsonl`, `temporal_2015_2016_2019_clean/{train,test}.jsonl` (chứa sẵn 5 facets của `Qwen3-8B`), và 4 file `generated_facets/{Qwen4B,Qwen14B,Llama8B,Gemma9B}/facets_silver.jsonl`.
   * Xuất ra `_local/demo_artifacts/`: `paper_corpus.jsonl`, `conference_train_pool.jsonl`, `demo_examples.json` (168 bài Test kèm `ground_truth_venue` + precomputed facets thật của **đủ cả 5 model**), và precomputed embeddings 6 trường (`whole_text` + 5 facets) cho `TF-IDF` và `BGE-small`.
2. **Bước 2 — Cập nhật Backend (`schemas.py`, `service.py`, `main.py`)**:
   * Nạp dữ liệu từ `_local/demo_artifacts/`.
   * Bỏ fallback heuristic ở chế độ `precomputed`; nạp đúng kết quả thật của cả 5 model.
   * Cài đặt đầy đủ các phương pháp ranking (`whole_text`, `equal_facets`, `weighted_facets` cho Bài báo; `whole_text_knn`, `flat_facet_knn`, `gated_knn`, `centroid` cho Hội nghị) + cập nhật `get_representative_papers` lấy đúng láng giềng Top-$k$ bỏ phiếu trong 602 bài Train.
   * Thêm endpoint/tham số re-rank nhanh cho một `analysis_id` đã có facet.
3. **Bước 3 — Cập nhật Frontend (`InputPage.tsx`, `AnalysisResultPage.tsx`, `ComparePage.tsx`)**:
   * Bổ sung bộ chọn **Phương pháp Ranking (Bài báo / Hội nghị)** ở `InputPage.tsx` (tự khóa chọn Extractor khi chọn thuần `Whole-Text`).
   * Ở `AnalysisResultPage.tsx`: thêm thanh chuyển nhanh phương pháp ranking (re-rank live) + nút *"Hiện/Ẩn hội nghị thực tế (Ground Truth)"* cho 168 bài mẫu Test.
   * Ở `ComparePage.tsx`: so sánh trực tiếp **đủ cả 5 LLM thật** trên 168 bài Test.
4. **Bước 4 — Kiểm thử & Xác minh**:
   * Kiểm tra build TypeScript/Vite, kiểm tra API trả về kết quả khác nhau thật sự giữa cả 5 LLM trên `ComparePage`, và xác minh thứ hạng thay đổi rõ rệt giữa `Whole-Text` vs. `Weighted 5-Facet` vs. `Gated 5-Facet k-NN`.
