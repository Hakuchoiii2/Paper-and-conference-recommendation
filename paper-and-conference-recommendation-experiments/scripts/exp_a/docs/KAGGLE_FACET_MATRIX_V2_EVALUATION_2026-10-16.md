# Matrix v2: kết quả đã xác minh — 2026-10-16

[Kernel version 2](https://www.kaggle.com/code/htnkhi/exp-a-qwen-facet-matrix) COMPLETE; đủ 50 bài/cấu hình, 200 kết quả. Runtime v2 ~63.8 phút; 4B được tái sử dụng.
Bài P001604 đã chạy qua trên T4, không có CUDA OOM trong log. Source/hash/reference đúng; 200 raw/applied replay qua; chấm lại local khớp 1,000 paper-facet comparisons.

| Cấu hình | Precision % | Recall % | Micro F1 % | Macro F1 % | Method F1 % | Contribution F1 % |
|---|---:|---:|---:|---:|---:|---:|
| 4b_original | 59.70 | 49.75 | 54.27 | 56.21 | 59.84 | 47.45 |
| 4b_source_first | 42.51 | 43.03 | 42.77 | 49.82 | 38.57 | 36.77 |
| 8b_original | 58.97 | 53.98 | 56.36 | 56.89 | 65.38 | 50.00 |
| 8b_source_first | 44.20 | 44.53 | 44.36 | 49.93 | 42.47 | 38.10 |

**8B original là mốc tốt nhất trong bốn cấu hình đã định trước.** So với 4B original: micro +2.09 điểm %, macro +0.69 điểm %, +17 TP, +16 FP, -17 FN. Method tăng TP 73→85; contribution F1 tăng chủ yếu nhờ FP giảm 82→65, TP 65→64. Task F1 giảm 59.42→54.05; dataset giảm 75.86→70.59. Đây là cải thiện nhỏ và không đồng đều.

## Vì sao bản tách facet giảm điểm

Thiết kế thử nghiệm thêm kind và span; model thường trả kind=method trong contribution thay vì artifact/finding. Validator làm đúng hợp đồng nhưng loại cả một số ý được nguồn hỗ trợ. Đây là vấn đề của prompt/schema hiện tại; không phải bằng chứng rằng mọi cách tách facet đều kém.

| Cấu hình | Raw items ở attempt được chọn | Items bị loại | Lỗi kind | Method fallback /50 | Contribution fallback /50 |
|---|---:|---:|---:|---:|---:|
| 4b_source_first | 426 | 107 | 50 | 31 | 33 |
| 8b_source_first | 384 | 102 | 53 | 18 | 37 |

4B còn 3 selected responses không đọc được items để đếm. Các con số lỗi là occurrences, không phải số lỗi ngữ nghĩa đã được người xác nhận. 8B contribution có 50 item kind=method và 1 item kind=resource bị loại; 2 item method mang kind=finding.

Ví dụ P001389: 4B trả đúng tên Joint Topic Viewpoint model (JTV), evidence là câu “We propose…”, nhưng kind=method trong contribution nên bị loại; contribution cuối cùng rỗng. 8B split cũng bị loại JTV vì cùng lỗi. P002586 của 8B split bỏ finding Tamil có điều kiện vì nhãn được gán kind=method.

Ngoài format, nhiều nhãn lấy cả câu, gộp các kỹ thuật độc lập, hoặc lấy quy trình/background làm contribution. 4B split tăng FP 135→234 và giảm TP 200→173; 8B split tăng FP 151→226 và giảm TP 217→179. Sửa kind đơn thuần chưa chứng minh sẽ vượt 8B original.

## Lỗi cũ và giới hạn điểm

- 8B original đã ghi rõ JTV/TARN trong contribution và lấy lại WMT15. JTV/TARN vẫn hiện FN trong matcher vì nhãn dài hơn reference tên-only; cần phân biệt mismatch với thiếu ý thật.
- Negative BLEU finding P004047 vẫn thiếu trong original; split khôi phục được finding này.
- P002586 original vẫn thiếu method bottleneck và điều kiện Tamil/tỷ lệ test-vs-training data. 4B split giữ finding đầy đủ nhưng 8B split lại loại nó do kind.
- Bốn bài method từng rỗng nay có label ở 8B original, nhưng P003187 chỉ có “survey” và P003614 lấy RST, chưa khớp/đủ phương pháp trong reference.

8B original còn 336 FP+FN, trong đó method+contribution chiếm 218 (~64.9%). Contribution là facet có nhiều disagreement nhất (65 FP + 63 FN).

Giữ 8B original làm baseline của vòng tiếp theo. Nếu tiếp tục thử tách facet, ưu tiên đơn giản hóa schema và phân biệt novelty/finding/procedure, rồi kiểm tra trên bài mới trước khi chạy lớn. Không đổi threshold hay trộn các facet tốt nhất theo chính tập này để gọi đó là winner.

Điểm là agreement với frozen AI reference, threshold 0.85, trên 50 bài dev đã dùng lặp; chưa phải human semantic accuracy hoặc đánh giá tổng quát hóa. 

Dữ liệu: `data/exp_a/evaluation/facet_matrix_v2/` gồm CSV/Markdown, evaluation từng arm, 200 records/audits, completion_verification.json và analysis.json. Log tải về giữ tại `data/exp_a/.kaggle/review/matrix_v2_complete/kernel.log`.
