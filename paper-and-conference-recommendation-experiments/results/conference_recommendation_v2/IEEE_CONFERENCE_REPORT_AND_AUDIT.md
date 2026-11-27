# BÁO CÁO TỔNG HỢP THỰC NGHIỆM EXP A, EXP B & NHÁNH KHUYẾN NGHỊ HỘI NGHỊ CHUẨN IEEE (BERT 768d + KHÓA TRỌNG SỐ EXP B)

> **Dự án NCKH DS300:** *From Facet Extraction to Scientific Recommendation: Evaluating LLM Extractors for Paper Retrieval and Conference Ranking*  
> **Cập nhật:** 27/11/2026 — Lưu trữ đồng bộ: (1) Các bảng số liệu gốc của **Exp A** & **Exp B**, và (2) Kết quả **Nhánh Khuyến nghị Hội nghị** trên **`google-bert/bert-base-uncased`** (`768d`, `mean` pooling, $L_2$-normalized), bộ dữ liệu sạch `602` bài Train ($\le 2015$) / `168` bài Test ($2016–2019$) và **bộ trọng số khóa cứng từ Exp B**: $\mathbf{w}_{\text{Exp B}}^* = (0.40, 0.20, 0.20, 0.10, 0.10)$.

---

## 1. TỔNG HỢP SỐ LIỆU THỰC NGHIỆM EXP A & EXP B ĐỘC LẬP

### 1.1. Thực nghiệm Exp A: Trích xuất 5 Khía cạnh Khoa học (5 Raw LLMs trên Gold Test 60 bài)

Đối soát trực tiếp từ `data/exp_a/final/results/llm_experiment_metrics.csv` và 5 tệp `experiment_summary.json` (giao thức `QLoRA-V-recall`, split `280` Train / `60` Valid / `60` Test tại `data/exp_a/final/reference/splits.json`):

| Mô hình (Raw LLM) | Base Checkpoint & Revision | Checkpoint Chọn | Precision (%) | Recall (%) | Micro-F1 (%) | Macro-F1 (%) | Problem F1 (%) | Task F1 (%) | Method F1 (%) | Dataset F1 (%) | Contrib F1 (%) | TP / FP / FN | Fallback | Thời gian Exp A (s) |
|---|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|---:|
| **Gemma-9B (Raw)** | `google/gemma-2-9b-it` (`11c9b309`) | `checkpoint-105` | **67.45** | 68.92 | **68.18** | **70.39** | **64.24** | **75.43** | 71.75 | 84.51 | **56.00** | 346 / 167 / 156 | 0 | 20,145.94 |
| **Qwen-8B (Raw)** | `Qwen/Qwen3-8B` (Corpus Gen) | `checkpoint-105` | 63.17 | **70.72** | 66.73 | 67.67 | 61.54 | 68.00 | **74.01** | 78.95 | 55.85 | 355 / 207 / 147 | 3 | 17,510.97 |
| **Llama-8B (Raw)** | `meta-llama/Llama-3.1-8B-Instruct` (`0e9e39f2`) | `checkpoint-105` | 63.51 | 65.54 | 64.51 | 65.28 | 48.00 | 65.56 | 73.57 | 84.51 | 54.76 | 329 / 189 / 173 | 1 | 13,466.27 |
| **Qwen-14B (Raw)** | `Qwen/Qwen3-14B` (`40c06982`) | `checkpoint-70` | 61.21 | 66.33 | 63.67 | 65.62 | 56.29 | 63.77 | 73.14 | **85.71** | 49.21 | 333 / 211 / 169 | 0 | 20,830.10 |
| **Qwen-4B (Raw)** | `Qwen/Qwen3-4B` (`1cfa9a72`) | `checkpoint-105` | 59.32 | 62.75 | 60.99 | 62.93 | 54.22 | 62.00 | 67.44 | 80.00 | 50.98 | 315 / 216 / 187 | 2 | 11,833.21 |

*(Đối chứng chưa fine-tune `base-V-recall` của `Qwen-8B`: `Precision = 22.55%`, `Recall = 30.28%`, `Micro-F1 = 25.85%`, `Macro-F1 = 25.97%`.)*

**Độ phủ & Thống kê Facet của 5 Raw LLMs trên bộ chia sạch Hội nghị (`602` Train / `168` Test):**

| Nguồn Raw LLM | Đường dẫn tệp trong Repo | Tổng bản ghi | Phủ Train (`602`) | Phủ Test (`168`) | Số bài có Facet trên `168` Test (`P / T / M / D / C`) | Phủ TB Test (%) | Số từ TB / bài Test |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Qwen-8B (Raw)** | `data/exp_a/generated/facets_silver.jsonl` | `4.210` | **`602 / 602`** (`72.06%`) | **`168 / 168`** | `77 / 166 / 165 / 47 / 165` | `73.81%` | `39.17` |
| **Gemma-9B (Raw)** | `data/conference_recommendation_dataset/generated_facets/Gemma9B/facets_silver.jsonl` | `186` | `0 / 602` | **`168 / 168`** | `103 / 168 / 168 / 43 / 168` | `77.38%` | `32.93` |
| **Qwen-14B (Raw)** | `data/conference_recommendation_dataset/generated_facets/Qwen14B/facets_silver.jsonl` | `186` | `0 / 602` | **`168 / 168`** | `112 / 168 / 167 / 43 / 168` | `78.33%` | `32.21` |
| **Llama-8B (Raw)** | `data/conference_recommendation_dataset/generated_facets/Llama8B/facets_silver.jsonl` | `186` | `0 / 602` | **`168 / 168`** | `120 / 168 / 167 / 45 / 168` | `79.52%` | `33.93` |
| **Qwen-4B (Raw)** | `data/conference_recommendation_dataset/generated_facets/Qwen4B/facets_silver.jsonl` | `186` | `0 / 602` | **`168 / 168`** | `95 / 168 / 167 / 36 / 167` | `75.36%` | `32.92` |

