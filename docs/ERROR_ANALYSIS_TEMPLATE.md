# Khung Phân Tích Lỗi Định Tính (Error Taxonomy) Cho Downstream Recommendation

**Tác vụ:** Exp B — Paper Retrieval & Downstream Facet Ranking  
**Cơ sở lý thuyết:** Mục 8.2 Cấu trúc Paper (23/10/2026)  
**Tác giả phụ trách:** Người 1 (Data & Qualitative Analysis)  

---

## 1. MỤC TIÊU CỦA PHÂN TÍCH LỖI
Phân tích lỗi (Error Analysis) là khâu bắt buộc trong một bài báo khoa học chất lượng cao nhằm:
1. Giải thích nguyên nhân tại sao một số câu truy vấn (queries) có điểm xếp hạng thấp.
2. Xác định xem lỗi phát sinh từ **khâu trích xuất (LLM Extraction)** hay từ **khâu xếp hạng (Downstream Scorer)**.
3. Cung cấp bằng chứng định tính chứng minh ưu thế của biểu diễn đa khía cạnh (5 Facets) so với đọc gộp toàn văn (Whole Abstract).

---

## 2. PHÂN LOẠI 6 DẠNG LỖI CỐT LÕI (ERROR TAXONOMY)

Theo quy định tại Mục 8.2, các trường hợp xếp hạng sai được phân loại vào 6 nhóm lỗi chuẩn sau:

| Mã | Tên loại lỗi | Mô tả chi tiết | Ví dụ cụ thể | Tác động downstream |
|:---:|:---|:---|:---|:---|
| **E1** | **Sai vai trò (Role Mismatch)** | Phương pháp hoặc dữ liệu của công trình baseline bị LLM nhầm thành phương pháp chính của bài báo. | Abstract viết: *"Khác với SVM, chúng tôi đề xuất mạng GNN..."* nhưng LLM lại trích xuất `method = ["SVM"]`. | Hệ thống gợi ý nhầm các bài dùng SVM thay vì các bài dùng GNN. |
| **E2** | **Lẫn Facet (Facet Confusion)** | Khái niệm bị đặt nhầm giữa các khía cạnh có tính tương đồng cao (Problem lẫn với Task, hoặc Method lẫn với Contribution). | Đặt *"Text Classification"* vào `problem` thay vì `task`. | Trọng số $w_f$ bị nhân lệch (ví dụ Problem có trọng số 0.4 bị tính nhầm theo Task 0.2). |
| **E3** | **Không có nguồn (Hallucination / Unsupported)** | LLM tự ý suy diễn hoặc bổ sung tên Dataset, thông tin đóng góp mà trong Title/Abstract không hề xuất hiện. | Abstract không nói tên tập dữ liệu nhưng LLM tự điền `dataset = ["ImageNet"]`. | Tạo ra các điểm giao ảo (false positives), khiến bài không liên quan bị kéo lên đầu. |
| **E4** | **Bỏ sót khía cạnh (Missing Important Facets)** | Trong văn bản có nêu rõ phương pháp hoặc đóng góp nhưng LLM bỏ qua và để trống `[]`. | Abstract nêu rõ tên thuật toán nhưng LLM không trích xuất được `method`. | Mất thông tin so sánh, hệ thống phải kích hoạt cơ chế fallback. |
| **E5** | **Biến thể từ vựng & Chuẩn hóa (Lexical Variation & Synonym Failure)** | Cùng một khái niệm kỹ thuật nhưng hai bài dùng cách viết khác nhau (viết tắt, từ đồng nghĩa). | Bài 1 viết `GNN`, Bài 2 viết `Graph Neural Network`. | **TF-IDF bị điểm 0**; chỉ có **Semantic Embedding** mới khắc phục được. |
| **E6** | **Dư thừa & Lặp lại (Redundancy Across Facets)** | Một khái niệm bị lặp lại ở nhiều khía cạnh khác nhau trong cùng một bài báo. | Cụm từ *"Attention Mechanism"* xuất hiện ở cả `method`, `task` và `contribution`. | Khái niệm này bị tính điểm nhiều lần (over-weighting), làm sai lệch cán cân xếp hạng. |

---

## 3. MẪU BẢNG BÓC TÁCH LỖI (CASE AUDIT SHEET)

Khi rà soát các câu query trong `results/exp_b/milestone_1/details.jsonl`, điền thông tin vào mẫu sau:

### Ca kiểm tra số: [Mã Query - ví dụ: Q0018]
* **Bài mốc (Query Paper ID):** `P...`
* **Tiêu đề bài mốc:** [Title]
* **Điểm số các mô hình:**
  * `text_tfidf`: [Điểm ndcg@10]
  * `text_embedding`: [Điểm ndcg@10]
  * `weighted_facet_embedding`: [Điểm ndcg@10]
* **Bài ứng viên bị xếp sai hạng (False Positive / False Negative):**
  * Mã bài: `P...` | Thứ hạng thực tế: `#...` | Nhãn Ground Truth: `0.0 / 0.4`
* **Loại lỗi xác định (E1 - E6):** `E...`
* **Phân tích cơ chế gây lỗi:**
  * [Giải thích tại sao mô hình toàn văn bị nhầm và mô hình Facet đã xử lý như thế nào]
