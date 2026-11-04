# Exp A: so sánh v1 và phần chuẩn bị v2 trước khi train

Ngày ghi nhận: 2026-10-18, Asia/Bangkok.

**Checkpoint cập nhật 2026-10-19: probe suy luận version 1 đã COMPLETE; collector xác minh 12/12 record và replay validator khớp. Chưa đạt gate nội dung/vận hành: base lỗi grounding 6/6; adapter bị duplicate stop 3/6, JSON chưa đóng. Chưa train adapter v2, chưa có F1 mới; không chuẩn hóa diện rộng hoặc push train từ kết quả này.**

## Thay đổi cụ thể

| Thành phần | v1 đã chạy | Chuẩn bị v2 hiện tại | Mức kiểm chứng |
|---|---|---|---|
| Base model | Qwen3-8B, revision b968826d9c46dd6066d109eabc6255188de91218 | Giữ cùng base/revision; probe dùng base hoặc adapter v1 đã seal | GPU đã đo; identity/runtime và 12 record đã xác minh |
| Trọng số | Adapter v1 đã train, micro F1 59.28 theo bộ nhãn v1 | Chưa tạo trọng số v2 | Không gọi probe là model v2 đã train |
| Policy/prompt | v3.7, evidence một câu | Candidate v2.2 và schema nhiều evidence đã có từ vòng rà nhãn trước; lượt này giữ nguyên để tách hiệu ứng decoding | Candidate cần xác nhận trên mẫu nguồn mới |
| Item đầu ra | concept + evidence_id | concept + evidence_ids theo thứ tự nguồn, giữ từng câu evidence riêng | Dùng validator v2 hiện có; không tự đổi tên field rồi coi nhãn đã được rà |
| Decoding | Greedy, do_sample=False | So greedy với do_sample=True, temperature=0.7, top_p=0.8, top_k=20 | GPU: adapter greedy đạt validator 1/3, sampling 2/3; còn loop và lỗi nghĩa, chưa chọn cấu hình đạt |
| Giới hạn mỗi lượt | Tối đa 2048 token trong lượt A/B timeout | 1024 token và 90 giây trong probe; watchdog worker 1500 giây | Test Transformers thật trên Qwen nhỏ; giới hạn thời gian được kiểm tra giữa các bước sinh |
| Kết thúc JSON | Tiếp tục chờ EOS hoặc trần token | Dừng ngay khi đủ object JSON cấp ngoài cùng; parser xử lý dấu ngoặc và escape trong string | Bắt được ca P000151 sinh hai JSON liên tiếp |
| Lặp trong facet | Bản A/B không chặn; probe cũ bắt object giống hệt mỗi 16 token | Kiểm tra mỗi bước; chặn concept đã normalize bị lặp trong cùng facet, kể cả evidence khác | Bắt được hai ca P000962, P001892; cho phép concept ở hai facet khác nhau |
| Output bị chặn | Có thể hết ngân sách rồi lỗi parse/fallback | Ghi stop_reason, bounded_stop, toàn bộ raw chưa cắt và suffix bị bỏ; lỗi ngân sách được ghi riêng | Không tự thêm dấu ngoặc để biến JSON thiếu thành kết quả hợp lệ |
| Review | Pipeline A/B yêu cầu draft và review, tối đa ba lượt | Giữ yêu cầu review cho pipeline chính; probe này chỉ đo draft như probe cũ | Probe chỉ đo draft; full pipeline hai lượt vẫn chưa đo |
| Train/dev/test | 467/100/100, AI references | Giữ split; đã lập hàng đợi nguồn cho đủ 567 train/dev, không chứa assistant targets hoặc test IDs | 40 nhãn pilot cũ chỉ là candidate; chưa đủ dữ liệu v2.2 đã xác nhận |
| Loss, LoRA và optimizer | JSON+EOS assistant-only; r16, alpha32, dropout0.05; NF4/FP16 | Trainer v1 không bị sửa; dự kiến tái dùng cấu hình cơ sở sau khi dữ liệu sẵn sàng | Chưa thay learning rate/epoch/rank để tránh đổi nhiều biến cùng lúc |
| Checkpoint và đánh giá | Chọn checkpoint bằng dev loss, threshold semantic 0.85 | Giữ nguyên tắc dùng dev; sẽ kiểm thêm schema, lặp, fallback, latency và chất lượng facet trước test | Test không dùng để chọn prompt/decoding/checkpoint; nhãn test theo policy mới phải có phiên bản riêng |
| Bảo toàn v1 | Artifact đã seal | Đối chiếu đúng hash của 38 file được bảo vệ; toàn bộ mã mới ở finetuning/v2 và test mới | PASS; adapter, split, dữ liệu, điểm v1 không đổi |

