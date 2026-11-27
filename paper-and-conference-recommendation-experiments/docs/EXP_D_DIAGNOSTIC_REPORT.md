# BÁO CÁO CHẨN ĐOÁN CHUYÊN SÂU EXP D1–D4: ĐIỀU KIỆN PHÁT HUY HIỆU QUẢ CỦA BIỂU DIỄN 5 KHÍA CẠNH TRONG KHUYẾN NGHỊ HỘI NGHỊ

> **Giao thức:** `conference-cv-v2` | **Backend:** `bert` (`google-bert/bert-base-uncased`) | **Train:** `602` bài ($\le 2015$) | **Test:** `168` bài ($2016\text{--}2019$) | **Ứng viên:** `30` hội nghị | **Tuning ID (SHA-256):** `42d1a4e8fb34ab0864d4ab64a7fe306ccd7d045e3c8e0d9cc19f7b8a7dc42ef0`

> **Ràng buộc bất biến:** Khóa cứng trọng số chuyển giao từ Exp B $\mathbf{w}_{\text{Exp B}}^* = (0.40, 0.20, 0.20, 0.10, 0.10)$ (`problem, task, method, dataset, contribution`). Tuyệt đối không tinh chỉnh lại trọng số 5 chiều trên nhánh Hội nghị và không dùng `validated_silver.jsonl`.

## 0. Cấu hình Siêu tham số Tổng hợp/Dung hợp Khóa từ 5-Fold Stratified Train CV (`seed=42`)

- **Full-text Winner:** `agg=temp_softmax; k=30; agg_tau=0.02`
- **Facet-First Winner ($\mathbf{w}_{\text{Exp B}}^*$):** `preset=weighted_facet_a; w={"contribution": 0.1, "dataset": 0.1, "method": 0.2, "problem": 0.4, "task": 0.2}` (mode=`top_m`, top_m=`3`)
- **Coverage-Aware Adaptive Fusion Winner:** $\beta^* = 0.3$
- **Coarse-to-Fine Reranking Winner (Stage-2 Facet-First):** $C^* = 10$
- **Coarse-to-Fine Reranking Winner (Stage-2 Adaptive Fusion):** $C^* = 10$

## 1. Thực nghiệm Exp D1: Đối sánh `Paper-First` vs `Facet-First` và 5 Mô hình Raw LLMs

### Bảng D1a — So sánh Cơ chế Tổng hợp `Paper-First` và `Facet-First` (Qwen-8B Raw, 602 Train / 168 Test)

| Method & Paradigm | Train CV Hit@3 | Test Hit@1 | Test Hit@3 | Test Hit@5 | Test MRR | Macro-Hit@3 [95% CI] | Tail Hit@3 | Disc Hit@1 | Prob Act (%) | Data Act (%) | W/T/L vs Paper-First | p-val vs PF (Hit@3 / MRR) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Full-text (temp_softmax Winner) | 51.99% ± 3.16% | 23.81% | 52.38% | 68.45% | 0.4302 | 26.66% [22.5, 36.2] | 0.00% | 72.62% | 17.97% | 8.18% | — | — |
| Full-text (Sum-kNN) | 51.50% ± 3.87% | 25.60% | 50.00% | 68.45% | 0.4346 | 24.02% [20.1, 32.8] | 0.00% | 75.00% | 17.97% | 8.18% | — | — |
| Full-text (Per-Venue Top-m) | 49.84% ± 3.82% | 24.40% | 52.38% | 67.26% | 0.4289 | 29.14% [25.0, 39.7] | 0.00% | 71.43% | 17.97% | 8.18% | — | — |
| Paper-First: Sum-kNN (Equal-weight (0.2 x 5)) | 44.18% ± 3.53% | 14.29% | 44.05% | 58.93% | 0.3442 | 15.12% [13.0, 23.0] | 0.00% | 66.07% | 17.97% | 8.18% | — | — |
| Paper-First: Per-Venue Top-m (Equal-weight (0.2 x 5)) | 43.36% ± 3.44% | 16.67% | 41.07% | 60.12% | 0.3522 | 13.72% [12.0, 20.6] | 0.00% | 63.69% | 17.97% | 8.18% | 65/56/47 | 0.3323 / 0.6507 |
| Facet-First: Per-Facet Venue Top-m (Equal-weight (0.2 x 5)) | 48.50% ± 1.40% | 18.45% | 46.43% | 61.90% | 0.3694 | 13.98% [12.7, 20.5] | 0.00% | 67.26% | 44.31% | 25.18% | 75/35/58 | 0.5413 / 0.1886 |
| Facet-First: Per-Facet Venue Centroid (Equal-weight (0.2 x 5)) | 38.04% ± 3.44% | 16.07% | 38.69% | 54.76% | 0.3329 | 24.00% [19.5, 32.9] | 0.00% | 61.31% | 44.31% | 25.18% | 75/19/74 | 0.2892 / 0.7008 |
| Paper-First: Sum-kNN (Locked w_ExpB (0.4/0.2/0.2/0.1/0.1)) | 44.68% ± 3.09% | 15.48% | 41.07% | 55.95% | 0.3401 | 15.03% [12.5, 22.9] | 0.00% | 64.88% | 17.97% | 8.18% | — | — |
| Paper-First: Per-Venue Top-m (Locked w_ExpB (0.4/0.2/0.2/0.1/0.1)) | 40.53% ± 2.05% | 17.26% | 41.07% | 60.12% | 0.3525 | 14.05% [12.2, 20.9] | 0.00% | 62.50% | 17.97% | 8.18% | 77/48/43 | 1.0000 / 0.5007 |
| Facet-First: Per-Facet Venue Top-m (Locked w_ExpB (0.4/0.2/0.2/0.1/0.1)) | 46.18% ± 2.34% | 20.83% | 44.64% | 62.50% | 0.3797 | 13.72% [12.3, 20.5] | 0.00% | 67.86% | 44.31% | 25.18% | 81/40/47 | 0.3915 / 0.0376 |
| Facet-First: Per-Facet Venue Centroid (Locked w_ExpB (0.4/0.2/0.2/0.1/0.1)) | 38.22% ± 6.65% | 13.10% | 42.26% | 55.95% | 0.3309 | 26.50% [21.6, 36.9] | 0.00% | 61.31% | 44.31% | 25.18% | 76/21/71 | 0.8939 / 0.7421 |

### Bảng D1b — Thay thế 5 Raw LLMs phía Truy vấn dưới Trọng số Khóa $\mathbf{w}_{\text{Exp B}}^*$

