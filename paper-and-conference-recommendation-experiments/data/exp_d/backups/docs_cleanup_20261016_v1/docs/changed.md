# Nhật ký thay đổi mã nguồn D — trạng thái đã đối chiếu

Cập nhật: 2026-10-16 (Asia/Saigon). Mốc so sánh: code trong Git HEAD với working tree hiện tại. Chỉ ghi file nguồn có thể đưa lên Git; không liệt kê thay đổi audit/docs/workspace hoặc các output bị ignore như thay đổi mã nguồn.

Bản giải thích bài toán, cách đọc metrics và nội dung báo cáo nhóm: [bao_cao_nhom_D.md](bao_cao_nhom_D.md).

## 1. Kết luận về phạm vi

- File đã có trong Git và đang sửa: `data/exp_d/build_exp_d.py` (diff hiện tại: 68 dòng thêm, 16 dòng bỏ).
- Sáu file Python đã thêm cho chuẩn bị/chạy/xuất/pilot/tests được liệt kê dưới đây; chúng đang là untracked, chưa tự được đưa vào commit.
- Chưa thay thuật toán estimator/ranker baseline dùng chung. Chưa có phương pháp đề xuất mới.
- README gốc `data/exp_d/README.md` đã hoàn tác, hiện không có diff với Git. Không coi đây là thay đổi còn hiệu lực.
- `README_changed.md` là file mới đang hiện Git, không được tính như thay đổi thuật toán do đợt này thực hiện và không chỉnh trong lượt cập nhật nhật ký.
- Không stage, commit hoặc push.

## 2. File nguồn cũ đã sửa: data/exp_d/build_exp_d.py

| Thành phần | Code cũ | Code hiện tại | Mục đích và đánh đổi |
|---|---|---|---|
| Tìm thiết kế phiên | Xáo anchors, chọn context/focus ngẫu nhiên; thiếu pool thì bỏ lần thử | Liệt kê tổ hợp khả thi trước, cache eligible theo context/focus | Chọn từ pool có thật, tránh chọn ngẫu nhiên không kiểm soát độ phủ |
| Phân bố focus | Phụ thuộc lần chọn ngẫu nhiên và phiên còn lại sau lọc | Ưu tiên focus ít phiên nhất riêng theo similar/different | Run hiện tại: mỗi focus 300 phiên = 150 similar + 150 different |
| Số positives trong pool | Không ưu tiên thiết kế có khả năng đạt quota positive | Trong focus đã chọn, ưu tiên khả năng positive đến quota cấu hình; sau đó thiết kế/context ít dùng | Mean grade 2 tăng từ 1,81/20 ở bộ cũ lên 4,5/20 ở bộ mới; anchors giảm từ 409 xuống 57. Đây là thay sampling, không phải ranker tốt hơn |
| Anchor trong một user | Duyệt mỗi anchor tối đa một lần | Theo dõi used_anchors, giữ tối đa một lần/user | Giữ không lặp anchor trong 5 phiên của cùng user; vẫn có thể lặp giữa users |
| Query | Lấy concept đầu theo alphabet và mẫu cố định | Chọn concept thật ngẫu nhiên theo seed, đa dạng mẫu similar/different tương thích parser | Vẫn là mock lexical, chưa phải query tự nhiên. Chưa chứng minh parser mới tốt hơn |
| Báo cáo sinh dữ liệu | Chủ yếu quota/shortfall/skipped/behavior_counts | Thêm phân bố focus/context, số thiết kế khả thi, positive capacity, mean positives và unique anchors | Theo dõi chất lượng pool và độ phủ, không chỉ tổng phiên |

Giữ nguyên: helper candidate_sample, relevance/session_grade, matching chính xác ngoài focus, công thức utility/noise phản ứng, cutoff, context/focus weights 0,6/0,4 và các loại query mode. Generator nguồn thật vẫn có 0 exposures/interactions trên run hiện tại; không tuyên bố đã giải quyết nguồn cặp thật.

## 3. File mới: công cụ tái lập và xuất kết quả

| File trong data/exp_d/ | Đã thêm gì? | Có thay phương pháp nghiên cứu không? |
|---|---|---|
| `prepare_workspace.py` | Snapshot biệt lập; chuẩn hóa LF cho hai bản sao đã xác nhận, kiểm tra hash; --name, --mode current/baseline; không ghi đè | Không. current dùng code D mới rồi phải sinh lại D; baseline chỉ khôi phục bản generator Git HEAD nếu hash khớp dataset cũ |
| `run_baseline_pipeline.py` | Tạo workspace mới, sinh/validate D, dry-run/scoring, tự export; --with-synthetic chạy thêm pilot; kiểm tra nguồn đã snapshot không đổi | Không. Đây là điều phối thực thi, không phải model mới |
| `export_results.py` | Kiểm hash output rồi copy nguyên bundle/manifest về exp_d/results; thêm receipt, chặn ghi đè và path traversal | Không. Không sửa manifest để giả đổi nơi chạy |
| `test_export_results.py` | 4 tests cho copy giữ nguồn/manifest, hash sai, không ghi đè, path traversal | Kiểm tra kỹ thuật |

## 4. File mới: pilot observation tổng hợp

