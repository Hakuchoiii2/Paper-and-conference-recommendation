# Exp A — sửa reference và matcher trên silver giữ nguyên

Ngày 2026-10-14. Output Qwen **4.210 bài giữ nguyên**; chỉ tính lại embedding và đánh giá 400 bài có reference.

## Kết quả kiểm soát từng thay đổi

| Lượt | Reference | Matcher | TP | FP | FN | Precision | Recall | Micro F1 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Mốc cũ | v1, 3.300 concept | cosine 0.85 | 1266 | 2087 | 2034 | 37.76% | 38.36% | 38.06% |
| Chỉ sửa reference | v2, 3.322 concept | matcher cũ, cosine 0.85 | 1284 | 2069 | 2038 | 38.29% | 38.65% | 38.47% |
| Bản hiện hành | v2, 3.322 concept | canonical + quy tắc chặn + cosine 0.85 | 1298 | 2055 | 2024 | 38.71% | 39.07% | **38.89%** |

Mức tăng tổng là **0,83 điểm phần trăm**; khoảng 0,41 từ sửa reference và 0,42 từ matcher trên cùng reference v2. Mẫu số gold đổi từ 3.300 thành 3.322 nên không lấy chênh lệch F1 làm tỷ trọng lỗi của từng nguồn. Baseline khớp chữ với reference v2 là 21.21%.

Điểm tăng còn nhỏ. Việc sửa xử lý được một số trường hợp cụ thể và làm quyết định ghép dễ kiểm tra hơn; chưa chứng minh matcher hiểu mọi cặp ngữ nghĩa tốt hơn. Điểm vẫn là agreement với AI reference, chưa phải semantic accuracy do người xác nhận.

## Reference đã sửa

Bản hiện hành là `codex_source_audit_revision_v2`: **18 bài / 21 trường facet** trong 29 bài đã audit. 382 bài còn lại giữ nhãn AI trước đó; không tuyên bố đã rà lại toàn bộ 400 bài.

- Gộp hai alias của SSWE và story ending selection; bỏ số lượng comments đứng riêng như artifact thứ hai.
- Bổ sung các artifact/findings chính có trong nguồn, như Sentinel vượt các bộ lọc trước, seq2seq vượt hai simulator baseline và các kết quả counterspeech.
- Khôi phục phạm vi/comparator của finding: text-based models tốt hơn cho **most abstract nouns**, BERT hơn 1.9 F1 với ít hơn bốn triệu ví dụ, cùng các mốc correlation của biomedical STS.
- Bổ sung task phân tích cấu trúc ngôn ngữ counterspeech theo source khi rà lại; tách khỏi task detection.
- Cập nhật evidence đồng thời với nhãn; tất cả 3.322 concept có evidence tương ứng. Năm bài nguồn còn nghi vấn vẫn pending, không đoán tên hoặc nội dung bị cắt.

Sửa dựa trên title/abstract và guideline; cùng cuộc hội thoại đã thấy Qwen trong audit, nên đây **không phải blind review hay human gold**. Sổ trước–sau và metadata bản trước được gộp trong [reference_revision](../../../data/exp_a/evaluation/reference_revision/summary.json).

## Matcher hiện hành

1. Giữ các cặp exact sau NFKC, casefold và chuẩn hóa khoảng trắng; baseline lexical vẫn dùng đúng quy tắc cũ.
2. Chuẩn hóa hậu tố loại tài nguyên `dataset/corpus/collection`, và prefix `a new dataset called ...`; giữ tên, phiên bản, năm và dấu câu.
3. Chỉ dùng acronym khi có định nghĩa trong chính title/abstract và khớp initials của toàn expansion. Tên artifact dạng `called/named/dubbed X` chỉ được rút về X khi toàn mô tả xuất hiện trong nguồn và không chứa finding/conjunction bị quy tắc loại.
4. Trước khi ghép, chặn bất đồng số liệu; ở contribution còn kiểm tra mất số liệu của finding, metric, phủ định và khác vai trò mức đạt được/mức tăng. Với task, phân biệt measurement/characterization với detection/prediction khi pattern đủ rõ.
5. Ghép một–một trong cùng paper/facet, tối đa số cặp rồi tổng assignment score. Cặp canonical dùng score=1 theo quy tắc định danh; cặp khác cần cosine ≥0.85. `similarity` luôn giữ cosine thật của cặp không exact, không đổi thành 1 để che điểm thấp.

Đây là các quy tắc hẹp, không phải bộ hiểu ngữ nghĩa đầy đủ. Chưa xử lý mọi qualifier, coreference, nhãn gộp nhiều ý, hoặc tên và mô tả không có định nghĩa rõ trong source. Không tạo bảng đồng nghĩa thủ công theo đáp án từng bài.

Kiểm tra số hiện chuẩn hóa dấu phẩy, khoảng trắng và cách viết percent; chưa quy đổi đầy đủ cách ghi số hoặc đơn vị tương đương. Quy tắc bảo thủ này có thể bỏ thêm cặp đúng, nên mọi cặp bị chặn vẫn được lưu để rà.

Trong lượt 400 bài: **43 canonical matches**, 547 embedding matches và 708 exact matches. Có 15 ứng viên cosine ≥0.85 bị chặn: 7 khác số liệu, 6 thiếu lượng trong finding, 1 khác phủ định và 1 khác thao tác task. So với matcher cũ trên reference v2 có 24 cặp thêm và 10 cặp bị bỏ/đổi đối tác, tăng ròng 14 TP theo quy tắc hiện hành.

