# D v2: mở rộng pool nhiều ứng viên thật

**Phạm vi:** bộ phụ chẩn đoán trên 8 anchors đã dùng; giữ v1 và dữ liệu canonical.

## Thiết kế đã chốt trước prediction v2

- 15 thiết kế / 8 anchors / 90 phiên / 20 candidates mỗi phiên.
- Giữ same và different của v1; thay outside bằng different bổ sung đến tối đa 5 bài.
- 9 thiết kế giữ 1 different; 2 thiết kế có 2; 4 thiết kế có 5. Không bỏ thiết kế theo điểm.
- 6 thiết kế / 5 anchors được mở rộng; vẫn chỉ 4/5 loại focus, không có problem.
- Query, intent, cutoff, C profiles, TF-IDF và phản ứng/observation giữ nguyên v1.
- 3 seed × 2 noise; không observation và xáo phản ứng giữ làm đối chứng.
- Không thay scorer, nhãn overlap, evaluator, validator hoặc thresholds.
- Xáo phản ứng tái sử dụng kết quả v1 đã kiểm hash vì evidence hoàn toàn giống nhau.

## Kết quả chính: cùng pool v2, cùng proposal, chỉ thay hướng

| Noise | Nhóm | Δ nDCG@10 | CI 95% theo anchor | Δ compliance@5 |
|---|---|---:|---|---:|
| 0.2 | overall | 0.092007 | [0.084690; 0.098108] | 0.026667 |
| 0.2 | intent_similar | 0.000000 | [0.000000; 0.000000] | 0.000000 |
| 0.2 | intent_different | 0.184015 | [0.169379; 0.196215] | 0.053333 |
| 0.2 | expanded | 0.077549 | [0.069965; 0.088166] | 0.066667 |
| 0.2 | expanded_intent_different | 0.155098 | [0.139931; 0.176332] | 0.133333 |
| 0.5 | overall | 0.078795 | [0.067291; 0.092513] | 0.022222 |
| 0.5 | intent_similar | -0.010833 | [-0.019450; 0.000000] | -0.001481 |
| 0.5 | intent_different | 0.168423 | [0.150595; 0.188899] | 0.045926 |
| 0.5 | expanded | 0.067106 | [0.053962; 0.084045] | 0.055556 |
| 0.5 | expanded_intent_different | 0.138708 | [0.118553; 0.168091] | 0.114815 |

Primary là overall Δ nDCG@10 behavior predicted − always-similar, chốt trước chạy.
Trung bình ba seed tại từng phiên trước cluster bootstrap 2.000 lần theo anchor.
CI nhóm phụ là mô tả, chưa điều chỉnh nhiều phép so; 8 anchors không đại diện ngoài phân bố.

## Điểm tuyệt đối theo từng cấu hình

