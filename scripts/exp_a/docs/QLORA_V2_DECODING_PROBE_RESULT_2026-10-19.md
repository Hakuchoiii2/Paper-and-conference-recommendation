# Exp A — kết quả decoding probe v2, 2026-10-19

**Quyết định: chưa đạt điều kiện chuẩn hóa diện rộng hoặc train v2.** Probe riêng tư `htnkhi/exp-a-v2-decoding-probe`, version 1 theo push report, đã COMPLETE. Đây là 12 **draft** của base/adapter **v1** × greedy/sampling × 3 bài, một seed; không phải adapter v2 đã train, không phải F1 hoặc benchmark tổng quát hóa.

## Tính toàn vẹn và kiểm thử

- Chạy `v2/collect.py` bằng `.venv-qwen/Scripts/python.exe -X utf8 -B`: **PASS 12/12** tổ hợp duy nhất, worker exits `[0, 0]`, checksum từng record, code, nguồn, adapter manifest, instruction, messages, seed, draft stage, model/revision, Transformers, NF4/FP16, non-thinking, cache và trần 1024 token. Replay validator khớp toàn bộ lỗi đã ghi trên Kaggle.
- Signature probe: `5ad1db912e956ceaab446bb5698401324f0d1d6c7cbda0f0c2d9b5decbfffb88`.
- Signature nguồn: `825fecb2556d886d754af96fffe2f70f08d3209a9b30f63bc7bfc0f8d4188427`.
- Đối chiếu byte của `settings.json`, hai instruction và `model_inputs/papers.jsonl` tải về với bundle nguồn đã seal: khớp. Hash prompt tải về khớp candidate prompt v2.2. Toàn bộ hash payload trong readiness, gồm code zip/bootstrap, source bundle, policy/prompt/schema, split và review queue: khớp.
- **38/38 artifact v1** vẫn đúng hash. Chỉ hash file test được bảo vệ; không đọc nội dung test để chỉnh prompt, decoding hoặc chọn checkpoint.
- Runtime quan sát: Tesla T4, Torch `2.11.0+cu128`, Transformers `4.57.6`, Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`; attention `matrix_efficient_no_gqa`, NF4 double FP16, thinking off, cache on. Hai worker cùng runtime, khác cờ adapter như dự kiến. Không có bất nhất chữ ký/runtime được phát hiện qua các kiểm tra trên.
- Chạy mới **10/10 test generation + collection: PASS**. Lượt đầu có 9 pass và 1 lỗi quyền ghi Temp của sandbox; đặt Temp trong workspace rồi chạy lại cả 10: PASS. Đây là lỗi môi trường local, không phải lỗi collection trên dữ liệu probe. Không chạy lại toàn bộ suite cũ vì không sửa code.

## Schema, grounding, stop, token và thời gian

`Đạt validator` ở bảng là không lỗi schema/grounding từ vựng và không bị dừng cưỡng bức. Nó **không** xác nhận vai trò facet, entailment, điều kiện hoặc coverage.

| Arm | Decoder | Schema hợp lệ | Đạt validator | stop_reason | JSON chưa đóng | Output token tổng | Sinh trung bình / trung vị (giây) |
|---|---|---:|---:|---|---:|---:|---:|
| base | greedy | 3/3 | 0/3 | json_complete: 3 | 0/3 | 928 | 24.010 / 23.219 |
| base | sampling | 3/3 | 0/3 | json_complete: 3 | 0/3 | 990 | 25.384 / 21.931 |
| adapter | greedy | 1/3 | 1/3 | json_complete: 1, duplicate_concept: 2 | 2/3 | 985 | 44.840 / 35.416 |
| adapter | sampling | 2/3 | 2/3 | json_complete: 2, duplicate_concept: 1 | 1/3 | 833 | 37.847 / 34.207 |

- Base: cả 6/6 JSON hoàn chỉnh nhưng 6/6 có lỗi `Concept must use selected source words in source order`; có diễn giải/đổi từ/thứ tự ngoài ràng buộc extractive của policy. Không đồng nhất lỗi grounding từ vựng với mọi loại sai sự thật.
- Adapter v1: 3/6 JSON hoàn chỉnh qua validator từ vựng; 3/6 bị duplicate guard dừng ở giữa mảng contribution. Phần còn thiếu không được tự đóng ngoặc, bỏ item rồi gọi hợp lệ hoặc dùng làm nhãn.
- Tổng stop: **9 json_complete, 3 duplicate_concept, 0 time_budget, 0 token_limit, 0 eos**. Cả 3 ca incomplete đều do guard bắt lặp; không có câu trả lời hợp lệ bị cắt vì timeout trong lượt này. `discarded_suffix_chars = 0` ở cả 12 record; không có suffix JSON thứ hai bị bỏ trong lượt mới.
- Tổng **20.896 input token, 3.736 output token**; output lớn nhất **528/1.024 token**, thời gian sinh lớn nhất **71,354/90 giây**. Input lần lượt P000151=1.618, P000962=1.733, P001892=1.873 token cho mỗi arm/decoder. Token là số đo từ tokenizer/model trong lượt chạy được collector xác minh, không ước tính bằng ký tự.
- Thời gian trong bảng là `generation_seconds` mỗi draft, không phải latency end-to-end gồm tải model, queue hoặc mandatory review. So base/adapter còn có ảnh hưởng PEFT/GPU; sampling/greedy chỉ có 3 cặp, 1 seed, chưa chọn cấu hình thắng.

| Ca bị chặn | Concept lặp trong contribution | Output token | Giây | Kết quả |
|---|---|---:|---:|---|
| adapter/greedy/P000962 | Communication costs are the principal constraint | 528 | 71.354 | incomplete JSON |
| adapter/greedy/P001892 | unified datasets, kể cả evidence khác | 254 | 35.416 | incomplete JSON |
| adapter/sampling/P001892 | new evaluation | 407 | 54.751 | incomplete JSON |

Đã replay duplicate detector trực tiếp trên cả ba raw: khớp concept/facet đã ghi; không có JSON cấp ngoài hoàn chỉnh. Guard giới hạn chi phí đúng thiết kế, nhưng **bắt được lặp không chứng minh nội dung đúng**. Tăng timeout/token không phải lời giải đã được chứng minh cho lỗi này.

## Rà nguồn và ý nghĩa: các vấn đề cụ thể

Đây là spot check bởi agent thu thập, **không phải review nhãn độc lập**. Không tạo hoặc chấp nhận nhãn mới. Validator hiện chỉ kiểm shape, evidence IDs và từ theo thứ tự nguồn; chính schema.py cũng nêu roles/coreference/qualifiers cần review.

1. **adapter/sampling/P000962, contribution, A7:** output `reduction in required communication rounds` qua validator, nhưng bỏ magnitude **10-100x** và comparator **synchronized stochastic gradient descent**. Nguồn A7 có cả hai; policy v2.2 yêu cầu giữ quantities/comparison của finding. Output này chưa đủ nghĩa dù grounding từ vựng không lỗi.
2. **adapter/sampling/P000151, contribution, A3:** `accurate results` bỏ bối cảnh `a large collection of free-form questions used in TREC 10`. Đây là performance finding; policy yêu cầu giữ empirical setting.
3. **adapter/sampling/P000151, contribution, A1:** `semantic classification` đến từ mệnh đề nền `These constraints may include ...`; riêng phrase đó chưa được nguồn xác định là artifact mới hay finding. Đưa vào contribution làm mất vai trò và modality.
4. **base/greedy/P000962, dataset, A5:** `Five different model architectures` là kiến trúc model; `Four datasets` chỉ là số lượng bộ không tên. Cả hai không đạt quy tắc named-resource của dataset dù từ xuất hiện trong nguồn. Đây là lỗi role ngoài lexical grounding.

Không chấm coverage tổng thể, F1, hoặc xác nhận policy bằng 3 bài đã biết. Full mandatory draft/review chưa được đo trong probe này. Cần chiến lược tạo câu trả lời vừa hoàn chỉnh vừa đúng nguồn; chỉ dừng sớm/sửa field/sửa ngoặc không giải quyết các finding thiếu nghĩa.

## Checkpoint và bước tiếp theo

- **Không** chuẩn hóa 567 train/dev, cập nhật dataset hoặc push train từ bằng chứng này. Không push probe trùng hoặc mở lượt GPU mới. Không thay nhãn/reference hiện có bằng student outputs.
- Còn nguyên các gate: mẫu nguồn train/dev mới xác nhận policy v2.2 qua review độc lập; rà nguồn đủ 567 bài (467/100); hashes nguồn/policy/prompt/schema/nhãn; tokenizer thật, prefix/EOS, không truncate; pipeline/train/package/preflight; bảng v1 → v2 thực tế ngay trước push. Nhãn vẫn là AI references với human review pending.
- Probe hiện COMPLETE; không còn run chờ theo dõi. **Đã tạm dừng automation (PAUSED đã xác minh), theo yêu cầu xử lý khi kết quả không đạt; chờ quyết định hướng phục hồi generation/grounding.** Cần chốt chiến lược trước một thí nghiệm GPU giới hạn mới. Chưa có bằng chứng để chọn sampling làm cấu hình đạt hoặc cho rằng train v2 sẽ tự sửa các lỗi này. Không tạo lịch theo dõi train v2; không archive chat.
- Bảo toàn `push_report.json` là bản ghi launch ban đầu. Đã lưu readiness trước collection rồi cập nhật blocker/checkpoint hiện tại. Dữ liệu v1 và bộ test tiếp tục được seal.

## Artifact

- [Raw JSON/log](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/finetuning/v2/downloads/probe_v1_20261019_0219>)
- [Collector summary](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/finetuning/v2/build/analysis_summary.json>)
- [Audit từng record và spot check nguồn](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/finetuning/v2/build/collection_audit_2026-10-19.json>)
- [Manifest SHA-256 toàn bộ file tải về](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/finetuning/v2/build/collection_manifest_2026-10-19.json>)
- [Readiness hiện tại](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/finetuning/v2/build/readiness.json>)
- [Snapshot readiness trước collection](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/finetuning/v2/build/readiness_before_collection_2026-10-19.json>)
- [10 test mới chạy](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/finetuning/v2/validation/probe_collection_tests_2026-10-19.log>)

Thu thập UTC: 2026-10-18T20:18:59.961032+00:00 (ngày báo cáo theo Asia/Bangkok).
