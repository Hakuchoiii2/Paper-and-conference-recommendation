# QLoRA v2 — kết quả paired test, 20/10/2026

Kaggle `htnkhi/exp-a-qwen-qlora-v2-test`: API xác nhận COMPLETE. Summary output status complete, 100 bài, 2 arm, 200 generation calls/arm. Không chạy lại GPU hoặc thay nhãn.

## Kết quả

Cùng instruction v2.2, greedy decoding, mandatory source-only review, semantic matching Qwen3-Embedding-0.6B threshold 0.85. Bài lỗi vẫn trong mẫu số; concept qua bộ lọc grounding được giữ lại và chấm khi fallback.

| Chỉ số | Base | QLoRA v2 |
|---|---:|---:|
| Micro F1 | 26.52 | 47.02 |
| Macro F1 | 29.71 | 49.54 |
| Precision | 45.87 | 51.89 |
| Recall | 18.66 | 42.99 |
| Problem F1 | 31.76 | 28.57 |
| Task F1 | 26.98 | 54.68 |
| Method F1 | 21.69 | 48.43 |
| Dataset F1 | 46.28 | 71.11 |
| Contribution F1 | 21.82 | 44.93 |
| Fallback papers / 100 | 96 | 15 |
| Draft schema valid / 100 | 99 | 98 |
| Draft validator valid / 100 | 1 | 85 |
| Selected schema valid / 100 | 100 | 98 |
| Selected validator valid / 100 | 4 | 85 |
| Duplicate stop calls / 200 | 0 | 2 |

Micro F1 tăng 20.50 điểm phần trăm. 72 bài tăng paper-micro-F1, 6 hòa, 22 giảm (tính từ TP/FP/FN của từng bài, không phải macro facet F1). Bootstrap ghép cặp thăm dò 10.000 lần, seed 42: khoảng percentile 95% cho chênh lệch Micro F1 là +15.52 đến +25.37 điểm phần trăm; chưa hiệu chỉnh cho nhiều phép so sánh.

## Diễn giải

V2 cải thiện rõ trong protocol này, nhất là recall và tuân thủ quy tắc trích từ nguồn. Base đúng schema gần hết nhưng chỉ 4/100 bài qua validator sau chọn output; JSON hợp lệ không đồng nghĩa grounding hợp lệ. Vì vậy không nên diễn giải F1 thấp của base thành khả năng hiểu ngữ nghĩa thấp tương ứng.

Problem là facet giảm (31.76 → 28.57): TP 27 → 30, FP 24 → 61, FN 92 → 89. Model lấy thêm ít đúng nhưng thêm nhiều nhãn sai so với reference. Contribution F1 tăng nhưng precision còn 44.84%, có 139 FP. V2 vẫn có 15 bài fallback, 2 selected output không hợp lệ schema, 2 call bị chặn lặp; không có time/token-limit stop.

Generation time cộng theo arm: base 4666.71 giây, v2 7651.19 giây; chạy song song hai T4 nên không cộng hai số thành thời gian thực toàn phiên. Đây không phải benchmark latency kiểm soát độc lập.

## Giới hạn

Reference được đóng băng từ trước v2, theo policy cũ, là AI reference và human review pending. Điểm đo agreement với reference này, chưa phải chất lượng theo human gold của policy v2.2. Cả hai arm chịu cùng quy tắc nhưng tác động policy mismatch lên từng arm có thể khác nhau. Không so trực tiếp với điểm v1 hoặc sửa prompt/label dựa trên test này rồi gọi lại là test độc lập.

Ưu tiên đọc lỗi problem và 15 bài fallback để mô tả lỗi; nếu chỉnh model/prompt, chọn trên dev và dùng bộ đánh giá độc lập cho lần xác nhận sau.

## Bằng chứng

Output local: `data/exp_a/finetuning/v2/downloads/test_v1_20261020/`. Summary, bảng CSV/MD, evaluation từng arm và record từng bài được giữ trong thư mục này. Settings output khớp toàn bộ sealed build_manifest settings; đúng chữ ký launch và adapter đã xác minh; 100 test IDs duy nhất, không giao train/dev. Kiểm record đầy đủ được lưu riêng ở `build/test_result_checks_2026-10-20.json`.

Kiểm tra local: **222/222 PASS**, gồm đủ 200 record (100/arm), checksum nội dung record, pairing/signature/runtime arm, số fallback/calls, đủ 100 bài chấm/arm, đếm lại TP/FP/FN và tính lại Micro F1 từ các số đếm. Không chạy lại model embedding hay inference. Base có 414 lỗi concept không theo từ/thứ tự nguồn ở selected output; v2 có 17 lỗi loại này cùng lỗi parse/evidence order. Đây là số thông báo lỗi, không phải số bài.
