# Thực nghiệm C — Khuyến nghị theo ý định tường minh

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

Tạo yêu cầu từ bài mẫu, như cùng problem nhưng khác method, cùng ứng viên và nhãn
thỏa toàn bộ ràng buộc. Mặc định **1.500 cases × 20 candidates = 30.000 cặp**.
Một anchor có thể tạo nhiều loại intent; số cases không bằng số bài độc lập.

Đầu vào là corpus, silver/metadata/manifest A, `configs/exp_c.json` và
`configs/intent_templates.json`. Không cần B labels hoặc human gold A.

| Intent type | Ràng buộc có hiệu lực | Quota |
|---|---|---:|
| same_problem | problem similar | 200 |
| same_problem_different_method | problem similar, method different | 200 |
| same_method_different_problem | method similar, problem different | 200 |
| similar_task | task similar | 200 |
| different_dataset | dataset different | 200 |
| same_problem_same_method | problem similar, method similar | 200 |
| similar_contribution | contribution similar | 150 |
| mixed_intent | problem/task similar, method different | 150 |

## Rule và sampling

Mỗi record chứa đủ năm constraint, với `similar`, `different` hoặc `ignore`.
`concept_overlap_v1` định nghĩa similar là giao concept chuẩn hóa khác rỗng;
different là hai tập có dữ liệu nhưng không giao. Tất cả constraint hoạt động
được nối bằng AND. Thiếu facet hoạt động → ineligible, không tự thành negative.

Mỗi case có positive/negative, mục tiêu 50% positive; 50% negative là hard negative
nếu pool cho phép. Hard negative vi phạm đúng một constraint. Không self-candidate
hoặc trùng ID. Anchor chỉ xuất hiện một lần trong mỗi intent type, chia theo
nhóm anchor 70/15/15 train/dev/test. Cùng anchor không vượt qua hai split.

Nếu pool không đủ thì skip anchor, ghi lý do và shortfall theo từng type;
không lặp case để đủ 1.500. Bộ thiếu quota có `status: partial` và exit code 2.
`--allow-shortfall` cho phép kiểm tra cấu trúc bộ partial.

## Tệp và schema

| Thư mục | Tệp | Nội dung |
|---|---|---|
| `data/exp_c/generated/` | `intents.jsonl` | intent_id, query_paper_id, intent_type, constraints, candidate_ids |
| generated | `splits.json` | Intent IDs chia theo nhóm anchor |
| generated | `generation_report.json`, `manifest.json` | Quota/actual/skipped/gap và hashes |
| `data/exp_c/ground_truth/` | `intent_labels.jsonl` | intent_id, candidate_id, satisfies_intent boolean |
| ground_truth | `label_provenance.jsonl` | synthetic_rule, rule/template versions và role |

`intent_id` có dạng I0001; khóa nhãn là (intent_id,candidate_id).
Tất cả candidates được judged đúng một lần. Mô hình đọc intents và nội dung/facets
được phép; satisfaction labels chỉ dành cho evaluator. So khớp concept chưa thay
thế kiểm tra ý nghĩa hoặc một đánh giá recommendation độc lập.

## Chạy và kiểm tra

Chạy từ thư mục gốc dự án, dùng Python 3.11+; B–E chỉ cần thư viện chuẩn:

~~~powershell
python data/exp_c/build_exp_c.py --dry-run
python data/exp_c/build_exp_c.py
python data/exp_c/build_exp_c.py --validate-only
~~~

`--dry-run` kiểm tra đầu vào và hiển thị mục tiêu, không sinh tệp.
`--config configs/exp_c.json` chỉ định cấu hình khác; đường dẫn bên trong config
được tính từ gốc dự án. Observable/truth phải ở hai thư mục riêng dưới đúng exp.
Chạy lại sẽ rebuild output tự động theo input/seed; không chạy hai lượt cùng output.

Manifest ghi config, input/generator hashes, actual counts và complete/partial.
Validator đối chiếu schema, refs, hashes, rule, quota, split và hidden truth; một
checksum hợp lệ không thay thế kiểm tra nội dung. Khi A thay đổi, rebuild dataset.
Xem [contract chung](../../DATA_CONTRACT.md) và
[hướng dẫn gộp A, chọn 400 bài và chạy B–E](../../docs/RUN_EXPERIMENTS.md).

Kiểm tra kỹ thuật không chứng minh đúng ngữ nghĩa hoặc tính đại diện của nhãn
silver và hành vi mô phỏng. Human gold A và đánh giá mô hình là các bước riêng.
