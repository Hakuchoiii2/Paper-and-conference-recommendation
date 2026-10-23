# Dữ liệu E — Stable/drift và rolling holdout

[Chỉ mục dữ liệu](../README.md) · [Scorer E](../../scripts/exp_e/README.md) · [Dữ liệu C](../exp_c/README.md)

## 1. Generator phục vụ câu hỏi nào?

E tạo sở thích ổn định/thay đổi theo kỳ, query/exposure/phản ứng và các case rolling. Scorer so static/recent/decay trên cùng stream, không dự đoán từ nhãn drift được cung cấp sẵn.

E dùng **danh tính C** rồi tạo profiles/logs riêng. Không dùng kết quả scorer C hay dữ liệu D.

## 2. Đầu vào và quy mô

Corpus canonical + full silver A/metadata/complete manifest; C users.jsonl và complete handoff được kiểm tra hashes/config/provenance.

Config `configs/exp_e.json`: seed 42, stable_fraction .5, drift_coefficients [0,.5,1,1], 15 events/user/kỳ. Boundaries: đầu tháng 1/2/3/4/5 năm 2026.

Với 300 users C: 150 stable/150 drift, bốn kỳ, **18.000 reactions độc lập**, 1.200 hidden profiles và 900 cases đánh giá kỳ 2/3/4.

## 3. Sinh profile thật từng kỳ

1. Xáo user IDs theo seed để chia stable/drift.
2. Với mỗi user, sinh old/new concept preferences và importance bằng cùng quy tắc profile C.
3. Stable dùng coefficient 0 mọi kỳ; drift dùng [0,.5,1,1].
4. Trên hợp concepts old/new, nội suy:
   preference(c) = (1−a)×old(c) + a×new(c).
5. Importance cũng nội suy old/new rồi normalize.
6. Lưu user_id, period, start/end, latent_preferences và facet_importance.

Concept có preference 0 sau nội suy không góp targeted exposure. Bài không có concept trong profile vẫn có thể được lấy từ pool chung. Không đưa nhãn stable/drift hoặc profile thật cho scorer.

## 4. Sinh hành vi trong từng kỳ

Phân bố 15 timestamps trong khoảng kỳ, giữ query trước reaction 2 giây và exposure trước 1 giây. Từng kỳ gọi simulator như C: targeted .8, search .6, bốn bài/exposure, feedback từ utility + noise .15 và thresholds −.25/.05/.2/.4.

Bài có phản ứng không lặp trong cùng chuỗi kỳ/user; giữa các kỳ có thể xuất hiện lại. Các bài hiển thị nhưng chưa phản ứng không tự là negative.

Cùng source users không có nghĩa profile/stream E là bản copy C. Mục tiêu E là đo thời gian với ground truth đổi có kiểm soát.

## 5. Lưu history/truth để rolling thế nào?

| Kỳ | Có trong history files? | Có trong truth files? | Vai trò |
|---|---|---|---|
| 1 | Có | Không | Quan sát trước case kỳ 2 |
| 2 | Có | Có | Truth kỳ 2; history cho kỳ 3/4 |
| 3 | Có | Có | Truth kỳ 3; history cho kỳ 4 |
| 4 | Không | Có | Truth kỳ 4 |

History reactions = 300×3×15 = 13.500; truth reactions cũng 13.500; overlap kỳ 2/3 = 9.000. Không cộng hai tệp thành 27.000 phản ứng độc lập. Các bản sao overlap phải giống nhau.

Scorer tháng 2 chỉ nhận kỳ 1; tháng 3 nhận kỳ 1–2; tháng 4 nhận kỳ 1–3. Runner lọc timestamp < cutoff dù history file có dữ liệu của mốc sau.

## 6. Case và tệp đầu ra

Mỗi case chứa case_id, user_id, period, cutoff = đầu kỳ và 15 candidate_ids của kỳ đó. Chỉ IDs quan sát được; feedback tương lai giữ trong truth.

| Phần | Tệp | Vai trò |
|---|---|---|
| generated | `interactions_train.jsonl` | Reactions kỳ 1–3 |
| generated | `search_events.jsonl`, `exposures.jsonl` | Logs kỳ 1–3 |
| generated | `cases.jsonl` | 900 rolling cases |
| ground_truth | `temporal_profiles.jsonl` | Profile thật mỗi user/kỳ |
| ground_truth | `interactions_test.jsonl` | Reactions kỳ 2–4 |
| ground_truth | `search_events_test.jsonl`, `exposures_test.jsonl` | Logs kỳ 2–4 |
| ground_truth | `period_metadata.json` | Groups, boundaries, drift coefficients |

Report/manifest ghi actual_users/events/profiles/cases, group_counts, history behavior_counts, hashes và handoff C. Evaluator dùng đúng period để ghép nhãn và chia cohort.

## 7. Sinh và kiểm tra

```powershell
python data/exp_e/build_exp_e.py --dry-run
python data/exp_e/build_exp_e.py
python data/exp_e/build_exp_e.py --validate-only
```

Từ gốc repository, Python 3.11+/stdlib. Dùng config/output mới cho [pilot E](samples/README.md). Loader vẫn yêu cầu C handoff complete dù E chỉ dùng IDs; không tách riêng users.jsonl rồi bỏ manifest.

Output 1.0 không trộn vào 2.0; không chạy đồng thời vào cùng output. E cần đủ distinct papers cho từng chuỗi mô phỏng, không sinh paper giả.

## 8. Bàn giao và chạy scorer

Bàn giao generated + ground_truth + config/manifest, giữ các bản sao rolling nhất quán. [Scorer E](../../scripts/exp_e/README.md) giải thích static/recent/decay, half-life, ví dụ score và các chỉ số.

Stable/drift là nhóm benchmark, không phải input của phương pháp. Điểm E chứng minh cách time weighting hoạt động trong simulator; chưa thay thế quan sát đổi sở thích người thật.
