# Thực nghiệm B — Báo cáo Hoàn thành Mốc 1 và Kế hoạch Chi tiết Mốc 2

**Dự án:** DS300 — From Facet Extraction to Scientific Recommendation  
**Tác vụ:** Exp B — Paper Retrieval và Downstream Facet Ranking  
**Ngày cập nhật:** 29/10/2026  

---

## PHẦN 1: TỔNG HỢP KẾT QUẢ ĐÃ HOÀN THÀNH Ở MỐC 1 (CHUẨN BỊ)

### 1. Bối cảnh và Yêu cầu mới theo cấu trúc Paper (23/10/2026)
* Thực nghiệm B chịu trách nhiệm trực tiếp cho **Câu hỏi nghiên cứu RQ2** và **Đóng góp C2**: *Đánh giá có kiểm soát giá trị của biểu diễn theo facet và gán trọng số*.
* B đóng vai trò là **trục xếp hạng chuẩn (Downstream Ranker)**: Được đóng băng (freeze) để cả nhóm sử dụng làm thước đo chung khi đối chứng các mô hình LLM trích xuất khác nhau (RQ3, RQ4) và bài toán gợi ý hội nghị (Conference Recommendation).

### 2. Các công việc kỹ thuật đã hoàn thành trong Mốc 1
1. **Thiết lập tập dữ liệu Benchmark tham chiếu F_ref (`configs/exp_b_curated.json`):**
   * Quy mô: 50 bài mốc x 50 ứng viên = **2.500 cặp nhãn**, chia cố định 35 Train / 7 Dev / 8 Test.
   * Cài cắm **81 bài bẫy (Hard Negatives)** với `positive_grade = 0.3` và `hard_negative_fraction = 0.7`.
   * Gỡ bỏ hoàn toàn hiện tượng phân cực và thiếu dữ liệu (Shortfall = 0, trạng thái `COMPLETE`).

2. **Cập nhật Scorer chuẩn hóa theo đúng Mục 6.3 của Paper (`scripts/exp_b/run_my_method.py`):**
   * Công thức tính điểm tương đồng chuẩn hóa được trình bày chính xác như sau:

```text
              ∑   [ m_f(q, d) · w_f · s_f(q, d) ]
             f∈F
  S_w(q, d) = ─────────────────────────────────────────
                  ∑   [ m_f(q, d) · w_f ]
                 f∈F

  Điều kiện: w_f ≥ 0,  ∑ w_f = 1
```

   * **Ý nghĩa các thành phần trong công thức:**
     * `s_f(q, d)`: Điểm tương đồng Cosine giữa bài mốc `q` và bài ứng viên `d` trên khía cạnh `f`.
     * `m_f(q, d)`: Mặt nạ nhị phân (Mask): bằng 1 nếu cả hai bài đều có thông tin ở khía cạnh `f`, bằng 0 nếu một trong hai bài bị khuyết khía cạnh đó.
     * `w_f`: Trọng số của khía cạnh `f`.
     * **Mẫu số ∑ [ m_f(q, d) · w_f ]**: Chỉ chia cho tổng trọng số của những khía cạnh thực sự có mặt, giúp không phạt oan bài báo bị thiếu khía cạnh.
     * **Cơ chế Fallback (Mục 6.3):** Nếu mẫu số bằng 0 (cả 5 khía cạnh đều không so sánh được), hệ thống tự động gán `S_w(q, d) = s_whole(q, d)` (sử dụng điểm tương đồng toàn văn Title + Abstract).

---

### 3. Bảng kết quả thực nghiệm Mốc 1 (Đánh giá trên Test split - 8 cases)

| Nhóm phương pháp | Tên mô hình | nDCG@10 | nDCG@5 | Precision@5 | Recall@5 | MRR@10 |
|:---|:---|---:|---:|---:|---:|---:|
| **Baseline sàn** | `random` | 0.1470 | 0.1289 | 0.1000 | 0.1250 | 0.3281 |
| **Toàn văn** | `text_tfidf` (Đếm từ) | 0.4263 | 0.3884 | 0.2000 | 0.3688 | 0.5531 |
| | `text_embedding` (Transformer) | **0.4303** | **0.4073** | **0.2250** | **0.3866** | 0.4972 |
| **Theo 5 Facet** | `equal_facets` (Đếm từ) | 0.9820 | 0.9743 | 0.7500 | 0.8455 | 1.0000 |
| | `weighted_facets` (Đếm từ) | 0.9811 | 0.9743 | 0.7500 | 0.8455 | 1.0000 |
| | `equal_facet_embedding` | 0.8980 | 0.8965 | 0.6000 | 0.7193 | 1.0000 |
| | `weighted_facet_embedding` | **0.9205** | **0.8983** | **0.6000** | **0.7193** | **1.0000** |

