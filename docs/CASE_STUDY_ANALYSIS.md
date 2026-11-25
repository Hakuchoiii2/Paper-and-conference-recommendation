# Báo Cáo Phân Tích Trường Hợp Điển Hình (Case Studies)

**Tác vụ:** Exp B — Paper Retrieval & Downstream Facet Ranking  
**Cơ sở dữ liệu:** `results/exp_b/milestone_1/details.jsonl`  
**Tác giả phụ trách:** Người 1 (Data & Qualitative Analysis)  

---

## 1. TỔNG QUAN
Tài liệu này cung cấp **2 ca nghiên cứu định tính điển hình (Case Studies)** được trích xuất trực tiếp từ tập kiểm thử thực tế (Test Split) nhằm giải thích bản chất cơ chế xếp hạng cho bài báo khoa học:
* **Ca 1 (Query Q0021):** Minh chứng cho sự thất bại hoàn toàn của biểu diễn toàn văn (Whole Abstract) trước các "từ gây nhiễu", trong khi biểu diễn theo Facet (`weighted_facet_embedding`) đạt điểm gần như tuyệt đối.
* **Ca 2 (Query Q0048):** Minh chứng cho ưu thế của mô hình ngữ nghĩa (Semantic Embedding) trước các bài toán khai phá dữ liệu khi từ ngữ bề mặt (Lexical) hoàn toàn bị đánh lừa.

---

## 2. CA NGHIÊN CỨU 1: QUERY Q0021 — FACET THẮNG ÁP ĐẢO TOÀN VĂN

### Thông tin bài mốc (Anchor Paper):
* **Mã bài (Paper ID):** `P000382`
* **Tiêu đề:** *"Interactive Goal Programming"*
* **Tóm tắt (Abstract):**  
  > *"The use of goal programming for the solution of the multiple criteria problem is discussed. An extension of this use is presented in the form of an algorithm which requires interaction with the relevant decision maker..."*
* **Các khía cạnh trích xuất (Facets):**
  * `method`: `["algorithm"]`
  * `task`: `["extension of this use is presented in the form of an algorithm"]`
  * `contribution`: `["algorithm provides a bridge"]`

### Bảng so sánh điểm xếp hạng giữa các mô hình trên Q0021:

| Mô hình | nDCG@10 | nDCG@5 | Precision@5 | Recall@10 | MRR@10 |
|:---|---:|---:|---:|---:|---:|
| `random` | 0.2341 | 0.2482 | 0.4000 | 0.3333 | 0.5000 |
| `text_tfidf` (Toàn văn đếm từ) | **0.0994** | **0.0000** | **0.0000** | **0.1667** | **0.1000** |
| `text_embedding` (Toàn văn Transformer) | **0.0000** | **0.0000** | **0.0000** | **0.0000** | **0.0000** |
| **`weighted_facet_embedding` (5 Facet)** | **0.9849** | **0.9343** | **0.8000** | **1.0000** | **1.0000** |

### Phân tích chuyên sâu (Qualitative Insights):
1. **Tại sao Toàn văn thất bại thảm hại (nDCG@5 = 0.0)?**
   * Abstract của bài mốc sử dụng các từ ngữ quá phổ thông trong toán tối ưu và khoa học máy tính như: *"algorithm"*, *"solution"*, *"problem"*, *"decision maker"*.
   * Khi đưa toàn bộ đoạn văn qua `text_tfidf` hoặc `text_embedding`, vector toàn bài bị chi phối bởi các từ ngữ ngữ cảnh này, khiến hệ thống gợi ý hàng loạt các bài toán tối ưu lý thuyết chung chung (các bài Hard Negatives gây nhiễu). Trong Top-5 của mô hình toàn văn, **không có bất kỳ bài nào thực sự liên quan** (Precision@5 = 0.0).