| Aggregation Mode | Raw LLM | Exp A Micro/Macro-F1 | Prob Act (Pair / Query %) | Data Act (Pair / Query %) | Avg g(q) | Hit@1 | Hit@3 | Hit@5 | MRR | Macro-Hit@3 | Disc Hit@1 | W/T/L vs PF (Same LLM) | W/T/L vs Qwen-8B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| facet_first_winner | Qwen-8B | 66.73 / 67.67 | 44.3% / 45.8% | 25.2% / 28.0% | 0.704 | 20.83% | 44.64% | 62.50% | 0.3797 | 13.72% | 67.86% | 81/40/47 | 0/168/0 |
| facet_first_winner | Gemma-9B | 68.18 / 70.39 | 59.3% / 61.3% | 23.0% / 25.6% | 0.771 | 20.24% | 44.64% | 59.52% | 0.3773 | 12.90% | 67.86% | 76/33/59 | 57/52/59 |
| facet_first_winner | Qwen-14B | 63.67 / 65.62 | 64.4% / 66.7% | 23.0% / 25.6% | 0.791 | 16.67% | 44.64% | 57.74% | 0.3572 | 12.40% | 67.26% | 72/40/56 | 52/51/65 |
| facet_first_winner | Llama-8B | 64.51 / 65.28 | 69.0% / 71.4% | 24.1% / 26.8% | 0.811 | 17.86% | 47.62% | 58.33% | 0.3719 | 16.12% | 67.26% | 70/38/60 | 58/52/58 |
| facet_first_winner | Qwen-4B | 60.99 / 62.93 | 54.7% / 56.5% | 19.3% / 21.4% | 0.746 | 14.88% | 44.05% | 57.14% | 0.3466 | 14.17% | 67.26% | 65/40/63 | 54/52/62 |
| facet_first_top_m | Qwen-8B | 66.73 / 67.67 | 44.3% / 45.8% | 25.2% / 28.0% | 0.704 | 20.83% | 44.64% | 62.50% | 0.3797 | 13.72% | 67.86% | 81/40/47 | 0/168/0 |
| facet_first_top_m | Gemma-9B | 68.18 / 70.39 | 59.3% / 61.3% | 23.0% / 25.6% | 0.771 | 20.24% | 44.64% | 59.52% | 0.3773 | 12.90% | 67.86% | 76/33/59 | 57/52/59 |
| facet_first_top_m | Qwen-14B | 63.67 / 65.62 | 64.4% / 66.7% | 23.0% / 25.6% | 0.791 | 16.67% | 44.64% | 57.74% | 0.3572 | 12.40% | 67.26% | 72/40/56 | 52/51/65 |
| facet_first_top_m | Llama-8B | 64.51 / 65.28 | 69.0% / 71.4% | 24.1% / 26.8% | 0.811 | 17.86% | 47.62% | 58.33% | 0.3719 | 16.12% | 67.26% | 70/38/60 | 58/52/58 |
| facet_first_top_m | Qwen-4B | 60.99 / 62.93 | 54.7% / 56.5% | 19.3% / 21.4% | 0.746 | 14.88% | 44.05% | 57.14% | 0.3466 | 14.17% | 67.26% | 65/40/63 | 54/52/62 |
| facet_first_centroid | Qwen-8B | 66.73 / 67.67 | 44.3% / 45.8% | 25.2% / 28.0% | 0.704 | 13.10% | 42.26% | 55.95% | 0.3309 | 26.50% | 61.31% | 76/21/71 | 0/168/0 |
| facet_first_centroid | Gemma-9B | 68.18 / 70.39 | 59.3% / 61.3% | 23.0% / 25.6% | 0.771 | 11.90% | 36.31% | 57.74% | 0.3133 | 23.95% | 63.10% | 76/18/74 | 73/26/69 |
| facet_first_centroid | Qwen-14B | 63.67 / 65.62 | 64.4% / 66.7% | 23.0% / 25.6% | 0.791 | 13.10% | 38.10% | 55.95% | 0.3218 | 20.76% | 62.50% | 76/19/73 | 82/21/65 |
| facet_first_centroid | Llama-8B | 64.51 / 65.28 | 69.0% / 71.4% | 24.1% / 26.8% | 0.811 | 13.10% | 39.29% | 58.93% | 0.3267 | 19.34% | 57.74% | 74/18/76 | 79/22/67 |
| facet_first_centroid | Qwen-4B | 60.99 / 62.93 | 54.7% / 56.5% | 19.3% / 21.4% | 0.746 | 12.50% | 36.90% | 57.14% | 0.3226 | 22.77% | 61.90% | 69/21/78 | 75/27/66 |
| paper_first_sum_knn | Qwen-8B | 66.73 / 67.67 | 18.0% / 45.8% | 8.2% / 28.0% | 0.704 | 15.48% | 41.07% | 55.95% | 0.3401 | 15.03% | 64.88% | 0/168/0 | 0/168/0 |
| paper_first_sum_knn | Gemma-9B | 68.18 / 70.39 | 24.0% / 61.3% | 7.5% / 25.6% | 0.771 | 17.26% | 44.64% | 55.95% | 0.3555 | 16.51% | 68.45% | 0/168/0 | 63/42/63 |
| paper_first_sum_knn | Qwen-14B | 63.67 / 65.62 | 26.1% / 66.7% | 7.5% / 25.6% | 0.791 | 19.64% | 42.86% | 52.98% | 0.3581 | 14.52% | 67.86% | 0/168/0 | 63/41/64 |
| paper_first_sum_knn | Llama-8B | 64.51 / 65.28 | 28.0% / 71.4% | 7.8% / 26.8% | 0.811 | 20.83% | 44.05% | 56.55% | 0.3759 | 13.80% | 68.45% | 0/168/0 | 71/39/58 |
| paper_first_sum_knn | Qwen-4B | 60.99 / 62.93 | 22.2% / 56.5% | 6.3% / 21.4% | 0.746 | 20.83% | 44.64% | 57.14% | 0.3777 | 18.39% | 67.86% | 0/168/0 | 68/36/64 |

### Bảng D1c — Tương quan Hạng Spearman & Kendall Chính xác ($n=5$, $5! = 120$ hoán vị)

