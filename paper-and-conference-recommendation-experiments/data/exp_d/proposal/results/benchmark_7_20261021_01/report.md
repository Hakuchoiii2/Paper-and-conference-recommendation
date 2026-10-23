# Kết quả benchmark D — QUAN SÁT v1

Đã chạy 4,788 predictions: 7 cấu hình × 114 phiên × 6 điều kiện.
114 phiên chia sẻ 19 thiết kế và 12 anchors; không coi 684 lần đánh giá mỗi method là mẫu độc lập.
Bảng chính lấy trung bình các lần lặp trong thiết kế, rồi trung bình theo nhóm công trình anchor. Không train hoặc tune theo kết quả.

| Method | Accuracy hướng | Đúng cả focus+hướng | Coverage hướng | nDCG@10 |
|---|---:|---:|---:|---:|
| fixed_similar | 50.00% | 0.00% | 100.00% | 0.8029 |
| profile_similar | 50.00% | 0.00% | 100.00% | 0.8019 |
| query_only | 33.33% | 33.33% | 33.33% | 0.8164 |
| direction_behavior | 95.83% | 95.83% | 96.80% | 0.8412 |
| direction_search | 96.91% | 96.91% | 97.84% | 0.8418 |
| vote | 91.74% | 91.74% | 92.05% | 0.8390 |
| bayes_h | 91.51% | 91.51% | 91.82% | 0.8386 |

Unknown tính sai trong accuracy toàn bộ. Coverage hướng được evaluator đo tại focus thật; luôn-similar có coverage 100% nhưng không nhận ra focus cụ thể.
fixed_similar dùng trọng số đều; các dòng còn lại dùng cùng profile C. So proposal công bằng giữa direction_search, vote và bayes_h vì cùng query + phản ứng.

## Chênh lệch paired và khoảng bootstrap 95%

| Phép so | Chỉ số | Chênh lệch | Khoảng 95% theo nhóm anchor |
|---|---|---:|---:|
| reaction_vs_no_signal | direction_accuracy | +45.8333 điểm % | [+43.2079, +47.7623] |
| query_vs_no_signal | direction_accuracy | -16.6667 điểm % | [-16.6667, -16.6667] |
| query_added_to_reactions | direction_accuracy | +1.0802 điểm % | [+0.3858, +1.8519] |
| reactions_added_to_query | direction_accuracy | +63.5802 điểm % | [+61.3426, +65.0463] |
| directions_vs_no_signal | ndcg10 | +0.0399 | [+0.0104, +0.0686] |
| bayes_vs_delta | direction_accuracy | -5.4012 điểm % | [-7.0216, -3.9352] |
| bayes_vs_delta | ndcg10 | -0.0032 | [-0.0056, -0.0009] |
| bayes_vs_vote | direction_accuracy | -0.2315 điểm % | [-0.6944, +0.0000] |
| bayes_vs_vote | ndcg10 | -0.0005 | [-0.0014, +0.0000] |

Khoảng gồm 0 nghĩa là chưa chắc dấu cải thiện trong pilot. Đây không phải kiểm định trên anchors/người dùng độc lập chưa từng thấy.

## Cách đọc các luận điểm

- Phản ứng so với luôn-similar (direction_accuracy): tăng, khoảng theo nhóm nằm trên 0.
- Query so với luôn-similar (direction_accuracy): giảm, khoảng theo nhóm nằm dưới 0.
- Query bổ sung cho phản ứng (direction_accuracy): tăng, khoảng theo nhóm nằm trên 0.
- Phản ứng bổ sung cho query (direction_accuracy): tăng, khoảng theo nhóm nằm trên 0.
- Directions qua scorer gốc so với luôn-similar (ndcg10): tăng, khoảng theo nhóm nằm trên 0.
- BAYES-H so với DELTA có query (direction_accuracy): giảm, khoảng theo nhóm nằm dưới 0.
- BAYES-H so với DELTA có query (ndcg10): giảm, khoảng theo nhóm nằm dưới 0.
- BAYES-H so với VOTE có query (direction_accuracy): chênh lệch chưa chắc chắn; khoảng chạm/cắt 0.
- BAYES-H so với VOTE có query (ndcg10): chênh lệch chưa chắc chắn; khoảng chạm/cắt 0.

## Phân nhóm và giới hạn

Chi tiết noise .2/.5, query clear/ambiguous/none, focus và candidates real_only/mixed nằm trong groups.csv. Cùng predictions được dùng cho tất cả phân nhóm.
Synthetic candidates chỉ bù 4 thiết kế problem; observations là facet mock. Nhãn concept overlap không là human relevance.
Scorer gốc giữ nguyên: unknown đi vào nhánh similar; các facet không phải focus vẫn ảnh hưởng qua profile C. Suy đúng hướng không tự bảo đảm ranker đổi ưu tiên đúng.
BAYES-H là adaptation với likelihood/threshold heuristic đã định trước; posterior chưa được hiệu chỉnh với người thật. Không chọn lại method hoặc tham số theo điểm test.
Không có dữ liệu cào ngoài corpus, không đổi dataset/candidates/nhãn, không train ranker, không dùng ground truth trong estimator.

## Tái lập

Xem config.json, baseline_parity.json và manifest.json; các file đầu vào và code được ghi SHA-256. Không ghi đè output cũ.
