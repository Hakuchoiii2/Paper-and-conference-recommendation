# Bản Thảo Mục 3: Bài Toán và Dữ Liệu Thực Nghiệm (Task Formulation & Benchmark Data)

**Đề tài:** From Facet Extraction to Scientific Recommendation: Evaluating LLM Extractors for Paper Retrieval and Conference Ranking  
**Tác giả phụ trách:** Người 1 (Data & Benchmark)  

---

## 3. TASK FORMULATION AND DATASET

### 3.1. Định nghĩa Biểu diễn Năm Khía Cạnh (Five-Facet Representation)
Trong nghiên cứu này, mỗi bài báo khoa học $d$ trong tập ngữ cảnh (corpus) $\mathcal{D}$ được biểu diễn không chỉ bằng văn bản thô (Title và Abstract) mà còn qua một bộ cấu trúc 5 khía cạnh đa chiều $\mathcal{F}(d) = \{F_{\text{prob}}, F_{\text{task}}, F_{\text{meth}}, F_{\text{data}}, F_{\text{cont}}\}$, trong đó:
1. **Problem ($F_{\text{prob}}$):** Vấn đề hoặc thách thức nghiên cứu tổng thể mà bài báo hướng tới giải quyết.
2. **Task ($F_{\text{task}}$):** Nhiệm vụ cụ thể hoặc bài toán hình thức hóa được thực hiện trong nghiên cứu.
3. **Method ($F_{\text{meth}}$):** Phương pháp, mô hình, kiến trúc hoặc thuật toán được đề xuất để giải quyết nhiệm vụ.
4. **Dataset ($F_{\text{data}}$):** Dữ liệu thực nghiệm, benchmark hoặc tập ngữ liệu được sử dụng để kiểm chứng.
5. **Contribution ($F_{\text{cont}}$):** Đóng góp khoa học, phát hiện mới hoặc cải tiến đột phá mà công trình mang lại.

Mỗi khía cạnh $f \in \mathcal{F}(d)$ là một tập hợp các khái niệm (concepts) cô đọng kèm câu dẫn chứng (evidence) được trích xuất từ tiêu đề và tóm tắt của bài báo. Nếu một bài báo không đề cập rõ ràng đến một khía cạnh nhất định, khía cạnh đó được gán giá trị rỗng $\emptyset$ (không tự ý bịa đặt hoặc suy diễn thông tin).

---

### 3.2. Phát biểu Bài toán Khuyến nghị Bài báo (Paper Retrieval Formulation)
Cho một bài báo mốc $q \in \mathcal{D}$ (đại diện cho bài báo người dùng đang đọc hoặc bản thảo manuscript đang viết) và một tập hợp các bài báo ứng viên $\mathcal{C}_q = \{d_1, d_2, \dots, d_K\} \subset \mathcal{D} \setminus \{q\}$. 

Mục tiêu của hệ thống là tính toán hàm điểm phù hợp $S(q, d)$ với mỗi $d \in \mathcal{C}_q$ và xuất ra một danh sách xếp hạng giảm dần:
$$\pi_q = \left[ d_{(1)}, d_{(2)}, \dots, d_{(K)} \right] \quad \text{sao cho} \quad S(q, d_{(1)}) \ge S(q, d_{(2)}) \ge \dots \ge S(q, d_{(K)})$$
Bảng xếp hạng $\pi_q$ được đối chiếu với tập nhãn liên quan độc lập $\mathcal{Y}_q = \{y_{q, d}\}_{d \in \mathcal{C}_q}$ thông qua các chỉ số đánh giá chuẩn trong hệ thống tìm kiếm thông tin: **nDCG@k**, **Precision@k**, **Recall@k**, và **MRR@k** (với $k \in \{5, 10\}$).

---

### 3.3. Quy trình Xây dựng Bộ Dữ liệu Kiểm Thử Chọn Lọc (Curated Benchmark Construction)
Để khắc phục hiện tượng thiếu hụt dữ liệu (shortfall) của cấu hình thô ban đầu và loại bỏ hiện tượng "chạm trần điểm số giả tạo" ($1.0$), chúng tôi thiết kế một giao thức lấy mẫu có kiểm soát (Curated Sampling Protocol) dựa trên tập ngữ liệu chuẩn gồm $4.210$ bài báo khoa học:

1. **Lọc bài mốc hợp lệ (Anchor Eligibility):** Lọc ra các bài báo có ít nhất 2 khía cạnh chứa thông tin hợp lệ ($|\{f \in \mathcal{F} \mid F_f \ne \emptyset\}| \ge 2$), thu được $3.086$ bài mốc tiềm năng.
2. **Cài cắm Bài bẫy (Hard Negatives Injection):** Với mỗi bài mốc $q$, toàn bộ các bài báo còn lại được phân vào 3 rổ dựa trên ngưỡng liên quan thực chất $\tau = 0.3$:
   * **Rổ Positive ($\mathcal{P}_q$):** Các bài có điểm liên quan $y_{q, d} \ge 0.3$.
   * **Rổ Negative ($\mathcal{N}_q$):** Các bài có điểm liên quan $y_{q, d} < 0.3$.
   * **Rổ Hard Negative ($\mathcal{H}_q \subset \mathcal{N}_q$):** Các bài có điểm $0 < y_{q, d} < 0.3$ (trùng 1 khía cạnh thứ yếu nhưng khác biệt về vấn đề hoặc phương pháp cốt lõi).
3. **Phân bổ hạn ngạch ứng viên ($K = 50$):**
   * Lấy $10\%$ bài Positive ($n_p = 5$ bài).
   * Trong số $45$ bài Negative còn lại, ưu tiên lấy tới $70\%$ từ rổ Hard Negative ($n_h = 31$ bài bẫy) và $14$ bài Easy Negative ($y = 0.0$).
   * Xáo trộn ngẫu nhiên danh sách ứng viên bằng hạt giống ngẫu nhiên cố định (`seed = 42`) để đảm bảo tính tái lập.

---

### 3.4. Thống kê Bộ Dữ liệu và Phân chia Phân hoạch (Data Splits)
Bộ dữ liệu chuẩn $F_{\text{ref}}$ bao gồm **50 bài truy vấn** (Queries) và **2.500 cặp đánh giá**, được phân chia theo tỷ lệ $70\% / 15\% / 15\%$ ở cấp độ bài mốc (Grouped Splitting) nhằm đảm bảo tuyệt đối không có sự rò rỉ thông tin (zero anchor leakage) giữa các tập:

| Phân hoạch (Split) | Số lượng Query ($|Q|$) | Số lượng Cặp đánh giá ($|Q| \times 50$) | Số lượng Cặp Positive ($y > 0$) | Vai trò trong Nghiên cứu |
|:---|:---:|:---:|:---:|:---|
| **Train** | 35 | 1.750 | 114 | Huấn luyện và tìm kiếm không gian trọng số tối ưu $w_B^*$. |
| **Dev (Validation)** | 7 | 350 | 22 | Tinh chỉnh siêu tham số và xác thực mô hình đóng băng. |
| **Test** | 8 | 400 | 26 | Đánh giá độc lập một lần duy nhất để báo cáo kết quả chính thức (RQ2). |
| **Tổng cộng** | **50** | **2.500** | **162** | Đạt trạng thái hoàn chỉnh (`COMPLETE`, shortfall = 0). |

---

### 3.5. Quy tắc Tính Nhãn Liên quan Tham chiếu (Ground Truth Relevance)
Nhãn liên quan $y_{q, d} \in [0, 2]$ giữa bài mốc $q$ và ứng viên $d$ được tính toán thông qua độ trùng khớp đa khía cạnh:
$$y_{q, d} = \sum_{f \in \mathcal{F}} w_f^{\text{ref}} \cdot \text{Grade}_f(q, d)$$
Trong đó bộ trọng số tham chiếu ban đầu được phân bổ theo mức độ ưu tiên nghiệp vụ: $w_{\text{prob}} = 0.4$, $w_{\text{task}} = 0.2$, $w_{\text{meth}} = 0.2$, $w_{\text{data}} = 0.1$, $w_{\text{cont}} = 0.1$. Điểm thành phần $\text{Grade}_f(q, d) \in \{0, 1, 2\}$ phản ánh mức độ trùng khớp khái niệm: bằng $2$ nếu hai tập khái niệm đồng nhất, bằng $1$ nếu có giao nhau, và bằng $0$ nếu rời nhau.