*(Trên `602` bài Train lịch sử, `Qwen-8B (Raw)` có số bài phủ từng facet: `problem=236`, `task=583`, `method=582`, `dataset=176`, `contribution=592`; trung bình `39.88` từ/bài.)*

---

### 1.2. Thực nghiệm Exp B: Xếp hạng Bài báo Khoa học (`data/exp_b/ranking/`)

- **Ba phương pháp chấm điểm cặp $S(q, c)$ ($c \ne q$) với tập khía cạnh chung $V(q, c) = \{f \mid m_f(q)=1 \land m_f(c)=1\}$:**
  1. `Method 1 (Full-text)`: $S_{\text{full}}(q, c) = \langle \mathbf{e}_{\text{full}}(q), \mathbf{e}_{\text{full}}(c) \rangle$.
  2. `Method 2 (Equal-weight Facet)`: $S_{\text{equal}}(q, c) = \frac{1}{|V(q,c)|}\sum_{f \in V(q,c)} s_f(q, c)$ (loại cặp có $V(q,c)=\emptyset$).
  3. `Method 3 (Weighted Facet)`: $S_{\text{weighted}}(q, c) = \frac{\sum_{f \in V(q,c)} w_f s_f(q, c)}{\sum_{f \in V(q,c)} w_f}$ (tái chuẩn hóa mẫu số động, loại cặp có $\sum_{f \in V(q,c)} w_f = 0$).
- **Kết quả trên DEV (`15` queries) & TEST (`35` queries) của Exp B** *(Lưu ý kiểm toán: tệp cấu hình `ranking_config.json` quy định `google-bert/bert-base-uncased` 768d, nhưng thư mục `intermediate/bert_base_uncased/` hiện chưa có trên đĩa; các tệp kết quả hiện hành trong `data/exp_b/ranking/output/` được tính trên cache MiniLM 384d của lượt chạy trước và sẽ được bổ sung lượt BERT 768d sau)*:

| Tập | Phương pháp Ranking | nDCG@10 (Chính) | nDCG@5 | P@5 ($\ge 2$) | P@10 ($\ge 2$) | Recall@10 | Recall@20 | MRR | Judged Cov@10 |
|:---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **DEV** (`15`q) | Method 1: Full-text Embedding | 0.6385 | 0.6520 | 0.0133 | 0.0333 | 0.0088 | 0.0602 | 0.0750 | 100.0% |
| **DEV** (`15`q) | Method 2: Equal-weight (`0.2 x 5`) | 0.9019 | 0.8710 | 0.0800 | 0.0733 | 0.0602 | 0.1152 | 0.1056 | 100.0% |
| **DEV** (`15`q) | **Method 3a: Weighted A (`0.4/0.2/0.2/0.1/0.1`)** | **0.9264** | **0.9072** | **0.0933** | **0.0933** | **0.1064** | **0.1409** | **0.1556** | 100.0% |
| **DEV** (`15`q) | Method 3b: Weighted B (`0.3/0.25/0.25/0.1/0.1`) | 0.9226 | 0.8965 | 0.0800 | **0.0933** | **0.1064** | 0.1187 | 0.1429 | 100.0% |
| **TEST** (`35`q) | Method 1: Full-text Embedding | 0.7104 | 0.6757 | 0.1200 | 0.1114 | 0.2801 | 0.3023 | 0.3029 | 100.0% |
| **TEST** (`35`q) | Method 2: Equal-weight (`0.2 x 5`) | 0.8567 | 0.8280 | 0.1714 | 0.1371 | 0.3607 | 0.4391 | 0.3685 | 100.0% |
| **TEST** (`35`q) | **Method 3a: Weighted A (Locked $\mathbf{w}_{\text{Exp B}}^*$)** | **0.9124** | **0.8877** | 0.2286 | **0.1829** | **0.4821** | **0.5210** | **0.4236** | 100.0% |
| *(TEST)* | *Method 3b: Weighted B* | *0.8929* | *0.8808* | ***0.2343*** | *0.1600* | *0.4231* | *0.5132* | *0.4105* | *100.0%* |

- **Bộ trọng số khóa chuyển giao sang nhánh Hội nghị:** $\mathbf{w}_{\text{Exp B}}^* = (\text{problem}: 0.40,\ \text{task}: 0.20,\ \text{method}: 0.20,\ \text{dataset}: 0.10,\ \text{contribution}: 0.10)$.

---

