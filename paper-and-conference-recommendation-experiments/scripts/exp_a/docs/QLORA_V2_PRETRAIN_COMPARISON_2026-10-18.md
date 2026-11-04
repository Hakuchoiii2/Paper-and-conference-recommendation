# Exp A v1 → v2: bản cuối trước push train

Cập nhật UTC: 2026-10-19T07:21:38.857997+00:00. Trạng thái: local preflight đạt; chưa push train, chưa có adapter/F1 v2.

| Hạng mục | v1 đã chạy | v2 chuẩn bị launch |
|---|---|---|
| Base | Qwen/Qwen3-8B | Cùng revision b968826d9c46dd6066d109eabc6255188de91218; train adapter mới từ base, không tiếp tục adapter v1 |
| Dữ liệu | 467 train /100 dev;100 test riêng | Giữ nguyên toàn bộ ID/split/nguồn; chỉ567 train/dev trong payload; test có ID trong manifest split nhưng không có nội dung/nhãn test |
| Schema | concept + evidence_id đơn | concept + evidence_ids một/nhiều câu, thứ tự nguồn; không chỉ đổi tên field |
| Policy | Prompt v3.7 | Policy v2.2, nguồn/role/điều kiện/phủ định/coverage; prompt/schema thống nhất train/inference |
| Nhãn | AI references v1 | 567 bản nguồn-first,98 bài rà độc lập (60 trước+38 ca chọn lọc),469 chưa rà chéo được ghi rõ; human review pending |
| Xác nhận policy | Quy tắc v1 |12 bài nguồn mới6/6train/dev;2 actor trích độc lập trước đối chiếu; chốt bằng2 lượt kiểm bản tích hợp; không phải chứng nhận toàn corpus |
| Loss/EOS | Assistant completion+EOS, prefix inference thật | Tái dùng trainer v1 nguyên trạng; kiểm thật567 prefix/EOS, không truncate |
| QLoRA | r16/alpha32/dropout0.05/all-linear, NF4 double,FP16 | Giữ nguyên;batch1,accumulation8,3epochs,LR2e-4,seed42,cosine,warmup0.03;dev-loss chọn checkpoint |
| Budget | Maxsequence4096 |4096sequence/2048assistant; thực tế maxtrain3007/839,dev2789/968 |
| Tổng token train |1,271,952 input;104,864 supervised |947,524 input;139,559 supervised |
| Tổng token dev |271,926 input;22,456 supervised |202,786 input;30,216 supervised |
| Runtime | Single TeslaT4,177steps,3epochs;train_runtime15933s | SingleT4,177steps dự kiến; không dùng runtime v1 làm ETA chắc chắn |
| Dataset/kernel |htnkhi/exp-a-qwen-qlora-inputs /exp-a-qwen-qlora | Đích mới riêng tư htnkhi/exp-a-qwen-qlora-v2-inputs /exp-a-qwen-qlora-v2 |
| Outputs | Adapter/checkpoint v1 |adapters/qwen3-8b-facets-qlora-v2;train_state_v2;v2_training_provenance.json |
| Test/F1 | Điểm v1 giữ nguyên | Kernel chỉ train+devloss; không test inference/F1, không tự publish adapter |
| Bảo toàn |38 artifact v1 đã khóa |38/38 hash khớp; không ghi đè v1 |

## Kiểm chứng bản cuối

- Nguồn/ID/split/schema/grounding:567/567 đạt; nguồn đóng băng giữ nguyên. Label nguồn thiếu thông tin không được bổ sung bằng student/fulltext hoặc đổi ID/split.
- Rà chọn lọc đã sửa mất antecedent, phạm vi thí nghiệm, baseline/method/resource roles, comparator bị cắt và số không xác định metric.98/567 là mẫu có chủ đích, không phải ước lượng tỷ lệ lỗi toàn tập.469 còn lại chỉ có lượt trích từ nguồn và kiểm tra tự động.
- Real pinned tokenizer: đủ567 bản cuối, prefix/EOS khớp, không truncate, maxsequence3007/4096,maxassistant968/2048.
-211 Exp A+38 project tests đạt ở checkpoint trước đổi gate lean.10 test riêng pipeline v2 đạt theo9pass lần chạy cuối+1 packaging rerun: lỗi còn lại của lần đầu là subprocessWindows thiếu-Xutf8 khi giải mã đường dẫn tiếng Việt; đã sửa và rerun riêng đạt. Không lặp fullsuite không đổi.
-2 kiểm thử gate mới và2 lượt reviewer-targeted tests đạt; reviewer source_confirmation_a không thấy blocker trong source/hash/split/mixed-review/coverage gates. Test entrypoint đã đưa về cuối để chạy trực tiếp không bỏ sót class.
- Bundle deterministic riêng tư: inventory chỉ train/dev+reviewproof+runtime; khớp hash; extraction an toàn; import/attention registration trong tiến trình mới và test cố ý thiếu helper đều đạt.
- Kiểm tra chỉ đọc own-list Kaggle thấy dataset/kernel v2 chưa tồn tại, account htnkhi truy cập được; không push trùng probe.