Ví dụ đã kiểm tra:

| Bài | Cặp hoặc thay đổi | Kết quả |
|---|---|---|
| P001758 | `atis corpus` ↔ `ATIS`, cosine 0.6341 | Nhận theo cùng tên resource |
| P001906 | `Natural Questions benchmark dataset` ↔ `Natural Questions`, cosine 0.8277 | Nhận theo canonical name |
| P003343 | `a novel end-to-end deep learning network called RespNet` ↔ `RespNet`, cosine 0.8118 | Nhận theo định danh có nguồn |
| P001880 | correlation ~0.84 ↔ tăng ~13%, cosine 0.8909 | Chặn; chuyển Qwen 0.84 sang finding 0.84 có source trong reference mới |
| P002925 | measurement study ↔ detect types, cosine 0.8525 | Chặn; measurement study ghép sang task characterization đúng, cosine 0.9324 |
| P004166 | PASCAL VOC 2006 ↔ PASCAL VOC 2006 **and 2007**, cosine 0.9382 | Chặn vì khác tập năm |

## Thử ngưỡng trên cặp thật

Tập [matcher_pairs.jsonl](../../../data/exp_a/samples/matcher_pairs.jsonl) có **100 cặp nhãn có nguồn**, do Codex gán equivalent/different/partial. Chỉ equivalent là positive; partial không được tính đúng đầy đủ.

- **56 cặp hiệu chỉnh:** 27 positive được chọn từ các cặp bỏ ghép trong audit trước, 29 negative/partial chọn trong cùng bài/facet. Đây là tập chẩn đoán khó có chủ đích.
- **44 cặp kiểm tra:** 22 positive và 22 negative/partial từ 12 bài khác, lấy ID bằng seed `20261015` trong phần còn lại của cohort. Không trùng paper ID với tập hiệu chỉnh. Nhãn reference của 12 bài này không được sửa trong lượt này.
- Các cặp được chọn lọc, không phải toàn bộ cross-pairs của 12 bài. Phân phối positive/negative không đại diện môi trường đánh giá thực tế.
- Chọn ngưỡng trên calibration trong 0.70–0.95: precision ≥90%, tối đa F1, hòa chọn ngưỡng cao hơn. Trước khi tính check đã đặt gate: chỉ đổi mặc định nếu check precision ≥90% và F1 không thấp hơn matcher cũ ở 0.85.

Calibration chọn ứng viên **0.78**: TP14 / FP1 / FN13, precision 93.33%, recall 51.85%, F1 66.67%. Sang check:

| Cách so trên 44 cặp | TP | FP | FN | TN | Precision | Recall | Pair F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Matcher cũ, 0.85 | 17 | 2 | 5 | 20 | 89.47% | 77.27% | 82.93% |
| Matcher mới, 0.78 | 17 | 2 | 5 | 20 | 89.47% | 77.27% | 82.93% |
| Matcher mới, 0.85 | 17 | 2 | 5 | 20 | 89.47% | 77.27% | 82.93% |

Ứng viên không đạt gate 90% và chưa thêm giá trị trên check; **giữ mặc định 0.85**. Không chọn lại một ngưỡng khác bằng kết quả check. Các quyết định đã được tái kiểm tra dưới code scoring cuối và không đổi.

Check vẫn có cặp đúng bị bỏ như `convolution kernels ... deep parses ...` ↔ `convolution kernels`, và cặp partial được nhận như finding mất phạm vi dream reports. Các điểm này được giữ trong sổ để thể hiện giới hạn, chưa thêm luật riêng theo từng bài.

Pair F1 ở đây **không phải extraction F1 của 400 bài**. Đây là review AI trong cùng cuộc hội thoại, chưa độc lập hoặc được người xác nhận; chưa thể coi 0.85 là ngưỡng semantic equivalence đã được kiểm chứng.

## File hiện hành, lịch sử và kiểm tra

- [embedding_400_revised/report.md](../../../data/exp_a/evaluation/embedding_400_revised/report.md): kết quả hiện hành; `per_paper.jsonl` có matched/rejected pairs và lý do.
- [matcher_calibration/summary.json](../../../data/exp_a/evaluation/matcher_calibration/summary.json): sweep, check, provenance, hash và ba mốc chạy 400 bài.
- [reference_revision/changes.jsonl](../../../data/exp_a/evaluation/reference_revision/changes.jsonl): nhãn/evidence trước–sau theo paper/facet.
- `embedding_400/` giữ mốc cũ; `reference_only_400/` giữ lượt kiểm soát reference. Các thư mục lịch sử có manifest gắn đúng hash reference/code tại thời điểm chạy.
- Không thêm script probe/calibration riêng; dùng lại encoder và matcher trong evaluator. Code chạy thử là lệnh inline và không giữ file Python mới. Các file log/cache test tạm đã dọn.

Kiểm tra: **19 test evaluator + 87 test project qua**; hash silver, metadata, manifest Qwen và output 400 bài cũ không đổi; nhãn/evidence, quote, 21 thay đổi facet, hash manifest, counts và quy tắc mỗi nhãn ghép một lần đều hợp lệ.

Mọi thay đổi của lượt này nằm trong `data/exp_a` và `scripts/exp_a`. Chưa sinh lại Qwen, chưa sửa prompt/generator, và chưa xác nhận toàn bộ reference thành human gold.