> **Phát hiện quan trọng:**  
> Nhờ công thức chuẩn hóa Mục 6.3, `weighted_facet_embedding` đã tăng vọt từ 0.7965 lên **0.9205** (tăng mạnh +0.1240 điểm nDCG@10).  
> Thiết lập bậc thang khoa học rõ ràng: **Whole-text (0.43) → Equal-facet (0.89) → Weighted-facet (0.92)** để trả lời trọn vẹn câu hỏi RQ2 của đề tài.

---

## PHẦN 2: KẾ HOẠCH PHÂN CÔNG CHI TIẾT MỐC 2 (TỐI ƯU HÓA TRỌNG SỐ VÀ KHÓA RANKER)

Theo **Mục 6.4 của cấu trúc Paper mới**:
> *"Chọn và khóa trọng số: Cố định split và nDCG@10 làm metric chính. Chọn trọng số w_B trên train/dev B. Khóa w_B, encoder, normalizer, scorer và missing policy. Đánh giá test B một lần duy nhất."*

Dưới đây là bảng phân công chi tiết công việc cho Người 1 và Người 2 trong Mốc 2:

### [NGƯỜI 1]: Phụ trách Đánh giá Train/Dev, Phân tích Lỗi và Bản thảo Dữ liệu (PHI)

| STT | Nhiệm vụ cụ thể | Phương pháp / Công cụ | Đầu ra cần đạt (Deliverable) |
|:---:|:---|:---|:---|
| **1.1** | Thiết lập dữ liệu Train và Dev độc lập | Trích xuất từ `configs/exp_b_curated.json` (35 Train, 7 Dev). | File kiểm tra dữ liệu phân tách rõ ràng, không rò rỉ thông tin (leakage). |
| **1.2** | Chuẩn bị khung Phân tích Lỗi định tính (Error Taxonomy - Mục 8.2) | Xây dựng tiêu chí bóc tách 6 loại lỗi: *Sai vai trò, lẫn facet, không có nguồn, bỏ sót, chuẩn hóa, dư thừa*. | Bảng phân tích lỗi chi tiết `docs/ERROR_ANALYSIS_TEMPLATE.md`. |
| **1.3** | Thu thập 2 ca nghiên cứu điển hình (Case Studies) | Đọc `details.jsonl`, trích dẫn 2 cặp bài báo: (1) Ca mà Facet thắng áp đảo Toàn văn; (2) Ca có từ đồng nghĩa mà Embedding nhận diện tốt. | Đoạn trích dẫn Title/Abstract và giải thích định tính cho Paper. |


---

### [NGƯỜI 2]: Phụ trách Thuật toán Tối ưu Trọng số, Khóa Ranker và Bản thảo Mô hình (Quỳnh)

| STT | Nhiệm vụ cụ thể | Phương pháp / Công cụ | Đầu ra cần đạt (Deliverable) |
|:---:|:---|:---|:---|
| **2.1** | Viết script tối ưu hóa trọng số w_B | Tạo `scripts/exp_b/tune_weights.py` dùng Grid Search / Scipy Optimize trên tập Train/Dev để tối đa hóa nDCG@10. | Script tự động tìm bộ trọng số `[w_prob, w_task, w_method, w_data, w_contrib]` tối ưu. |
| **2.2** | Khóa (Freeze) cấu hình Downstream Ranker | Tạo file cấu hình chính thức `configs/exp_b_frozen.json` lưu bộ trọng số w_B* đã học và đường dẫn mô hình. | Cấu hình đóng băng cố định, không thay đổi trước khi chạy test. |
| **2.3** | Đóng gói Module Ranker để chuyển giao | Đóng gói hàm chuẩn `evaluate_downstream_ranker(facet_data)` cho phép nhóm Exp A thử nghiệm các LLM khác (RQ3). | Module Python độc lập sẵn sàng tích hợp với Exp A và Conference. |
---

