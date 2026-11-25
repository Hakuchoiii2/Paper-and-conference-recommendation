# Kiểm tra kết quả Kaggle R2a — 25/10/2026

Kernel: https://www.kaggle.com/code/htnkhi/exp-a-r2a-v-p-full-pilot50

Kaggle báo COMPLETE. Log ghi đủ 50/50 record cho từng nhánh V/P/full, không có traceback. Thời gian phần chạy và đánh giá: 2.669,20 giây, khoảng 44,49 phút. Không huấn luyện model.

## Kết quả

| Nhánh | Micro F1 (%) | Macro F1 (%) | Fallback /50 | Calls repair mới |
|---|---:|---:|---:|---:|
| R0 đã lưu | 56,3636 | 56,8943 | 33 | — |
| R2 lịch sử | 56,5046 | 56,0045 | 18 | 75 |
| R2a-V | 56,6929 | 56,5333 | 18 | 74 |
| R2a-P | 55,4124 | 56,9054 | 15 | 60 |
| R2a-full | 55,4124 | 56,9054 | 14 | 58 |

Calls R2 lịch sử lấy từ cấu hình gốc (`historical_R2.new_calls=75`), không lấy cột `new_calls=0` trong bảng chạy hiện tại: bảng đó ghi chi phí mới của việc tái dùng control. Các nhánh R2a dùng lại 50 draft đầu tiên; R0 control là output đã chọn của lần chạy cũ, không phải mọi raw draft đầu tiên.

V cao hơn R2 0,1883 điểm phần trăm Micro F1: TP tăng 215→216, FP giữ 144, FN giảm 187→186. Đây là thay đổi nhỏ trên pilot đã dùng để phát triển; chưa chứng minh tổng quát hóa.

Full thấp hơn R2 1,0922 điểm phần trăm: TP cùng 215, FN cùng 187, FP tăng 144→159. P và full có toàn bộ evaluation giống nhau, không chỉ cùng F1. Full tiết kiệm hai calls và giảm một fallback so với P, chưa tạo thêm lợi ích về điểm.

## Đánh đổi của indexed repair

- P/full có `protected_items_changed=0` trước bộ lọc named-dataset chung. Đạt mục tiêu giữ item ngoài phạm vi patch; không bảo đảm các item được giữ là đúng nghĩa.
- Bộ lọc dataset chung vẫn loại 14 item ở P/full, 15 ở V. Không được diễn giải bảo toàn trước filter thành bảo toàn toàn bộ output cuối.
- V có 29 item ngoài tập lỗi ban đầu bị mất hoặc đổi cách viết; đó là số đếm mô tả vì V vẫn dùng full review. Chưa thể gọi cả 29 là mất ý đúng.
- P/full mỗi nhánh có hai attempt lỗi patch, đều ở P003211 lượt 2 và 3: `Replacement duplicates another item`. Đây là một ca lặp hai lần, không phải hai bài khác nhau. Fallback giảm không đồng nghĩa chất lượng ngữ nghĩa tăng.
- Full dùng 58 calls mới so với 75 của R2 (giảm 22,67%); 12.261 output tokens so với 20.939 (giảm 41,44%). Generation time cộng theo calls giảm 2.351,30→1.239,62 giây; không phải thời gian chạy wall-clock riêng từng nhánh.

| Facet | R2 F1 (%) | V F1 (%) | P/full F1 (%) |
|---|---:|---:|---:|
| problem | 36,07 | 38,71 | 39,02 |
| task | 54,05 | 54,05 | 51,35 |
| method | 65,64 | 65,64 | 66,93 |
| dataset | 72,73 | 72,73 | 78,79 |
| contribution | 51,54 | 51,54 | 48,44 |

Problem của P/full có 16 TP và 35 FP; R2 có 11 TP và 19 FP. Recall tăng, nhưng còn nhiều nhãn dư theo reference. Contribution và task là hai phần giảm điểm so với R2. Bảng này phản ánh scorer/reference hiện tại, không tự xác nhận từng FP là sai nghĩa.

## Các ca đã đối chiếu câu nguồn và evaluation