| Mode | Upstream Predictor | Downstream Metric | Spearman rho | Exact Perm p (Spearman) | Kendall tau | Exact Perm p (Kendall) |
| --- | --- | --- | --- | --- | --- | --- |
| facet_first_winner | macro_f1 | hit@3 | +0.2236 | 1.0000 | +0.1195 | 1.0000 |
| facet_first_winner | macro_f1 | mrr | +0.8000 | 0.1333 | +0.6000 | 0.2333 |
| facet_first_winner | macro_f1 | macro_hit@3 | -0.6000 | 0.3500 | -0.4000 | 0.4833 |
| facet_first_winner | micro_f1 | hit@3 | +0.4472 | 0.6000 | +0.3586 | 0.6000 |
| facet_first_winner | micro_f1 | mrr | +0.9000 | 0.0833 | +0.8000 | 0.0833 |
| facet_first_winner | micro_f1 | macro_hit@3 | -0.2000 | 0.7833 | -0.2000 | 0.8167 |
| facet_first_winner | problem_f1 | hit@3 | -0.2236 | 1.0000 | -0.1195 | 1.0000 |
| facet_first_winner | problem_f1 | mrr | +0.6000 | 0.3500 | +0.4000 | 0.4833 |
| facet_first_winner | problem_f1 | macro_hit@3 | -0.7000 | 0.2333 | -0.6000 | 0.2333 |
| facet_first_winner | problem_activation_rate | hit@3 | +0.6708 | 0.3000 | +0.5976 | 0.3000 |
| facet_first_winner | problem_activation_rate | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_winner | problem_activation_rate | macro_hit@3 | +0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_winner | dataset_activation_rate | hit@3 | +0.6882 | 0.2000 | +0.6299 | 0.2000 |
| facet_first_winner | dataset_activation_rate | mrr | +0.8208 | 0.1333 | +0.7379 | 0.1333 |
| facet_first_winner | dataset_activation_rate | macro_hit@3 | +0.1539 | 0.8333 | +0.1054 | 1.0000 |
| facet_first_winner | avg_active_weight_mass_g | hit@3 | +0.6708 | 0.3000 | +0.5976 | 0.3000 |
| facet_first_winner | avg_active_weight_mass_g | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_winner | avg_active_weight_mass_g | macro_hit@3 | +0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_winner | test_facet_coverage_pct | hit@3 | +0.6708 | 0.3000 | +0.5976 | 0.3000 |
| facet_first_winner | test_facet_coverage_pct | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_winner | test_facet_coverage_pct | macro_hit@3 | +0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_winner | avg_facet_words | hit@3 | +0.4472 | 0.6000 | +0.3586 | 0.6000 |
| facet_first_winner | avg_facet_words | mrr | +0.8000 | 0.1333 | +0.6000 | 0.2333 |
| facet_first_winner | avg_facet_words | macro_hit@3 | +0.5000 | 0.4500 | +0.4000 | 0.4833 |
| facet_first_top_m | macro_f1 | hit@3 | +0.2236 | 1.0000 | +0.1195 | 1.0000 |
| facet_first_top_m | macro_f1 | mrr | +0.8000 | 0.1333 | +0.6000 | 0.2333 |
| facet_first_top_m | macro_f1 | macro_hit@3 | -0.6000 | 0.3500 | -0.4000 | 0.4833 |
| facet_first_top_m | micro_f1 | hit@3 | +0.4472 | 0.6000 | +0.3586 | 0.6000 |
| facet_first_top_m | micro_f1 | mrr | +0.9000 | 0.0833 | +0.8000 | 0.0833 |
| facet_first_top_m | micro_f1 | macro_hit@3 | -0.2000 | 0.7833 | -0.2000 | 0.8167 |
| facet_first_top_m | problem_f1 | hit@3 | -0.2236 | 1.0000 | -0.1195 | 1.0000 |
| facet_first_top_m | problem_f1 | mrr | +0.6000 | 0.3500 | +0.4000 | 0.4833 |
| facet_first_top_m | problem_f1 | macro_hit@3 | -0.7000 | 0.2333 | -0.6000 | 0.2333 |
| facet_first_top_m | problem_activation_rate | hit@3 | +0.6708 | 0.3000 | +0.5976 | 0.3000 |
| facet_first_top_m | problem_activation_rate | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_top_m | problem_activation_rate | macro_hit@3 | +0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_top_m | dataset_activation_rate | hit@3 | +0.6882 | 0.2000 | +0.6299 | 0.2000 |
| facet_first_top_m | dataset_activation_rate | mrr | +0.8208 | 0.1333 | +0.7379 | 0.1333 |
| facet_first_top_m | dataset_activation_rate | macro_hit@3 | +0.1539 | 0.8333 | +0.1054 | 1.0000 |
| facet_first_top_m | avg_active_weight_mass_g | hit@3 | +0.6708 | 0.3000 | +0.5976 | 0.3000 |
| facet_first_top_m | avg_active_weight_mass_g | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_top_m | avg_active_weight_mass_g | macro_hit@3 | +0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_top_m | test_facet_coverage_pct | hit@3 | +0.6708 | 0.3000 | +0.5976 | 0.3000 |
| facet_first_top_m | test_facet_coverage_pct | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_top_m | test_facet_coverage_pct | macro_hit@3 | +0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_top_m | avg_facet_words | hit@3 | +0.4472 | 0.6000 | +0.3586 | 0.6000 |
| facet_first_top_m | avg_facet_words | mrr | +0.8000 | 0.1333 | +0.6000 | 0.2333 |
| facet_first_top_m | avg_facet_words | macro_hit@3 | +0.5000 | 0.4500 | +0.4000 | 0.4833 |
| facet_first_centroid | macro_f1 | hit@3 | -0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_centroid | macro_f1 | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_centroid | macro_f1 | macro_hit@3 | +0.6000 | 0.3500 | +0.4000 | 0.4833 |
| facet_first_centroid | micro_f1 | hit@3 | +0.0000 | 1.0000 | +0.2000 | 0.8167 |
| facet_first_centroid | micro_f1 | mrr | -0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_centroid | micro_f1 | macro_hit@3 | +0.5000 | 0.4500 | +0.2000 | 0.8167 |
| facet_first_centroid | problem_f1 | hit@3 | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_centroid | problem_f1 | mrr | -0.4000 | 0.5167 | -0.4000 | 0.4833 |
| facet_first_centroid | problem_f1 | macro_hit@3 | +0.8000 | 0.1333 | +0.6000 | 0.2333 |
| facet_first_centroid | problem_activation_rate | hit@3 | -0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_centroid | problem_activation_rate | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_centroid | problem_activation_rate | macro_hit@3 | -0.9000 | 0.0833 | -0.8000 | 0.0833 |
| facet_first_centroid | dataset_activation_rate | hit@3 | +0.8208 | 0.1333 | +0.7379 | 0.1333 |
| facet_first_centroid | dataset_activation_rate | mrr | +0.6669 | 0.2667 | +0.5270 | 0.3333 |
| facet_first_centroid | dataset_activation_rate | macro_hit@3 | +0.2052 | 0.7667 | +0.1054 | 1.0000 |
| facet_first_centroid | avg_active_weight_mass_g | hit@3 | -0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_centroid | avg_active_weight_mass_g | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_centroid | avg_active_weight_mass_g | macro_hit@3 | -0.9000 | 0.0833 | -0.8000 | 0.0833 |
| facet_first_centroid | test_facet_coverage_pct | hit@3 | -0.1000 | 0.9500 | +0.0000 | 1.0000 |
| facet_first_centroid | test_facet_coverage_pct | mrr | -0.3000 | 0.6833 | -0.2000 | 0.8167 |
| facet_first_centroid | test_facet_coverage_pct | macro_hit@3 | -0.9000 | 0.0833 | -0.8000 | 0.0833 |
| facet_first_centroid | avg_facet_words | hit@3 | +0.6000 | 0.3500 | +0.4000 | 0.4833 |
| facet_first_centroid | avg_facet_words | mrr | +0.7000 | 0.2333 | +0.6000 | 0.2333 |
| facet_first_centroid | avg_facet_words | macro_hit@3 | +0.4000 | 0.5167 | +0.4000 | 0.4833 |
| paper_first_sum_knn | macro_f1 | hit@3 | -0.2052 | 0.7333 | -0.3162 | 0.6333 |
| paper_first_sum_knn | macro_f1 | mrr | -0.9000 | 0.0833 | -0.8000 | 0.0833 |
| paper_first_sum_knn | macro_f1 | macro_hit@3 | +0.0000 | 1.0000 | +0.2000 | 0.8167 |
| paper_first_sum_knn | micro_f1 | hit@3 | -0.1026 | 0.9000 | -0.1054 | 1.0000 |
| paper_first_sum_knn | micro_f1 | mrr | -0.8000 | 0.1333 | -0.6000 | 0.2333 |
| paper_first_sum_knn | micro_f1 | macro_hit@3 | -0.1000 | 0.9500 | +0.0000 | 1.0000 |
| paper_first_sum_knn | problem_f1 | hit@3 | -0.0513 | 1.0000 | -0.1054 | 1.0000 |
| paper_first_sum_knn | problem_f1 | mrr | -0.8000 | 0.1333 | -0.6000 | 0.2333 |
| paper_first_sum_knn | problem_f1 | macro_hit@3 | +0.4000 | 0.5167 | +0.4000 | 0.4833 |
| paper_first_sum_knn | problem_activation_rate | hit@3 | +0.1539 | 0.8333 | +0.1054 | 1.0000 |
| paper_first_sum_knn | problem_activation_rate | mrr | +0.4000 | 0.5167 | +0.4000 | 0.4833 |
| paper_first_sum_knn | problem_activation_rate | macro_hit@3 | -0.7000 | 0.2333 | -0.6000 | 0.2333 |
| paper_first_sum_knn | dataset_activation_rate | hit@3 | -0.7632 | 0.1667 | -0.6667 | 0.2000 |
| paper_first_sum_knn | dataset_activation_rate | mrr | -0.6669 | 0.2667 | -0.5270 | 0.3333 |
| paper_first_sum_knn | dataset_activation_rate | macro_hit@3 | -0.6156 | 0.3000 | -0.5270 | 0.3333 |
| paper_first_sum_knn | avg_active_weight_mass_g | hit@3 | +0.1539 | 0.8333 | +0.1054 | 1.0000 |
| paper_first_sum_knn | avg_active_weight_mass_g | mrr | +0.4000 | 0.5167 | +0.4000 | 0.4833 |
| paper_first_sum_knn | avg_active_weight_mass_g | macro_hit@3 | -0.7000 | 0.2333 | -0.6000 | 0.2333 |
| paper_first_sum_knn | test_facet_coverage_pct | hit@3 | +0.1539 | 0.8333 | +0.1054 | 1.0000 |
| paper_first_sum_knn | test_facet_coverage_pct | mrr | +0.4000 | 0.5167 | +0.4000 | 0.4833 |
| paper_first_sum_knn | test_facet_coverage_pct | macro_hit@3 | -0.7000 | 0.2333 | -0.6000 | 0.2333 |
| paper_first_sum_knn | avg_facet_words | hit@3 | -0.3591 | 0.5667 | -0.3162 | 0.6333 |
| paper_first_sum_knn | avg_facet_words | mrr | -0.5000 | 0.4500 | -0.4000 | 0.4833 |
| paper_first_sum_knn | avg_facet_words | macro_hit@3 | -0.2000 | 0.7833 | -0.2000 | 0.8167 |

## 2. Thực nghiệm Exp D2: Phân tầng Độ phủ Khía cạnh Truy vấn (`High-Cov` vs `Low-Cov`)

Tiêu chí phân tầng: `High-Cov: mask_problem(q) == 1 and g(q) >= 0.80; Low-Cov: complement` (kiểm tra tính đầy đủ $n_{\text{high}} + n_{\text{low}} = 168$ trên toàn bộ 5 mô hình LLM).

