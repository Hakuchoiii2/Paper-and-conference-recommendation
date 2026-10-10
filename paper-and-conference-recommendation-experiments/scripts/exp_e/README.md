# Exp E — Cập nhật profile theo thời gian

[Chỉ mục script](../README.md) · [Generator E](../../data/exp_e/README.md) · [Profile C](../exp_c/README.md) · [Giao diện chung](../BASELINE_GUIDE.md)

## 1. E khác C/D ở đâu?

C kiểm tra profile tại một cutoff, D kiểm tra hướng phiên. E giữ profile builder/ranker C, thay **cách cân thời gian evidence** để đo thích ứng khi sở thích đổi.

E dùng users C rồi sinh stream/profile riêng. Không cần predictions/checkpoint model C hoặc kết quả D. Có popularity/static/recent/decay; chưa có encoder/model học drift.

## 2. Dữ liệu và mốc đánh giá

300 users, bốn kỳ tháng, 15 events/kỳ/user; 150 stable, 150 drift. Group và true profiles được giấu trong ground_truth.

| Case | Cutoff | Lịch sử hợp lệ | Candidates |
|---|---|---|---|
| Kỳ 2 | Đầu tháng 2 | Kỳ 1 | 15 bài kỳ 2 |
| Kỳ 3 | Đầu tháng 3 | Kỳ 1–2 | 15 bài kỳ 3 |
| Kỳ 4 | Đầu tháng 4 | Kỳ 1–3 | 15 bài kỳ 4 |

Scorer nhận corpus/facets, history/search/exposure **trước cutoff**, user_id, period, candidate_ids. Evaluator đọc temporal_profiles, phản ứng tương lai và period_metadata.

900 cases = 300 users × 3 mốc. History chứa kỳ 1–3, truth kỳ 2–4; kỳ 2/3 có bản sao để chấm hiện tại rồi làm lịch sử mốc sau. Tổng **18.000 phản ứng độc lập**, không cộng thành 27.000.

## 3. Generator đổi profile thật thế nào?

Profile cũ/mới có trước hành vi. Drift nội suy concept preferences và importance bằng **[0,.5,1,1]** qua bốn kỳ; stable giữ profile cũ.

Kỳ 1 hướng cũ, kỳ 2 chuyển tiếp, kỳ 3–4 hướng mới. Query/exposure/feedback sinh theo profile từng kỳ cộng noise. Đây là drift mô phỏng, không phải label drift do model suy ra.

Chi tiết ở [generator E](../../data/exp_e/README.md).

## 4. Cùng profile C, khác thời gian thế nào?

Vẫn signed feedback −1/0/1/2/3, query include/exclude +1/−1, concept counts, mass → importance, unit vectors và dot-product ranking như C.

| Model | Evidence trước cutoff |
|---|---|
| `popularity` | Tổng phản ứng dương toàn bộ users |
| `static` | Toàn bộ quá khứ, time weight 1 |
| `recent` | Chỉ kỳ ngay trước cutoff |
| `decay` | Toàn bộ quá khứ, giảm weight theo tuổi |

**Static vẫn tính lại khi có history mới**, không đóng băng profile ở kỳ 1.

```text
time_weight = 2 ^ (−age_days / half_life_days)
evidence_weight = feedback_or_query_weight × time_weight
```

Half-life mặc định 30 ngày: tuổi 30 ngày còn .5, 60 ngày còn .25. Cả reactions và queries đều decay.

Sau khi cộng evidence, mỗi model tính lại vectors/importance. Candidate score giữ công thức importance × dot với binary concept vector của bài.

## 5. Ví dụ thay đổi ranking

Giả sử method có ba GNN likes (+3 mỗi lần) tuổi 60 ngày, hai LLM saves (+2 mỗi lần) tuổi 5 ngày:

| Model | Evidence GNN | Evidence LLM | Ưu tiên trong ví dụ |
|---|---:|---:|---|
| Static | 9 | 4 | GNN |
| Decay, half-life 30 | 9×.25 = 2.25 | 4×2^(−5/30) ≈ 3.56 | LLM |
| Recent | 0 nếu GNN ngoài kỳ trước | 4 | LLM |

Vectors vẫn normalize như C. Nếu sở thích đổi sang LLM, recent/decay có thể giúp; user stable hoặc evidence mới ít/nhiễu có thể phù hợp static hơn. Không mặc định decay phải thắng.

## 6. Runner và evaluator

1. Kiểm tra corpus/A, C handoff và E manifests.
2. Nhóm cases theo cutoff kỳ 2/3/4.
3. Lọc reactions/queries/exposures timestamp < cutoff.
4. recent_start = đầu kỳ trước; half-life lấy từ CLI.
5. Tạo bốn model từ cùng prefix, xếp 15 ứng viên.
6. Evaluator đổi phản ứng kỳ được chấm thành relevance 0/0/1/2/3.
7. So importance với latent weights đúng user/kỳ.
8. Tổng hợp overall và các nhóm/kỳ.

Tháng 2 chưa dùng feedback tháng 2 dù có trong history file; sang tháng 3 mới được dùng. Không truyền nguyên interactions_train vào mọi mốc.

Baseline không training neural. Model online bổ sung chỉ cập nhật bằng evidence trước mốc chấm; không tune theo kỳ test đang báo cáo.

## 7. So sánh và output

So **nDCG/Recall/Precision/MRR@5/10**, **importance_mae** của static/recent/decay; popularity MAE N/A.

Report có overall, stable/drift, period_2/3/4 và stable/drift từng kỳ:

- Drift: recent/decay theo profile mới hơn static không?
- Stable: giảm/bỏ quá khứ có mất tín hiệu hữu ích không?

MAE thấp = gần latent weights; ranking tốt = bài có feedback tích cực/cao lên trước. Concept preference có thể đổi mạnh dù importance đổi ít, nên đọc cả hai.

Đủ quota có 3.600 predictions. Đọc report.md/report.json/details.jsonl; [baseline guide](../BASELINE_GUIDE.md) giải thích sáu tệp.

## 8. Chạy

```powershell
python data/exp_e/build_exp_e.py --dry-run
python data/exp_e/build_exp_e.py
python data/exp_e/build_exp_e.py --validate-only
python scripts/exp_e/run_exp_e.py --dry-run
python scripts/exp_e/run_exp_e.py --ks 5 10 --half-life-days 30
```

Output dưới `results/exp_e/`; dùng output mới/overwrite. So half-life khác phải giữ dataset/cutoff; chọn tham số trên phần phát triển riêng.

## 9. Thành viên E bổ sung gì?

Dùng cùng encoder freeze/profile representation đã thống nhất rồi so static/recent/decay trong không gian ngữ nghĩa. Chưa cần model drift mới để chạy baseline.

Adaptive decay/change detection là hướng riêng nếu muốn vượt baseline. Giữ nguồn search/reactions và ranker để phép so rõ ràng. Đổi encoder và time rule cùng lúc cần ablation để biết nguyên nhân.

E dùng helper C nhưng có câu hỏi, stream, cutoff và phép so riêng. Dataset C complete là prerequisite; phương pháp mới của thành viên C không chặn E.
