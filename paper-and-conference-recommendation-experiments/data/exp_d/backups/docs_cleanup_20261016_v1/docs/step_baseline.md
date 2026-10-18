# Các bước hoàn thành baseline exp_d

Cập nhật: 2026-10-15 (Asia/Saigon).

Hướng dẫn thao tác từng lệnh trong CMD, phân biệt checkout/workspace và vị trí file kết quả: [guideline.md](guideline.md).

**Quyết định hiện hành: chạy toàn bộ baseline trên dữ liệu hiện tại theo protocol đã giao; các cải tiến tính sau.** Không yêu cầu tạo pilot có đủ cặp trước khi chạy. Thiếu cặp thì giữ số thực tế, estimator được abstain và trả `unknown` theo protocol.

Tài liệu này thay phần kế hoạch đang yêu cầu chọn A/B/C/D hoặc bổ sung tín hiệu trước baseline trong `step.md`, `buoc2.md` và `Understand_D.md`. Các phương án đó chỉ để xem xét khi nghiên cứu tiếp, không còn là điều kiện chặn baseline.

## 1. Phạm vi và điều kiện chạy

- Dùng snapshot `data/exp_d/workspace/`; mọi đường dẫn chạy bên dưới tính từ workspace.
- Chỉ ghi trong `data/exp_d/` của checkout nguồn, kể cả output nằm trong workspace. Giữ nguyên dữ liệu, config, generator, scorer và evaluator đang được kiểm tra.
- Không cần chạy scorer C trước: runner D tự dựng importance từ dữ liệu C đã bàn giao.
- Chạy bốn baseline công khai: `fixed_similar`, `profile_similar`, `direction_behavior`, `direction_search`. Evaluator tự thêm `oracle_intent`.
- Không cần thu thập bài, extraction A, tải model, đổi matching, hạ ngưỡng, tạo lại D hoặc triển khai phương pháp riêng để chạy baseline.

Đầu vào đã từng pass A complete, C/D validate và runner dry-run trong workspace. Trước khi chạy scoring, đối chiếu kết quả kiểm tra mới nhất ở [audit workspace](../audit/step1_workspace_audit.json). Chỉ coi sẵn sàng khi `step1_complete=true`, mọi command exit 0, checksum khớp và không có watched input/code/manifest thay đổi.

## 2. Kiểm tra đầu vào

Từ gốc `paper-and-conference-recommendation-experiments`:

```cmd
python -B data/exp_d/audit/audit_step1.py --root data/exp_d/workspace --report-prefix step1_workspace_audit
```

Script kiểm tra A complete, C validate, D validate và D runner dry-run; không chạy scoring. Không chạy lại `prepare_workspace.py` trên snapshot đang có.

- [x] Xác nhận audit ngày 2026-10-15 pass: A/C/D và dry-run exit 0; 47 checksum checks khớp; không có watched input/code/manifest thay đổi.
- [x] Ghi ngày kiểm tra và báo cáo vào tiến độ; timestamp chi tiết ở `checked_at` trong JSON audit. Nếu lượt sau fail thì xử lý lỗi cụ thể trước scoring, không sửa hash để vượt validator.

## 3. Chạy toàn bộ baseline

Từ gốc project thực nghiệm, chuyển vào workspace rồi chạy:

```cmd
cd /d E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments\data\exp_d\workspace
python -B scripts/exp_d/run_exp_d.py --config configs/exp_d.json --output results/exp_d/baseline_current_v1 --ks 5 10
```

Một lệnh chạy cả bốn baseline và evaluator thêm oracle, không cần chạy từng model. Output vật lý ở:

```text
data/exp_d/workspace/results/exp_d/baseline_current_v1/
```

Nếu thư mục đã có kết quả, chọn tên lượt mới như `baseline_current_v2`; không thêm `--overwrite`. Không dùng `--output data/exp_d/results/...` vì runner yêu cầu output thuộc project/results của workspace.

- [ ] Runner kết thúc exit 0, báo PASS cho 1.500 cases.
- [ ] Có đủ sáu file: `predictions.jsonl`, `details.jsonl`, `report.json`, `summary.csv`, `report.md`, `manifest.json`.
- [ ] Có đủ năm tên phương pháp, mỗi phương pháp đủ 1.500 cases; tổng dự kiến 7.500 predictions gồm oracle.