| Cấu hình | Model | nDCG@10 | Compliance@5 | Intent recall@5 (phụ) |
|---|---|---:|---:|---:|
| seed_42_noise_0.2 | direction_behavior | 0.785149 | 0.220000 | 0.833333 |
| seed_42_noise_0.2 | direction_search | 0.785149 | 0.220000 | 0.833333 |
| seed_42_noise_0.2 | proposal_behavior_flipped | 0.798503 | 0.266667 | 0.840000 |
| seed_42_noise_0.2 | proposal_behavior_predicted | 1.000000 | 0.320000 | 1.000000 |
| seed_42_noise_0.2 | proposal_behavior_similar | 0.907993 | 0.293333 | 0.973333 |
| seed_42_noise_0.2 | proposal_search_predicted | 1.000000 | 0.320000 | 1.000000 |
| seed_42_noise_0.2 | proposal_search_similar | 0.907993 | 0.293333 | 0.973333 |
| seed_42_noise_0.2 | strict_behavior_predicted | 0.785149 | 0.220000 | 0.833333 |
| seed_42_noise_0.2 | strict_behavior_similar | 0.775691 | 0.213333 | 0.826667 |
| seed_42_noise_0.5 | direction_behavior | 0.777588 | 0.217778 | 0.822222 |
| seed_42_noise_0.5 | direction_search | 0.779847 | 0.217778 | 0.822222 |
| seed_42_noise_0.5 | proposal_behavior_flipped | 0.811717 | 0.271111 | 0.853333 |
| seed_42_noise_0.5 | proposal_behavior_predicted | 0.977605 | 0.315556 | 0.986667 |
| seed_42_noise_0.5 | proposal_behavior_similar | 0.905661 | 0.293333 | 0.973333 |
| seed_42_noise_0.5 | proposal_search_predicted | 0.984454 | 0.315556 | 0.986667 |
| seed_42_noise_0.5 | proposal_search_similar | 0.907993 | 0.293333 | 0.973333 |
| seed_42_noise_0.5 | strict_behavior_predicted | 0.777588 | 0.217778 | 0.822222 |
| seed_42_noise_0.5 | strict_behavior_similar | 0.775691 | 0.213333 | 0.826667 |
| seed_43_noise_0.2 | direction_behavior | 0.785149 | 0.220000 | 0.833333 |
| seed_43_noise_0.2 | direction_search | 0.785149 | 0.220000 | 0.833333 |
| seed_43_noise_0.2 | proposal_behavior_flipped | 0.798503 | 0.266667 | 0.840000 |
| seed_43_noise_0.2 | proposal_behavior_predicted | 1.000000 | 0.320000 | 1.000000 |
| seed_43_noise_0.2 | proposal_behavior_similar | 0.907993 | 0.293333 | 0.973333 |
| seed_43_noise_0.2 | proposal_search_predicted | 1.000000 | 0.320000 | 1.000000 |
| seed_43_noise_0.2 | proposal_search_similar | 0.907993 | 0.293333 | 0.973333 |
| seed_43_noise_0.2 | strict_behavior_predicted | 0.785149 | 0.220000 | 0.833333 |
| seed_43_noise_0.2 | strict_behavior_similar | 0.775691 | 0.213333 | 0.826667 |
| seed_43_noise_0.5 | direction_behavior | 0.785149 | 0.220000 | 0.833333 |
| seed_43_noise_0.5 | direction_search | 0.785149 | 0.220000 | 0.833333 |
| seed_43_noise_0.5 | proposal_behavior_flipped | 0.802564 | 0.266667 | 0.857778 |
| seed_43_noise_0.5 | proposal_behavior_predicted | 0.983129 | 0.313333 | 0.993333 |
| seed_43_noise_0.5 | proposal_behavior_similar | 0.897194 | 0.288889 | 0.968889 |
| seed_43_noise_0.5 | proposal_search_predicted | 0.991194 | 0.320000 | 1.000000 |
| seed_43_noise_0.5 | proposal_search_similar | 0.901446 | 0.293333 | 0.973333 |
| seed_43_noise_0.5 | strict_behavior_predicted | 0.785149 | 0.220000 | 0.833333 |
| seed_43_noise_0.5 | strict_behavior_similar | 0.775691 | 0.213333 | 0.826667 |
| seed_44_noise_0.2 | direction_behavior | 0.785149 | 0.220000 | 0.833333 |
| seed_44_noise_0.2 | direction_search | 0.785149 | 0.220000 | 0.833333 |
| seed_44_noise_0.2 | proposal_behavior_flipped | 0.798503 | 0.266667 | 0.840000 |
| seed_44_noise_0.2 | proposal_behavior_predicted | 1.000000 | 0.320000 | 1.000000 |
| seed_44_noise_0.2 | proposal_behavior_similar | 0.907993 | 0.293333 | 0.973333 |
| seed_44_noise_0.2 | proposal_search_predicted | 1.000000 | 0.320000 | 1.000000 |
| seed_44_noise_0.2 | proposal_search_similar | 0.907993 | 0.293333 | 0.973333 |
| seed_44_noise_0.2 | strict_behavior_predicted | 0.785149 | 0.220000 | 0.833333 |
| seed_44_noise_0.2 | strict_behavior_similar | 0.775691 | 0.213333 | 0.826667 |
| seed_44_noise_0.5 | direction_behavior | 0.781697 | 0.215556 | 0.828889 |
| seed_44_noise_0.5 | direction_search | 0.782293 | 0.217778 | 0.831111 |
| seed_44_noise_0.5 | proposal_behavior_flipped | 0.806288 | 0.266667 | 0.848889 |
| seed_44_noise_0.5 | proposal_behavior_predicted | 0.981195 | 0.308889 | 0.988889 |
| seed_44_noise_0.5 | proposal_behavior_similar | 0.902689 | 0.288889 | 0.968889 |
| seed_44_noise_0.5 | proposal_search_predicted | 0.983802 | 0.311111 | 0.991111 |
| seed_44_noise_0.5 | proposal_search_similar | 0.903741 | 0.288889 | 0.968889 |
| seed_44_noise_0.5 | strict_behavior_predicted | 0.781697 | 0.215556 | 0.828889 |
| seed_44_noise_0.5 | strict_behavior_similar | 0.775691 | 0.213333 | 0.826667 |