## Payload và giới hạn

Upload chỉ bundle v2 chứa567 nguồn train/dev, nhãn và provenance/reviewproof, policy/prompt/schema, mã runtime và cấu hình. Không chứa v1 adapter/base weights,credentials hoặc nội dung/nhãn test. Dataset mới được tạo private mặc định, kernel metadata private. Sau launch chỉ xác nhận version/code/signature/statusQUEUED hoặc RUNNING, ghi launchreport rồi giữ automationPAUSED; không lập lịch theo dõi trainv2.

Probe cũ là diagnostic base/adapterv1, không đo adapterv2. Lỗi loop/grounding của probe được giữ làm rủi ro; không yêu cầu adapterv1 phải đạt promptv2 mới được train mô hình phù hợp mới. Fine-tune v2 chưa chứng minh hết loop/JSON/semantic errors cho đến khi có đánh giá sau train.

## Hash bản cuối

- source_queue: `c4e3939b723ba61a91ec76de30c5786aa0bc0ed85a92ff382d2b7ab51f72f030`
- source_papers: `12c18487e720be13e970db767384e6454fbf973522d9322b499554c15bfa7ba1`
- annotations: `01ec2c340af8dcb1333a433683e5f323022251c370a0949fc4f8782f4a98970f`
- decisions: `53c0f39dc3eb56a92cf7b10ce558fca0c0fc1e008ebaef8f33cbdb29bf599d67`
- review_manifest: `998d18de3a40f9cfc18e858a3ca2f333698e5be7f43a61f409a323e66774814d`
- review_scope: `ad8aed8d63bf758691bf2de5c1f713c7bf46296844520b5f95901607bae3ee52`
- data_manifest: `d8b7acc0a1a70b067c173debdc9c9fdd6ec3b18ec2776d1b297e406dcaeccaf2`
- train: `58db0e5da392ae972066f650c4b77875a53228497e9a899f3b923d627a1b1595`
- dev: `319d1fe038be28f3a510b7e007e4122fda4010f351e68a640991130738e763ed`
- training_boundary: `c401b3357db6def3161e94f1027bf897e39c5ccd7084a802f9d1222859f510a3`
- training_kernel_template: `9f97986a6b248862faaf59be25b02e888ec8daa599e5619b2ed381651d415b82`
- tests: `191a4d47d23d903e4e57e9bfe84c34dc0d2727acbd6f9bb60b80c9d0d6147125`
- build_manifest: `af93600fa8fe8ecb04140a3496965bcac688cae9411f13537d6f95e82ad52f92`
- policy: `6b21f9ac8e196d0afeaf6605349346c85ff8ea549d8240ae5c8f00b56464e2e3`
- prompt_file: `9880b174b0a934d06e18845ad7ed9404380922c5a00dda34f90b71759489c1fa`
- schema: `2df0c73f5e81eea0b3c21fbb830208302e49f24dc288ae29d417620b242297d7`
- instruction: `65bf8ff8661bd076f658337b6f921f5ba360851bff3c3ca8d182ed95da2c0d8b`
- rendered_system: `25ee03ff0b1f8a5486841afef741e45e3d2c2d0254355674182846d98382a9ce`
- bundle: `3a4093e7113bfa9bf69bbd5b1a9f58418f7409ec7482653eb9d393da45138860`
- kernel: `55ac8a667bd829e23806ccbbec302ac7627c01c8382c696f3881b4de09782016`
- launch_signature: `3875d3d25d83d48170e26a97b07fb2338388b7ba3b557ff261396578f5207550`

Instruction hash khác hash file prompt do newline CRLF được đọc/ghi thành LF; chuỗi instruction khớp prompt đọc qua read_text và system thực sự render được hash riêng. Train/inference đều dùng cùng messages().

Báo cáo probe lịch sử: QLORA_V2_DECODING_PROBE_RESULT_2026-10-19.md. Bản so sánh trước chuẩn bị train được giữ tại v2/build/comparison_before_training_release.md.
