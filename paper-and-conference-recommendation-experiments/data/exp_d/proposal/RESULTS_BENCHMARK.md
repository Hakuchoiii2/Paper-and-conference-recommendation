# Kết quả D đã chạy — 21/10/2026

**Hai luận điểm của D được hỗ trợ có điều kiện trong benchmark mock hiện tại. BAYES-H chưa tốt hơn baseline DELTA + query.** Không tune hoặc đổi dataset sau khi xem điểm.

Lượt đã hoàn thành: [benchmark_7_20261021_01/report.md](results/benchmark_7_20261021_01/report.md). Một benchmark, 7 cấu hình × 114 phiên × 6 điều kiện = 4.788 predictions. Cùng dataset QUAN SÁT v1, cùng scorer gốc `intent_scores`, vector và profile C. Bốn baseline được giữ nguyên logic và đã qua đối chiếu runner gốc; 16 tests mới pass. Dataset giữ nguyên, validator PASS.

## Một bảng kết quả chính

Trung bình các lần lặp theo thiết kế, rồi các thiết kế theo nhóm công trình anchor, cuối cùng trung bình 12 nhóm anchor. Unknown tính sai trong accuracy toàn bộ.

| Method | Accuracy hướng | Đúng cả focus+hướng | Coverage hướng | nDCG@10 |
|---|---:|---:|---:|---:|
| fixed_similar | 50,00% | 0,00% | 100,00% | 0,8029 |
| profile_similar | 50,00% | 0,00% | 100,00% | 0,8019 |
| QUERY-ONLY | 33,33% | 33,33% | 33,33% | 0,8164 |
| DELTA — direction_behavior | 95,83% | 95,83% | 96,80% | 0,8412 |
| **DELTA + query — direction_search** | **96,91%** | **96,91%** | **97,84%** | **0,8418** |
| VOTE + query | 91,74% | 91,74% | 92,05% | 0,8390 |
| BAYES-H + query | 91,51% | 91,51% | 91,82% | 0,8386 |

Coverage hướng được evaluator đo tại focus thật, không phải thông tin đưa cho estimator. Hai baseline luôn-similar có coverage hướng 100% nhưng không xác định được focus cụ thể, nên joint accuracy bằng 0 theo quy tắc đã chốt. Dùng cột accuracy hướng để so mốc giả định similar, không diễn giải joint=0 thành không đoán được bất kỳ hướng nào.

## Kết luận 1 — query/phản ứng giúp suy hướng không?

**Phản ứng: có bằng chứng hỗ trợ rõ trong mock.** DELTA behavior tăng từ 50,00% lên 95,83%, chênh +45,83 điểm %, khoảng bootstrap 95% theo nhóm anchor [+43,21; +47,76].

**Query: hữu ích khi thể hiện hướng rõ, chưa phải mọi query đều hữu ích.** QUERY-ONLY đạt 100% accuracy/coverage ở nhóm clear; ở ambiguous và none trả unknown. Do ba mode cân bằng, accuracy toàn bộ chỉ 33,33%, thấp hơn mốc luôn đoán similar 50%. Không được viết QUERY-ONLY tốt hơn không tín hiệu trên toàn bộ dataset.

DELTA + query so với DELTA behavior tăng +1,08 điểm % accuracy toàn bộ, khoảng [+0,39; +1,85]. Đây là bằng chứng query rõ bổ sung khi phản ứng có nhiễu. Với noise .2, cả hai đạt 100%; với noise .5, behavior đạt 91,67% và có query đạt 93,83%.

Ở clear, QUERY-ONLY và DELTA + query đều đạt 100% accuracy và cùng ranking: chưa chứng minh phản ứng thêm giá trị khi query đã nói đủ rõ. Ở ambiguous/none, parser gốc không trích được hướng nên hệ thống dựa vào phản ứng. Kết quả hỗ trợ tận dụng các nguồn theo mức sẵn có, không chứng minh fusion phức tạp luôn tạo lợi ích vượt từng nguồn.

## Kết luận 2 — dùng directions có giúp ranking không?

**Có bằng chứng hỗ trợ ở mức tổng hợp trong benchmark mock.** Giữ nguyên scorer/profile C/vector/pool, direction_search so với profile_similar:

