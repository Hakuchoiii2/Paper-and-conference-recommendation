# Kế hoạch & Ý tưởng Cải tiến: DS300 FacetRec Demo

Tài liệu này ghi lại các đề xuất cải tiến và lộ trình nâng cấp hệ thống Demo để bám sát và hiện thực hóa đầy đủ phương pháp nghiên cứu của nhóm (Weighted-Facet-Ranking cho bài báo và Khuyến nghị hội nghị có cơ chế bỏ phiếu).

---

## 1. Ý tưởng cốt lõi: Nút chuyển đổi Mô hình Embedding & Chế độ Chấm điểm (Scorer)

### 1.1. Hiện trạng giao diện và hệ thống hiện tại
* Hiện tại ở trang `InputPage`, người dùng chỉ có một dropdown **"CHỌN EXTRACTOR"** (gồm: Qwen3-4B, Qwen3-8B, Qwen3-14B, Llama3.1-8B, Gemma2-9B) cùng chế độ thực thi (Chạy trực tiếp / Mẫu có sẵn).
* Bộ mã hóa và chấm điểm tương đồng ở backend hiện đang chạy mặc định bằng **TF-IDF Cosine Similarity** (heuristic baseline nhẹ để phục vụ demo nhanh).

### 1.2. Đề xuất cải tiến trên giao diện (UI Control)
Ngay cạnh hoặc phía dưới mục **CHỌN EXTRACTOR**, bổ sung thêm hai bộ điều khiển mới:
1. **Dropdown "CHỌN MÔ HÌNH EMBEDDING / ENCODER":**
   * `TF-IDF (Mặc định - Siêu nhẹ)`: Chạy tức thì, không cần tải mô hình nặng.
   * `SPECTER v2 (allenai/specter2)`: Mô hình embedding chuyên sâu cho tài liệu khoa học và trích đoạn nghiên cứu.
   * `BGE (BAAI/bge-large-en-v1.5)`: Mô hình dense embedding hiệu năng cao cho tìm kiếm ngữ nghĩa.
   * `SciBERT`: Mã hóa ngữ cảnh văn bản khoa học.
2. **Selector "PHƯƠNG THỨC XẾP HẠNG / CHẤM ĐIỂM (SCORING STRATEGY)":**
   * **Đối với Gợi ý Bài báo (Paper Recommendation):**
     * `Whole-text`: So sánh trực tiếp toàn văn Title + Abstract (không chia facet).
     * `Equal-facet`: Mã hóa từng facet riêng, tính cosine từng cặp và lấy trung bình bằng nhau ($w_i = 0.2$).
     * `Weighted-facet (Khuyên dùng)`: Tổng hợp có trọng số riêng cho từng facet ($w_{problem}=0.25, w_{task}=0.20, w_{method}=0.25, w_{dataset}=0.15, w_{contribution}=0.15$). Cho phép tùy chỉnh thanh trượt trọng số (Facet Sliders) trực tiếp trên UI.
   * **Đối với Gợi ý Hội nghị (Conference Recommendation):**
     * `Whole-text`: So sánh toàn văn với hồ sơ hội nghị / bài lịch sử.
     * `5-Facet Flat`: So sánh 5 facet độc lập không qua cổng điều kiện.
     * `5-Facet Gated`: Nhân điểm tổng hợp với cổng tương đồng của facet **Problem** (chỉ khuyến nghị nếu bài báo cùng giải quyết miền bài toán/vấn đề phù hợp).

---

## 2. Đồng bộ hóa với Phương pháp Cốt lõi của Nhóm

### 2.1. Khuyến nghị Bài báo (Weighted-Facet-Ranking)
Bám sát mô hình:
```
[Bản thảo q + Tập bài ứng viên] 
  -> [Trích xuất 5 Facet] 
  -> [Biểu diễn Vector theo từng Facet qua Encoder đã chọn] 
  -> [Tính độ tương đồng từng cặp Facet] 
  -> [Tổng hợp điểm có trọng số] 
  -> [Xếp hạng Top-K bài báo]
```
* **Cần cải tiến ở Backend:**
  * Hiện tại backend đang tính TF-IDF trên chuỗi gộp `title + abstract`.
  * Cần nâng cấp hàm `_compute_rankings`: tính cosine riêng cho từng facet (`sim_problem`, `sim_task`, `sim_method`, `sim_dataset`, `sim_contribution`), sau đó nhân với `FIXED_WEIGHTS` để tạo điểm `total_score` chuẩn xác.

### 2.2. Khuyến nghị Hội nghị (KNN Voting từ Tập Train)
Bám sát mô hình:
```
[Bản thảo q + Tập Train có nhãn Hội nghị]
  -> [Trích xuất và mã hóa 5 Facet]
  -> [So sánh 5 Facet giữa q và từng bài trong tập Train]
  -> [Lọc Top-k bài tương đồng nhất trên toàn tập Train]
  -> [Mỗi bài trong Top-k bỏ 1 phiếu cho hội nghị của bài đó]
  -> [Gợi ý Top-N hội nghị theo số phiếu giảm dần (KNN Voting)]
```
* **Cần cải tiến ở Backend:**
  * Hiện tại backend đang so sánh tương đồng trực tiếp với từ khóa hồ sơ hội nghị (`conf_keywords`).
  * Cần tích hợp cơ chế bỏ phiếu: lấy nhãn hội nghị của các bài báo tương đồng nhất trong tập train để xếp hạng hội nghị và trả về các bài báo đại diện chính là các bài đã bỏ phiếu cho hội nghị đó.

---

## 3. Lộ trình Triển khai Kỹ thuật (Technical Roadmap)

### Giai đoạn 1: Chuẩn hóa tính điểm Facet-level TF-IDF (Không phụ thuộc GPU)
1. Tách hàm tính điểm bài báo thành tổng có trọng số 5 facet:
   $$Score(q, d) = \sum_{f \in \mathcal{F}} w_f \cdot \text{CosineSim}(q_f, d_f)$$
2. Cập nhật cơ chế gợi ý hội nghị bằng KNN Voting dựa trên nhãn venue của Top-K bài báo trong `papers.jsonl`.

### Giai đoạn 2: Tích hợp Dense Embeddings (SPECTER / BGE)
1. Tạo module `dense_encoder.py` hỗ trợ nạp mô hình SentenceTransformer/HuggingFace (chạy CPU hoặc CUDA khi có tài nguyên).
2. Lưu trước (pre-compute) vector embedding 5 facet cho corpus để việc truy vấn và xếp hạng đạt tốc độ dưới 100ms.
3. Thêm tham số `embedding_model` vào request API `CreateAnalysisRequest`.

### Giai đoạn 3: Bổ sung Điều khiển trên Giao diện Frontend
1. Thêm bộ chọn Encoder và Scoring Mode vào trang `InputPage.tsx`.
2. Bổ sung bảng điều khiển trọng số (Weight Sliders) ở trang `AnalysisResultPage.tsx` cho phép người dùng kéo thả trọng số facet và xem kết quả xếp hạng cập nhật theo thời gian thực (Interactive Re-ranking).
