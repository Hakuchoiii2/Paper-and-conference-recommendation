# Thực nghiệm D — kế hoạch và luồng chạy hoàn chỉnh

Cập nhật 21/10/2026. Runner chính: `scripts/exp_d/proposal/run_benchmark.py`. Chạy từ dataset đã khóa, suy lại tám phương pháp, thêm Oracle Intent, chấm toàn bộ metrics và tự xuất báo cáo có hai sơ đồ. Không phụ thuộc predictions từ các lượt trước.

## 1. Câu hỏi và phạm vi

| Luận điểm | Phép so |
|---|---|
| Query/phản ứng giúp suy hướng? | Không tín hiệu phiên, chỉ query, chỉ phản ứng, kết hợp |
| Intent suy được giúp ranking? | Dự đoán qua cùng R_active và intent_scores gốc |
| Method bổ sung có tốt hơn? | DELTA+query, VOTE, BAYES-H, Ordinal-Intent cùng tín hiệu |

Một benchmark, một batch; source/query/noise/focus là phân nhóm của cùng predictions. Đây là pilot mock đã được xem trước; không gọi kết quả là thắng trên test độc lập, không chọn lại tham số để method mới thắng.

## 2. Dữ liệu cố định

| Phần | Vị trí / quy mô |
|---|---|
| Nguồn đã khóa | `proposal/inputs/base_v1/`: bài thật, silver A đã lọc, users/history C mock |
| Benchmark dùng chạy | `proposal/datasets/observation_v1/` |
| Toàn bộ | 19 thiết kế, 12 anchors, 114 phiên |
| Chỉ candidates thật | 15 thiết kế, 90 phiên; pool 20 bài thật |
| Có bổ sung candidate tổng hợp | 4 thiết kế problem, 24 phiên; pool 19 thật + 1 tổng hợp |
| Observation | 152 facet records tổng hợp riêng, 4 cặp/phiên; tách khỏi candidates |
| Query | Clear/ambiguous/none; cùng pool cho hai hướng đối lập và ba modes |
| Phản ứng | Seeds 42/43/44 × Gaussian noise .2/.5 |
| Nhãn mỗi pool | Một grade 2, một grade 1, 18 grade 0; concept overlap theo intent mô phỏng |

“4” là số thiết kế mixed và cũng có bốn candidate tổng hợp duy nhất; không có bộ chỉ gồm candidates tổng hợp. Nguồn bài từng cào thêm đã ở backup, không dùng. [Provenance chi tiết](proposal/README_DATA.md).

Không sinh lại dữ liệu trong mỗi lượt benchmark. Validator kiểm hashes/nguồn/nhãn/thời gian/observation tách pool. Semantic review pending được giữ nguyên: đây là controlled mock, chưa phải human gold; không là gate chặn phép thử mô phỏng.

## 3. Phương pháp và scorer chung

| Method | Vai trò |
|---|---|
| fixed_similar | Baseline gốc: luôn similar, weights đều |
| profile_similar | Baseline gốc: luôn similar, C weights |
| direction_behavior | Baseline gốc: DELTA phản ứng |
| direction_search | Baseline gốc: DELTA + query |
| query_only | Parser gốc, không phản ứng |
| vote | Dấu phiếu phản ứng + query |
| bayes_h | Posterior focus–direction từ dấu phản ứng + query |
| ordinal_intent | Posterior từ mức chênh phản ứng, kể cả hòa + query |
| oracle_intent — đặc quyền | Evaluator dùng true session directions VÀ weights; không chọn làm method thắng |

Tất cả public methods không train. Hai file config trong scripts/exp_d/proposal giữ ngưỡng cũ: DELTA minimum_pairs=2/margin=.25; VOTE=.75; BAYES-H reaction/query reliability=.8, posterior_min=.25/gap=.10; Ordinal strengths=[.25,.75,1.5], query=.8, minimum_pairs=2, posterior=.25/gap=.10. Không đọc noise thật để đặt estimator.

R_active chung: duy nhất một focus ngoài context có hướng xác định → context/focus hoạt động, facet khác ignore; chưa rõ → fallback always-similar. Raw directions không đổi khi chấm intent.