## 2. THIẾT LẬP GIAO THỨC NHÁNH HỘI NGHỊ & KIỂM SOÁT CHỐNG RÒ RỈ (PROVENANCE & ZERO DATA LEAKAGE)

| Thành phần | Giá trị Chuẩn hóa & Kiểm định |
|---|---|
| **Bộ chia thời gian sạch** | `data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019_clean/` (`602` Train $\le 2015$, `168` Test $2016–2019$, `30` hội nghị; $0$ bài trùng với tập `train + valid` của Adapter Exp A). |
| **Phân tầng quy mô hội nghị** | `Head` ($\ge 20$ Train): `8` hội nghị (`433` Train / `119` Test); `Mid` ($5–19$ Train): `16` hội nghị (`147` Train / `40` Test); `Tail` ($<5$ Train): `6` hội nghị (`22` Train / **`n = 9` Test**: `CONF_ACM_MM`, `CONF_ICLR`, `CONF_ICORE_1123`, `CONF_ICORE_2311`, `CONF_ICORE_642`, `CONF_WSDM`). |
| **Nguồn dữ liệu Facet** | Tuyệt đối **không dùng `validated_silver.jsonl`**. Chỉ mục lịch sử Train (`602` bài) cố định bằng **`Qwen-8B (Raw)`** (`data/exp_a/generated/facets_silver.jsonl`, độ phủ TB `72.06%`); tập Test (`168` bài) đánh giá trên `Qwen-8B (Raw)` (Bảng 1–2) và hoán đổi 5 Raw LLMs (`Qwen-8B`, `Gemma-9B`, `Qwen-14B`, `Llama-8B`, `Qwen-4B`) (Bảng 3). |
| **Encoder & Tiền xử lý** | `google-bert/bert-base-uncased` (`768d`, `mean` pooling, `np.float32`, $L_2$-normalized). Toàn văn giữ nguyên `"{title}. {abstract}"`, từng facet nối bằng `"; "`. |
| **Chuyển giao Trọng số Khóa cứng (Đóng góp C2)** | Khóa cứng 100% trọng số $\mathbf{w}_{\text{Exp B}}^* = (\text{problem}: 0.40,\ \text{task}: 0.20,\ \text{method}: 0.20,\ \text{dataset}: 0.10,\ \text{contribution}: 0.10)$ theo cơ chế *Zero-Shot Cross-Task Transfer* kèm **tái chuẩn hóa mẫu số động** $S(q, p) = \frac{\sum_{f \in V(q,p)} w_f s_f(q,p)}{\sum_{f \in V(q,p)} w_f}$ (loại cặp có $\sum_{f \in V(q,p)} w_f = 0$). |
| **Chọn siêu tham số & Khóa băm** | Chỉ tối ưu tham số Tầng Tổng hợp Hội nghị ($k \in \{5,10,15,20,25,30\}$, $\tau \in \{0.02,0.05,0.10,0.20\}$, $\alpha \in \{0.5,1.0\}$, $m \in \{1,2,3\}$) qua 5-Fold Stratified CV (`seed=42`, `ddof=1`). Mã băm artifact gốc: `4ca690624de67a7b698508103badea88915d9d11735b36766ee683b871037d12`. |
| **Môi trường Thực nghiệm** | GPU `NVIDIA GeForce RTX 4060 Laptop`, `torch==2.5.1+cu121`, `sentence-transformers==3.4.1`, `numpy==2.2.6`, `scipy==1.15.3`. |

---

## 3. BẢNG 1: HIỆU NĂNG XẾP HẠNG HỘI NGHỊ CHÍNH (MAIN RESULTS — RQ2)

Bảng 1 đối chiếu 3 phương pháp chấm điểm cặp kế thừa trực tiếp từ Exp B (`Full-text`, `Equal-weight Facet`, `Exp B Locked Weighted Facet` với $\mathbf{w}_{\text{Exp B}}^* = 0.40/0.20/0.20/0.10/0.10$) kết hợp với 4 cơ chế tổng hợp điểm hội nghị trên `168` bài Test sạch ($2016–2019$).

*(Ký hiệu `†` chỉ sự khác biệt có ý nghĩa thống kê với $p_{\text{raw}} < 0.05$ so với `Method 1: Full-text BERT` trên cùng cơ chế tổng hợp qua **McNemar Exact Test** cho `Hit@3` và **Paired Permutation Test 10.000 lần** cho `MRR`; ký hiệu `‡` chỉ cấu hình vẫn giữ ý nghĩa thống kê $p_{\text{adj}} < 0.05$ sau hiệu chỉnh **Holm-Bonferroni** trên $8$ phép thử so sánh.)*