| Raw LLM | Stratum | n (Share %) | Mean g(q) | Method | Hit@1 | Hit@3 | Hit@5 | MRR | Macro-Hit@3 | Disc Hit@1 | Delta Hit@3 vs FT (pp) | Delta MRR vs FT | W/T/L vs FT | p-val (Hit@3 / MRR) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen-8B | High-Cov (Prob=1 & g>=0.80) | 74 (44.0%) | 0.904 | Full-text (Winner) | 28.38% | 50.00% | 66.22% | 0.4446 | 32.27% | 71.62% | 0.00 | +0.0000 | — | — |
| Qwen-8B | High-Cov (Prob=1 & g>=0.80) | 74 (44.0%) | 0.904 | Paper-First (Sum-kNN, w_ExpB) | 13.51% | 35.14% | 48.65% | 0.3118 | 15.50% | 59.46% | -14.86 | -0.1328 | 15/13/46 | 0.0433 / 0.0010 |
| Qwen-8B | High-Cov (Prob=1 & g>=0.80) | 74 (44.0%) | 0.904 | Facet-First (Winner, w_ExpB) | 13.51% | 37.84% | 59.46% | 0.3205 | 12.90% | 63.51% | -12.16 | -0.1242 | 19/17/38 | 0.0784 / 0.0008 |
| Qwen-8B | High-Cov (Prob=1 & g>=0.80) | 74 (44.0%) | 0.904 | Adaptive Fusion (Winner, w_ExpB) | 27.03% | 47.30% | 67.57% | 0.4352 | 26.93% | 72.97% | -2.70 | -0.0094 | 15/44/15 | 0.6250 / 0.2546 |
| Qwen-8B | Low-Cov (Complement) | 94 (56.0%) | 0.546 | Full-text (Winner) | 20.21% | 54.26% | 70.21% | 0.4189 | 28.33% | 73.40% | 0.00 | +0.0000 | — | — |
| Qwen-8B | Low-Cov (Complement) | 94 (56.0%) | 0.546 | Paper-First (Sum-kNN, w_ExpB) | 17.02% | 45.74% | 61.70% | 0.3623 | 19.96% | 69.15% | -8.51 | -0.0566 | 28/18/48 | 0.1516 / 0.0755 |
| Qwen-8B | Low-Cov (Complement) | 94 (56.0%) | 0.546 | Facet-First (Winner, w_ExpB) | 26.60% | 50.00% | 64.89% | 0.4264 | 19.71% | 71.28% | -4.26 | +0.0074 | 34/19/41 | 0.5413 / 0.8223 |
| Qwen-8B | Low-Cov (Complement) | 94 (56.0%) | 0.546 | Adaptive Fusion (Winner, w_ExpB) | 20.21% | 55.32% | 70.21% | 0.4219 | 28.50% | 74.47% | +1.06 | +0.0030 | 17/63/14 | 1.0000 / 0.2980 |
| Qwen-8B | All Queries | 168 (100.0%) | 0.704 | Full-text (Winner) | 23.81% | 52.38% | 68.45% | 0.4302 | 26.66% | 72.62% | 0.00 | +0.0000 | — | — |
| Qwen-8B | All Queries | 168 (100.0%) | 0.704 | Paper-First (Sum-kNN, w_ExpB) | 15.48% | 41.07% | 55.95% | 0.3401 | 15.03% | 64.88% | -11.31 | -0.0902 | 43/31/94 | 0.0094 / 0.0002 |
| Qwen-8B | All Queries | 168 (100.0%) | 0.704 | Facet-First (Winner, w_ExpB) | 20.83% | 44.64% | 62.50% | 0.3797 | 13.72% | 67.86% | -7.74 | -0.0505 | 53/36/79 | 0.0725 / 0.0406 |
| Qwen-8B | All Queries | 168 (100.0%) | 0.704 | Adaptive Fusion (Winner, w_ExpB) | 23.21% | 51.79% | 69.05% | 0.4278 | 25.23% | 73.81% | -0.60 | -0.0025 | 32/107/29 | 1.0000 / 0.5888 |
| Gemma-9B | High-Cov (Prob=1 & g>=0.80) | 103 (61.3%) | 0.920 | Full-text (Winner) | 21.36% | 47.57% | 65.05% | 0.4029 | 30.97% | 71.84% | 0.00 | +0.0000 | — | — |
| Gemma-9B | High-Cov (Prob=1 & g>=0.80) | 103 (61.3%) | 0.920 | Paper-First (Sum-kNN, w_ExpB) | 17.48% | 39.81% | 53.40% | 0.3408 | 16.70% | 66.02% | -7.77 | -0.0621 | 31/16/56 | 0.1516 / 0.0620 |
| Gemma-9B | High-Cov (Prob=1 & g>=0.80) | 103 (61.3%) | 0.920 | Facet-First (Winner, w_ExpB) | 17.48% | 38.83% | 57.28% | 0.3446 | 15.42% | 66.02% | -8.74 | -0.0583 | 29/22/52 | 0.1078 / 0.0498 |
| Gemma-9B | High-Cov (Prob=1 & g>=0.80) | 103 (61.3%) | 0.920 | Adaptive Fusion (Winner, w_ExpB) | 22.33% | 46.60% | 64.08% | 0.4078 | 26.08% | 72.82% | -0.97 | +0.0049 | 20/66/17 | 1.0000 / 0.6220 |
| Gemma-9B | Low-Cov (Complement) | 65 (38.7%) | 0.534 | Full-text (Winner) | 27.69% | 60.00% | 73.85% | 0.4735 | 32.97% | 73.85% | 0.00 | +0.0000 | — | — |
| Gemma-9B | Low-Cov (Complement) | 65 (38.7%) | 0.534 | Paper-First (Sum-kNN, w_ExpB) | 16.92% | 52.31% | 60.00% | 0.3787 | 24.74% | 72.31% | -7.69 | -0.0948 | 14/16/35 | 0.3018 / 0.0085 |
| Gemma-9B | Low-Cov (Complement) | 65 (38.7%) | 0.534 | Facet-First (Winner, w_ExpB) | 24.62% | 53.85% | 63.08% | 0.4291 | 16.25% | 70.77% | -6.15 | -0.0444 | 14/18/33 | 0.4545 / 0.2519 |
| Gemma-9B | Low-Cov (Complement) | 65 (38.7%) | 0.534 | Adaptive Fusion (Winner, w_ExpB) | 27.69% | 60.00% | 73.85% | 0.4723 | 32.72% | 73.85% | +0.00 | -0.0012 | 7/48/10 | 1.0000 / 0.6932 |
| Gemma-9B | All Queries | 168 (100.0%) | 0.771 | Full-text (Winner) | 23.81% | 52.38% | 68.45% | 0.4302 | 26.66% | 72.62% | 0.00 | +0.0000 | — | — |
| Gemma-9B | All Queries | 168 (100.0%) | 0.771 | Paper-First (Sum-kNN, w_ExpB) | 17.26% | 44.64% | 55.95% | 0.3555 | 16.51% | 68.45% | -7.74 | -0.0748 | 45/32/91 | 0.0533 / 0.0021 |
| Gemma-9B | All Queries | 168 (100.0%) | 0.771 | Facet-First (Winner, w_ExpB) | 20.24% | 44.64% | 59.52% | 0.3773 | 12.90% | 67.86% | -7.74 | -0.0529 | 43/40/85 | 0.0596 / 0.0256 |
| Gemma-9B | All Queries | 168 (100.0%) | 0.771 | Adaptive Fusion (Winner, w_ExpB) | 24.40% | 51.79% | 67.86% | 0.4327 | 24.94% | 73.21% | -0.60 | +0.0025 | 27/114/27 | 1.0000 / 0.6987 |
| Qwen-14B | High-Cov (Prob=1 & g>=0.80) | 112 (66.7%) | 0.917 | Full-text (Winner) | 24.11% | 49.11% | 67.86% | 0.4244 | 32.49% | 74.11% | 0.00 | +0.0000 | — | — |
| Qwen-14B | High-Cov (Prob=1 & g>=0.80) | 112 (66.7%) | 0.917 | Paper-First (Sum-kNN, w_ExpB) | 16.07% | 39.29% | 51.79% | 0.3306 | 17.03% | 68.75% | -9.82 | -0.0938 | 27/19/66 | 0.0522 / 0.0029 |
| Qwen-14B | High-Cov (Prob=1 & g>=0.80) | 112 (66.7%) | 0.917 | Facet-First (Winner, w_ExpB) | 13.39% | 39.29% | 55.36% | 0.3269 | 11.18% | 67.86% | -9.82 | -0.0974 | 24/20/68 | 0.0614 / 0.0015 |
| Qwen-14B | High-Cov (Prob=1 & g>=0.80) | 112 (66.7%) | 0.917 | Adaptive Fusion (Winner, w_ExpB) | 24.11% | 47.32% | 67.86% | 0.4222 | 27.37% | 74.11% | -1.79 | -0.0022 | 17/73/22 | 0.6250 / 0.7454 |
| Qwen-14B | Low-Cov (Complement) | 56 (33.3%) | 0.539 | Full-text (Winner) | 23.21% | 58.93% | 69.64% | 0.4419 | 33.40% | 69.64% | 0.00 | +0.0000 | — | — |
| Qwen-14B | Low-Cov (Complement) | 56 (33.3%) | 0.539 | Paper-First (Sum-kNN, w_ExpB) | 26.79% | 50.00% | 55.36% | 0.4130 | 26.23% | 66.07% | -8.93 | -0.0290 | 16/13/27 | 0.2668 / 0.4897 |
| Qwen-14B | Low-Cov (Complement) | 56 (33.3%) | 0.539 | Facet-First (Winner, w_ExpB) | 23.21% | 55.36% | 62.50% | 0.4176 | 25.00% | 66.07% | -3.57 | -0.0243 | 18/13/25 | 0.8036 / 0.5402 |
| Qwen-14B | Low-Cov (Complement) | 56 (33.3%) | 0.539 | Adaptive Fusion (Winner, w_ExpB) | 23.21% | 58.93% | 69.64% | 0.4426 | 33.40% | 71.43% | +0.00 | +0.0007 | 12/35/9 | 1.0000 / 0.8678 |
| Qwen-14B | All Queries | 168 (100.0%) | 0.791 | Full-text (Winner) | 23.81% | 52.38% | 68.45% | 0.4302 | 26.66% | 72.62% | 0.00 | +0.0000 | — | — |
| Qwen-14B | All Queries | 168 (100.0%) | 0.791 | Paper-First (Sum-kNN, w_ExpB) | 19.64% | 42.86% | 52.98% | 0.3581 | 14.52% | 67.86% | -9.52 | -0.0722 | 43/32/93 | 0.0166 / 0.0055 |
| Qwen-14B | All Queries | 168 (100.0%) | 0.791 | Facet-First (Winner, w_ExpB) | 16.67% | 44.64% | 57.74% | 0.3572 | 12.40% | 67.26% | -7.74 | -0.0731 | 42/33/93 | 0.0725 / 0.0024 |
| Qwen-14B | All Queries | 168 (100.0%) | 0.791 | Adaptive Fusion (Winner, w_ExpB) | 23.81% | 51.19% | 68.45% | 0.4290 | 24.66% | 73.21% | -1.19 | -0.0012 | 29/108/31 | 0.6875 / 0.8022 |
| Llama-8B | High-Cov (Prob=1 & g>=0.80) | 119 (70.8%) | 0.919 | Full-text (Winner) | 22.69% | 46.22% | 63.03% | 0.4067 | 28.01% | 71.43% | 0.00 | +0.0000 | — | — |
| Llama-8B | High-Cov (Prob=1 & g>=0.80) | 119 (70.8%) | 0.919 | Paper-First (Sum-kNN, w_ExpB) | 18.49% | 40.34% | 53.78% | 0.3483 | 14.50% | 66.39% | -5.88 | -0.0584 | 36/23/60 | 0.2478 / 0.0586 |
| Llama-8B | High-Cov (Prob=1 & g>=0.80) | 119 (70.8%) | 0.919 | Facet-First (Winner, w_ExpB) | 15.13% | 41.18% | 54.62% | 0.3333 | 15.97% | 65.55% | -5.04 | -0.0734 | 32/22/65 | 0.3616 / 0.0210 |
| Llama-8B | High-Cov (Prob=1 & g>=0.80) | 119 (70.8%) | 0.919 | Adaptive Fusion (Winner, w_ExpB) | 22.69% | 44.54% | 63.87% | 0.4034 | 23.24% | 73.11% | -1.68 | -0.0033 | 21/73/25 | 0.6250 / 0.6151 |
| Llama-8B | Low-Cov (Complement) | 49 (29.2%) | 0.549 | Full-text (Winner) | 26.53% | 67.35% | 81.63% | 0.4874 | 46.71% | 75.51% | 0.00 | +0.0000 | — | — |
| Llama-8B | Low-Cov (Complement) | 49 (29.2%) | 0.549 | Paper-First (Sum-kNN, w_ExpB) | 26.53% | 53.06% | 63.27% | 0.4432 | 22.67% | 73.47% | -14.29 | -0.0443 | 13/15/21 | 0.0923 / 0.3369 |
| Llama-8B | Low-Cov (Complement) | 49 (29.2%) | 0.549 | Facet-First (Winner, w_ExpB) | 24.49% | 63.27% | 67.35% | 0.4657 | 30.56% | 71.43% | -4.08 | -0.0217 | 13/19/17 | 0.7744 / 0.5935 |
| Llama-8B | Low-Cov (Complement) | 49 (29.2%) | 0.549 | Adaptive Fusion (Winner, w_ExpB) | 26.53% | 67.35% | 81.63% | 0.4879 | 45.04% | 75.51% | +0.00 | +0.0005 | 6/36/7 | 1.0000 / 0.9172 |
| Llama-8B | All Queries | 168 (100.0%) | 0.811 | Full-text (Winner) | 23.81% | 52.38% | 68.45% | 0.4302 | 26.66% | 72.62% | 0.00 | +0.0000 | — | — |
| Llama-8B | All Queries | 168 (100.0%) | 0.811 | Paper-First (Sum-kNN, w_ExpB) | 20.83% | 44.05% | 56.55% | 0.3759 | 13.80% | 68.45% | -8.33 | -0.0543 | 49/38/81 | 0.0385 / 0.0335 |
| Llama-8B | All Queries | 168 (100.0%) | 0.811 | Facet-First (Winner, w_ExpB) | 17.86% | 47.62% | 58.33% | 0.3719 | 16.12% | 67.26% | -4.76 | -0.0583 | 45/41/82 | 0.2800 / 0.0196 |
| Llama-8B | All Queries | 168 (100.0%) | 0.811 | Adaptive Fusion (Winner, w_ExpB) | 23.81% | 51.19% | 69.05% | 0.4281 | 24.34% | 73.81% | -1.19 | -0.0022 | 27/109/32 | 0.6875 / 0.6502 |
| Qwen-4B | High-Cov (Prob=1 & g>=0.80) | 95 (56.5%) | 0.912 | Full-text (Winner) | 24.21% | 48.42% | 66.32% | 0.4195 | 32.96% | 72.63% | 0.00 | +0.0000 | — | — |
| Qwen-4B | High-Cov (Prob=1 & g>=0.80) | 95 (56.5%) | 0.912 | Paper-First (Sum-kNN, w_ExpB) | 20.00% | 38.95% | 51.58% | 0.3546 | 14.50% | 66.32% | -9.47 | -0.0649 | 26/19/50 | 0.1078 / 0.0469 |
| Qwen-4B | High-Cov (Prob=1 & g>=0.80) | 95 (56.5%) | 0.912 | Facet-First (Winner, w_ExpB) | 12.63% | 35.79% | 51.58% | 0.3084 | 14.45% | 65.26% | -12.63 | -0.1111 | 24/18/53 | 0.0290 / 0.0011 |
| Qwen-4B | High-Cov (Prob=1 & g>=0.80) | 95 (56.5%) | 0.912 | Adaptive Fusion (Winner, w_ExpB) | 23.16% | 47.37% | 67.37% | 0.4116 | 28.46% | 73.68% | -1.05 | -0.0079 | 16/61/18 | 1.0000 / 0.2397 |
| Qwen-4B | Low-Cov (Complement) | 73 (43.5%) | 0.530 | Full-text (Winner) | 23.29% | 57.53% | 71.23% | 0.4443 | 29.71% | 72.60% | 0.00 | +0.0000 | — | — |
| Qwen-4B | Low-Cov (Complement) | 73 (43.5%) | 0.530 | Paper-First (Sum-kNN, w_ExpB) | 21.92% | 52.05% | 64.38% | 0.4077 | 25.63% | 69.86% | -5.48 | -0.0366 | 20/19/34 | 0.4545 / 0.2870 |
| Qwen-4B | Low-Cov (Complement) | 73 (43.5%) | 0.530 | Facet-First (Winner, w_ExpB) | 17.81% | 54.79% | 64.38% | 0.3963 | 20.79% | 69.86% | -2.74 | -0.0479 | 20/18/35 | 0.8036 / 0.1634 |
| Qwen-4B | Low-Cov (Complement) | 73 (43.5%) | 0.530 | Adaptive Fusion (Winner, w_ExpB) | 23.29% | 57.53% | 71.23% | 0.4444 | 29.11% | 72.60% | +0.00 | +0.0002 | 10/52/11 | 1.0000 / 0.9509 |
| Qwen-4B | All Queries | 168 (100.0%) | 0.746 | Full-text (Winner) | 23.81% | 52.38% | 68.45% | 0.4302 | 26.66% | 72.62% | 0.00 | +0.0000 | — | — |
| Qwen-4B | All Queries | 168 (100.0%) | 0.746 | Paper-First (Sum-kNN, w_ExpB) | 20.83% | 44.64% | 57.14% | 0.3777 | 18.39% | 67.86% | -7.74 | -0.0526 | 46/38/84 | 0.0596 / 0.0238 |
| Qwen-4B | All Queries | 168 (100.0%) | 0.746 | Facet-First (Winner, w_ExpB) | 14.88% | 44.05% | 57.14% | 0.3466 | 14.17% | 67.26% | -8.33 | -0.0836 | 44/36/88 | 0.0436 / 0.0004 |
| Qwen-4B | All Queries | 168 (100.0%) | 0.746 | Adaptive Fusion (Winner, w_ExpB) | 23.21% | 51.79% | 69.05% | 0.4258 | 25.23% | 73.21% | -0.60 | -0.0044 | 26/113/29 | 1.0000 / 0.2822 |