`intent_scores` gốc: context thiếu/cosine≤0 → −1. Mỗi facet active dùng cosine S nếu similar, 1−S nếu different; ignore bị bỏ. Score = ΣwT/Σw. Candidate thiếu facet active có weight → −1; anchor thiếu thì bỏ facet; hết weights dùng cosine context; hòa theo ID. Hàm gốc xử lý unknown như similar, nhưng policy mới xử lý scope/fallback trước khi gọi hàm. C weights/vector/pool chung; fixed_similar giữ weights đều.

## 4. Metrics đầy đủ và định nghĩa

| Bảng | Chỉ số và cách tổng hợp |
|---|---|
| Chính | Accuracy/coverage/joint tại focus; F1 focus; nDCG@10; Grade-2@1. Trung bình lặp trong thiết kế → thiết kế trong workgroup → workgroups |
| Metrics gốc | Evaluator/aggregate gốc: context+focus accuracy/coverage/F1, importance MAE; case-condition mean và confusion gộp |
| Retrieval gốc | nDCG/Recall/Precision/MRR@5/10; grade 1 và 2 đều positive cho Recall/Precision/MRR |
| Tuân thủ intent | Compliance@5/@10 chỉ grade 2; trần hiện tại .20/.10 |
| Chẩn đoán | Strict pair, pair order, thành công cả hai hướng, joint focus–direction |
| Phân nhóm | Candidates real_only/mixed, query, noise, focus, direction |

Không nhầm accuracy focus với accuracy context+focus gốc: always-similar lần lượt đạt 50% và 75%. Context do benchmark cung cấp. F1 chính tạo confusion có trọng số theo thiết kế trong từng workgroup rồi lấy mean groups; bảng legacy gọi nguyên aggregate gốc. Hai đơn vị tổng hợp được đặt tên riêng, không trộn số.

Oracle dùng cùng scorer nhưng biết cả weights/directions; không đảm bảo là trần toán học do nhãn overlap và score cosine mềm khác nhau. Oracle chỉ được tạo sau khi lưu toàn bộ public predictions, lưu file riêng; true weights/focus không lọt estimator.

## 5. Chạy toàn bộ

Từ thư mục `paper-and-conference-recommendation-experiments`:

```powershell
python -B -m unittest discover -s scripts/exp_d/proposal -p "test_*.py" -v
python -B scripts/exp_d/proposal/run_benchmark.py
```

Output mặc định tự có tên mới trong `data/exp_d/proposal/results/`. Chọn tên cụ thể với `--output`. Không chạy bước bổ sung metrics, không cần các runner lịch sử. `run_ordinal_benchmark.py` chỉ chuyển tiếp đến cùng runner chính.

Runner validate dataset → tính C/vector chung → suy đủ 8 methods cho 6 conditions → kiểm parity bốn baseline trên mọi phiên/condition → lưu public predictions → evaluator đọc truth/thêm Oracle → chấm/xuất bảng/CI/report → kiểm hashes. 5.472 public predictions + 684 oracle predictions cho dữ liệu hiện tại. Chỉ manifest status complete mới xác nhận lượt hợp lệ.

Các bảng tự xuất gồm summary/groups, legacy_summary/legacy_groups; report.md tự có hai hình và giải thích scorer/data/metrics. `conclusions.json` loại Oracle khỏi lựa chọn best public. [Hướng dẫn modules và output](../../scripts/exp_d/proposal/README.md).

## 6. Bảo toàn và lịch sử

Không sửa `data/exp_d/{README.md,build_exp_d.py,generated,ground_truth,samples}`, `scripts/exp_d/{README.md,run_exp_d.py}` hoặc code dùng chung. Không đổi dataset, nhãn, trọng số C đầu vào hay output cũ. Toàn bộ thay đổi code mới nằm trong scripts/exp_d/proposal; dữ liệu/báo cáo ở data/exp_d/proposal.

Code trước khi hoàn thiện runner được chụp tại `scripts/exp_d/backup/20261021_complete_runner/`, có snapshot_manifest.json; README kế hoạch cũ ở `data/exp_d/backup/20261021_complete_runner/README_PROPOSAL_before.md`. Các thư mục backup đã gitignore. Các manifest kết quả lịch sử giữ hashes code phiên bản cũ; đối chiếu với snapshot tương ứng thay vì yêu cầu code hiện hành mãi trùng bản cũ.

Kết quả 7 methods, focus probe và ordinal replay cũ vẫn giữ như lịch sử. Đọc report của lượt complete mới để lấy bảng đầy đủ; các nghiên cứu thử trước không là các bước bắt buộc của pipeline hiện hành.