| Phương pháp | Tổng hợp (Tham số chọn CV) | Train CV Hit@3 | Test Hit@1 | Test Hit@3 | Test Hit@5 | Test MRR | Test Macro-Hit@3 [95% CI] | Tail Hit@3 (n=9, 6v) | Disc Hit@1 |
|---|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| **Random Baseline (30 venues)** | — | — | 3.33% | 10.00% | 16.67% | 0.1332 | — | — | — |
| **Method 1: Full-text BERT** | `Sum-kNN` ($k=30$) | 51.50% ± 3.87% | **25.60%** | 50.00% | **68.45%** | **0.4346** | 24.02% [20.1, 32.8] | 0.00% | **75.00%** |
| **Method 1: Full-text BERT** | `Temp-Softmax` ($k=30, \tau=0.02$) | **51.99% ± 3.16%** | 23.81% | **52.38%** | **68.45%** | 0.4302 | 26.66% [22.5, 36.2] | 0.00% | 72.62% |
| **Method 1: Full-text BERT** | `Prior-Norm` ($k=30, \tau=0.20, \alpha=0.5$) | 42.87% ± 5.16% | 17.86% | 45.24% | 58.33% | 0.3651 | **32.49%** [26.1, 42.9] | **11.11%** | 60.12% |
| **Method 1: Full-text BERT** | `Per-Venue Top-m` ($m=3$) | 49.84% ± 3.82% | 24.40% | **52.38%** | 67.26% | 0.4289 | 29.14% [25.0, 39.7] | 0.00% | 71.43% |
| **Method 2: Equal-weight (0.2 x 5)** | `Sum-kNN` ($k=25$) | 44.18% ± 3.53% | 14.29% | 44.05% | 58.93% | 0.3442†‡ | 15.12% [13.0, 23.0] | 0.00% | 66.07% |
| **Method 2: Equal-weight (0.2 x 5)** | `Temp-Softmax` ($k=25, \tau=0.20$) | 44.18% ± 3.53% | 14.88% | **44.64%** | 58.93% | 0.3476†‡ | 15.47% [13.3, 23.5] | 0.00% | 66.07% |
| **Method 2: Equal-weight (0.2 x 5)** | `Prior-Norm` ($k=30, \tau=0.20, \alpha=0.5$) | 29.91% ± 5.96% | 10.12% | 29.76%†‡ | 43.45% | 0.2701†‡ | **15.49%** [11.7, 24.5] | **11.11%** | 51.19% |
| **Method 2: Equal-weight (0.2 x 5)** | `Per-Venue Top-m` ($m=3$) | 43.36% ± 3.44% | 16.67% | 41.07%† | 60.12% | 0.3522†‡ | 13.72% [12.0, 20.6] | 0.00% | 63.69% |
| **Method 3: Exp B Locked Weighted ($\mathbf{w}_{\text{Exp B}}^*$)** | `Sum-kNN` ($k=25$) | **44.68% ± 3.09%** | 15.48% | 41.07%† | 55.95% | 0.3401†‡ | 15.03% [12.5, 22.9] | 0.00% | 64.88% |
| **Method 3: Exp B Locked Weighted ($\mathbf{w}_{\text{Exp B}}^*$)** | `Temp-Softmax` ($k=25, \tau=0.20$) | **44.68% ± 3.09%** | 15.48% | 41.07%† | 55.95% | 0.3404†‡ | 15.03% [12.5, 22.9] | 0.00% | 64.88% |
| **Method 3: Exp B Locked Weighted ($\mathbf{w}_{\text{Exp B}}^*$)** | `Prior-Norm` ($k=30, \tau=0.10, \alpha=0.5$) | 28.57% ± 4.72% | 10.71% | 22.02%†‡ | 41.67% | 0.2546†‡ | 10.90% [7.5, 18.3] | 0.00% | 48.81% |
| **Method 3: Exp B Locked Weighted ($\mathbf{w}_{\text{Exp B}}^*$)** | `Per-Venue Top-m` ($m=3$) | 40.53% ± 2.05% | **17.26%** | 41.07%† | **60.12%** | **0.3525†‡** | 14.05% [12.2, 20.9] | 0.00% | 62.50% |

### Phân tích Chi tiết Bảng 1 (Kiểm chứng Thống kê & Phản ánh Cơ chế)
1. **Phân kỳ Giữa Truy xuất Bài báo (Exp B) và Xếp hạng Hội nghị (RQ2):**
   - Trong không gian `google-bert/bert-base-uncased` (768d) không tinh chỉnh, **`Method 1: Full-text BERT` vượt trội đáng kể so với cả `Equal-weight` lẫn `Exp B Locked Weighted`** ở toàn bộ các chỉ số chính (`Test Hit@3` lên tới `52.38%`, `Test MRR` lên tới `0.4346`, `Discipline Hit@1 = 75.00%`).
   - Toàn bộ $8/8$ cặp so sánh về `Test MRR` giữa phương pháp Facet và `Full-text` đều đạt ý nghĩa thống kê vững chắc kể cả sau hiệu chỉnh **Holm-Bonferroni** ($p_{\text{adj}} \in [0.0016, 0.0290]$).
   - **Nguyên nhân:** Việc nén toàn văn thành các cụm từ rời rạc trong 5 facets làm mất văn phong học thuật và ngữ cảnh câu hoàn chỉnh đặc trưng của từng hội nghị; đồng thời `Qwen-8B (Raw)` có tỷ lệ khuyết `problem` cao (`54.17%` trên Test, `60.80%` trên Train), khiến trọng số lớn nhất $w_{\text{problem}} = 0.40$ của $\mathbf{w}_{\text{Exp B}}^*$ chỉ kích hoạt trên chưa đầy một nửa số cặp bài báo.