## Suy intent và giới hạn trần pool

Focus accuracy/coverage/F1 giữ nguyên v1: chỉ thay candidates, không thay evidence hoặc estimator.

| Cấu hình | Behavior focus accuracy | Behavior focus coverage |
|---|---:|---:|
| seed_42_noise_0.2 | 1.000000 | 1.000000 |
| seed_42_noise_0.5 | 0.877778 | 0.933333 |
| seed_43_noise_0.2 | 1.000000 | 1.000000 |
| seed_43_noise_0.5 | 0.911111 | 0.922222 |
| seed_44_noise_0.2 | 1.000000 | 1.000000 |
| seed_44_noise_0.5 | 0.911111 | 0.966667 |

| Intent | Trần compliance@5 trung bình |
|---|---:|
| similar | 0.200000 |
| different | 0.440000 |

Compliance v2 cao hơn v1 không tự chứng minh thuật toán tốt hơn: v2 có nhiều grade 2 hơn.
So v1/v2 chỉ là độ nhạy theo thành phần pool; xem analysis/pool_effects.csv.
Các bài cùng grade có gain bằng nhau; nDCG không đánh giá thứ tự nội bộ giữa chúng.
Proposal vẫn có thể đạt nDCG=1 khi suy đúng hướng vì ưu tiên đúng quy tắc overlap của nhãn.

## Kết luận và cách dùng trong báo cáo

Primary dương và CI theo anchor nằm trên 0 ở cả hai mức nhiễu.
V2 mở rộng kiểm chứng từ một sang nhiều bài thỏa intent ở một phần cohort; không tăng anchors độc lập.
Đối chứng strict scorer được giữ đầy đủ; không quy chênh lệch giữa hai scorer thành hiệu ứng riêng của direction.

| Noise | Strict Δ nDCG@10 overall | CI 95% | Proposal leave-one-anchor-out |
|---|---:|---|---|
| 0.2 | 0.009458 | [0.0, 0.035468444872739646] | [0.08959764766214358, 0.09358178365390635] |
| 0.5 | 0.005787 | [0.0, 0.02223331597340021] | [0.07308226295092547, 0.08323156481007518] |

Cách diễn đạt phù hợp: “Trong benchmark overlap mô phỏng có pool nhiều ứng viên ở một phần thiết kế,
chúng tôi đánh giá tác dụng của hướng suy được bằng các đối chứng giữ nguyên ranker, trọng số và bằng chứng.”
Kèm số liệu đạt/không đạt ở trên; không suy ra semantic relevance, người dùng thật, novelty hoặc khả năng nhận bài.
Muốn khẳng định tổng quát hơn cần anchors/corpus giữ riêng và relevance được đánh giá độc lập.

## Kiểm tra và tái lập

- verification.json: kiểm nguồn, replay hướng/profile, ba arms, fallback, sáu overlays và v1 không đổi.
- manifest.json: hashes code/input/output; design.json: quyết định trước prediction v2.
- analysis/seed_averaged_comparisons.json: CI, leave-one-anchor-out và delta từng anchor.
- analysis/pool_ceilings.json: trần compliance từng phiên; ground_truth/pool_changes.jsonl: thay đổi IDs.

```powershell
python -B -m unittest discover -s scripts/exp_d -p test_multicandidate_proposal.py
python -B scripts/exp_d/run_multicandidate_proposal.py --output data/exp_d/results/my_multicandidate_v2
python -B scripts/exp_d/run_multicandidate_proposal.py --verify-only --output data/exp_d/results/multicandidate_proposal_20261017_v2
```

Mỗi lượt dùng output mới; không ghi đè. Không sửa dữ liệu hoặc kết quả cũ để cải thiện điểm.