2. **Tại sao Facet lại chiến thắng ngoạn mục (nDCG@10 = 0.9849, MRR = 1.0)?**
   * Khi bóc tách độc lập, mô hình không còn bị nhiễu bởi các câu văn dẫn dắt.
   * `weighted_facet_embedding` nhận diện chính xác sự tương đồng tập trung ở khía cạnh nhiệm vụ thuật toán (`task`) và phương pháp (`method`), đẩy ngay các bài có bản chất thuật toán tương tự (như `P000538`, `P001096`) lên ngay vị trí #1 và #2 của danh sách.

---

## 3. CA NGHIÊN CỨU 2: QUERY Q0048 — SEMANTIC EMBEDDING VƯỢT TRỘI TF-IDF TRƯỚC TỪ GÂY NHIỄU

### Thông tin bài mốc (Anchor Paper):
* **Mã bài (Paper ID):** `P000463`
* **Tiêu đề:** *"A probabilistic approach to hybrid role mining"*
* **Tóm tắt (Abstract):**  
  > *"Role mining algorithms address an important access control problem: configuring a role-based access control system. Given a direct assignment of users to permissions, role mining discovers a set of roles together with an assignment of users to roles..."*
* **Các khía cạnh trích xuất (Facets):**
  * `problem`: `["configuring a role-based access control system"]`
  * `method`: `["probabilistic model"]`
  * `task`: `["discover a set of roles together with an assignment of users to roles"]`
  * `contribution`: `["algorithm yields roles that both explain given user-permission assignments and are meaningful"]`

### Bảng so sánh điểm xếp hạng giữa các mô hình trên Q0048:

| Mô hình | nDCG@10 | nDCG@5 | Precision@5 | Recall@10 | MRR@10 |
|:---|---:|---:|---:|---:|---:|
| `text_tfidf` (Toàn văn đếm từ) | **0.0479** | **0.0000** | **0.0000** | 0.1429 | 0.1250 |
| `text_embedding` (Toàn văn Transformer) | **0.1094** | **0.0657** | **0.2000** | 0.2857 | 0.2000 |
| **`weighted_facet_embedding` (5 Facet)** | **0.9808** | **0.9343** | **0.8000** | **1.0000** | **1.0000** |

### Phân tích chuyên sâu (Qualitative Insights):
1. **Khoảng cách giữa TF-IDF và Transformer trên Toàn văn:**
   * `text_tfidf` chỉ đạt 0.0479 vì các bài viết về phân quyền (Access Control / Role Mining) sử dụng các thuật ngữ rất đa dạng (*permissions, authorization, user-role mapping*). Đếm từ vựng thô bị mất dấu gần như toàn bộ bài liên quan.
   * `text_embedding` đạt **0.1094 (cao hơn gấp đôi so với TF-IDF)** nhờ nhận diện được trường ngữ nghĩa phân quyền, tìm được bài liên quan trong Top-5 (Precision@5 = 0.2 so với 0.0 của TF-IDF).
2. **Sức mạnh kết hợp khi chia Facet:**
   * Khi kết hợp cả **Semantic Embedding + Biểu diễn 5 Facet**, điểm số nhảy vọt lên **0.9808**, tìm thấy toàn bộ 100% bài liên quan trong Top-10 (Recall@10 = 1.0, MRR = 1.0).

---

## 4. KẾT LUẬN CHO BẢN THẢO PAPER (MỤC 6 - DISCUSSION)
Hai ca nghiên cứu này cung cấp bằng chứng định tính vững chắc cho bài báo:
> *"Biểu diễn toàn văn (Whole-text) rất dễ bị sập bẫy bởi các từ ngữ ngữ cảnh phổ thông trong abstract. Việc bóc tách thành 5 khía cạnh độc lập và nhúng bằng mô hình ngôn ngữ (Semantic Facet Embedding) là chìa khóa then chốt để cô lập nhiễu, đảm bảo độ chính xác vượt trội ngay cả trong các miền chuyên ngành phức tạp."*