**P001181 — phạm vi phủ định và coverage.** Nguồn phân biệt prior finding “not to improve in-domain accuracy” với finding hiện tại về parser domain adaptation. Evaluation của V/full giữ các finding và problem khớp reference. Method vẫn gộp “self-training with and without reranking”; scorer ghi thiếu “self-training with reranking”. Cần xem khả năng tách hai phương pháp, không chỉ sửa phủ định. R2a chưa thêm bước coverage nên chưa giải quyết phần này.

Record của bài này: P dùng hai calls mới vẫn fallback; full dùng zero calls mới và hết fallback, final facets P/full giống nhau. V dùng một call mới và không fallback. Điều này cho thấy lợi ích của scoped validator ở đây chủ yếu là tránh sửa không cần thiết và thay đổi trạng thái kiểm tra.

**P001211 — nguồn lỗi chữ và gộp finding.** Nguồn thực sự chứa “bri le”, “a acks”, “a ack-resistant”. Full dùng một contribution ghép kết quả adversarial training với so sánh character-level/word-level, trong khi reference tách hai finding và dùng chữ đã sửa. Evaluation ghi thừa nhãn ghép và thiếu hai nhãn riêng. Đây là ca có cả vấn đề đơn vị concept và nhiễu nguồn/scorer; không nên quy toàn bộ FN thành mất nội dung. Task ở full là finding “perform well only when tested…” thay vì nhãn hate speech detection.

**P002471 — vẫn thiếu artifact và sai vai trò.** Nguồn nói đã xây web tutor, đánh giá animation có ích nhưng không hiệu quả hơn text explanation. V/full giữ hai mảnh finding riêng, còn reference gộp finding với caveat; scorer không ghép nhiều nhãn với một nhãn. Cả hai vẫn thiếu artifact “web-based tutor incorporating animation of the data space”. Full còn nhãn problem “students struggle to learn the semantics of C++ pointers”, trong khi abstract cung cấp không khẳng định struggle. Việc giữ item qua validator không bảo đảm nó có hỗ trợ ngữ nghĩa.

## Hướng tiếp theo

1. Giữ V làm mốc cho sửa validator; chưa chọn full thay R2 chỉ vì fallback ít hơn.
2. Rà source-first các item được bảo vệ nhưng sai vai trò/không có hỗ trợ rõ; thiết kế một bước review hẹp với căn cứ câu nguồn thay vì khóa vĩnh viễn item đã pass validator.
3. Chuẩn hóa đơn vị finding độc lập và cách gắn caveat; xem riêng các ca nguồn vỡ chữ và scorer tách/gộp trước khi đổi extractor để chạy theo điểm.
4. Sửa phản hồi retry cho patch lặp/duplicate. Sau đó mới thử coverage cho method/artifact còn thiếu trên cohort độc lập, giữ giới hạn calls và control tương đương.

Chưa sửa code hoặc khởi chạy Kaggle mới trong lần kiểm tra này. Reference là AI reference đóng băng; human review vẫn pending, scorer có các hạn chế đã biết. Chưa có kiểm định ý nghĩa thống kê hay đánh giá tổng quát hóa.

## Dữ liệu và kiểm tra

- [Summary tải từ Kaggle](../.kaggle/r2a/review_20261025/exp_a_r2a/results/experiment_summary.json)
- [Bảng gốc](../.kaggle/r2a/review_20261025/exp_a_r2a/results/experiment_table.md)
- [Log Kaggle](../.kaggle/r2a/review_20261025/exp-a-r2a-v-p-full-pilot50.log)

Đã xác nhận settings trong summary khớp release local; mỗi evaluation có đúng 50 paper ID khác nhau; cộng lại TP/FP/FN từ từng paper khớp summary; tính lại Micro F1 khớp. Log xác nhận 50 record/nhánh và fallback tương ứng 18/15/14.

Đã tải và kiểm checksum/signature đủ 200 record (50 R0 và 150 R2a); byte hash của 50 R0 khớp snapshot phát hành. Đã cộng lại fallback/calls/item thay đổi/filter removals/lỗi patch từ record và đối chiếu summary. Kiểm riêng bằng original item identity xác nhận 271 item được bảo vệ ở P và 272 ở full giữ nguyên trước filter. Final facets P/full giống nhau trên cả 50 bài. Chi tiết kiểm tra: [verification.json](../.kaggle/r2a/review_20261025/verification.json).