2. **So sánh `Method 3 (Exp B Locked Weighted)` vs. `Method 2 (Equal-weight)`:**
   - Trên **Train CV**, $\mathbf{w}_{\text{Exp B}}^*$ (`44.68%`) nhỉnh hơn `Equal-weight` (`44.18%`, `+0.50 pp`). Tuy nhiên trên **Test $2016–2019$**, $\mathbf{w}_{\text{Exp B}}^*$ đạt `Hit@1` nhỉnh hơn (`15.48%–17.26%` vs `14.29%–16.67%`) nhưng thua nhẹ ở `Hit@3` (`41.07%` vs `44.05%–44.64%`). Sự suy giảm từ Train CV (`44.68%`) xuống Test (`41.07%`) phản ánh độ nhạy của trọng số dồn `0.40` vào `problem` trước dịch chuyển từ vựng thời gian.
   - **Ghi chú đối chứng Overfitting khi tune lại trọng số (Discussion):** Một thử nghiệm đối chứng cho thấy nếu cố dò lưới trọng số mới ngay trên 602 bài Train Hội nghị, cấu hình thắng CV đạt tới `45.52%` CV Hit@3 nhưng lại rớt **Test MRR xuống còn `0.3291`–`0.3296`** và **Test Hit@1 xuống `14.88%`**, kém hơn cả $\mathbf{w}_{\text{Exp B}}^*$ (`0.3401`–`0.3525` MRR, `15.48%–17.26%` Hit@1). Điều này khẳng định tính hợp lý của việc khóa cứng $\mathbf{w}_{\text{Exp B}}^*$ thay vì quá khớp trọng số trên tập Train Hội nghị nhỏ.
3. **Phân tích Tầng Quy mô (`Head` / `Mid` / `Tail`):**
   - `Sum-kNN` & `Temp-Softmax` tập trung mạnh vào nhóm **`Head` (`8` hội nghị, `119` bài Test)**: đạt `63.87%–64.71%` Hit@3 ở `Full-text` và `54.62%` ở $\mathbf{w}_{\text{Exp B}}^*$, nhưng hoàn toàn bỏ qua nhóm **`Tail` (`6` hội nghị hiếm, `n = 9` bài Test)**: `0.00%` Hit@3.
   - `Prior-Norm` phá vỡ thiên lệch tần suất lớp ($N_v^{-\alpha}$), giúp nâng `Mid Hit@3` của `Full-text` lên `37.50%`, `Tail Hit@3` lên **`11.11%`** (và `Macro-Hit@3` đạt đỉnh **`32.49%`**), đồng thời đưa `Tail Hit@3` của `Equal-weight` lên `11.11%`; tuy nhiên làm sụt giảm mạnh `Head Hit@3` trên $\mathbf{w}_{\text{Exp B}}^*$ (`54.62%` $\rightarrow$ `26.89%`).
   - `Per-Venue Top-m` ($m=3$) giúp `Method 3` ($\mathbf{w}_{\text{Exp B}}^*$) đạt điểm Test cao nhất ở cả `Hit@1` (**`17.26%`**), `Hit@5` (**`60.12%`**) và `MRR` (**`0.3525`**).

---

## 4. BẢNG 2: KHỬ KHÍA CẠNH (`LEAVE-ONE-OUT`), DỊCH CHUYỂN THỜI GIAN & `EXP C3` TRÊN $\mathbf{w}_{\text{Exp B}}^*$

Thực nghiệm chạy trực tiếp trên cấu hình thắng CV của `Method 3: Exp B Locked Weighted Facet` (**$\mathbf{w}_{\text{Exp B}}^* = [0.40, 0.20, 0.20, 0.10, 0.10]$**, `Sum-kNN`, $k=25$). Mỗi biến thể Leave-One-Out gán đúng 1 trọng số về $0$ và tái chuẩn hóa 4 phần tử còn lại có tổng bằng $1.0$.