## 4. Kiểm tra kết quả và thiếu bằng chứng

- [ ] Đối chiếu manifest kết quả với data/config/code đã chạy; bảo đảm dùng đúng snapshot và không ghi đè dữ liệu cũ.
- [ ] Kiểm tra ranking trên candidates của từng case và các trường direction/importance/confidence theo contract hiện hành.
- [ ] Ghi nhận D hiện có 0 exposures và 0 interactions; không diễn giải số phiên/nhãn đủ quota thành đủ evidence cho behavior.
- [ ] Kiểm tra `direction_behavior`: context được cung cấp nên vẫn có thể là `similar`; focus thiếu bằng chứng phải giữ `unknown`. Không kỳ vọng mọi facet đều unknown hay coverage tổng bằng 0.
- [ ] Kiểm tra `direction_search` có thể dùng query rõ; không ép query mơ hồ hoặc không có query thành hướng chắc chắn.
- [ ] Không đổi `unknown` thành nhãn đúng để chấm. Ranking fallback similar khi unknown là quy tắc sẵn có, không phải dự đoán hướng similar.
- [ ] Phân biệt kết quả đo được với kỳ vọng; không suy ra behavior hiệu quả/kém chỉ từ phép so không có evidence phản ứng.

Oracle chỉ được evaluator dùng hidden intent. Scorer thông thường không được đọc hidden focus/directions/importance, query_mode hoặc relevance labels.

## 5. Tổng hợp và phân tích

- [ ] Lập bảng direction macro-F1/accuracy/coverage, nDCG/Recall/Precision/MRR@5/10 và intent compliance@5/10.
- [ ] Phân tích `fixed_similar` → `profile_similar` để xem ảnh hưởng importance từ C.
- [ ] Phân tích `profile_similar` → `direction_behavior`, kèm giới hạn thiếu phản ứng; không mặc định đây là phép đo đầy đủ khả năng suy hướng behavior.
- [ ] Phân tích `direction_behavior` → `direction_search` để xem đóng góp search.
- [ ] Đọc oracle như đối chứng có thông tin đặc quyền, không coi là phương pháp cùng đầu vào hoặc trần toán học.
- [ ] Báo cáo theo clear/ambiguous/none, similar/different và facet khi đủ mẫu; ghi số mẫu và mẫu số của metrics. Query_mode thật chỉ dùng ở bước đánh giá/phân tích.
- [ ] Xem case đúng/sai/unknown tiêu biểu và giải thích bằng evidence quan sát được.

Grade 1 vẫn positive cho Recall/MRR nhưng sai hướng focus; phải đọc compliance và direction cùng ranking. Context đã được cung cấp có thể đóng góp vào điểm direction tổng; không dùng điểm tổng để khẳng định đã suy được focus khi focus vẫn unknown.

## 6. Báo cáo và bàn giao baseline

- [ ] Viết báo cáo baseline, dữ liệu/config sử dụng, các phép so, kết quả và giới hạn.
- [ ] Ghi rõ bài thật, facet silver, user/intent/query/phản ứng/relevance là mô phỏng; kết quả chưa xác nhận hiệu quả trên người dùng thật.
- [ ] Đính kèm sáu file output, manifest/hashes và lệnh chạy lại; giữ snapshot cần thiết để tái lập.
- [ ] Cập nhật `progress.md` và `changed.md` theo kết quả thực tế, chỉ đánh dấu bước đã có bằng chứng.
- [ ] Nếu cần kiểm tra tái lập, chạy vào thư mục mới và đối chiếu predictions/metrics; giải thích metadata thời gian khác nhau.

**Hoàn thành baseline khi:** đầu vào hợp lệ, toàn bộ baseline/oracle chạy thành công, output đủ và đã kiểm tra, có bảng kết quả cùng phân tích giới hạn và hướng dẫn tái lập. Không yêu cầu phương pháp mới thắng baseline hay phải có thêm dữ liệu behavior để được hoàn thành mốc này.

## 7. Sau baseline

Chỉ sau khi có kết quả mới xem xét semantic ranking, parser, confidence/abstention hoặc bổ sung evidence behavior. Nếu làm phương pháp đề xuất, chốt một giả thuyết và phép so dựa trên kết quả thực tế. Đây là giai đoạn tiếp theo, không phải điều kiện của các bước trên.