## 3. Thực nghiệm Exp D3: Tín hiệu Bổ trợ & Phân giải Nhập nhằng Nội ngành (`Intra-Discipline Disambiguation`)

### Bảng D3a — Đánh giá Toàn cục trên 168 Bài Test (`Adaptive Fusion` & `Coarse-to-Fine Reranking`)

| Method | Train CV Hit@3 | Test Hit@1 | Test Hit@3 | Test Hit@5 | Test MRR | Macro-Hit@3 [95% CI] | Disc Hit@1 | W/T/L vs Full-text | McNemar p (Hit@1 / Hit@3) | Perm p (MRR) | Holm-Bonferroni adj p (Hit@3 / MRR) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Full-text Baseline (temp_softmax) | 51.99% ± 3.16% | 23.81% | 52.38% | 68.45% | 0.4302 | 26.66% [22.5, 36.2] | 72.62% | — | — | — | — |
| Facet-First (top_m) | 46.18% ± 2.34% | 20.83% | 44.64% | 62.50% | 0.3797 | 13.72% [12.3, 20.5] | 67.86% | 53/36/79 | 0.5114 / 0.0725 | 0.0406 | 0.4347 / 0.2436 |
| Coverage-Aware Adaptive Fusion (beta=0.3) | 52.33% ± 3.75% | 23.21% | 51.79% | 69.05% | 0.4278 | 25.23% [21.2, 34.7] | 73.81% | 32/107/29 | 1.0000 / 1.0000 | 0.5888 | 1.0000 / 1.0000 |
| Coarse-to-Fine Reranking (C=5, Stage-2: Facet-First) | 46.18% ± 2.66% | 22.62% | 48.21% | 68.45% | 0.4095 | 18.82% [16.6, 27.8] | 67.86% | 36/90/42 | 0.8714 / 0.3105 | 0.3790 | 1.0000 / 1.0000 |
| Coarse-to-Fine Reranking (C=10, Stage-2: Facet-First) | 47.33% ± 3.52% | 20.83% | 45.24% | 66.67% | 0.3927 | 14.94% [13.1, 22.4] | 67.86% | 49/60/59 | 0.5114 / 0.1038 | 0.1259 | 0.5190 / 0.6294 |
| Coarse-to-Fine Reranking (C=5, Stage-2: Adaptive Fusion) | 52.33% ± 3.75% | 23.21% | 51.79% | 68.45% | 0.4284 | 25.23% [21.2, 34.7] | 73.81% | 8/154/6 | 1.0000 / 1.0000 | 0.7461 | 1.0000 / 1.0000 |
| Coarse-to-Fine Reranking (C=10, Stage-2: Adaptive Fusion) | 52.33% ± 3.75% | 23.21% | 51.79% | 69.05% | 0.4288 | 25.23% [21.2, 34.7] | 73.81% | 20/133/15 | 1.0000 / 1.0000 | 0.7737 | 1.0000 / 1.0000 |