- nDCG@10: 0,8019 → 0,8418, chênh **+0,0399**, khoảng bootstrap 95% [+0,0104; +0,0686].
- Tỷ lệ điểm bài grade 2 cao hơn grade 1: 45,83% → 70,37%.
- Ưu tiên đúng bằng điểm ở cả hai phiên đối lập: 0% → 49,07%. Chỉ số này khắt khe hơn nDCG; tie không tính thành công.

Hiệu ứng không đồng đều: nhóm candidates toàn thật nDCG 0,7537 → 0,7656 (+0,0119); nhóm mixed/problem 0,8984 → 0,9942 (+0,0958). Không lấy CI tổng hợp để khẳng định riêng nhóm toàn thật đã có bằng chứng chắc. Nhóm mixed chỉ có 4 anchors và đồng thời chính là focus problem, không tách được ảnh hưởng source và facet.

Accuracy intent cao chưa làm ranking hoàn hảo vì scorer gốc vẫn dùng trọng số của các facet khác, xử lý missing và unknown như similar. Không sửa scorer hoặc dùng hidden weights để làm điểm tăng.

## Proposal có tốt hơn không?

**Chưa.** So cùng query + phản ứng, BAYES-H kém direction_search −5,40 điểm % accuracy và −0,0032 nDCG@10; các khoảng theo nhóm đều nằm dưới 0. VOTE cũng không đứng đầu. Kết quả BAYES-H so với VOTE rất gần, khoảng chạm 0 nên không khẳng định hơn/kém chắc chắn giữa hai method này.

BAYES-H/VOTE trả lời ít hơn và có conditional accuracy khoảng 99,66%, so với 99,05% của DELTA + query. Đó là đánh đổi coverage–precision, không đủ để gọi proposal tốt hơn về accuracy toàn bộ hoặc ranking. Không đổi threshold sau khi xem kết quả.

Phương án có điểm tổng hợp cao nhất trong lượt này là **direction_search gốc**. Có thể chọn làm phương án triển khai của pilot; chưa có kết quả hỗ trợ đóng góp “BAYES-H vượt baseline”.

## Có thể viết kết luận nào?

> Trong benchmark facet mô phỏng có kiểm soát, phản ứng đầu phiên giúp suy direction và query rõ có thể bổ sung khi phản ứng nhiễu. Với cùng scorer và candidate pool, sử dụng directions suy được cải thiện nDCG@10 trung bình so với luôn giả định similar. DELTA kết hợp query đạt kết quả tổng hợp cao nhất trong các cấu hình đã so; VOTE và BAYES-H chưa cải thiện accuracy toàn bộ/ranking so với baseline này.

Giới hạn: 12 anchors/19 thiết kế, observations tổng hợp, một phần candidates tổng hợp, nhãn exact concept overlap và query theo template; không suy rộng thành hiệu quả người dùng thật, semantic retrieval ngoài corpus hoặc anchors độc lập chưa từng thấy. Bootstrap theo nhóm anchor giảm việc đếm lặp nhưng không loại được mọi phụ thuộc do dùng chung nguồn/donor.

## Chứng cứ và tái lập

- [Bảng CSV chính](results/benchmark_7_20261021_01/summary.csv)
- [Phân nhóm](results/benchmark_7_20261021_01/groups.csv)
- [Chênh lệch và khoảng paired](results/benchmark_7_20261021_01/paired_comparisons.csv)
- [Đối chiếu baseline gốc](results/benchmark_7_20261021_01/baseline_parity.json)
- [Manifest/hashes](results/benchmark_7_20261021_01/manifest.json)

Hướng dẫn chạy và cấu trúc code: [scripts/exp_d/proposal/README.md](../../../scripts/exp_d/proposal/README.md). Kết quả gốc được giữ nguyên; tài liệu này bổ sung cách diễn giải query-only và khác biệt real_only/mixed, không thay predictions hoặc điểm.

## Bổ sung sau lượt chạy này

Đã có [thăm dò DELTA-ACTIVE và phân tích vì sao điểm cao](FOLLOWUP_FOCUS_MASK.md). Đây là method được đề xuất sau khi xem bảng bảy cấu hình, không sửa kết quả gốc và chưa là kiểm chứng trên test độc lập. Kết luận direction_search tốt nhất ở trên chỉ áp dụng đúng bảy cấu hình đã định trước.
