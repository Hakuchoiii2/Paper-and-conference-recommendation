# BÁO CÁO PHÂN TÍCH QUY TRÌNH POOLING & FINAL GROUND TRUTH (EXP B)
*Khóa luận tốt nghiệp / Báo cáo DS300 — Ngày cập nhật: 20/11/2026*

---

## 1. Mục tiêu và Nguyên lý Triển khai Pooling
Theo tiêu chuẩn đánh giá hệ thống truy xuất thông tin của **TREC (Text REtrieval Conference)**, quy trình Pooling được thực hiện nhằm mục đích:
1. **Tránh thiên lệch hệ thống đơn lẻ (Single-system Bias)**: Không chỉ đánh giá các bài báo do một phương pháp duy nhất tìm thấy, mà gộp các ứng viên từ nhiều phương pháp khác nhau:
   - Ground Truth Candidate Generation (Top 100 bằng MiniLM Full-text).
   - Method 1: Full-text Embedding Ranking (Top 20).
   - Method 2: Equal-weight Facet Ranking (Top 20).
   - Method 3: Weighted Facet Ranking (Top 20).
2. **Loại bỏ trùng lặp (Deduplication)**: Hợp nhất các bài ứng viên trùng lặp theo cặp duy nhất `(query_id, candidate_id)` và lưu vết danh sách nguồn phát hiện (`retrieved_by`).
3. **Thẩm định con người (Human Relevance Judgment)**: Đánh giá thực chất mức độ liên quan theo thang đo chuẩn 4 mức (Grade 0–3).

---

## 2. Thống kê Kích thước và Tỷ lệ Bao phủ của Pool

| Chỉ số Thống kê | Giá trị | Tỷ lệ (%) |
| :--- | :---: | :---: |
| **Tổng số cặp trong Pool** | **3931** | 100.0% |
| **Số cặp đã được Con người đánh giá (Grade 0–3)** | **3931** | **100.0%** |
| **Số cặp chưa đánh giá (UNJUDGED)** | **0** | 0.0% |
| **Số cặp đánh giá trên tập DEV (15 Queries)** | 0 | - |
| **Số cặp đánh giá trên tập TEST (35 Queries)** | 3931 | - |

---

## 3. Phân bổ Thang điểm Đánh giá (Relevance Grade Distribution)

| Thang điểm Human Grade | Ý nghĩa Thực tế | Số lượng cặp | Tỷ lệ (%) |
| :--- | :--- | :---: | :---: |
| **Grade 0** | Không liên quan | 1161 | 29.5% |
| **Grade 1** | Có liên quan nhẹ, giá trị sử dụng hạn chế | 2642 | 67.2% |
| **Grade 2** | Có liên quan đáng kể | 125 | 3.2% |
| **Grade 3** | Rất liên quan, có giá trị tham khảo trực tiếp | 3 | 0.1% |

---

## 4. Các Quy tắc Nghiên cứu Đã Tuân thủ (Scientific Compliance)
1. **Deduplicate theo từng cặp**: Khóa duy nhất là `(query_id, candidate_id)`.
2. **Không tự ý gán Grade 0**: Các cặp chưa được đánh giá giữ nguyên nhãn `UNJUDGED`, không mặc định gán là 0 khi chưa qua Human Review.
3. **Khóa Qrels cho tập TEST**: Bộ Qrels được khóa cứng tại `final_human_qrels.jsonl` trước khi chạy tính toán metric cuối cùng trên tập TEST để bảo đảm tính khách quan.