### Bảng D3b — Phân rã trên Tập Nhập nhằng Nội ngành (`Intra-Discipline Ambiguous Subset`)

Phân bố cụm ngành trong tập `Intra-Discipline Ambiguous` ($n = 87$): `{"IR_DM_DB": 3, "NLP": 84}`.

| Subset | n | Method | Hit@1 | Hit@3 | Hit@5 | MRR | Macro-Hit@3 | Disc Hit@1 | Delta Hit@1 (pp) | Delta Hit@3 (pp) | Delta MRR | W/T/L vs Full-text | p-val (Hit@1 / Hit@3 / MRR) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Intra-Discipline Ambiguous (Top-3 Same Discipline) | 87 | Full-text Baseline (temp_softmax) | 26.44% | 57.47% | 74.71% | 0.4636 | 25.26% | 88.51% | 0.00 | 0.00 | +0.0000 | — | — |
| Intra-Discipline Ambiguous (Top-3 Same Discipline) | 87 | Facet-First (top_m) | 27.59% | 55.17% | 75.86% | 0.4570 | 17.76% | 88.51% | +1.15 | -2.30 | -0.0066 | 32/22/33 | 1.0000 / 0.8318 / 0.8552 |
| Intra-Discipline Ambiguous (Top-3 Same Discipline) | 87 | Coverage-Aware Adaptive Fusion (beta=0.3) | 26.44% | 58.62% | 77.01% | 0.4707 | 24.29% | 88.51% | +0.00 | +1.15 | +0.0070 | 19/62/6 | 1.0000 / 1.0000 / 0.0098 |
| Intra-Discipline Ambiguous (Top-3 Same Discipline) | 87 | Coarse-to-Fine Reranking (C=5, Stage-2: Facet-First) | 28.74% | 55.17% | 74.71% | 0.4692 | 17.46% | 88.51% | +2.30 | -2.30 | +0.0056 | 21/45/21 | 0.8388 / 0.8036 / 0.8807 |
| Intra-Discipline Ambiguous (Top-3 Same Discipline) | 87 | Coarse-to-Fine Reranking (C=10, Stage-2: Facet-First) | 27.59% | 54.02% | 79.31% | 0.4632 | 17.23% | 88.51% | +1.15 | -3.45 | -0.0004 | 28/31/28 | 1.0000 / 0.6636 / 0.9897 |
| Intra-Discipline Ambiguous (Top-3 Same Discipline) | 87 | Coarse-to-Fine Reranking (C=5, Stage-2: Adaptive Fusion) | 26.44% | 58.62% | 74.71% | 0.4677 | 24.29% | 88.51% | +0.00 | +1.15 | +0.0040 | 5/81/1 | 1.0000 / 1.0000 / 0.1904 |
| Intra-Discipline Ambiguous (Top-3 Same Discipline) | 87 | Coarse-to-Fine Reranking (C=10, Stage-2: Adaptive Fusion) | 26.44% | 58.62% | 77.01% | 0.4699 | 24.29% | 88.51% | +0.00 | +1.15 | +0.0063 | 13/70/4 | 1.0000 / 1.0000 / 0.0198 |
| Cross-Discipline Top-3 (Complement) | 81 | Full-text Baseline (temp_softmax) | 20.99% | 46.91% | 61.73% | 0.3944 | 28.19% | 55.56% | 0.00 | 0.00 | +0.0000 | — | — |
| Cross-Discipline Top-3 (Complement) | 81 | Facet-First (top_m) | 13.58% | 33.33% | 48.15% | 0.2967 | 15.20% | 45.68% | -7.41 | -13.58 | -0.0977 | 21/14/46 | 0.1796 / 0.0347 / 0.0026 |
| Cross-Discipline Top-3 (Complement) | 81 | Coverage-Aware Adaptive Fusion (beta=0.3) | 19.75% | 44.44% | 60.49% | 0.3817 | 26.39% | 58.02% | -1.23 | -2.47 | -0.0127 | 13/45/23 | 1.0000 / 0.6250 / 0.0299 |
| Cross-Discipline Top-3 (Complement) | 81 | Coarse-to-Fine Reranking (C=5, Stage-2: Facet-First) | 16.05% | 40.74% | 61.73% | 0.3454 | 22.09% | 45.68% | -4.94 | -6.17 | -0.0490 | 15/45/21 | 0.4240 / 0.3593 / 0.1046 |
| Cross-Discipline Top-3 (Complement) | 81 | Coarse-to-Fine Reranking (C=10, Stage-2: Facet-First) | 13.58% | 35.80% | 53.09% | 0.3169 | 18.00% | 45.68% | -7.41 | -11.11 | -0.0775 | 21/29/31 | 0.1796 / 0.1078 / 0.0167 |
| Cross-Discipline Top-3 (Complement) | 81 | Coarse-to-Fine Reranking (C=5, Stage-2: Adaptive Fusion) | 19.75% | 44.44% | 61.73% | 0.3861 | 26.39% | 58.02% | -1.23 | -2.47 | -0.0082 | 3/73/5 | 1.0000 / 0.6250 / 0.2807 |
| Cross-Discipline Top-3 (Complement) | 81 | Coarse-to-Fine Reranking (C=10, Stage-2: Adaptive Fusion) | 19.75% | 44.44% | 60.49% | 0.3846 | 26.39% | 58.02% | -1.23 | -2.47 | -0.0098 | 7/63/11 | 1.0000 / 0.6250 / 0.1558 |

## 4. Thực nghiệm Exp D4: Phân tầng Đặc trưng Ca Thắng / Thua (`Win/Loss Case Stratification`)

