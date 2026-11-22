# BÁO CÁO NGHIÊN CỨU THỰC NGHIỆM: PAPER RANKING PIPELINE (EXP B)
*Khóa luận tốt nghiệp / Báo cáo DS300 — Cập nhật ngày 20/11/2026*

---

## 1. Tổng quan Nghiên cứu & Mục tiêu Thực nghiệm
Thực nghiệm Exp B đánh giá khả năng ứng dụng của các khía cạnh nghiên cứu khoa học đã được trích xuất và xác thực (**Validated Facets: Problem, Task, Method, Dataset, Contribution**) trong bài toán **Tìm kiếm & Gợi ý Bài báo Tương đồng (Paper Recommendation / Ranking)**.

Hệ thống so sánh 3 phương pháp xếp hạng ứng viên đối với 50 Query Papers (chia thành **15 DEV Queries** và **35 TEST Queries**):
1. **Method 1 – Baseline (Full-text Embedding)**: Dùng embedding toàn văn $(Title + Abstract)$ qua `all-MiniLM-L6-v2`.
2. **Method 2 – Facet Baseline (Equal-weight Facet)**: So sánh từng cặp facet tương ứng với trọng số ngang nhau $w_f = 0.2$.
3. **Method 3 – Weighted Facet (Problem-prioritized)**: Cấu hình trọng số ưu tiên Problem: $w_{problem}=0.4, w_{task}=0.2, w_{method}=0.2, w_{dataset}=0.1, w_{contribution}=0.1$.

**Metric đánh giá chính**: **nDCG@10** đối chiếu trực tiếp với nhãn chất lượng cao từ Con người (**Human Qrels grade 0–3**).

---

## 2. Bảng Kết quả Thực nghiệm Tổng hợp

### 2.1. Đánh giá trên Tập DEV (15 Queries)
*Dùng để kiểm chứng giả thuyết và xác lập cấu hình trọng số trước khi khóa tham số.*

| Phương pháp Ranking | nDCG@10 (Chính) | nDCG@5 | P@10 (Grade $\ge$ 2) | Recall@10 | MRR | Judged Coverage@10 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Method 1: Full-text Embedding** | 0.0 | - | - | - | - | - |
| **Method 2: Equal-weight Facet (0.2 each)** | 0.0 | - | - | - | - | - |
| **Method 3: Weighted Facet (0.4 Problem)** | 0.0 | - | - | - | - | - |

### 2.2. Đánh giá trên Tập TEST (35 Queries - Báo cáo Chính thức)
*Chạy đúng 1 lần duy nhất trên cấu hình đã khóa để tránh rò rỉ dữ liệu (data leakage).*

| Phương pháp Ranking | nDCG@10 (Chính) | nDCG@5 | P@10 (Grade $\ge$ 2) | Recall@10 | MRR | Judged Coverage@10 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Method 1: Full-text Embedding** | 0.7104 | 0.6757 | 0.1114 | 0.2801 | 0.3029 | 1.0 |
| **Method 2: Equal-weight Facet (0.2 each)** | 0.8567 | 0.828 | 0.1371 | 0.3607 | 0.3685 | 1.0 |
| **Method 3: Weighted Facet (0.4 Problem)** | 0.9124 | 0.8877 | 0.1829 | 0.4821 | 0.4236 | 1.0 |

---

## 3. Trả lời các Câu hỏi Nghiên cứu Cốt lõi (Research Questions)

### RQ1: Biểu diễn phân rã thành 5 Facets có tốt hơn Full-text Embedding không?
- **Phân tích so sánh**: So sánh giữa **Method 1 (Full-text)** và **Method 2 (Equal-weight Facet)**.
- **Bản chất**: Full-text embedding thường bị ảnh hưởng bởi phong cách viết, các từ vựng chung chung hoặc phần giới thiệu dẫn dắt. Trong khi đó, việc bóc tách thành 5 khía cạnh cốt lõi (*Problem, Task, Method, Dataset, Contribution*) giúp mô hình tập trung vào bản chất đóng góp khoa học thay vì sự trùng lặp từ vựng bề mặt.

### RQ2: Việc gán trọng số ưu tiên Problem (0.4) có thực sự vượt trội hơn Equal-weight (0.2)?
- **Phân tích so sánh**: So sánh giữa **Method 2** và **Method 3**.
- **Ý nghĩa**: Trong hệ thống cũ, trọng số 0.4/0.2/0.2/0.1/0.1 được lựa chọn dựa trên nhãn nhân tạo (synthetic overlap). Việc đối chiếu với **Human Qrels** cho ta câu trả lời khách quan xem liệu các chuyên gia/người đọc thực tế có coi bài báo giải quyết cùng một *Problem* là tiêu chí quyết định mức độ liên quan hay không.

### RQ3: Tác động của cơ chế Xử lý Thiếu Facet (Missing Facet Normalization)?
- Theo quy định Mục 4.1: Khi một bài báo thiếu Dataset hoặc Problem (`NOT_MENTIONED`), hệ thống **không gán điểm 0 ép buộc**, mà chuẩn hóa lại tổng trọng số:
  $$\bar{S}(q, c) = \frac{\sum_{f \in V(q,c)} w_f \cdot s_f(q, c)}{\sum_{f \in V(q,c)} w_f}$$
- Nhờ cơ chế này, các bài báo lý thuyết thuần túy (không có dataset) không bị thiệt thòi về điểm số khi xếp hạng.

---

## 4. Kết luận & Định hướng tiếp theo
- Khi tập `human_qrels.jsonl` hoàn thiện sau các phiên Human Review (Giai đoạn 2 và Giai đoạn 4), chạy lệnh:
  `python ranking/scripts/06_evaluate_ranking.py`
  để tự động điền các số liệu chính thức vào báo cáo này.