| File trong data/exp_d/ | Đã thêm gì? | Ranh giới phải giữ |
|---|---|---|
| `run_synthetic_observation_pilot.py` | Chọn 30 phiên theo focus × direction × query mode; dựng observation synthetic riêng; sinh phản ứng có điều kiện theo intent và noise; chạy baseline/oracle trong hai điều kiện không/có observation | Giữ nguyên anchor/candidates/query/labels/cutoff của phiên chọn; không nối synthetic vào corpus real hoặc gọi là A silver |
| Cũng trong runner pilot | Facet ngoài focus cùng trạng thái; focus same/different lấy concept nguồn. Public scorer không nhận truth/provenance ẩn. Matching/time/labels kiểm bằng check_d hiện hành; profile/vector ranking giữ cố định | Không sửa estimator/validator chung, không nới matching; synthetic mới là nguồn evidence bổ sung |
| Cũng trong runner pilot | Check control khớp predict baseline nguồn; focus-only metrics, 3 seeds × 2 noise; manifest/hash và kiểm nguồn không đổi | Kiểm cơ chế trong simulator, chưa phải bằng chứng người dùng thật. ID synthetic khác nhau không bảo đảm nội dung độc lập |
| `test_synthetic_observation_pilot.py` | 5 tests cho deterministic/provenance, không có hidden fields trong logs, matching sai, cutoff sai, nhãn sai, feedback theo intent | Kiểm tra contract, không xác nhận độ thực tế của simulator |
| `SYNTHETIC_OBSERVATION_PILOT.md` | Hướng dẫn nguồn bổ sung: protocol overlay, lệnh CMD, output và giới hạn | Tài liệu nguồn có thể đưa lên Git, không phải thay đổi model |

Không gọi LLM, không tải model/dataset từ mạng. Phần mô tả observation là template giả định và facet dựng có kiểm soát; không bịa citation hoặc kết quả nghiên cứu để giả bài thật.

## 5. Các file/thành phần không thay đổi

| Thành phần | Trạng thái |
|---|---|
| `scripts/baseline_common.py` | Không sửa direction_estimate, intent_scores hoặc chính sách score -1 |
| `scripts/validate_experiments.py` | Không sửa validator chung, không bỏ kiểm matching |
| `scripts/experiment_runner.py`, `scripts/exp_d/run_exp_d.py` | Không sửa evaluator/runner baseline chung |
| `data/experiment_common.py` | Không sửa helper chung |
| Corpus, A, C, config chung | Không sửa nguồn/handoff chung |
| `data/exp_d/README.md` | Đã hoàn tác; Git diff rỗng |

Score -1, missing facet và query ambiguous/none là quy tắc/trường hợp có chủ đích hiện hành, không được ghi như lỗi đã sửa.

## 6. Bằng chứng thực thi hiện tại: baseline_20261016_v1

- Pipeline do người thực hiện chạy đã báo PIPELINE COMPLETE.
- Canonical: 1.500 phiên, 30.000 labels; đủ 7.500 predictions và 7.500 details, 5 phương pháp × 1.500 case. Dataset mới mean grade 2 = 4,5, 57 anchors, mỗi focus 150 similar + 150 different.
- Pilot: 30 phiên, **28 anchor riêng**; 6 cấu hình × 120 exposures/240 interactions. Có 300 predictions/cấu hình (5 phương pháp × 2 điều kiện × 30 phiên), tổng 1.800.
- Hash export canonical 6 files và synthetic 78 files đều khớp. Input/code hashes so với workspace khớp; kiểm tra 9.300 rankings đúng pool 20 IDs riêng, score hữu hạn và sắp đúng.
- Control công khai đã được runner kiểm khớp baseline nguồn; source snapshot không đổi. Test exporter 4/4 và test overlay 5/5 đã pass ở giai đoạn triển khai; lượt cập nhật tài liệu này không chạy lại scoring/tests hoặc sửa code.

## 7. Kết quả phải diễn giải đúng

| Phép đo | Kết quả của run hiện tại | Kết luận được phép |
|---|---|---|
| Canonical behavior focus | Accuracy/coverage 0%; toàn unknown do thiếu evidence D | Chưa kiểm chứng behavior trên nguồn bài thật; coverage direction tổng 50% chỉ do context cho sẵn |
| Canonical search focus | Accuracy/coverage 33,33% toàn bộ; query clear được xử lý đúng | Có tín hiệu từ mẫu query clear; chưa chứng minh hiểu query tự nhiên |
| Synthetic behavior, noise 0,2 | Focus accuracy/coverage 100% ở 3 seeds | Estimator hoạt động với bằng chứng mô phỏng này |
| Synthetic behavior, noise 0,5 | Focus accuracy 83,33–100%; coverage 86,67–100% | Có độ nhạy với noise/seed trên pilot nhỏ, chưa phải hiệu quả người thật |
| Pilot ranking behavior | nDCG@10 0,8305 → 0,8284; compliance@5 0,4533 → 0,4533 | Chưa có cải thiện ranking, dù focus được suy tốt hơn |

Các số của pilot cũ trên dataset cũ (ví dụ 30 anchors hoặc accuracy noise 0,5 từ 73,33%) không dùng thay cho lượt hiện tại. Các output thử cũ đã được người thực hiện yêu cầu dọn; báo cáo cũ chỉ là lịch sử.

## 8. Trạng thái cuối

Đã hoàn thành mốc tạo dữ liệu/pilot, baseline và pipeline tái lập. **Chưa có phương pháp đề xuất mới hoặc bằng chứng vượt baseline.** Bước tiếp theo cần chốt câu hỏi cải tiến và phép so trên cùng dataset, xem độ phủ anchor/simulator và tách phần phát triển với đánh giá cuối. Không dùng chênh lệch giữa hai dataset để quy thành cải thiện thuật toán.