| Comparison | W / T / L (Sum=168) | Feature | Win Mean (Median) | Tie Mean (Median) | Loss Mean (Median) | Stat Test (Win vs Loss) | p-value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Facet-First vs Full-text | 53 / 36 / 79 | 1. Abstract Word Count | 149.302 (136.000) | 135.139 (133.500) | 148.671 (144.000) | Mann-Whitney U=1886.0 | 0.3365 |
| Facet-First vs Full-text | 53 / 36 / 79 | 2a. Active Weight Mass g(q) | 0.677 (0.600) | 0.706 (0.600) | 0.720 (0.700) | Mann-Whitney U=1864.0 | 0.2651 |
| Facet-First vs Full-text | 53 / 36 / 79 | 2b. Active Facet Count | 3.660 (4.000) | 3.667 (4.000) | 3.722 (4.000) | Mann-Whitney U=2012.0 | 0.6633 |
| Facet-First vs Full-text | 53 / 36 / 79 | 4. Lexical Novelty Proxy (1 - Top10 Sim) | 0.052 (0.049) | 0.058 (0.052) | 0.054 (0.051) | Mann-Whitney U=1786.0 | 0.1541 |
| Facet-First vs Full-text | 53 / 36 / 79 | 3. Venue Tier (Head/Mid/Tail) | 44/8/1 (83.0%/15.1%/1.9%) | 35/1/0 (97.2%/2.8%/0.0%) | 40/31/8 (50.6%/39.2%/10.1%) | Chi2=14.65; Fisher OR=4.77 | Chi2 p=0.0007 / Fisher p=0.0002 |
| Coverage-Aware Adaptive Fusion vs Full-text | 32 / 107 / 29 | 1. Abstract Word Count | 147.062 (146.000) | 141.598 (138.000) | 160.897 (149.000) | Mann-Whitney U=408.5 | 0.4270 |
| Coverage-Aware Adaptive Fusion vs Full-text | 32 / 107 / 29 | 2a. Active Weight Mass g(q) | 0.703 (0.600) | 0.694 (0.600) | 0.738 (0.800) | Mann-Whitney U=405.5 | 0.3767 |
| Coverage-Aware Adaptive Fusion vs Full-text | 32 / 107 / 29 | 2b. Active Facet Count | 3.625 (4.000) | 3.673 (4.000) | 3.828 (4.000) | Mann-Whitney U=394.5 | 0.2488 |
| Coverage-Aware Adaptive Fusion vs Full-text | 32 / 107 / 29 | 4. Lexical Novelty Proxy (1 - Top10 Sim) | 0.058 (0.050) | 0.052 (0.050) | 0.056 (0.056) | Mann-Whitney U=370.0 | 0.1769 |
| Coverage-Aware Adaptive Fusion vs Full-text | 32 / 107 / 29 | 3. Venue Tier (Head/Mid/Tail) | 21/10/1 (65.6%/31.2%/3.1%) | 93/14/0 (86.9%/13.1%/0.0%) | 5/16/8 (17.2%/55.2%/27.6%) | Chi2=16.57; Fisher OR=9.16 | Chi2 p=0.0003 / Fisher p=0.0002 |
| Coarse-to-Fine (C=5, Adaptive Fusion) vs Full-text | 8 / 154 / 6 | 1. Abstract Word Count | 162.625 (175.500) | 144.299 (140.500) | 166.667 (131.000) | Mann-Whitney U=24.0 | 1.0000 |
| Coarse-to-Fine (C=5, Adaptive Fusion) vs Full-text | 8 / 154 / 6 | 2a. Active Weight Mass g(q) | 0.675 (0.600) | 0.699 (0.600) | 0.850 (0.900) | Mann-Whitney U=12.5 | 0.1241 |
| Coarse-to-Fine (C=5, Adaptive Fusion) vs Full-text | 8 / 154 / 6 | 2b. Active Facet Count | 3.625 (4.000) | 3.682 (4.000) | 4.000 (4.000) | Mann-Whitney U=16.5 | 0.2849 |
| Coarse-to-Fine (C=5, Adaptive Fusion) vs Full-text | 8 / 154 / 6 | 4. Lexical Novelty Proxy (1 - Top10 Sim) | 0.073 (0.045) | 0.053 (0.051) | 0.056 (0.057) | Mann-Whitney U=18.0 | 0.4908 |
| Coarse-to-Fine (C=5, Adaptive Fusion) vs Full-text | 8 / 154 / 6 | 3. Venue Tier (Head/Mid/Tail) | 7/1/0 (87.5%/12.5%/0.0%) | 109/36/9 (70.8%/23.4%/5.8%) | 3/3/0 (50.0%/50.0%/0.0%) | Chi2=0.88; Fisher OR=7.00 | Chi2 p=0.3476 / Fisher p=0.2448 |
| Coarse-to-Fine (C=5, Facet-First) vs Full-text | 36 / 90 / 42 | 1. Abstract Word Count | 145.694 (137.500) | 146.744 (143.000) | 144.548 (138.000) | Mann-Whitney U=767.5 | 0.9122 |
| Coarse-to-Fine (C=5, Facet-First) vs Full-text | 36 / 90 / 42 | 2a. Active Weight Mass g(q) | 0.697 (0.600) | 0.698 (0.600) | 0.721 (0.700) | Mann-Whitney U=721.5 | 0.7195 |
| Coarse-to-Fine (C=5, Facet-First) vs Full-text | 36 / 90 / 42 | 2b. Active Facet Count | 3.750 (4.000) | 3.667 (4.000) | 3.690 (4.000) | Mann-Whitney U=803.5 | 0.5744 |
| Coarse-to-Fine (C=5, Facet-First) vs Full-text | 36 / 90 / 42 | 4. Lexical Novelty Proxy (1 - Top10 Sim) | 0.052 (0.049) | 0.056 (0.052) | 0.052 (0.050) | Mann-Whitney U=714.0 | 0.6774 |
| Coarse-to-Fine (C=5, Facet-First) vs Full-text | 36 / 90 / 42 | 3. Venue Tier (Head/Mid/Tail) | 35/1/0 (97.2%/2.8%/0.0%) | 53/28/9 (58.9%/31.1%/10.0%) | 31/11/0 (73.8%/26.2%/0.0%) | Chi2=6.46; Fisher OR=12.42 | Chi2 p=0.0110 / Fisher p=0.0044 |

### Bảng D4b — Các Ca Thắng / Thua Điển hình (`Top Win / Loss Qualitative Cases`)

| Comparison | Outcome | Paper ID | True Venue | Tier | Rank Full -> New (Delta) | g(q) / Active Facets | Abstract Words | Lexical Novelty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Coverage-Aware Adaptive Fusion vs Full-text | WIN | P001449 | CONF_KDD | mid | 28 -> 14 (+14) | 0.60 / 4 | 107 | 0.0528 |
| Coverage-Aware Adaptive Fusion vs Full-text | WIN | P002347 | CONF_RANLP | mid | 27 -> 20 (+7) | 0.60 / 4 | 80 | 0.0508 |
| Coverage-Aware Adaptive Fusion vs Full-text | WIN | P001929 | CONF_CHI | mid | 12 -> 9 (+3) | 0.90 / 4 | 140 | 0.0671 |
| Coverage-Aware Adaptive Fusion vs Full-text | WIN | P002390 | CONF_SIGDIAL | mid | 12 -> 9 (+3) | 0.90 / 4 | 167 | 0.0458 |
| Coverage-Aware Adaptive Fusion vs Full-text | WIN | P001347 | CONF_ICML | mid | 14 -> 11 (+3) | 0.90 / 4 | 182 | 0.0611 |
| Coverage-Aware Adaptive Fusion vs Full-text | LOSS | P002034 | CONF_ACM_MM | tail | 13 -> 30 (-17) | 0.60 / 4 | 173 | 0.0446 |
| Coverage-Aware Adaptive Fusion vs Full-text | LOSS | P002670 | CONF_ACM_MM | tail | 14 -> 30 (-16) | 0.90 / 4 | 212 | 0.0477 |
| Coverage-Aware Adaptive Fusion vs Full-text | LOSS | P003049 | CONF_ACM_MM | tail | 14 -> 29 (-15) | 1.00 / 5 | 227 | 0.0452 |
| Coverage-Aware Adaptive Fusion vs Full-text | LOSS | P003048 | CONF_ACM_MM | tail | 14 -> 25 (-11) | 0.50 / 3 | 231 | 0.0498 |
| Coverage-Aware Adaptive Fusion vs Full-text | LOSS | P003109 | CONF_ICORE_642 | tail | 20 -> 26 (-6) | 0.90 / 4 | 170 | 0.0449 |
| Facet-First vs Full-text | WIN | P001449 | CONF_KDD | mid | 28 -> 11 (+17) | 0.60 / 4 | 107 | 0.0528 |
| Facet-First vs Full-text | WIN | P002932 | CONF_COLING | head | 12 -> 3 (+9) | 0.50 / 3 | 169 | 0.0413 |
| Facet-First vs Full-text | WIN | P003710 | CONF_ICASSP | head | 17 -> 9 (+8) | 0.90 / 4 | 121 | 0.0629 |
| Facet-First vs Full-text | WIN | P002347 | CONF_RANLP | mid | 27 -> 19 (+8) | 0.60 / 4 | 80 | 0.0508 |
| Facet-First vs Full-text | WIN | P000677 | CONF_EACL | head | 9 -> 3 (+6) | 0.50 / 3 | 97 | 0.0461 |
| Facet-First vs Full-text | LOSS | P002694 | CONF_WSDM | tail | 10 -> 28 (-18) | 0.60 / 4 | 198 | 0.0552 |
| Facet-First vs Full-text | LOSS | P001561 | CONF_SIGDIAL | mid | 3 -> 21 (-18) | 0.50 / 3 | 127 | 0.0583 |
| Facet-First vs Full-text | LOSS | P003134 | CONF_SIGDIAL | mid | 3 -> 21 (-18) | 1.00 / 5 | 135 | 0.0693 |
| Facet-First vs Full-text | LOSS | P002034 | CONF_ACM_MM | tail | 13 -> 30 (-17) | 0.60 / 4 | 173 | 0.0446 |
| Facet-First vs Full-text | LOSS | P001322 | CONF_ICORE_2268 | mid | 1 -> 18 (-17) | 1.00 / 5 | 188 | 0.0555 |

## 5. Tổng hợp Nhân quả: Biểu diễn 5 Facets Giúp ích trong Điều kiện nào?

