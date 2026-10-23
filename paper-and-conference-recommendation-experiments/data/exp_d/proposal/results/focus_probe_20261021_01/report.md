# Thăm dò: dự đoán facet hoạt động và chẩn đoán oracle

**Đây là phân tích thăm dò được đề xuất sau khi xem benchmark trước, không phải test độc lập hoặc chứng minh tính mới.**
Không sửa dataset, baseline/scorer hoặc trọng số C đầu vào. Mask ignore thay tập facet hoạt động và mẫu số trong scorer, nên không được gọi là chỉ cải thiện dấu similar/different.

| Method | Accuracy hướng | nDCG@10 | Điểm grade 2 > grade 1 |
|---|---:|---:|---:|
| direction_search | 96.91% | 0.8418 | 70.37% |
| active_similar | 48.88% | 0.8944 | 50.00% |
| delta_active | 96.91% | 0.9632 | 97.34% |
| oracle_sign_only | 100.00% | 0.8427 | 70.83% |
| oracle_full_intent | 100.00% | 0.9711 | 99.31% |

active_similar dùng cùng focus suy được và cùng mask, chỉ buộc hướng similar. delta_active giữ hướng DELTA+query và dự đoán các facet khác ignore.
Hai oracle dùng đáp án ẩn CHỈ trong evaluator. oracle_sign_only giữ facet khác unknown; oracle_full_intent biết cả ignore. Không đưa oracle vào bảng phương pháp cạnh tranh.

Chỉ hai bài có nhãn dương ở top 2 nhưng sai thứ tự vẫn có nDCG@10=0.7967; nDCG 0.8 không tương đương 80% chọn đúng nhu cầu.

Chi tiết source real_only/mixed ở groups.csv, khoảng paired thăm dò ở paired_comparisons.csv. Các khoảng không xử lý việc lựa chọn method sau khi xem kết quả.
Hướng này phải được khóa và đánh giá thêm trên nội dung độc lập trước khi khẳng định ưu thế tổng quát. Không đổi dữ liệu hiện tại để tạo thắng lợi.
