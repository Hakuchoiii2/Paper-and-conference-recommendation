# BÁO CÁO PHÂN TÍCH TỔNG THỂ THỰC NGHIỆM EXP A, EXP B VÀ NHÁNH KHUYẾN NGHỊ HỘI NGHỊ CHUẨN IEEE

> **Dự án NCKH DS300:** *From Facet Extraction to Scientific Recommendation: Evaluating LLM Extractors for Paper Retrieval and Conference Ranking*  
> **Cấu hình chuẩn hóa:** Bộ mã hóa `google-bert/bert-base-uncased` ($768\text{d}$, `mean` pooling, chuẩn hóa $L_2$), bộ chia thời gian sạch $602$ bài Train ($\le 2015$) / $168$ bài Test ($2016\text{--}2019$) trên $30$ hội nghị, $5$ mô hình LLM trích xuất bản thô (`Raw`, tuyệt đối không sử dụng `validated_silver.jsonl`), và bộ trọng số khóa cứng chuyển giao từ Exp B: $\mathbf{w}_{\text{Exp B}}^* = (0.40, 0.20, 0.20, 0.10, 0.10)$.

---

## MỤC LỤC
1. [Bối cảnh, Bài toán và Mạch nhân quả xuyên suốt 3 phân hệ](#1-bối-cảnh-bài-toán-và-mạch-nhân-quả-xuyên-suốt-3-phân-hệ)
2. [Nền tảng Thực nghiệm: Kết quả và Tiền đề từ Exp A và Exp B](#2-nền-tảng-thực-nghiệm-kết-quả-và-tiền-đề-từ-exp-a-và-exp-b)
3. [Thiết kế Giao thức Nhánh Hội nghị: Lý do cho từng Quyết định Kỹ thuật](#3-thiết-kế-giao-thức-nhánh-hội-nghị-lý-do-cho-từng-quyết-định-kỹ-thuật)
4. [Phân tích Nhân quả Kết quả Thực nghiệm Nhánh Hội nghị (Bảng 1, 2, 3 & Độ nhạy $k$)](#4-phân-tích-nhân-quả-kết-quả-thực-nghiệm-nhánh-hội-nghị)
5. [Tổng hợp Đóng góp Khoa học & Các Điểm Giới hạn cần Minh bạch trước khi Nộp IEEE](#5-tổng-hợp-đóng-góp-khoa-học--các-điểm-giới-hạn-cần-minh-bạch-trước-khi-nộp-ieee)
6. [Giải đáp Chuyên sâu các Câu hỏi Phương pháp luận Trọng tâm (Q&A)](#6-giải-đáp-chuyên-sâu-các-câu-hỏi-phương-pháp-luận-trọng-tâm-qa)

---

## 1. Bối cảnh, Bài toán và Mạch nhân quả xuyên suốt 3 phân hệ

Khi hoàn thiện một bản thảo khoa học mới chỉ gồm **Tiêu đề (Title)** và **Tóm tắt (Abstract)** (bối cảnh *cold-start*, chưa có mạng trích dẫn), tác giả đối mặt đồng thời với hai quyết định: tìm các bài báo nền tảng để đối chiếu (**Exp B: Paper Retrieval**) và chọn hội nghị phù hợp để nộp bài (**Nhánh Hội nghị: Conference Recommendation**). Các hệ thống truyền thống thường nén toàn bộ `Title + Abstract` thành một vector duy nhất (`Full-text`), khiến thông tin về miền bài toán bị trộn lẫn với công cụ kỹ thuật và văn phong bề mặt.

Để kiểm định khoa học giá trị của biểu diễn có cấu trúc so với toàn văn, nghiên cứu được thiết kế thành một **thực nghiệm có kiểm soát (Controlled Empirical Study)** nối tiếp qua 3 phân hệ theo mạch nhân quả thống nhất:

1. **Exp A (Trích xuất 5 khía cạnh — Đánh giá nội tại, RQ1):** Huấn luyện tinh chỉnh (`QLoRA-V-recall`) $5$ mô hình ngôn ngữ lớn mã nguồn mở (`Gemma-9B`, `Qwen-8B`, `Llama-8B`, `Qwen-14B`, `Qwen-4B`) nhằm phân rã văn bản khoa học thành $5$ khía cạnh trực giao: `problem`, `task`, `method`, `dataset` và `contribution`.
2. **Exp B (Xếp hạng bài báo — Đánh giá vi mô, RQ2):** Đưa đầu ra $5$ khía cạnh vào $3$ hàm tính điểm tương đồng cặp $S(q, c)$ (`Full-text`, `Equal-weight`, `Weighted Facet`) để chọn và khóa bộ trọng số tối ưu $\mathbf{w}_{\text{Exp B}}^*$ ở cấp độ bài báo.
3. **Nhánh Khuyến nghị Hội nghị (Đánh giá vĩ mô & Độ nhạy bộ trích xuất, RQ2–RQ4):** Kế thừa trực tiếp hàm chấm điểm và trọng số khóa cứng $\mathbf{w}_{\text{Exp B}}^*$ từ Exp B, kết hợp tầng tổng hợp điểm lên $30$ hội nghị để kiểm chứng hai câu hỏi trọng tâm: *(a) biểu diễn $5$ khía cạnh và trọng số học từ bài toán bài báo có chuyển giao tốt sang bài toán hội nghị hay không*, và *(b) độ chính xác F1 ở Exp A có quyết định chất lượng khuyến nghị ở đầu ra thực tế hay không*.

---

## 2. Nền tảng Thực nghiệm: Kết quả và Tiền đề từ Exp A và Exp B

### 2.1. Exp A: Chất lượng trích xuất và sự bất đối xứng cấu trúc của 5 Raw LLMs

Trên tập `Gold Test` gồm $60$ bài báo (từ bộ chia $280$ Train / $60$ Valid / $60$ Test), việc tinh chỉnh QLoRA tạo ra bước nhảy chất lượng rõ rệt: mô hình `Qwen-8B` gốc chưa tinh chỉnh (`base-V-recall`) chỉ đạt $25.85\%$ Micro-F1 và $25.97\%$ Macro-F1, sau khi tinh chỉnh tăng lên $66.73\%$ Micro-F1 và $67.67\%$ Macro-F1.

| Mô hình (Raw LLM) | Precision (%) | Recall (%) | Micro-F1 (%) | Macro-F1 (%) | Problem / Task / Method / Dataset / Contrib F1 (%) | Phủ TB Test 168 (%) | Số bài có `Problem` (Test) | Độ dài TB (từ/bài Test) | Thời gian Exp A (s) |
|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|
| **Gemma-9B (Raw)** | **67.45** | 68.92 | **68.18** | **70.39** | **64.24** / **75.43** / 71.75 / 84.51 / **56.00** | 77.38% | 103 / 168 (61.3%) | 32.93 | 20,145.94 |
| **Qwen-8B (Raw)** | 63.17 | **70.72** | 66.73 | 67.67 | 61.54 / 68.00 / **74.01** / 78.95 / 55.85 | 73.81% | **77 / 168 (45.8%)** | **39.17** | 17,510.97 |
| **Llama-8B (Raw)** | 63.51 | 65.54 | 64.51 | 65.28 | 48.00 / 65.56 / 73.57 / 84.51 / 54.76 | **79.52%** | **120 / 168 (71.4%)** | 33.93 | 13,466.27 |
| **Qwen-14B (Raw)** | 61.21 | 66.33 | 63.67 | 65.62 | 56.29 / 63.77 / 73.14 / **85.71** / 49.21 | 78.33% | 112 / 168 (66.7%) | 32.21 | 20,830.10 |
| **Qwen-4B (Raw)** | 59.32 | 62.75 | 60.99 | 62.93 | 54.22 / 62.00 / 67.44 / 80.00 / 50.98 | 75.36% | 95 / 168 (56.5%) | 32.92 | **11,833.21** |

Hai đặc điểm cấu trúc từ Exp A đóng vai trò nguyên nhân trực tiếp giải thích các hiện tượng ở nhánh Hội nghị:
* **Sự phân hóa năng lực theo khía cạnh:** `Gemma-9B` dẫn đầu toàn diện ở chỉ số nội tại ($70.39\%$ Macro-F1), `Qwen-8B` mạnh nhất về độ phủ hồi tưởng ($\text{Recall} = 70.72\%$) và `Method-F1` ($74.01\%$), `Qwen-14B` dẫn đầu `Dataset-F1` ($85.71\%$), trong khi `Qwen-4B` có F1 thấp nhất ($62.93\%$ Macro-F1) nhưng chi phí huấn luyện–suy luận thấp nhất ($11,833\text{s}$).
* **Sự thiếu hụt nghiêm trọng của `Problem` và độ dài chuỗi ở `Qwen-8B (Raw)`:** Trên tập $602$ bài Train lịch sử, `Qwen-8B (Raw)` chỉ trích xuất được `problem` ở $236/602$ bài (vắng mặt $60.80\%$) và `dataset` ở $176/602$ bài, trong khi trung bình mỗi bài dài tới $39.88$ từ. Trên $168$ bài Test, `Qwen-8B (Raw)` tiếp tục có tỷ lệ phủ `problem` thấp nhất ($45.83\%$, tức $77/168$ bài) nhưng độ dài lại lớn nhất ($39.17$ từ/bài), trái ngược với $4$ mô hình còn lại đều phủ `problem` cao hơn rõ rệt ($56.55\%\text{--}71.43\%$) với cách diễn đạt cô đọng hơn ($32.21\text{--}33.93$ từ/bài).

### 2.2. Exp B: Khung chấm điểm cặp và cơ sở khóa trọng số $\mathbf{w}_{\text{Exp B}}^*$

Với tập khía cạnh chung mà cả bài truy vấn $q$ và bài ứng viên $c$ ($c \ne q$) cùng có mặt là $V(q, c) = \{f \mid m_f(q) = 1 \land m_f(c) = 1\}$, Exp B chuẩn hóa $3$ hàm chấm điểm cặp:

1. **Method 1 (`Full-text`):**
   $$S_{\text{full}}(q, c) = \langle \mathbf{e}_{\text{full}}(q), \mathbf{e}_{\text{full}}(c) \rangle$$
2. **Method 2 (`Equal-weight Facet`):**
   $$S_{\text{equal}}(q, c) = \frac{1}{|V(q, c)|} \sum_{f \in V(q, c)} s_f(q, c) \qquad \big(V(q, c) \ne \emptyset\big)$$
3. **Method 3 (`Weighted Facet` với tái chuẩn hóa mẫu số động):**
   $$S_{\text{weighted}}(q, c) = \frac{\sum_{f \in V(q, c)} w_f s_f(q, c)}{\sum_{f \in V(q, c)} w_f} \qquad \left(\sum_{f \in V(q, c)} w_f > 0\right)$$

| Tập đánh giá | Phương pháp Ranking | nDCG@10 (Chính) | P@5 ($\ge 2$) | P@10 ($\ge 2$) | Recall@10 | MRR |
|:---:|---|---:|---:|---:|---:|---:|
| **DEV** ($15$q) | Method 1: Full-text Embedding | 0.6385 | 0.0133 | 0.0333 | 0.0088 | 0.0750 |
| **DEV** ($15$q) | Method 2: Equal-weight ($0.2 \times 5$) | 0.9019 | 0.0800 | 0.0733 | 0.0602 | 0.1056 |
| **DEV** ($15$q) | **Method 3a: Weighted A ($0.4/0.2/0.2/0.1/0.1$)** | **0.9264** | **0.0933** | **0.0933** | **0.1064** | **0.1556** |
| **DEV** ($15$q) | Method 3b: Weighted B ($0.3/0.25/0.25/0.1/0.1$) | 0.9226 | 0.0800 | **0.0933** | **0.1064** | 0.1429 |
| **TEST** ($35$q) | Method 1: Full-text Embedding | 0.7104 | 0.1200 | 0.1114 | 0.2801 | 0.3029 |
| **TEST** ($35$q) | Method 2: Equal-weight ($0.2 \times 5$) | 0.8567 | 0.1714 | 0.1371 | 0.3607 | 0.3685 |
| **TEST** ($35$q) | **Method 3a: Weighted A (Locked $\mathbf{w}_{\text{Exp B}}^*$)** | **0.9124** | 0.2286 | **0.1829** | **0.4821** | **0.4236** |
| *(TEST)* | *Method 3b: Weighted B* | *0.8929* | ***0.2343*** | *0.1600* | *0.4231* | *0.4105* |

Ở cấp độ bài báo, cấu trúc $5$ khía cạnh vượt xa `Full-text`, và `Weighted A` đạt $\text{nDCG@10}$ cao nhất trên cả DEV ($0.9264$) lẫn TEST ($0.9124$), trở thành bộ trọng số khóa cứng $\mathbf{w}_{\text{Exp B}}^* = (\text{problem}: 0.40,\ \text{task}: 0.20,\ \text{method}: 0.20,\ \text{dataset}: 0.10,\ \text{contribution}: 0.10)$ để chuyển giao sang nhánh Hội nghị.

> **Lưu ý kiểm toán quan trọng cần minh bạch:** Tệp cấu hình `ranking_config.json` của Exp B quy định `google-bert/bert-base-uncased` ($768\text{d}$), nhưng thư mục `intermediate/bert_base_uncased/` hiện chưa được tạo trên đĩa; các con số Exp B trong bảng trên đang phản ánh lượt chạy trước trên cache MiniLM $384\text{d}$ và cần được chạy đồng bộ lại trên BERT $768\text{d}$ trước khi chốt bản thảo cuối cùng.

---

## 3. Thiết kế Giao thức Nhánh Hội nghị: Lý do cho từng Quyết định Kỹ thuật

Mọi quyết định thiết kế trong nhánh Khuyến nghị Hội nghị đều nhằm ngăn chặn một nguy cơ sai lệch thực nghiệm cụ thể:

1. **Khử rò rỉ dữ liệu theo thời gian và Adapter (`Zero Data Leakage`):**
   * **What:** Sử dụng bộ chia `temporal_2015_2016_2019_clean` gồm $602$ bài Train ($\le 2015$) và $168$ bài Test ($2016\text{--}2019$) thuộc $30$ hội nghị, trong đó $0$ bài Test trùng với tập `train + valid` của Adapter Exp A.
   * **Why:** Nếu bài Test từng đi qua quá trình tinh chỉnh QLoRA ở Exp A hoặc xuất bản trước các bài Train, mô hình sẽ hưởng lợi từ ghi nhớ ngữ nghĩa và thông tin tương lai.
   * **How:** Loại bỏ hoàn toàn $18$ bài trùng lặp trước khi chạy thực nghiệm và chỉ tối ưu siêu tham số qua 5-Fold Stratified CV (`seed=42`) trên $602$ bài Train, khóa cấu hình bằng mã băm SHA-256 (`4ca69062...037d12`) trước khi mở khóa tập Test.

2. **Loại bỏ tuyệt đối `validated_silver.jsonl`, chỉ dùng 5 Raw LLMs:**
   * **What:** Toàn bộ chỉ mục lịch sử Train ($602$ bài) dùng `Qwen-8B (Raw)` từ `data/exp_a/generated/facets_silver.jsonl`, còn $168$ bài Test đánh giá `Qwen-8B (Raw)` (Bảng 1–2) và hoán đổi lần lượt $5$ Raw LLMs (Bảng 3) theo kịch bản *Fixed-Index, Query-Side Extractor Substitution*.
   * **Why:** Trong `validated_silver.jsonl`, quy trình gắn cờ `needs_review` trước đây đã làm mất hàng nghìn nhãn `task` và `method` hợp lệ, gây méo nghiêm trọng phân phối dữ liệu. Đồng nhất $5$ bản `Raw` đảm bảo mọi mô hình chia sẻ cùng schema (`List[str]`, khuyết là `[]`) và quy tắc nối chuỗi `"; "`.

3. **Khóa cứng trọng số $\mathbf{w}_{\text{Exp B}}^*$ thay vì dò tìm trọng số 5 chiều mới (`Zero-Shot Cross-Task Transfer`):**
   * **What:** Truyền nguyên trạng $\mathbf{w}_{\text{Exp B}}^* = (0.40, 0.20, 0.20, 0.10, 0.10)$ vào hàm chấm điểm cặp $S_{\text{weighted}}(q, p)$ của nhánh Hội nghị.
   * **Why:** Tập Train Hội nghị chỉ có $602$ bài và phân bố lệch mạnh: `Head` ($8$ hội nghị $\ge 20$ bài: $433$ Train / $119$ Test), `Mid` ($16$ hội nghị $5\text{--}19$ bài: $147$ Train / $40$ Test) và `Tail` ($6$ hội nghị $< 5$ bài: $22$ Train / $n = 9$ Test). Dò lưới trọng số $5$ chiều trên tập nhỏ và lệch này tất yếu gây quá khớp (*overfitting*) vào giai đoạn $\le 2015$ — thực tế kiểm chứng cho thấy cấu hình tự dò trọng số thắng Train CV ($45.52\%$) nhưng tụt `Test MRR` xuống $0.3291\text{--}0.3296$ và `Test Hit@1` xuống $14.88\%$, thấp hơn cả $\mathbf{w}_{\text{Exp B}}^*$ khóa cứng ($0.3401\text{--}0.3525$ MRR, $15.48\%\text{--}17.26\%$ Hit@1). Khóa cứng $\mathbf{w}_{\text{Exp B}}^*$ đồng thời bảo toàn đóng góp C2 (trọng số dùng chung) và cô lập biến thực nghiệm cho tầng tổng hợp hội nghị.

4. **Thiết kế 4 cơ chế tổng hợp điểm hội nghị để xử lý hai điểm nghẽn toán học:**
   * **Vấn đề:** *(a)* Vector mean-pooling của raw `bert-base-uncased` chịu hiện tượng *anisotropy* (độ tương đồng cosine co cụm trong khoảng hẹp, làm mờ ranh giới giữa láng giềng rất gần và hơi gần); *(b)* cộng dồn điểm toàn cục trong Top-$k$ khiến nhóm `Head` nhiều bài áp đảo hoàn toàn nhóm `Tail`.
   * **Giải pháp:** Giữ `Sum-kNN` ($k \in \{5, 10, 15, 20, 25, 30\}$) làm mốc cơ sở kế thừa Exp B, đối chiếu với `Temp-Softmax` ($\tau \in \{0.02, 0.05, 0.10, 0.20\}$ để khuếch đại độ sắc nét cosine), `Prior-Norm` (chia $N_v^\alpha$ với $\alpha \in \{0.5, 1.0\}$ để triệt tiêu lợi thế số lượng của hội nghị lớn), và `Per-Venue Top-m` ($m \in \{1, 2, 3\}$, lấy trung bình đúng $m$ bài gần nhất thuộc từng hội nghị để bất biến quy mô mẫu).

5. **Bắt buộc kiểm định ý nghĩa thống kê trên $N = 168$ bài Test:**
   * Vì mỗi bài báo tương đương $\approx 0.595\%$ ở $\text{Hit@}K$, mọi so sánh trong Bảng 1 và Bảng 3 đều đi kèm **McNemar Exact Test** (`Hit@3`), **Paired Permutation Test** ($10.000$ lần cho `MRR`), **Paired Bootstrap 95% CI** (`Macro-Hit@3`), hiệu chỉnh đa phép thử **Holm-Bonferroni** (trên $8$ cặp so sánh Bảng 1) và **Exact Permutation $p$-value** cho tương quan hạng Spearman/Kendall ($n = 5$ mô hình, $5! = 120$ hoán vị, $p_{\min} = 0.0167$).

---

## 4. Phân tích Nhân quả Kết quả Thực nghiệm Nhánh Hội nghị

### 4.1. Bảng 1 (Main Results — RQ2): Phân kỳ giữa Paper Retrieval và Conference Ranking

*(Ký hiệu $\dagger$: $p_{\text{raw}} < 0.05$ so với `Full-text` trên cùng cơ chế tổng hợp qua McNemar Exact Test cho `Hit@3` và Paired Permutation Test $10.000$ lần cho `MRR`; $\ddagger$: giữ vững $p_{\text{adj}} < 0.05$ sau hiệu chỉnh Holm-Bonferroni trên $8$ phép thử.)*

| Phương pháp | Cơ chế tổng hợp (Chọn CV) | Train CV Hit@3 | Test Hit@1 | Test Hit@3 | Test Hit@5 | Test MRR | Test Macro-Hit@3 [95% CI] | Tail Hit@3 ($n=9$) | Disc Hit@1 |
|---|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| **Random Baseline (30 venues)** | — | — | 3.33% | 10.00% | 16.67% | 0.1332 | — | — | — |
| **Method 1: Full-text BERT** | `Sum-kNN` ($k=30$) | $51.50\% \pm 3.87\%$ | **25.60%** | 50.00% | **68.45%** | **0.4346** | 24.02% [20.1, 32.8] | 0.00% | **75.00%** |
| **Method 1: Full-text BERT** | `Temp-Softmax` ($k=30, \tau=0.02$) | **$51.99\% \pm 3.16\%$** | 23.81% | **52.38%** | **68.45%** | 0.4302 | 26.66% [22.5, 36.2] | 0.00% | 72.62% |
| **Method 1: Full-text BERT** | `Prior-Norm` ($k=30, \tau=0.20, \alpha=0.5$) | $42.87\% \pm 5.16\%$ | 17.86% | 45.24% | 58.33% | 0.3651 | **32.49%** [26.1, 42.9] | **11.11%** | 60.12% |
| **Method 1: Full-text BERT** | `Per-Venue Top-m` ($m=3$) | $49.84\% \pm 3.82\%$ | 24.40% | **52.38%** | 67.26% | 0.4289 | 29.14% [25.0, 39.7] | 0.00% | 71.43% |
| **Method 2: Equal-weight ($0.2 \times 5$)** | `Sum-kNN` ($k=25$) | $44.18\% \pm 3.53\%$ | 14.29% | 44.05% | 58.93% | $0.3442^{\dagger\ddagger}$ | 15.12% [13.0, 23.0] | 0.00% | 66.07% |
| **Method 2: Equal-weight ($0.2 \times 5$)** | `Temp-Softmax` ($k=25, \tau=0.20$) | $44.18\% \pm 3.53\%$ | 14.88% | **44.64%** | 58.93% | $0.3476^{\dagger\ddagger}$ | 15.47% [13.3, 23.5] | 0.00% | 66.07% |
| **Method 2: Equal-weight ($0.2 \times 5$)** | `Prior-Norm` ($k=30, \tau=0.20, \alpha=0.5$) | $29.91\% \pm 5.96\%$ | 10.12% | $29.76\%^{\dagger\ddagger}$ | 43.45% | $0.2701^{\dagger\ddagger}$ | **15.49%** [11.7, 24.5] | **11.11%** | 51.19% |
| **Method 2: Equal-weight ($0.2 \times 5$)** | `Per-Venue Top-m` ($m=3$) | $43.36\% \pm 3.44\%$ | 16.67% | $41.07\%^{\dagger}$ | 60.12% | $0.3522^{\dagger\ddagger}$ | 13.72% [12.0, 20.6] | 0.00% | 63.69% |
| **Method 3: $\mathbf{w}_{\text{Exp B}}^*$ Weighted** | `Sum-kNN` ($k=25$) | **$44.68\% \pm 3.09\%$** | 15.48% | $41.07\%^{\dagger}$ | 55.95% | $0.3401^{\dagger\ddagger}$ | 15.03% [12.5, 22.9] | 0.00% | 64.88% |
| **Method 3: $\mathbf{w}_{\text{Exp B}}^*$ Weighted** | `Temp-Softmax` ($k=25, \tau=0.20$) | **$44.68\% \pm 3.09\%$** | 15.48% | $41.07\%^{\dagger}$ | 55.95% | $0.3404^{\dagger\ddagger}$ | 15.03% [12.5, 22.9] | 0.00% | 64.88% |
| **Method 3: $\mathbf{w}_{\text{Exp B}}^*$ Weighted** | `Prior-Norm` ($k=30, \tau=0.10, \alpha=0.5$) | $28.57\% \pm 4.72\%$ | 10.71% | $22.02\%^{\dagger\ddagger}$ | 41.67% | $0.2546^{\dagger\ddagger}$ | 10.90% [7.5, 18.3] | 0.00% | 48.81% |
| **Method 3: $\mathbf{w}_{\text{Exp B}}^*$ Weighted** | `Per-Venue Top-m` ($m=3$) | $40.53\% \pm 2.05\%$ | **17.26%** | $41.07\%^{\dagger}$ | **60.12%** | **$0.3525^{\dagger\ddagger}$** | 14.05% [12.2, 20.9] | 0.00% | 62.50% |

**Phân tích nhân quả 3 hiện tượng chính từ Bảng 1:**

* **Hiện tượng 1 — `Full-text BERT` vượt trội có ý nghĩa thống kê trước cả hai phương pháp Facet:** `Method 1` đạt đỉnh $52.38\%$ Test Hit@3 (`Temp-Softmax`, `Per-Venue Top-m`), $0.4346$ MRR và $75.00\%$ Discipline Hit@1 (`Sum-kNN`), cao hơn toàn bộ các cấu hình 5 Facets ($41.07\%\text{--}44.64\%$ Hit@3, $0.3401\text{--}0.3525$ MRR), với $8/8$ so sánh MRR giữ vững ý nghĩa thống kê sau Holm-Bonferroni ($p_{\text{adj}} \in [0.0016, 0.0290]$).
  * **Nguyên nhân:** Ba cơ chế cộng hưởng gây ra sự phân kỳ này so với Exp B: *(1)* `bert-base-uncased` chưa qua huấn luyện đối sánh (contrastive) nên biểu diễn câu liên mạch tốt hơn nhiều so với danh sách cụm từ ngắn nối bằng dấu `;`, đồng thời văn phong trình bày đặc trưng của từng hội nghị bị mất khi bóc tách facet; *(2)* ở `Qwen-8B (Raw)`, khía cạnh `problem` vắng mặt tới $60.80\%$ trên Train và $54.17\%$ trên Test, khiến trọng số chủ lực $0.40$ của $\mathbf{w}_{\text{Exp B}}^*$ không kích hoạt trên quá nửa số cặp bài báo; *(3)* phân loại hội nghị phụ thuộc mạnh vào bức tranh ngữ cảnh lĩnh vực rộng thay vì sự trùng khớp kỹ thuật vi mô giữa hai bài báo đơn lẻ.

* **Hiện tượng 2 — Sự đánh đổi giữa `Hit@1` và `Hit@3` của $\mathbf{w}_{\text{Exp B}}^*$ so với `Equal-weight`:** Trên Train CV ($\le 2015$), $\mathbf{w}_{\text{Exp B}}^*$ ($44.68\%$) vượt `Equal-weight` ($44.18\%$, $+0.50\text{ pp}$). Sang tập Test ($2016\text{--}2019$), $\mathbf{w}_{\text{Exp B}}^*$ vẫn giữ ưu thế ở **`Hit@1`** ($15.48\%\text{--}17.26\%$ vs $14.29\%\text{--}16.67\%$) nhưng thấp hơn nhẹ ở `Hit@3` ($41.07\%$ vs $44.05\%\text{--}44.64\%$).
  * **Nguyên nhân:** Dồn $40\%$ trọng số vào `problem` tạo tín hiệu sắc nét ở hạng $1$ khi cả hai bài đều trích xuất trúng vấn đề nghiên cứu, nhưng lại làm tăng phương sai ở Top-$3$ khi chuyển sang giai đoạn $2016\text{--}2019$ do tỷ lệ thiếu `problem` cao của `Qwen-8B (Raw)` và sự dịch chuyển từ vựng.

* **Hiện tượng 3 — Đánh đổi Micro vs. Macro giữa 4 cơ chế tổng hợp hội nghị:**
  * `Temp-Softmax` xử lý hiệu quả tính *anisotropy* của raw BERT, giúp nâng `Full-text` từ $50.00\%$ lên $52.38\%$ Hit@3 (`Macro-Hit@3` từ $24.02\%$ lên $26.66\%$) và nâng `Equal-weight` lên $44.64\%$.
  * `Per-Venue Top-m` ($m=3$) khai thác hiệu quả cấu trúc đa phân nhánh của từng hội nghị, giúp `Method 3` ($\mathbf{w}_{\text{Exp B}}^*$) đạt điểm Test cao nhất ở cả `Hit@1` ($17.26\%$), `Hit@5` ($60.12\%$) và `MRR` ($0.3525$), đồng thời nâng `Macro-Hit@3` của `Full-text` từ $24.02\%$ lên $29.14\%$. Tuy nhiên, `Tail Hit@3` vẫn bằng $0.00\%$ do thiên lệch thống kê cực trị (*Order Statistics Bias*): kỳ vọng trung bình của Top-$3$ bài giống nhất rút từ tập lớn (`Head`) luôn lớn hơn rút từ tập chỉ có $3\text{--}4$ bài (`Tail`).
  * `Prior-Norm` là cơ chế duy nhất phá vỡ áp đảo tần suất lớp, nâng `Mid Hit@3` của `Full-text` lên $37.50\%$, `Macro-Hit@3` đạt đỉnh $32.49\%$, và đưa `Tail Hit@3` lên $11.11\%$ (trên cả `Full-text` và `Equal-weight`, tương ứng $1/9$ bài nhóm `Tail`), nhưng phải đánh đổi giảm mạnh hiệu năng nhóm `Head` (trên $\mathbf{w}_{\text{Exp B}}^*$, `Head Hit@3` giảm từ $54.62\%$ xuống $26.89\%$).

---

### 4.2. Bảng 2 (Ablation, Temporal Drift & Exp C3): Chẩn đoán từng khía cạnh và công thức tái chuẩn hóa

Thí nghiệm chạy trên điểm vận hành thắng CV của $\mathbf{w}_{\text{Exp B}}^*$ (`Sum-kNN`, $k=25$), lần lượt gán từng trọng số về $0$ và tái chuẩn hóa $4$ phần tử còn lại về tổng $1.0$.

| Biến thể | Trọng số $(P, T, M, D, C)$ | Train CV ($\le 2015$) Hit@3 | $\Delta$ CV (pp) | Test ($2016\text{--}2019$) Hit@3 | $\Delta$ Test (pp) | Test MRR | $\Delta$ MRR | Cross-Disc Error (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Full 5 Facets (Baseline)** | $(0.400, 0.200, 0.200, 0.100, 0.100)$ | $44.68\% \pm 3.09\%$ | $+0.00$ | 41.07% | $+0.00$ | 0.3401 | $+0.0000$ | 35.12% |
| `w/o Problem` | $(0.000, 0.333, 0.333, 0.167, 0.167)$ | $45.34\% \pm 2.50\%$ | $+0.67$ | **42.26%** | **$+1.19$** | 0.3495 | $+0.0094$ | 34.52% |
| `w/o Task` | $(0.500, 0.000, 0.250, 0.125, 0.125)$ | **$41.02\% \pm 4.66\%$** | **$-3.66$** | **42.26%** | **$+1.19$** | **0.3708** | **$+0.0308$** | 33.33% |
| `w/o Method` | $(0.500, 0.250, 0.000, 0.125, 0.125)$ | $43.36\% \pm 1.87\%$ | $-1.32$ | **42.26%** | **$+1.19$** | 0.3340 | $-0.0061$ | **31.55%** |
| `w/o Dataset` | $(0.444, 0.222, 0.222, 0.000, 0.111)$ | **$45.68\% \pm 2.22\%$** | $+1.00$ | 41.67% | $+0.60$ | 0.3432 | $+0.0031$ | 35.12% |
| `w/o Contribution` | $(0.444, 0.222, 0.222, 0.111, 0.000)$ | $41.53\% \pm 2.35\%$ | $-3.14$ | **38.69%** | **$-2.38$** | 0.3396 | $-0.0005$ | 32.14% |
| **Zero-Imputation (Exp C3)** | $(0.400, 0.200, 0.200, 0.100, 0.100)$ (mẫu số $=1$) | $43.01\% \pm 3.01\%$ | $-1.66$ | **38.10%** | **$-2.98$** | **0.3025** | **$-0.0376$** | **35.71%** |

**Phân tích nhân quả từ Bảng 2:**

1. **Bảo vệ vững chắc công thức tái chuẩn hóa mẫu số động (`Exp C3`):** Khi thay bằng `Zero-Imputation` (gán $0.0$ cho khía cạnh bị khuyết và giữ mẫu số cố định bằng $1.0$), hệ thống suy giảm đồng loạt trên mọi thước đo: Train CV giảm $-1.66\text{ pp}$, Test Hit@3 giảm $-2.98\text{ pp}$, Test MRR tụt sâu $-0.0376$ ($0.3401 \rightarrow 0.3025$) và tỷ lệ nhầm chéo ngành tăng lên $35.71\%$. Xét riêng **$121$ bài Test không có `dataset`**, `Dynamic Renormalization` vượt trội hoàn toàn ở cả $4$ chỉ số (`Hit@1`: $14.88\%$ vs $11.57\%$; `Hit@3`: $40.50\%$ vs $37.19\%$; `Hit@5`: $57.85\%$ vs $52.89\%$; `MRR`: $0.3358$ vs $0.2987$).
   * **Cơ chế:** Gán điểm $0$ ép các bài báo lý thuyết hoặc bài bị LLM bỏ sót `problem`/`dataset` nhận điểm tương đồng giả tạo gần $0$ với cả những bài cùng hội nghị, trong khi tái chuẩn hóa mẫu số giữ nguyên thang đo trên tập khía cạnh thực sự tồn tại.

2. **Bản chất dịch chuyển thời gian (`Temporal Drift`) và vai trò bù đắp của từng khía cạnh:**
   * **`Contribution` đóng vai trò lớp đệm bảo toàn độ phủ:** Đây là khía cạnh duy nhất khi loại bỏ làm giảm điểm trên **cả hai giai đoạn** ($-3.14\text{ pp}$ trên CV, $-2.38\text{ pp}$ trên Test). Nguyên nhân là `Contribution` gần như luôn hiện diện ($592/602$ Train, $165/168$ Test) nên giúp bù đắp tín hiệu ngữ nghĩa cho các cặp bài bị thiếu `Problem` hoặc `Dataset`.
   * **`Task` và `Method` nhạy cảm với dịch chuyển thuật ngữ $2016\text{--}2019$:** Trên giai đoạn lịch sử $\le 2015$, bỏ `Task` làm CV tụt mạnh nhất ($-3.66\text{ pp}$) và bỏ `Method` làm CV tụt $-1.32\text{ pp}$ (đồng thời làm Test MRR giảm $-0.0061$). Nhưng trên tập Test $2016\text{--}2019$, bỏ `Method` lại kéo tỷ lệ nhầm chéo ngành xuống mức thấp nhất toàn bảng (**$31.55\%$**). Nguyên nhân nhân quả: giai đoạn $2016\text{--}2019$ chứng kiến sự phổ cập xuyên ngành của các kiến trúc học sâu (CNN, RNN, Attention); những từ khóa `Method` giống nhau có thể kéo một bài báo NLP sang gần hội nghị Thị giác máy tính hoặc Học máy, làm tăng lỗi chéo ngành.
   * **Hệ quả của trọng số lớn đặt lên trường thưa (`Problem`):** Bỏ `Problem` trên dữ liệu `Qwen-8B (Raw)` khiến CV tăng $+0.67\text{ pp}$ và Test Hit@3 tăng $+1.19\text{ pp}$ ($42.26\%$). Điều này không có nghĩa khía cạnh vấn đề là vô ích, mà phản ánh rủi ro khi đặt trọng số $0.40$ lên một trường có tỷ lệ vắng mặt vượt quá một nửa ở `Qwen-8B (Raw)` — nhận định này được chứng minh trực tiếp ở Bảng 3 ngay bên dưới.

---

### 4.3. Bảng 3 (Benchmark 5 Raw LLMs — RQ3, RQ4 & Exp C4): Mối liên hệ giữa F1 nội tại và hiệu năng thực tế

Kho lịch sử Train ($602$ bài) cố định bằng `Qwen-8B (Raw)`, lần lượt hoán đổi $5$ Raw LLMs trên $168$ bài Test sạch ở cả `Equal-weight` (`Temp-Softmax`, $k=25, \tau=0.20$) và $\mathbf{w}_{\text{Exp B}}^*$ (`Sum-kNN`, $k=25$).

| Facet Scorer | Raw LLM | Exp A Micro / Macro-F1 (%) | Test Cov (%) | BERT Encode (ms/p) | Retrieval (ms/q) | Hit@1 | Hit@3 | Hit@5 | MRR | Macro-Hit@3 | W/T/L vs Qwen-8B |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| `Equal-weight` | **Qwen-8B** | 66.73 / 67.67 | 73.81% | 3.29 | 0.25 | 14.88% | 44.64% | 58.93% | 0.3476 | 15.47% | 0 / 168 / 0 |
| `Equal-weight` | **Gemma-9B** | **68.18 / 70.39** | 77.38% | 3.18 | 0.27 | 17.86% | 43.45% | 55.95% | 0.3535 | 14.43% | 63 / 36 / 69 |
| `Equal-weight` | **Qwen-14B** | 63.67 / 65.62 | 78.33% | 3.24 | 0.26 | 19.64% | 39.88% | 52.38% | 0.3588 | 12.37% | 57 / 45 / 66 |
| `Equal-weight` | **Llama-8B** | 64.51 / 65.28 | **79.52%** | 3.28 | 0.25 | **21.43%** | 42.86% | 53.57% | **0.3732** | 12.26% | 59 / 46 / 63 |
| `Equal-weight` | **Qwen-4B** | 60.99 / 62.93 | 75.36% | **3.00** | 0.25 | 19.05% | **45.83%** | **59.52%** | 0.3714 | **20.34%** | 55 / 50 / 63 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Qwen-8B** | 66.73 / 67.67 | 73.81% | 3.29 | 0.25 | 15.48% | 41.07% | 55.95% | 0.3401 | 15.03% | 0 / 168 / 0 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Gemma-9B** | **68.18 / 70.39** | 77.38% | 3.18 | 0.25 | 17.26% | **44.64%** | 55.95% | 0.3555 | 16.51% | 63 / 42 / 63 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Qwen-14B** | 63.67 / 65.62 | 78.33% | 3.24 | 0.25 | 19.64% | 42.86% | 52.98% | 0.3581 | 14.52% | 63 / 41 / 64 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Llama-8B** | 64.51 / 65.28 | **79.52%** | 3.28 | 0.27 | **20.83%** | 44.05% | 56.55% | 0.3759 | 13.80% | **71** / 39 / 58 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Qwen-4B** | 60.99 / 62.93 | 75.36% | **3.00** | 0.27 | **20.83%** | **44.64%** | **57.14%** | **0.3777** | **18.39%** | 68 / 36 / 64 |

**Phân tích nhân quả 3 phát hiện trọng tâm từ Bảng 3:**

1. **Giải mã sự đứt gãy giữa F1 nội tại (Exp A) và hiệu năng gợi ý hội nghị (RQ4):**
   * **Hiện tượng:** `Gemma-9B` đứng đầu Exp A ($70.39\%$ Macro-F1), nhưng **`Qwen-4B`** (F1 thấp nhất: $62.93\%$) lại dẫn đầu hoặc đồng hạng nhất về `Hit@3` ở cả hai cấu hình ($45.83\%$ ở `Equal-weight`, $44.64\%$ ở $\mathbf{w}_{\text{Exp B}}^*$), đồng thời đứng đầu tuyệt đối về `MRR` ($0.3777$), `Hit@5` ($57.14\%$) và `Macro-Hit@3` ($18.39\%\text{--}20.34\%$) trên $\mathbf{w}_{\text{Exp B}}^*$.
   * **Kiểm định thống kê chặt chẽ:** Với $n = 5$ mô hình ($p_{\text{exact}}$ hai phía tối thiểu $= 0.0167$), mọi tương quan hạng giữa F1 nội tại và hiệu năng hội nghị đều âm nhưng không đạt ngưỡng $p < 0.05$ (`Macro-F1 vs MRR` trên $\mathbf{w}_{\text{Exp B}}^*$: $\rho = -0.9000, p_{\text{exact}} = 0.0833$; `Method-F1 vs Hit@3`: $\rho = -0.8721, p_{\text{exact}} = 0.1000$; `Macro-F1 vs Hit@3`: $\rho = -0.2052, p_{\text{exact}} = 0.7333$), và chưa có cặp LLM nào tạo chênh lệch đạt ý nghĩa thống kê từng cặp trên $168$ bài ($p_{\text{mc}} \in [0.1516, 0.8506]$, $p_{\text{perm}} \in [0.0812, 0.7958]$). Do đó, kết luận khoa học chuẩn xác là **chỉ số F1 trích xuất nội tại trên tập Gold không đủ sức dự báo thứ hạng hiệu năng ở tác vụ khuyến nghị hội nghị**.

2. **Bằng chứng nhân quả về độ phủ `Problem` và độ súc tích văn bản:**
   * **Hiện tượng:** Khi giữ nguyên chỉ mục Train của `Qwen-8B` nhưng thay đầu vào Test bằng bất kỳ mô hình nào trong $4$ LLM còn lại (`Gemma-9B`, `Qwen-14B`, `Llama-8B`, `Qwen-4B`), hiệu năng của **$\mathbf{w}_{\text{Exp B}}^*$ tăng đồng loạt trên cả $4$ mô hình**: `Hit@1` từ $15.48\%$ lên $17.26\%\text{--}20.83\%$, `Hit@3` từ $41.07\%$ lên $42.86\%\text{--}44.64\%$, và `MRR` từ $0.3401$ lên $0.3555\text{--}0.3777$ (với `Llama-8B` đạt $71$ thắng / $58$ thua và `Qwen-4B` đạt $68$ thắng / $64$ thua so với `Qwen-8B`).
   * **Nguyên nhân:** Bốn mô hình thay thế vừa có **độ phủ `problem` cao hơn hẳn** ($56.55\%\text{--}71.43\%$ so với $45.83\%$ của `Qwen-8B`), giúp mở khóa trọng số $0.40$ của $\mathbf{w}_{\text{Exp B}}^*$ trên nhiều bài truy vấn hơn, vừa trích xuất **cô đọng hơn** ($32.21\text{--}33.93$ từ/bài so với $39.17$ từ/bài của `Qwen-8B`), giảm hiện tượng pha loãng ngữ nghĩa khi lấy trung bình token (`mean pooling`) trong raw BERT. Điều này chứng minh ở tác vụ truy xuất dùng encoder cố định, **độ phủ khía cạnh trọng yếu và độ gọn ngữ nghĩa** quan trọng hơn việc khớp chặt từng cụm từ theo chuẩn F1.

3. **Phân tích đánh đổi chi phí – hiệu quả hệ thống (`Exp C4`):**
   * Biểu diễn $5$ khía cạnh cần $15.01\text{ KB/bài}$ (gấp $5.0\times$ dung lượng $3.00\text{ KB/bài}$ của `Full-text`).
   * Sau bước warm-up CUDA (`batch_size=16`), tốc độ mã hóa BERT trên GPU RTX 4060 gần như đồng nhất giữa $5$ LLM ($3.00\text{--}3.29\text{ ms/bài}$), và thời gian xếp hạng $30$ hội nghị chỉ tốn $0.25\text{--}0.27\text{ ms/query}$.
   * Vì nút thắt cổ chai nằm ở chi phí chạy LLM (`Qwen-4B` tốn $11,833\text{s}$ cho Exp A, gần bằng một nửa `Qwen-14B` với $20,830\text{s}$ và `Gemma-9B` với $20,146\text{s}$), **`Qwen-4B` nằm ở điểm tối ưu trên đường biên Pareto** khi triển khai thực tế ở phía truy vấn.

---

### 4.4. Độ nhạy theo số láng giềng $k$ trên Train CV ($\le 2015$)

| Phương pháp (`Sum-kNN`) | $k=5$ | $k=10$ | $k=15$ | $k=20$ | $k=25$ | $k=30$ |
|---|---:|---:|---:|---:|---:|---:|
| **`Method 1: Full-text BERT`** (Hit@3 / MRR) | 41.05% / 0.3570 | 45.86% / 0.3816 | 51.17% / 0.4055 | 50.00% / 0.4092 | 50.50% / **0.4213** | **51.50%** / 0.4182 |
| **`Method 2: Equal-weight`** (Hit@3 / MRR) | 30.07% / 0.2667 | 38.54% / 0.3207 | 42.03% / 0.3357 | 43.85% / 0.3598 | **44.18%** / **0.3699** | 43.85% / 0.3692 |
| **`Method 3: $\mathbf{w}_{\text{Exp B}}^*$ Weighted`** (Hit@3 / MRR) | 33.39% / 0.2805 | 37.87% / 0.3144 | 39.37% / 0.3424 | 43.35% / 0.3597 | **44.68%** / **0.3732** | 44.52% / 0.3725 |

* **Cơ chế phân biệt:** Cả hai phương pháp Facet đều đạt đỉnh bão hòa nội tại rõ rệt ở **$k^* = 25$** (và giảm nhẹ tại $k=30$), trong khi `Full-text` vẫn tăng Hit@3 chạm biên $k^* = 30$ (dù MRR đạt đỉnh tại $k=25$ là $0.4213$). Nguyên nhân là không gian tương đồng $5$ khía cạnh có lân cận ngữ nghĩa hẹp và chuyên biệt hơn: khi mở rộng quá $25$ bài báo lịch sử, các láng giềng mới kéo theo nhiễu ngoại hội nghị, còn `Full-text` hưởng lợi từ việc làm mượt chủ đề tổng quát trên nhiều láng giềng. Tại đúng điểm bão hòa $k=25$, $\mathbf{w}_{\text{Exp B}}^*$ ($44.68\%$ Hit@3, $0.3732$ MRR) vượt `Equal-weight` ($44.18\%$ Hit@3, $0.3699$ MRR).

---

## 5. Tổng hợp Đóng góp Khoa học & Các Điểm Giới hạn cần Minh bạch trước khi Nộp IEEE

Toàn bộ kết quả thực nghiệm hình thành một chuỗi lập luận nhất quán trả lời trọn vẹn $4$ câu hỏi nghiên cứu của đề tài:

* **Trả lời RQ1 (Exp A):** Tinh chỉnh QLoRA giúp các LLM mã nguồn mở trích xuất $5$ khía cạnh khoa học đạt $62.93\%\text{--}70.39\%$ Macro-F1 (vượt xa bản chưa tinh chỉnh $25.97\%$), nhưng bộc lộ sự khác biệt rõ rệt về độ phủ trường khó (`problem`) và độ dài diễn đạt giữa các mô hình.
* **Trả lời RQ2 (Exp B vs. Conference & Cross-Task Transfer):** Biểu diễn $5$ khía cạnh và trọng số $\mathbf{w}_{\text{Exp B}}^*$ không mặc nhiên áp đảo `Full-text` ở mọi tác vụ; dưới raw `bert-base-uncased` $768\text{d}$, `Full-text` vượt trội có ý nghĩa thống kê ở cấp độ hội nghị do bảo toàn ngữ cảnh toàn văn và không chịu tác động từ độ thưa của `problem`. Ở tầng tổng hợp, `Temp-Softmax` và `Per-Venue Top-m` cải thiện độ chính xác tổng thể, còn `Prior-Norm` là đòn bẩy đánh đổi rõ rệt để nâng `Macro-Hit@3` và cứu nhóm `Tail`. Ngoài ra, `Exp C3` xác nhận công thức tái chuẩn hóa mẫu số động kế thừa từ Exp B là thiết yếu ($+2.98\text{ pp}$ Test Hit@3 và $+0.0376$ MRR so với gán $0$).
* **Trả lời RQ3 & RQ4 (Cross-LLM Utility & Efficiency):** Chất lượng F1 nội tại trên tập Gold không đồng biến với hiệu năng khuyến nghị hội nghị; ngược lại, độ phủ khía cạnh trọng số cao (`problem`) và độ cô đọng của cụm từ mới là yếu tố cải thiện trực tiếp chất lượng xếp hạng dưới raw BERT, đưa mô hình gọn nhẹ `Qwen-4B` lên vị trí tối ưu về chi phí – hiệu quả.

Để bài báo đạt độ chặt chẽ cao nhất trước hội đồng phản biện IEEE, cần minh bạch và xử lý $3$ giới hạn sau trong phần *Threats to Validity / Future Work*:
1. **Đóng vòng đồng bộ Encoder với Exp B:** Chạy bổ sung lượt thực nghiệm Exp B trên đúng cache `google-bert/bert-base-uncased` $768\text{d}$ (thay thế lượt $384\text{d}$ hiện hành trên đĩa) để đảm bảo đối chiếu Exp B $\leftrightarrow$ Conference diễn ra trên cùng một không gian vector.
2. **Kịch bản bất đối xứng ở Bảng 3 và kích thước mẫu nhóm `Tail`:** Ghi rõ Bảng 3 đánh giá kịch bản thực tiễn *Fixed-Index, Query-Side Substitution* (chỉ mục lịch sử cố định bằng `Qwen-8B Raw`), và ghi chú quy mô nhóm `Tail` trên tập Test chỉ gồm $n = 9$ bài thuộc $6$ hội nghị (mức $11.11\%$ tương đương $1/9$ bài) để giữ nhận định ở mức trung thực tuyệt đối.
3. **Đo độ trễ suy luận LLM trên từng truy vấn:** Bổ sung số đo thời gian sinh $5$ khía cạnh thực tế (giây/bài) cho từng LLM trên GPU RTX 4060 bên cạnh tổng thời gian chạy Exp A (`Exp A Wall`), hoàn thiện bức tranh chi phí vận hành đầu–cuối trong `Exp C4`.

---

## 6. Giải đáp Chuyên sâu các Câu hỏi Phương pháp luận Trọng tâm (Q&A)

Phần này tổng hợp lập luận giải đáp trực tiếp $4$ câu hỏi cốt lõi thường gặp khi bảo vệ đồ án hoặc đối thoại với hội đồng phản biện IEEE.

### Câu hỏi 1: Ở nhánh Hội nghị, Input và Output là gì? Tập Train có phải là kho ứng viên cho tập Test sử dụng trọng số và ranking từ Exp B không?

**Trả lời:**
* **Input của nhánh Hội nghị gồm 3 thành phần:**
  1. **Bản thảo truy vấn mới $q$** ở bối cảnh *cold-start* (chưa có mạng trích dẫn), gồm `Title` và `Abstract`, được mã hóa trực tiếp thành $1$ vector `Full-text` hoặc trích xuất qua LLM thành $5$ khía cạnh (`problem`, `task`, `method`, `dataset`, `contribution`), sau đó mã hóa thành $5$ vector $768\text{d}$ bằng `google-bert/bert-base-uncased` (`mean` pooling, chuẩn hóa $L_2$) kèm mặt nạ hiện diện $m_f(q)$.
  2. **Kho bài báo lịch sử có nhãn hội nghị:** Gồm $602$ bài Train ($\le 2015$, trích xuất sẵn từ `Qwen-8B Raw`) cùng danh mục $30$ hội nghị ứng viên $\mathcal{V}$.
  3. **Cấu hình chấm điểm và tổng hợp:** Hàm tính điểm cặp $S(q, p)$ với bộ trọng số khóa cứng từ Exp B ($\mathbf{w}_{\text{Exp B}}^* = (0.40, 0.20, 0.20, 0.10, 0.10)$) và siêu tham số tầng tổng hợp đã khóa ($k, \tau, \alpha, m$).
* **Output của nhánh Hội nghị gồm 2 cấp độ:**
  1. **Cấp độ một bản thảo:** Danh sách xếp hạng toàn bộ $30$ hội nghị ứng viên sắp xếp giảm dần theo điểm phù hợp $\text{VenueScore}(q, v)$ (nếu đồng điểm thì xếp theo `conference_id` tăng dần).
  2. **Cấp độ đánh giá hệ thống:** Bộ chỉ số đo chất lượng xếp hạng trên toàn tập kiểm thử gồm `Hit@1/3/5`, `MRR`, `Macro-Hit@3`, `Tail Hit@3` và `Discipline Hit@1`.
* **Vai trò của tập Train so với Exp B:** Tập Train ($602$ bài $\le 2015$) đóng vai trò là **kho bài báo lịch sử tham chiếu (reference/neighbor pool)**. Khi nhận một bài $q$ từ tập Test ($168$ bài), hệ thống tính điểm tương đồng cặp $S(q, p)$ giữa $q$ với từng bài $p$ trong $602$ bài Train bằng đúng bộ mã hóa BERT, công thức tái chuẩn hóa mẫu số động và trọng số khóa cứng $\mathbf{w}_{\text{Exp B}}^*$ kế thừa nguyên trạng từ Exp B. Tuy nhiên, khác với Exp B (dừng ở danh sách bài báo ứng viên), nhánh Hội nghị dùng kết quả xếp hạng trên $602$ bài Train làm **bước trung gian** để đưa vào tầng tổng hợp (`Sum-kNN`, `Temp-Softmax`, `Prior-Norm`, `Per-Venue Top-m`), cho các bài lịch sử gần nhất bỏ phiếu nhằm xếp hạng **$30$ hội nghị ứng viên**.

---

### Câu hỏi 2: Tại sao nhánh Hội nghị vẫn cần tập Train và phải tách bạch Train ($\le 2015$) với Test ($2016\text{--}2019$) dù không huấn luyện tham số?

**Trả lời:**
Dù không huấn luyện trọng số mạng nơ-ron hay trọng số $5$ khía cạnh, việc tách bạch tập Train ($602$ bài, $\le 2015$) và tập Test ($168$ bài, $2016\text{--}2019$) là bắt buộc vì $3$ vai trò kỹ thuật và khoa học không thể thay thế:

| Tập dữ liệu | Quy mô & Thời gian | Vai trò cốt lõi trong thực nghiệm |
|---|---|---|
| **Tập Train** | $602$ bài ($\le 2015$) | 1. **Làm kho tri thức lịch sử (Reference Index):** Cung cấp hồ sơ ngữ nghĩa cho $30$ hội nghị để thuật toán bỏ phiếu nhận diện đặc trưng từng hội nghị (nếu không có, $30$ hội nghị chỉ là $30$ nhãn rỗng), đồng thời cung cấp tần suất bài $N_v$ cho cơ chế chuẩn hóa `Prior-Norm` ($N_v^{-\alpha}$).<br>2. **Chọn và khóa siêu tham số tầng tổng hợp không rò rỉ Test:** Thực hiện 5-Fold Stratified CV (`seed=42`, mỗi fold dùng $\approx 481$ bài làm kho tham chiếu để dự đoán $\approx 120$ bài còn lại) nhằm tìm giá trị tối ưu cho $k, \tau, \alpha, m$ trước khi chạm vào tập Test.<br>3. **Làm mốc đối chiếu quá khứ:** Cung cấp kết quả CV ($\le 2015$) để so sánh với Test ($2016\text{--}2019$) trong phân tích dịch chuyển thời gian (*Temporal Drift*, Bảng 2). |
| **Tập Test** | $168$ bài ($2016\text{--}2019$) | 1. **Đánh giá khách quan theo dòng thời gian thực:** Mô phỏng đúng tình huống tác giả nộp bản thảo mới ở tương lai chỉ dựa trên lịch sử công bố trước đó, đã loại sạch $18$ bài trùng với tập `train`/`valid` của Adapter Exp A ($0$ rò rỉ).<br>2. **Đo độ nhạy của 5 Raw LLMs (`Query-Side Substitution`):** Giữ cố định kho chỉ mục $602$ bài Train từ `Qwen-8B (Raw)`, lần lượt hoán đổi $5$ bộ trích xuất LLM trên đúng $168$ bài Test để kiểm chứng mối quan hệ giữa điểm F1 ở Exp A và hiệu năng gợi ý hội nghị. |

---

### Câu hỏi 3: Tại sao sử dụng cơ chế kế thừa và khóa cứng duy nhất bộ trọng số $\mathbf{w}_{\text{Exp B}}^*$ từ Exp B mà không tìm ra tập trọng số 5 facet riêng cho nhánh Hội nghị?

**Trả lời:**
Quyết định khóa cứng $\mathbf{w}_{\text{Exp B}}^*$ và chuyển giao không tinh chỉnh (*Zero-Shot Cross-Task Weight Transfer*) xuất phát từ $4$ lý do chặt chẽ về phương pháp luận và bằng chứng thực nghiệm:

1. **Bảo toàn Đóng góp C2 (`Shared Facet Weights`) và tính thống nhất của nghiên cứu có kiểm soát:** Đề tài đánh giá cùng một biểu diễn $5$ khía cạnh và bộ trọng số dùng chung xuyên suốt hai tác vụ downstream. Nếu dò một bộ trọng số mới riêng cho nhánh Hội nghị, liên kết nhân quả giữa hai phân hệ sẽ bị tách rời thành hai thực nghiệm độc lập.
2. **Hạn chế quá khớp (*Overfitting*) trên tập Train nhỏ và có dịch chuyển thời gian:** Tập Train Hội nghị chỉ có $602$ bài ($\le 2015$) và mất cân bằng lớp nghiêm trọng ($6$ hội nghị hiếm chỉ có $3\text{--}4$ bài). Bằng chứng thực nghiệm đã xác nhận: cấu hình tự dò trọng số trên Train CV đạt đỉnh CV ($45.52\%$), nhưng khi đánh giá trên $168$ bài Test ($2016\text{--}2019$) lại tụt xuống mức thấp nhất ở cả `Test Hit@1` ($14.88\%$) và `Test MRR` ($0.3291\text{--}0.3296$), thua cả $\mathbf{w}_{\text{Exp B}}^*$ khóa cứng ($15.48\%\text{--}17.26\%$ Hit@1, $0.3401\text{--}0.3525$ MRR).
3. **Cô lập biến thực nghiệm:** Nhánh Hội nghị đã có hai nhóm biến lớn cần đánh giá độc lập là $4$ cơ chế tổng hợp hội nghị ($k, \tau, \alpha, m$) và $5$ bộ trích xuất Raw LLM. Khóa chặt tầng chấm điểm cặp $S_{\text{weighted}}(q, p)$ từ Exp B giúp đảm bảo mọi sai khác ở Bảng 1 phản ánh thuần túy tác động của cơ chế tổng hợp, và Bảng 3 phản ánh thuần túy tác động của từng LLM.
4. **Không gian giả thuyết hẹp giúp tránh khớp ngẫu nhiên (*multiple testing*):** Dù tập DEV của Exp B chỉ có $15$ truy vấn, Exp B chỉ chọn lọc giữa các cấu hình trọng số có cơ sở học thuật định sẵn (`Weighted A` vs `Weighted B`) thay vì quét lưới tự do trên toàn không gian $5$ chiều.
* **Đánh đổi cần minh bạch (Task Mismatch):** Việc khóa cứng $\mathbf{w}_{\text{Exp B}}^*$ chấp nhận rủi ro lệch tác vụ (tầm quan trọng của từng facet khi tìm bài báo không trùng khít hoàn toàn với việc dự đoán hội nghị). Do đó, bài báo sử dụng **Bảng 2 (Leave-One-Out Ablation)** ngay trên $\mathbf{w}_{\text{Exp B}}^*$ để chẩn đoán định lượng khía cạnh nào chuyển giao tốt và khía cạnh nào nhạy cảm với dịch chuyển thời gian.

---

### Câu hỏi 4: Trong đề tài này có cần chứng minh 5 facets đạt kết quả cao hơn `Full-text` không?

**Trả lời:**
**Không.** Trong một bài báo thuộc thể loại **Nghiên cứu Thực nghiệm có Kiểm soát (*Controlled Empirical Study*)**, bạn không cần (và không nên ép) chứng minh biểu diễn $5$ facets luôn thắng `Full-text` ở mọi tác vụ.

* **Giá trị khoa học của kết quả có điều kiện (*nuanced / negative finding*):** Ở các hội nghị chuẩn IEEE, một phát hiện thực nghiệm trung thực chỉ ra rõ **điều kiện biên nơi biểu diễn đa khía cạnh phát huy tác dụng hoặc suy giảm** kèm cơ chế nhân quả rõ ràng có giá trị học thuật cao hơn việc cố tinh chỉnh để tạo mức chênh lệch nhỏ không có ý nghĩa thống kê.
* **Sức mạnh của bức tranh đối lập hiện có:** Kết quả chỉ ra sự phân kỳ rõ rệt giữa hai tác vụ: ở cấp độ bài báo (Exp B, lượt chạy $384\text{d}$), $5$ facets vượt xa `Full-text` ($0.9124$ vs $0.7104$ $\text{nDCG@10}$), nhưng sang cấp độ hội nghị trên raw `bert-base-uncased` $768\text{d}$, `Full-text` lại dẫn đầu có ý nghĩa thống kê ($52.38\%$ vs $41.07\%\text{--}44.64\%$ Hit@3; $0.4346$ vs $0.3401\text{--}0.3525$ MRR).
* **Lập luận nhân quả bảo vệ trước phản biện:** Bài báo giải thích thuyết phục hiện tượng này qua $3$ nguyên nhân cụ thể: *(1)* raw BERT biểu diễn văn bản liên mạch tốt hơn cụm từ ngắn rời rạc và giữ được văn phong đặc trưng của cộng đồng hội nghị; *(2)* độ thưa cực lớn của `problem` ở `Qwen-8B Raw` ($60.80\%$ Train, $54.17\%$ Test) làm tê liệt trọng số chủ lực $0.40$; và *(3)* bản chất bài toán tìm bài báo đòi hỏi đối sánh kỹ thuật vi mô trong khi chọn hội nghị cần ngữ cảnh lĩnh vực vĩ mô. Điều kiện duy nhất cần hoàn tất để khóa chặt lập luận này là chạy bổ sung lượt Exp B trên đúng `google-bert/bert-base-uncased` $768\text{d}$ để đồng bộ hoàn toàn không gian biểu diễn giữa hai phân hệ.