| Biến thể | Vector Trọng số Thực dùng $(P, T, M, D, C)$ | Train CV ($\le 2015$) Hit@3 | $\Delta$ CV (pp) | Test ($2016–2019$) Hit@3 | $\Delta$ Test (pp) | Test MRR | $\Delta$ MRR | Cross-Disc Error (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Full 5 Facets (Baseline)** | $(0.400, 0.200, 0.200, 0.100, 0.100)$ | 44.68% ± 3.09% | +0.00 | 41.07% | +0.00 | 0.3401 | +0.0000 | 35.12% |
| `w/o Problem` | $(0.000, 0.333, 0.333, 0.167, 0.167)$ | 45.34% ± 2.50% | +0.67 | **42.26%** | **+1.19** | 0.3495 | +0.0094 | 34.52% |
| `w/o Task` | $(0.500, 0.000, 0.250, 0.125, 0.125)$ | **41.02% ± 4.66%** | **-3.66** | **42.26%** | **+1.19** | **0.3708** | **+0.0308** | 33.33% |
| `w/o Method` | $(0.500, 0.250, 0.000, 0.125, 0.125)$ | 43.36% ± 1.87% | -1.32 | **42.26%** | **+1.19** | 0.3340 | -0.0061 | **31.55%** |
| `w/o Dataset` | $(0.444, 0.222, 0.222, 0.000, 0.111)$ | **45.68% ± 2.22%** | +1.00 | 41.67% | +0.60 | 0.3432 | +0.0031 | 35.12% |
| `w/o Contribution` | $(0.444, 0.222, 0.222, 0.111, 0.000)$ | 41.53% ± 2.35% | -3.14 | **38.69%** | **-2.38** | 0.3396 | -0.0005 | 32.14% |
| **Zero-Imputation Policy (Exp C3)** | $(0.400, 0.200, 0.200, 0.100, 0.100)$ (mẫu số $=1.0$) | 43.01% ± 3.01% | -1.66 | **38.10%** | **-2.98** | **0.3025** | **-0.0376** | **35.71%** |

### Phân tích Bảng 2 (Cơ chế Khía cạnh, Dịch chuyển Thời gian & `Exp C3`)
1. **Kiểm chứng Tuyệt đối Cơ chế Tái chuẩn hóa Mẫu số Động (`Exp C3`):**
   - Khi chuyển từ `Dynamic Renormalization` sang `Zero-Imputation` (gán `0.0` cho facet khuyết và giữ mẫu số $= 1.0$), hiệu năng suy giảm đồng loạt trên cả hai giai đoạn: **Train CV giảm `-1.66 pp` (`44.68%` $\rightarrow$ `43.01%`)**, **Test Hit@3 sụt `-2.98 pp` (`41.07%` $\rightarrow$ `38.10%`)**, **Test MRR giảm mạnh `-0.0376` (`0.3401` $\rightarrow$ `0.3025`)** và lỗi chéo ngành tăng lên `35.71%`.
   - Kiểm tra riêng phân nhóm **`121` bài Test khuyết `dataset`**: `Dynamic Renormalization` giữ **`Hit@1 = 14.88%`, `Hit@3 = 40.50%`, `Hit@5 = 57.85%`, `MRR = 0.3358`**, vượt trội toàn diện so với `Zero-Imputation` (`Hit@1 = 11.57%`, `Hit@3 = 37.19%`, `Hit@5 = 52.89%`, `MRR = 0.2987`). Điều này bảo vệ hoàn toàn thiết kế toán học kế thừa từ Exp B.
2. **Đóng góp Bất đối xứng giữa Quá khứ ($\le 2015$) và Tương lai ($2016–2019$):**
   - **`Contribution`** là khía cạnh duy nhất mà khi loại bỏ khiến hiệu năng **sụt giảm trên cả hai tập** (`-3.14 pp` trên CV, `-2.38 pp` trên Test), chứng tỏ trong cấu trúc trọng số $\mathbf{w}_{\text{Exp B}}^*$, `Contribution` giúp bổ khuyết thông tin cho các bài báo bị thiếu `Problem` hoặc `Dataset`.
   - **`Task` và `Method`** đóng vai trò giữ ổn định thứ hạng đầu bảng trên tập lịch sử (`w/o Task` tụt CV mạnh nhất `-3.66 pp`; `w/o Method` tụt CV `-1.32 pp` và tụt Test MRR `-0.0061`), nhưng sang giai đoạn $2016–2019$ bị nhiễu nhẹ bởi sự dịch chuyển thuật ngữ mới (loại bỏ từng facet riêng lẻ giúp tăng nhẹ `Hit@3`, riêng `w/o Method` giảm `Cross-Disc Error` xuống mức thấp nhất `31.55%`).
   - **`Problem`** khi bỏ giúp loại bỏ bớt tác động của việc dồn `0.40` trọng số vào một trường có độ phủ thấp (`45.83%` trên Test), đẩy Test Hit@3 lên `42.26%` (`+1.19 pp`).

---

## 5. BẢNG 3: ĐÁNH GIÁ CHÉO 5 RAW LLMS (`QUERY-SIDE SUBSTITUTION` — RQ3, RQ4 & `EXP C4`)

Kịch bản: Cố định kho chỉ mục Train `602` bài từ **`Qwen-8B (Raw)`**; lần lượt thay 5 Raw LLMs ở phía truy vấn trên `168` bài Test sạch với hai đường cơ sở Facet chuẩn:
- `Method 2: Equal-weight Facet (0.2 x 5)` tại điểm vận hành `Temp-Softmax` ($k=25, \tau=0.20$)
- `Method 3: Exp B Locked Weighted Facet` ($\mathbf{w}_{\text{Exp B}}^* = 0.40/0.20/0.20/0.10/0.10$) tại điểm vận hành `Sum-kNN` ($k=25$)

*(Độ trễ `BERT Encode (ms/p)` được đo chuẩn hóa riêng trên GPU RTX 4060 sau bước CUDA warm-up, cố định `batch_size=16`, chạy trực tiếp trên toàn bộ các facet khác rỗng của đúng `168` bài Test không qua cache đĩa. `Exp A Wall (s)` là tổng thời gian chạy thí nghiệm Exp A trên tập Gold theo `experiment_summary.json`.)*

| Facet Scorer | Raw LLM | Exp A Micro / Macro-F1 (%) | Key Facets F1 (P / T / M) | Test Cov (%) | BERT Encode (ms/p) | Retrieval (ms/q) | Storage (KB/p) | Exp A Wall (s) | Hit@1 | Hit@3 | Hit@5 | MRR | Macro-Hit@3 | W/T/L vs Qwen-8B |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| `Equal-weight` | **Qwen-8B** | 66.73 / 67.67 | 61.5 / 68.0 / **74.0** | 73.81% | 3.29 | 0.25 | 15.01 | 17,511 | 14.88% | 44.64% | 58.93% | 0.3476 | 15.47% | 0 / 168 / 0 |
| `Equal-weight` | **Gemma-9B** | **68.18 / 70.39** | **64.2 / 75.4** / 71.8 | 77.38% | 3.18 | 0.27 | 15.01 | 20,146 | 17.86% | 43.45% | 55.95% | 0.3535 | 14.43% | 63 / 36 / 69 |
| `Equal-weight` | **Qwen-14B** | 63.67 / 65.62 | 56.3 / 63.8 / 73.1 | 78.33% | 3.24 | 0.26 | 15.01 | 20,830 | 19.64% | 39.88% | 52.38% | 0.3588 | 12.37% | 57 / 45 / 66 |
| `Equal-weight` | **Llama-8B** | 64.51 / 65.28 | 48.0 / 65.6 / 73.6 | **79.52%** | 3.28 | 0.25 | 15.01 | 13,466 | **21.43%** | 42.86% | 53.57% | **0.3732** | 12.26% | 59 / 46 / 63 |
| `Equal-weight` | **Qwen-4B** | 60.99 / 62.93 | 54.2 / 62.0 / 67.4 | 75.36% | **3.00** | 0.25 | 15.01 | **11,833** | 19.05% | **45.83%** | **59.52%** | 0.3714 | **20.34%** | 55 / 50 / 63 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Qwen-8B** | 66.73 / 67.67 | 61.5 / 68.0 / **74.0** | 73.81% | 3.29 | 0.25 | 15.01 | 17,511 | 15.48% | 41.07% | 55.95% | 0.3401 | 15.03% | 0 / 168 / 0 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Gemma-9B** | **68.18 / 70.39** | **64.2 / 75.4** / 71.8 | 77.38% | 3.18 | 0.25 | 15.01 | 20,146 | 17.26% | **44.64%** | 55.95% | 0.3555 | 16.51% | 63 / 42 / 63 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Qwen-14B** | 63.67 / 65.62 | 56.3 / 63.8 / 73.1 | 78.33% | 3.24 | 0.25 | 15.01 | 20,830 | 19.64% | 42.86% | 52.98% | 0.3581 | 14.52% | 63 / 41 / 64 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Llama-8B** | 64.51 / 65.28 | 48.0 / 65.6 / 73.6 | **79.52%** | 3.28 | 0.27 | 15.01 | 13,466 | **20.83%** | 44.05% | 56.55% | 0.3759 | 13.80% | **71** / 39 / 58 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | **Qwen-4B** | 60.99 / 62.93 | 54.2 / 62.0 / 67.4 | 75.36% | **3.00** | 0.27 | 15.01 | **11,833** | **20.83%** | **44.64%** | **57.14%** | **0.3777** | **18.39%** | 68 / 36 / 64 |

### Kiểm định Tương quan Hạng Chính xác (`Exact Permutation`, $n = 5$ mô hình, $5! = 120$ hoán vị, $p_{\min} = 0.0167$)

| Cấu hình Facet | Cặp Biến Đối chiếu (Exp A $\leftrightarrow$ Hội nghị) | Spearman $\rho$ | $p_{\text{exact}}$ (Spearman) | Kendall $\tau$ | $p_{\text{exact}}$ (Kendall) |
|---|---|---:|---:|---:|---:|
| `Equal-weight` | `Macro-F1` vs `Test Hit@3` | -0.2000 | 0.7833 | -0.2000 | 0.8167 |
| `Equal-weight` | `Macro-F1` vs `Test MRR` | -0.8000 | 0.1333 | -0.6000 | 0.2333 |
| `Equal-weight` | `Problem-F1` vs `Test MRR` | -0.9000 | 0.0833 | -0.8000 | 0.0833 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | `Macro-F1` vs `Test Hit@3` | -0.2052 | 0.7333 | -0.3162 | 0.6333 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | `Macro-F1` vs `Test MRR` | **-0.9000** | 0.0833 | **-0.8000** | 0.0833 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | `Method-F1` vs `Test Hit@3` | -0.8721 | 0.1000 | -0.7379 | 0.1333 |
| **$\mathbf{w}_{\text{Exp B}}^*$ Weighted** | `Micro-F1` vs `Test MRR` | -0.8000 | 0.1333 | -0.6000 | 0.2333 |

### Phân tích Bảng 3 (`Query-Side Substitution`, `Exact Correlation` & `Exp C4`)
1. **Không tồn tại tương quan đồng biến giữa F1 nội tại (Exp A) và Hiệu năng Khuyến nghị Hội nghị (RQ4):**
   - Mặc dù **`Gemma-9B (Raw)`** dẫn đầu Exp A (`Macro-F1 = 70.39%`), **`Qwen-4B (Raw)`** (mô hình có F1 thấp nhất: `62.93%`) lại đạt `Hit@3` cao nhất trên cả hai cấu hình (`45.83%` ở `Equal-weight`, **`44.64%`** đồng hạng `Gemma-9B` ở $\mathbf{w}_{\text{Exp B}}^*$), đồng thời dẫn đầu tuyệt đối về **`MRR = 0.3777`**, **`Hit@5 = 57.14%`** và **`Macro-Hit@3 = 18.39%–20.34%`** trên $\mathbf{w}_{\text{Exp B}}^*$.
   - Với $n = 5$ mô hình ($p_{\text{exact}}$ hai phía tối thiểu $= 0.0167$), mọi hệ số tương quan giữ $\rho \le 0$ (`Macro-F1 vs MRR` đạt $\rho = -0.9000, p_{\text{exact}} = 0.0833$), khẳng định chắc chắn rằng **chỉ số F1 trích xuất tốt hơn không đảm bảo hiệu năng xếp hạng hội nghị cao hơn** dưới kịch bản hoán đổi phía truy vấn. Tuy nhiên, không có cặp LLM nào vượt qua ngưỡng khác biệt có ý nghĩa thống kê từng cặp ($p_{\text{mc}} \in [0.1516, 0.8506]$; $p_{\text{perm}} \in [0.0812, 0.7958]$).
2. **Độ nhạy với Khả năng Phủ `Problem` trên $\mathbf{w}_{\text{Exp B}}^*$:**
   - Khi chuyển từ `Qwen-8B` (độ phủ `problem` trên Test chỉ `45.83%`, tổng độ phủ `73.81%`) sang 4 bộ trích xuất còn lại (`Gemma-9B`, `Qwen-14B`, `Llama-8B`, `Qwen-4B`, có độ phủ `problem` `56.55%–71.43%` và tổng độ phủ `75.36%–79.52%`), hiệu năng của **$\mathbf{w}_{\text{Exp B}}^*$ cải thiện đồng loạt ở cả 4 LLM thay thế**: `Hit@1` tăng từ `15.48%` lên `17.26%–20.83%`, `Hit@3` tăng từ `41.07%` lên `42.86%–44.64%`, `MRR` tăng từ `0.3401` lên `0.3555–0.3777` (với `Llama-8B` đạt `71` thắng / `58` thua và `Qwen-4B` đạt `68` thắng / `64` thua so với `Qwen-8B`).
3. **Hiệu năng Hệ thống (`Exp C4`):**
   - Lưu trữ 5 Facets BERT 768d tiêu tốn **`15.01 KB/bài`** (gấp `5.0x` so với `3.00 KB/bài` của `Full-text` 1 vector 768d).
   - Sau warm-up CUDA với `batch_size=16`, tốc độ encode BERT của 5 LLMs trên `168` bài Test hết sức đồng đều (**`3.00–3.29 ms/bài`**), và thời gian đối sánh + tổng hợp 30 hội nghị chỉ **`0.25–0.27 ms/query`**. Xét trên đường biên chi phí–hiệu quả, **`Qwen-4B`** là điểm vận hành tối ưu ở phía truy vấn.

---

## 6. ĐỘ NHẠY THEO SỐ LÁNG GIỀNG $k$ TRÊN TRAIN CV ($\le 2015$)

Đối chiếu trực tiếp độ nhạy `Train CV Hit@3` và `Train CV MRR` theo $k \in \{5, 10, 15, 20, 25, 30\}$ với `Sum-kNN`:

| Phương pháp | $k=5$ (CV Hit@3 / MRR) | $k=10$ | $k=15$ | $k=20$ | $k=25$ | $k=30$ |
|---|---:|---:|---:|---:|---:|---:|
| **`Method 1: Full-text BERT`** | 41.05% / 0.3570 | 45.86% / 0.3816 | 51.17% / 0.4055 | 50.00% / 0.4092 | 50.50% / **0.4213** | **51.50%** / 0.4182 |
| **`Method 2: Equal-weight (0.2 x 5)`** | 30.07% / 0.2667 | 38.54% / 0.3207 | 42.03% / 0.3357 | 43.85% / 0.3598 | **44.18%** / **0.3699** | 43.85% / 0.3692 |
| **`Method 3: Exp B Locked Weighted ($\mathbf{w}_{\text{Exp B}}^*$)`** | 33.39% / 0.2805 | 37.87% / 0.3144 | 39.37% / 0.3424 | 43.35% / 0.3597 | **44.68%** / **0.3732** | 44.52% / 0.3725 |

- **Nhận xét:** Hai phương pháp Facet (`Equal-weight` và $\mathbf{w}_{\text{Exp B}}^*$) đều **đạt đỉnh bão hòa nội tại rõ rệt ở $k^* = 25$** (giảm nhẹ khi lên $k=30$), trái với `Full-text` chạm biên trên tại $k^* = 30$. Tại vùng láng giềng tối ưu ($k=25$), $\mathbf{w}_{\text{Exp B}}^*$ (`44.68%` Hit@3, `0.3732` MRR) vượt `Equal-weight` (`44.18%` Hit@3, `0.3699` MRR) trên Train CV.