## Bằng chứng kiểm thử local

- 9 test mới cho generation: PASS, gồm raw output thật của cả 3 ca Kaggle và
  kiểm tra giới hạn thời gian qua Transformers/Qwen3 nhỏ.
- 1 test đóng gói/readiness: PASS, xác nhận 567 nguồn train/dev, không overlap
  100 test IDs, không chứa nhãn trong payload chẩn đoán và không tạo train.jsonl.
- Test collector mới phát hiện thiếu record, checksum sai, sai nguồn/messages,
  seed/stage/mode/quantization hoặc vượt 1024 token kể cả khi record bị ký lại.
  Test đã đi qua RED rồi GREEN. Tổng cộng 11 test mới.
- Toàn bộ 54 test fine-tuning hiện tại: PASS; 38 test trong tests/: PASS.
- Reviewer độc lập rà 5 file mới, chạy lại 10 test liên quan: không có launch blocker.
- Lượt rà collector sau đó tìm hai khoảng trống kiểm chứng seed/mode và trần token;
  đã tái hiện, sửa, kiểm thử và được reviewer xác nhận không còn blocker.
- Instruction của probe khớp prompt v2.2 hiện có; bundle nguồn đã có trên Kaggle
  không chứa reference/target/annotation files.
- Log: data/exp_a/finetuning/v2/validation/.

## Payload suy luận được chuẩn bị

Đích dự kiến: kernel **riêng tư** `htnkhi/exp-a-v2-decoding-probe`.
Chỉ upload bootstrap và ba file Python: generation.py, probe.py, legacy_probe.py.
Hai dataset riêng tư đã tồn tại được gắn làm đầu vào:
`htnkhi/exp-a-qlora-policy-ab-v2-inputs` và
`htnkhi/exp-a-qwen3-8b-facets-qlora-v1`.
Không upload thêm nguồn/nhãn train/dev, trọng số, credentials hoặc checkpoint.

Probe chạy 12 lượt: base/adapter v1 × greedy/sampling × ba bài chẩn đoán đã có,
một seed, không train. Hai worker dùng hai T4, mỗi worker thấy một GPU.
Kết quả chỉ dùng chẩn đoán định dạng/lặp và thời gian; 3 bài không chứng minh
khả năng tổng quát hóa. Khác biệt throughput giữa base/adapter còn có thể chịu
ảnh hưởng GPU/PEFT; ưu tiên so hai decoder trong cùng arm.

Mã và metadata: data/exp_a/finetuning/v2/build/kernel/.
Hash payload và trạng thái sẵn sàng: data/exp_a/finetuning/v2/build/readiness.json.
Upload đầu bị automatic approval review từ chối vì cần xác nhận cụ thể payload
và đích. Sau đó người dùng chọn “Cho phép chạy probe riêng tư”; đúng payload đó
đã được push thành version 1. Không dùng đường vòng. Đã tải lại mã cloud và
metadata, xác minh khớp mã local, riêng tư và đúng hai dataset đầu vào.

Launch report: data/exp_a/finetuning/v2/build/push_report.json.
Đã cập nhật heartbeat “Theo dõi Exp A v2” thành mỗi 30 phút. Nếu probe và kiểm
chứng tiếp theo phù hợp, người dùng cho phép tự chuẩn hóa đủ train/dev, cập
nhật dataset riêng tư và push train v2; vẫn gửi bảng so sánh cuối trước push,
không cần xin lại xác nhận. Nếu không ổn thì báo bằng chứng, chưa push train.
Sau khi xác nhận launch train v2 thành công, pause lịch; không tạo schedule
theo dõi train v2. Collector mới ở finetuning/v2/collect.py không chấm F1.

