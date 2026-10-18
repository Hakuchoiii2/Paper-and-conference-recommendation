# D: kết quả benchmark cặp intent và proposal

**Kết luận:** có bằng chứng cho cả suy hướng và tác dụng direction lên ranking trong benchmark cơ chế mới; kết luận có điều kiện trên corpus nhỏ và simulator, chưa phải hiệu quả người thật hay generalization trên anchors mới.

## 1. Vì sao cần phép thử mới?

Bộ canonical cũ có 750/750 phiên different không có candidate grade 1, nên chưa tách rõ context khỏi direction. Bộ mới giữ nguyên corpus/facet thật nhưng tạo các phiên mô phỏng mới có cả ứng viên đúng và sai hướng trong cùng context. Không sửa dữ liệu/nhãn/kết quả cũ.

Thiết kế đã ghi trước khi tính metrics: tất cả 15 tổ hợp khả thi/8 anchors, 2 directions × 3 query modes = 90 phiên. Mỗi pool gồm 1 same-focus cùng context, 1 different-focus cùng context và 18 ngoài context; có 1 grade 2 và 1 grade 1 ở mọi phiên. Cặp similar/different giữ nguyên user, cutoff, anchor, context, candidates; chỉ intent và query/phản ứng tương ứng khác nhau.

Không thể tạo thiết kế ban đầu 1 same/9 different trong corpus; kết quả thiếu hụt được giữ ở audit. Không tạo paper/facet giả để ép quota. Các focus có dữ liệu: task, method, dataset, contribution; không có problem.

Source target 1.500 phiên còn shortfall 1.410: bundle là diagnostic riêng, không tự nhận canonical complete. Synthetic chỉ dành cho observation, 4 cặp/phiên, 3 seed × 2 noise. `check_d` hiện hành kiểm tra cả bộ không observation và sáu overlay.

## 2. Luận điểm 1: evidence giúp suy facet và hướng

| Cấu hình | Accuracy behavior | Coverage behavior | Accuracy không observation | Accuracy xáo (10 lần) |
|---|---:|---:|---:|---:|
| seed_42_noise_0.2 | 1.0000 | 1.0000 | 0.0000 | 0.3300 |
| seed_42_noise_0.5 | 0.8778 | 0.9333 | 0.0000 | 0.3533 |
| seed_43_noise_0.2 | 1.0000 | 1.0000 | 0.0000 | 0.3478 |
| seed_43_noise_0.5 | 0.9111 | 0.9222 | 0.0000 | 0.3867 |
| seed_44_noise_0.2 | 1.0000 | 1.0000 | 0.0000 | 0.3267 |
| seed_44_noise_0.5 | 0.9111 | 0.9667 | 0.0000 | 0.3756 |

Unknown được tính là chưa đúng. Xáo giữ timestamps, IDs và số lượng action trong phiên; phản ứng gắn đúng bài là điều tạo tín hiệu dưới simulator. Query rõ hỗ trợ search; ambiguous/none giữ thiếu evidence đúng thiết kế. Không suy ra hành vi người thật từ kết quả này.

## 3. Luận điểm 2: tác dụng riêng của direction

Đối chứng giữ nguyên proposal scorer, focus dự đoán, C weights, context/missingness gate và secondary score không phụ thuộc direction. Chỉ đổi focus direction giữa predicted / always-similar / flipped. Bảng seed 42, noise 0,2:

| Model | nDCG@10 | Compliance@1 (chẩn đoán thêm) | Compliance@5 |
|---|---:|---:|---:|
| direction_behavior | 0.8208 | 0.5000 | 0.1800 |
| direction_search | 0.8208 | 0.5000 | 0.1800 |
| strict_behavior_similar | 0.8142 | 0.4556 | 0.1800 |
| strict_behavior_predicted | 0.8208 | 0.5000 | 0.1800 |
| proposal_behavior_predicted | 1.0000 | 1.0000 | 0.2000 |
| proposal_behavior_similar | 0.8984 | 0.5000 | 0.2000 |
| proposal_behavior_flipped | 0.7967 | 0.0000 | 0.2000 |
| proposal_search_predicted | 1.0000 | 1.0000 | 0.2000 |
| proposal_search_similar | 0.8984 | 0.5000 | 0.2000 |

Primary chốt trước chạy là nDCG@10; compliance@1 chỉ bổ sung để quan sát việc đưa bài đúng lên đầu. Compliance@5 có trần 0,2 vì chỉ một bài grade 2; khi bài đó đã nằm trong top 5, đổi vị trí từ thứ 2 lên thứ 1 không làm chỉ số này tăng. @10 có trần 0,1. Không sửa metric/nhãn để làm tăng điểm.

Delta predicted − always-similar, trung bình ba seed trước khi bootstrap theo 8 anchors:

| Noise | Nhánh / nhóm | Metric | Delta | CI 95% theo anchor | Leave-one-anchor-out min–max |
|---|---|---|---:|---|---|
| 0.2 | strict_behavior_predicted / overall | ndcg@10 | +0.006513 | [-0.0007897628832633748, 0.030493862851424004] | [-0.00028205817259406243, 0.010855266120936645] |
| 0.2 | strict_behavior_predicted / intent_different | ndcg@10 | +0.013026 | [-0.0015795257665267497, 0.06098772570284801] | [-0.0005641163451881249, 0.02171053224187329] |
| 0.2 | proposal_behavior_predicted / overall | ndcg@10 | +0.101646 | [0.10164620950474663, 0.1016462095047467] | [0.1016462095047466, 0.10164620950474662] |
| 0.2 | proposal_behavior_predicted / intent_different | ndcg@10 | +0.203292 | [0.20329241900949327, 0.2032924190094934] | [0.2032924190094932, 0.20329241900949324] |
| 0.5 | strict_behavior_predicted / overall | ndcg@10 | +0.003221 | [-0.003889253855618465, 0.020329241900949334] | [-0.0013890192341494518, 0.005368652265748754] |
| 0.5 | strict_behavior_predicted / intent_different | ndcg@10 | +0.012641 | [0.0, 0.05510292148598963] | [0.0006368641072319524, 0.02106894110601448] |
| 0.5 | proposal_behavior_predicted / overall | ndcg@10 | +0.087340 | [0.07968560868581992, 0.09788153507864494] | [0.08376400598076345, 0.0916070777018087] |
| 0.5 | proposal_behavior_predicted / intent_different | ndcg@10 | +0.185222 | [0.1761867631415609, 0.19764540737034078] | [0.1807043724528829, 0.19074350425582084] |

CI và leave-one-out chỉ mô tả độ ổn định trong cohort 8 anchors này; không đại diện cho toàn bộ khoa học hoặc người dùng. Strict scorer vẫn là đối chứng quan trọng: hướng đúng không tự bảo đảm tổng score mềm/gate gốc chuyển nó thành cải thiện. Không dùng mức tăng giữa hai scorer để quy hết cho direction.

## 4. Proposal đề xuất

**Evidence-guided facet reranking:** suy focus/hướng bằng evidence trước cutoff; thiếu hoặc xung đột thì fallback; khi đủ evidence, giữ context, active context/focus, ưu tiên ứng viên thỏa hướng, dùng profile C làm tie-break không phụ thuộc direction. Chi tiết tại docs/proposal.md.

Proposal là phương pháp quy tắc có thể giải thích, chưa phải thuật toán mới đã được xác nhận với semantic/human relevance. Việc đạt điểm cao khi dự đoán đúng là kỳ vọng vì ranking ưu tiên trực tiếp điều kiện của nhãn overlap. Giá trị thực nghiệm là đo estimator/noise/fallback và tách direction khỏi context bằng các đối chứng công bằng.

## 5. Luận điểm có thể đưa vào báo cáo

> Trong benchmark mô phỏng cặp intent đối lập, phản ứng đầu phiên cho phép suy facet và hướng similar/different tốt hơn khi không có hoặc xáo phản ứng; với cùng ranker đề xuất và candidate pool có bài cạnh tranh hai hướng, directions dự đoán cải thiện nDCG@10 so với luôn-similar, cho thấy tác dụng của intent lên thứ tự khuyến nghị trong điều kiện được kiểm soát.

Kèm giới hạn bắt buộc: 8 anchors đã xuất hiện ở dữ liệu trước, episodes mới nhưng không phải corpus/anchor untouched; 4/5 focus; label/evidence mô phỏng và ưu tiên overlap; không chứng minh hiệu quả người dùng thật, semantic relevance độc lập hoặc novelty so với toàn bộ nghiên cứu trước.

## 6. Việc tiếp theo và tái lập

- Giữ cả kết quả null của canonical cũ và kết quả cơ chế mới; không thay số giữa hai benchmark để tuyên bố tăng thuật toán.
- Mở rộng corpus thật và tạo phần giữ riêng trước nghiên cứu tiếp, đặc biệt thêm problem-focus và nhiều ứng viên đối lập cùng context; review semantic relevance độc lập.
- Không tune trọng số/ngưỡng trên bundle này. Nếu thêm supervised ranker, cần split và ngân sách nhãn train riêng.
- Code mới: scripts/exp_d/run_contrast_proposal.py, proposal_ranker.py; generator data/exp_d/build_contrast_sessions.py. Không sửa baseline, A/C, source corpus, validator hoặc config chung.

```powershell
python -B -m unittest discover -s scripts/exp_d -p test_contrast_proposal.py
python -B scripts/exp_d/run_contrast_proposal.py
python -B scripts/exp_d/summarize_contrast_proposal.py
```

Các lệnh không ghi đè output. Output chính ở data/exp_d/results/contrast_proposal_20261016_v1/. Manifest suite và analysis theo dõi input/code/output riêng.
