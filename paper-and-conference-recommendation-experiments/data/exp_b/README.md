# Thực nghiệm B — Truy hồi bài báo theo một facet

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

Từ một bài mẫu và một facet được chỉ định, tạo tập ứng viên để kiểm tra khả năng
xếp hạng theo facet. Mặc định **300 queries × 100 candidates = 30.000 cặp**,
60 queries cho mỗi problem/task/method/dataset/contribution. Đây cũng là quy mô
pilot hiện được yêu cầu; không bắt đầu bằng bộ 5 queries.

Đầu vào là corpus, silver/metadata/manifest A và `configs/exp_b.json`.
Không cần human gold A, C/D/E hoặc nhãn CSFCube. Nhãn CSFCube 0–3 và ba facet
gốc vẫn giữ trong raw; không được trộn vào B năm facet/scale 0–2.

## Rule và sampling

`concept_overlap_v1` chuẩn hóa concept bằng cùng hàm chuẩn hóa của corpus:
hai tập không rỗng bằng nhau → relevance 2; có giao nhưng khác tập → 1;
không giao → 0. Thiếu facet đích ở anchor/candidate → ineligible.

Mỗi query có ít nhất một positive và một negative. Mục tiêu 20% positive,
50% negative là hard negative, có điều chỉnh theo pool hợp lệ để đủ 100 ứng viên.
Hard negative khác facet đích nhưng có concept chung ở ít nhất một facet khác.
Không có self-candidate hoặc ID trùng. Chia train/dev/test theo **nhóm anchor**
70/15/15; một bài có thể làm query cho nhiều facets nhưng thuộc một split.

Nếu không đủ positive/negative/candidates, bỏ anchor và ghi lý do. Thiếu quota
được xuất minh bạch với `status: partial`, `generation_report.json` và exit code 2.
`--allow-shortfall` cho phép kiểm tra bộ partial; không biến nó thành complete.

## Tệp và schema

| Thư mục | Tệp | Nội dung |
|---|---|---|
| `data/exp_b/generated/` | `retrieval_queries.jsonl` | query_id, query_paper_id, target_facet, candidate_ids |
| generated | `splits.json` | Query IDs của train/dev/test, nhóm theo anchor |
| generated | `generation_report.json`, `manifest.json` | Quota/actual/skipped/gap và hashes |
| `data/exp_b/ground_truth/` | `retrieval_labels.jsonl` | query_id, candidate_id, relevance 0/1/2 |
| ground_truth | `label_provenance.jsonl` | synthetic_rule, rule version, concepts và candidate role |

`query_id` có dạng Q0001, khóa nhãn duy nhất là (query_id,candidate_id).
Mỗi candidate của mỗi query có đúng một nhãn. Nhãn không nằm trong query record.
Mô hình về sau đọc queries/corpus/facets được phép để trả ranking; evaluator đọc
labels riêng. Nhãn theo rule chỉ là đáp án mock, cần review để đánh giá ngữ nghĩa.

## Chạy và kiểm tra

Chạy từ thư mục gốc dự án, dùng Python 3.11+; B–E chỉ cần thư viện chuẩn:

~~~powershell
python data/exp_b/build_exp_b.py --dry-run
python data/exp_b/build_exp_b.py
python data/exp_b/build_exp_b.py --validate-only
~~~

`--dry-run` kiểm tra đầu vào và hiển thị mục tiêu, không sinh tệp.
`--config configs/exp_b.json` chỉ định cấu hình khác; đường dẫn bên trong config
được tính từ gốc dự án. Observable/truth phải ở hai thư mục riêng dưới đúng exp.
Chạy lại sẽ rebuild output tự động theo input/seed; không chạy hai lượt cùng output.

Manifest ghi config, input/generator hashes, actual counts và complete/partial.
Validator đối chiếu schema, refs, hashes, rule, quota, split và hidden truth; một
checksum hợp lệ không thay thế kiểm tra nội dung. Khi A thay đổi, rebuild dataset.
Xem [contract chung](../../DATA_CONTRACT.md) và
[hướng dẫn gộp A, chọn 400 bài và chạy B–E](../../docs/RUN_EXPERIMENTS.md).

Kiểm tra kỹ thuật không chứng minh đúng ngữ nghĩa hoặc tính đại diện của nhãn
silver và hành vi mô phỏng. Human gold A và đánh giá mô hình là các bước riêng.