## Điều kiện trước kernel train v2

1. Kiểm chứng hai kiểu lặp trên GPU, chọn decoding theo cả chất lượng và thời gian;
   giữ cấu hình còn lại làm đối chứng, không chọn theo JSON hợp lệ đơn thuần.
2. Xác nhận policy v2.2 bằng nguồn train/dev mới; hoàn thiện rà nguồn cho 567
   train/dev. Không lấy output student làm nhãn và không trộn nhãn v1 chưa rà
   vào một bộ dữ liệu gọi là đã chuẩn hóa v2.
3. Khóa prompt/schema, nhãn, source, split, tokenizer và cấu hình; kiểm token
   bằng tokenizer thật, không truncate; kiểm train/dev prefix và EOS.
4. Dùng base model đã pin để train adapter mới; output/checkpoint mới, không
   ghi đè v1. Gửi lại bảng thay đổi với số liệu và manifest cuối trước khi push.
5. Theo dõi bằng signature/kernel version cụ thể; thu adapter và dự đoán,
   kiểm hash trước khi báo kết quả. Không báo điểm v2 khi nhãn tham chiếu hoặc
   lượt chạy chưa đủ điều kiện.

Nguồn tham khảo decoding: [model card chính thức Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B#best-practices).
Thông số sampling là nhánh thử theo khuyến nghị non-thinking, chưa được chứng
minh là sửa được lỗi trong tác vụ này.

## Kết quả đo thực tế — cập nhật 2026-10-19

| Hạng mục | v1 đã seal / trước sửa | Bằng chứng v2 diagnostic mới |
|---|---|---|
| Trọng số | Adapter v1 và điểm cũ giữ nguyên | Vẫn dùng base/adapter v1; không tạo adapter v2 hoặc F1 mới |
| JSON stop | Ca cũ có hai JSON hoặc lặp tới trần | 9/12 dừng json_complete; 3/12 duplicate guard bắt lặp nhưng JSON chưa đóng; suffix bỏ 0 |
| Greedy vs sampling của adapter | Chưa có so cặp | Schema+grounding từ vựng: 1/3 vs 2/3; loop 2/3 vs 1/3; chưa có decoder đủ điều kiện |
| Grounding base | Chưa đo lượt mới | 6/6 JSON hợp lệ nhưng 6/6 lỗi từ/thứ tự nguồn |
| Nghĩa của output qua validator | Chưa được xác nhận | Sampling mất comparator/10–100x ở P000962 và bối cảnh TREC 10 ở P000151; chưa đạt semantic policy |
| Budget | Trần probe 1024 token / 90 giây | Max 528 token / 71.354 giây; không có time_budget/token_limit; lỗi incomplete là do duplicate stop |
| Thời gian trung bình greedy/sampling | Chưa đo lượt mới | Base 24.010/25.384 giây; adapter 44.840/37.847 giây mỗi draft; 3 bài/1 seed, không suy ra khả năng tổng quát |
| Kiểm chứng | Các suite cũ là checkpoint 2026-10-18 | Collector/replay 12/12; hash v1 38/38; 10/10 test generation+collection chạy mới PASS |
| Dữ liệu và launch | 467/100/100, 40 pilot candidate | Chưa chuẩn hóa 567 train/dev hoặc cập nhật dataset; train v2 chưa push; monitor đã PAUSED, không còn run chờ |

Signature probe: `5ad1db912e956ceaab446bb5698401324f0d1d6c7cbda0f0c2d9b5decbfffb88`.
Hash code zip/bootstrap, source bundle, policy/prompt/schema, split, review queue đều khớp readiness ban đầu; không có thay đổi code trong lần collection.

Chi tiết, từng ca dừng, giới hạn validator và manifest: [báo cáo probe](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/scripts/exp_a/docs/QLORA_V2_DECODING_PROBE_RESULT_2026-10-19.md>).
