# Thực nghiệm E — Theo dõi sở thích thay đổi theo thời gian

Trạng thái 2026-10-05: đã có generator, config và validator. Đã kiểm tra ở quy mô
mục tiêu bằng fixture chỉ dành cho tests; chưa sinh dataset trên corpus thật vì
máy mới có A part_1 (842/4.210), còn thiếu part_2–part_5.

Mọi bài giữ nguyên ID/title/abstract trong `data/processed/papers.jsonl`.
Generator yêu cầu silver A toàn corpus ở `data/exp_a/generated/`, kèm metadata
và manifest `status: complete` đã qua validator A. Bài có `fallback_used` hoặc
`validation_errors` bị loại khỏi sampling; facet `[]` vẫn là thiếu bằng chứng.
Không tự sinh facet hoặc thêm bài để lấp chỉ tiêu. Output B–E là `dataset_kind: mock`,
seed 42, vì queries/nhãn/hành vi được sinh theo rule trên silver bài thật.

## Mục đích và quy mô

Dùng **cùng 300 user IDs của D**, tạo stream E riêng để kiểm tra khả năng theo dõi
sở thích thay đổi. **4 periods × 15 events/user/period = 18.000 events**,
1.200 temporal profiles; nằm trong mục tiêu 15.000–20.000 của README.
Không cộng D/E thành 600 users.

Đầu vào là corpus, silver/metadata/manifest A, `configs/exp_e.json` và
`data/exp_d/generated/users.jsonl` kèm D manifest. Kiểm tra user checksum/count,
corpus và facet hashes D/E trùng nhau. E chỉ đọc danh tính và manifest D,
không đọc D future events hoặc D latent profiles; tự sinh initial profile.

## Stable/drift và thời gian

150 users stable giữ nguyên profile cả bốn periods; 150 users drift có profile
ban đầu và đích mới. Tỷ lệ 0.5 và hệ số chuyển [0,0.5,1,1] được ghi trong config.
Mỗi weight nội suy (1-alpha)×old + alpha×new, concept vắng có weight 0.
Nhóm user và các profiles nằm trong ground_truth.

Bốn periods là tháng 1,2,3,4 năm 2026 (UTC), theo khoảng liên tiếp [start,end).
Mỗi user có 15 events/period, timestamp tăng nghiêm ngặt và nằm trong period.
Không lặp bài trong một period; có thể gặp lại ở period khác.
Periods 1–3 là history (13.500 events), period 4 holdout (4.500 events).
Holdout không tham gia tạo observable report về loại hành vi.

## Rule mô phỏng `profile_first_v1`

Sinh latent profile **trước hành vi**, dùng concept có thật trong silver A.
Mặc định tối đa hai concept/facet: concept ưa thích có weight [0.5,1],
concept tránh có weight [-1,-0.5]; concept không nằm trong profile có weight 0.
Affinity là trung bình weight trên toàn bộ concepts của bài.

Mỗi event chọn một bài: xác suất mục tiêu 0.8 từ pool có concept chung với profile
(gồm cả thích và tránh), còn lại từ pool tổng; hết targeted pool thì dùng pool tổng.
Cộng nhiễu Gaussian độ lệch chuẩn 0.15. Các ngưỡng [-0.25,0.05,0.2,0.4] biến score
thành dislike/view/click/save/like theo thứ tự. Đây là giả thuyết mô phỏng công bố
trong config, chưa được hiệu chỉnh từ hành vi người thật. Không xuất exposure log
riêng hoặc suy profile ngược từ events để tạo truth.

## Tệp và schema

| Thư mục | Tệp | Nội dung |
|---|---|---|
| `data/exp_e/generated/` | `interactions_train.jsonl` | History periods 1–3 |
| generated | `generation_report.json`, `manifest.json` | Counts/rule/hashes; behavior_counts chỉ đếm history |
| `data/exp_e/ground_truth/` | `temporal_profiles.jsonl` | user_id, period, start_timestamp, end_timestamp, latent_preferences |
| ground_truth | `interactions_test.jsonl` | Future period 4 |
| ground_truth | `period_metadata.json` | Nhóm stable/drift, boundaries, drift_coefficients |

Event có đúng user_id, paper_id, interaction_type, timestamp; E không tạo users file mới.
Khóa profile là (user_id,period), không thiếu hoặc trùng. Validator kiểm tra cùng
IDs D, bốn khoảng, nội suy, stable không đổi, drift thay đổi và cutoff history/future.
Mô hình chỉ đọc history và nội dung/facets được phép; evaluator đọc truth riêng.

## Chạy và kiểm tra

Chạy từ thư mục gốc dự án, dùng Python 3.11+; B–E chỉ cần thư viện chuẩn:

~~~powershell
python data/exp_e/build_exp_e.py --dry-run
python data/exp_e/build_exp_e.py
python data/exp_e/build_exp_e.py --validate-only
~~~

`--dry-run` kiểm tra đầu vào và hiển thị mục tiêu, không sinh tệp.
`--config configs/exp_e.json` chỉ định cấu hình khác; đường dẫn bên trong config
được tính từ gốc dự án. Observable/truth phải ở hai thư mục riêng dưới đúng exp.
Chạy lại sẽ rebuild output tự động theo input/seed; không chạy hai lượt cùng output.

Manifest ghi config, input/generator hashes, actual counts và complete/partial.
Validator đối chiếu schema, refs, hashes, rule, quota, split và hidden truth; một
checksum hợp lệ không thay thế kiểm tra nội dung. Khi A thay đổi, rebuild dataset.
Xem [contract chung](../../DATA_CONTRACT.md) và
[hướng dẫn gộp A, chọn 400 bài và chạy B–E](../../docs/RUN_EXPERIMENTS.md).

Kiểm tra kỹ thuật không chứng minh đúng ngữ nghĩa hoặc tính đại diện của nhãn
silver và hành vi mô phỏng. Human gold A và đánh giá mô hình là các bước riêng.
