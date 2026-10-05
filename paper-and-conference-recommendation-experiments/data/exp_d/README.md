# Thực nghiệm D — Suy ra sở thích ngầm từ hành vi người dùng

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

Tạo người dùng, sở thích ẩn và tương tác để kiểm tra mô hình suy sở thích từ lịch sử.
Mặc định **300 users × 50 events = 15.000 tương tác**: mỗi người 30 history/20 future,
tổng 9.000 history và 6.000 holdout. Users U0001–U0300 chỉ có `user_id` quan sát được.

Đầu vào là corpus, silver/metadata/manifest A và `configs/exp_d.json`.
Không cần human gold A hoặc B/C outputs. E dùng lại danh tính D.
Nếu không đủ 50 bài đủ điều kiện cho một user thì báo lỗi, không lặp bài lấp quota.

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

## Thời gian, tệp và schema

D không lặp bài trong 50 events của một user. Timestamps UTC bắt đầu
2026-01-01T00:00:00Z, cách nhau một ngày; 30 events đầu là history, 20 sau là future.
Lịch sử cuối phải sớm hơn holdout đầu **nghiêm ngặt**, không random temporal split.

| Thư mục | Tệp | Nội dung |
|---|---|---|
| `data/exp_d/generated/` | `users.jsonl` | Chỉ user_id; không có latent preferences |
| generated | `interactions_train.jsonl` | 9.000 history events |
| generated | `generation_report.json`, `manifest.json` | Số lượng, rule, hashes; behavior_counts chỉ đếm history |
| `data/exp_d/ground_truth/` | `latent_user_profiles.jsonl` | 300 records user_id + latent_preferences |
| ground_truth | `interactions_test.jsonl` | 6.000 future events |

Event có đúng `user_id`, `paper_id`, `interaction_type`, `timestamp`.
Profile có đủ năm facets, mỗi facet là map concept → finite weight [-1,1].
Mô hình chỉ đọc users/history và nội dung/facets được phép. Evaluator đọc latent
profiles và future events riêng; không cho mô hình đọc report về outcomes tương lai.

## Chạy và kiểm tra

Chạy từ thư mục gốc dự án, dùng Python 3.11+; B–E chỉ cần thư viện chuẩn:

~~~powershell
python data/exp_d/build_exp_d.py --dry-run
python data/exp_d/build_exp_d.py
python data/exp_d/build_exp_d.py --validate-only
~~~

`--dry-run` kiểm tra đầu vào và hiển thị mục tiêu, không sinh tệp.
`--config configs/exp_d.json` chỉ định cấu hình khác; đường dẫn bên trong config
được tính từ gốc dự án. Observable/truth phải ở hai thư mục riêng dưới đúng exp.
Chạy lại sẽ rebuild output tự động theo input/seed; không chạy hai lượt cùng output.

Manifest ghi config, input/generator hashes, actual counts và complete/partial.
Validator đối chiếu schema, refs, hashes, rule, quota, split và hidden truth; một
checksum hợp lệ không thay thế kiểm tra nội dung. Khi A thay đổi, rebuild dataset.
Xem [contract chung](../../DATA_CONTRACT.md) và
[hướng dẫn gộp A, chọn 400 bài và chạy B–E](../../docs/RUN_EXPERIMENTS.md).

Kiểm tra kỹ thuật không chứng minh đúng ngữ nghĩa hoặc tính đại diện của nhãn
silver và hành vi mô phỏng. Human gold A và đánh giá mô hình là các bước riêng.