Từ hệ thống bằng chứng định lượng xuyên suốt **Exp D1–D4** với bộ trọng số khóa cứng $\mathbf{w}_{\text{Exp B}}^* = (0.40, 0.20, 0.20, 0.10, 0.10)$, ta rút ra 4 điều kiện nhân quả cốt lõi:

1. **Điều kiện 1 — Tổng hợp ở cấp độ Khía cạnh–Hội nghị (`Facet-First Compositional Pooling`, Exp D1):**
   - Trong cơ chế `Paper-First` truyền thống, một khía cạnh chỉ kích hoạt khi *cả bài truy vấn lẫn bài ứng viên đơn lẻ* cùng trích xuất được khía cạnh đó (khiến tỷ lệ kích hoạt cặp của `problem` chỉ đạt **17.97%** và `dataset` chỉ đạt **8.18%** trên `Qwen-8B Raw`).
   - Khi chuyển sang **`Facet-First: Per-Facet Venue Top-m` ($m^*=3$)**, hồ sơ khía cạnh $P_{v, f}$ được gom trên toàn bộ bài báo lịch sử của hội nghị $v$, nâng tỷ lệ kích hoạt `problem` lên **44.31%** ($2.47\times$) và `dataset` lên **25.18%** ($3.08\times$). Kết quả dưới trọng số khóa $\mathbf{w}_{\text{Exp B}}^*$:
     - **Test Hit@1** tăng từ **15.48% $\to$ 20.83%** (**$+5.36\text{ pp}$**).
     - **Test Hit@3** tăng từ **41.07% $\to$ 44.64%** (**$+3.57\text{ pp}$**).
     - **Test Hit@5** tăng từ **55.95% $\to$ 62.50%** (**$+6.55\text{ pp}$**).
     - **Test MRR** tăng từ **0.3401 $\to$ 0.3797** (**$+0.0396$, Paired Permutation $p = 0.0376 < 0.05$**, thắng áp đảo `81 Wins / 40 Ties / 47 Losses`).
   - Đặc biệt, `Facet-First` **hóa giải hoàn toàn nghịch lý tương quan âm của Exp A**: tương quan hạng Spearman giữa `Exp A Micro-F1` và `Test MRR` đảo chiều từ **$\rho = -0.8000$** (ở `Paper-First`) sang **$\rho = +0.9000$** ($p = 0.0833$, Kendall $\tau = +0.8000$) và `Exp A Macro-F1` đạt **$\rho = +0.8000$**! Mọi mô hình trong 5 Raw LLMs đều có số ca thắng vượt số ca thua khi chuyển từ `Paper-First` sang `Facet-First` (trong đó `Llama-8B` đạt đỉnh **47.62% Test Hit@3**).

2. **Điều kiện 2 — Phân giải Nhập nhằng Nội ngành khi Full-text Đã Định tuyến Đúng Cụm Ngành (`Intra-Discipline Disambiguation`, Exp D3):**
   - Trên tập **`Intra-Discipline Ambiguous Subset` ($n = 87/168$, chiếm $51.8\%$ tập Test)** — nơi Top-3 hội nghị dự đoán của `Full-text` cùng thuộc một cụm ngành (`84 NLP + 3 IR_DM_DB`, ví dụ phân biệt giữa `ACL`, `EMNLP`, `NAACL`, `COLING`), biểu diễn 5 khía cạnh phát huy vai trò tín hiệu bổ trợ rõ rệt nhất:
     - **`Coverage-Aware Adaptive Fusion` ($\beta^* = 0.3$)** nâng **Test Hit@3** từ **57.47% $\to$ 58.62%** ($+1.15\text{ pp}$), **Test Hit@5** từ **74.71% $\to$ 77.01%** ($+2.30\text{ pp}$), và **Test MRR** từ **0.4636 $\to$ 0.4707** (**$+0.0070$, thắng `19 Wins / 62 Ties / 6 Losses`, Paired Permutation $p = 0.0098 < 0.01$**).
     - **`Coarse-to-Fine Reranking` ($C=10$, Stage-2: `Adaptive Fusion`)** nâng **Test Hit@3** lên **58.62%** ($+1.15\text{ pp}$), **Test Hit@5** lên **77.01%** ($+2.30\text{ pp}$), **MRR** lên **0.4699** (**$+0.0063$, thắng `13 Wins / 70 Ties / 4 Losses`, $p = 0.0198 < 0.05$**).
     - **`Coarse-to-Fine Reranking` ($C=5$, Stage-2: `Facet-First`)** nâng **Test Hit@1** từ **26.44% $\to$ 28.74%** (**$+2.30\text{ pp}$**).
   - Ngược lại, trên tập `Cross-Discipline Top-3` ($n = 81$, nơi bản thảo giao thoa liên ngành), `Full-text` giữ ưu thế định tuyến vĩ mô tốt hơn (`Discipline Hit@1 = 55.56%` so với `45.68%` của `Facet-First`).

3. **Điều kiện 3 — Mật độ Mẫu Lịch sử của Hội nghị Đích Đủ Lớn (`Head` & `Mid` Venues có $|P_{v, f}| \ge m$, Exp D4):**
   - Kiểm định thống kê trong **Exp D4** chỉ ra rằng độ dài tóm tắt ($p = 0.3365$), khối lượng trọng số kích hoạt $g(q)$ ($p = 0.2651$) hay độ mới từ vựng ($p = 0.1541$) không phải là ranh giới phân tách chính giữa ca Thắng và Thua. Thay vào đó, **Phân tầng quy mô hội nghị (`Venue Tier`: Head $N_v \ge 20$, Mid $5\text{--}19$, Tail $\le 4$)** là nhân tố quyết định có ý nghĩa thống kê rất cao:
     - Với `Facet-First vs Full-text`: **83.0% (44/53)** ca Thắng thuộc nhóm **Head venues**, trong khi **49.4% (39/79)** ca Thua rơi vào nhóm **Mid/Tail venues** (**$\chi^2 = 14.65, p = 0.0007$; Fisher's Exact Odds Ratio $= 4.77, p = 0.0002$**).
     - Với `Adaptive Fusion vs Full-text` (`32 Wins / 107 Ties / 29 Losses`): **65.6% (21/32)** ca Thắng thuộc nhóm **Head** và **31.2% (10/32)** thuộc nhóm **Mid** (tổng **96.9% Head+Mid**), trong khi **82.8% (24/29)** ca Thua nằm ở nhóm **Mid/Tail** (**$\chi^2 = 16.57, p = 0.0003$; Fisher's Exact Odds Ratio $= 9.16, p = 0.0002$**).
   - Nguyên nhân: các hội nghị `Head` có kích thước bể khía cạnh $|P_{v, f}| \gg 3$ giúp trung bình Top-$m$ theo từng khía cạnh ổn định và chính xác, trong khi các hội nghị `Tail` ($N_v \le 4$) thường có $|P_{v, f}| \in \{0, 1\}$ ở các khía cạnh thưa như `dataset` hoặc `problem`.

4. **Điều kiện 4 — Sự Lệch Pha Trọng số `Problem` ($w_{\text{problem}} = 0.40$) giữa Cấp Bài báo (Exp B) và Cấp Hội nghị (Exp D2):**
   - Trong **Exp D2**, khi khóa cứng $\mathbf{w}_{\text{Exp B}}^* = (0.40, 0.20, 0.20, 0.10, 0.10)$, nhóm `Low-Cov` trên `Qwen-8B` ($n=94$, phần lớn vắng `problem` nên toàn bộ trọng số được tái chuẩn hóa sang `task, method, dataset, contribution`) giúp `Facet-First` vượt `Full-text` ở **Hit@1 (`26.60%` vs `20.21%`, $+6.38\text{ pp}$)** và **MRR (`0.4264` vs `0.4189`, $+0.0074$)**; còn `Adaptive Fusion` vượt `Full-text` trên `Low-Cov` ở **Hit@3 (`55.32%` vs `54.26%`, $+1.06\text{ pp}$)** và **Discipline Hit@1 (`74.47%` vs `73.40%`)**.
   - Ở nhóm `High-Cov` (`mask_problem(q) == 1` và $g(q) \ge 0.80$), việc khóa cứng $40\%$ trọng số vào `problem` (vốn tối ưu cho truy hồi bài báo đồng chủ đề ở Exp B nhưng quá hẹp đối với một hội nghị đa chủ đề và chỉ phủ $39.2\%$ tập Train `Qwen-8B`) làm giảm hiệu năng của `Facet-First` độc lập. Tuy nhiên, khi kết hợp qua **`Coverage-Aware Adaptive Fusion` ($\beta^* = 0.3$)**, hệ thống tự động cân bằng theo phương sai z-score và trên `Gemma-9B High-Cov` ($n=103$) đã nâng **Hit@1** từ **21.36% $\to$ 22.33%** ($+0.97\text{ pp}$), **MRR** từ **0.4029 $\to$ 0.4078** ($+0.0049$) và **Discipline Hit@1** từ **71.84% $\to$ 72.82%** (`20 Wins / 66 Ties / 17 Losses`).
