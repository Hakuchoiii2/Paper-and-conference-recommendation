# Chạy generator và thực nghiệm A–E — contract 2.0

Thứ tự mới: A trích facet, B truy xuất, C suy profile, D suy hướng theo phiên, E temporal.
C mới thay D cũ, D mới thay C cũ; D/E lấy users từ C.
Xem [giao thức đầy đủ](EXPERIMENT_PROTOCOL.md), gồm searching, schema, baseline và metrics.

| Exp | Quy mô mặc định |
|---|---|
| A | Full silver trên corpus 4.210 bài; gold review mục tiêu 400 |
| B | 300 query × 100 candidates |
| C | 300 users × 50 phản ứng; 30 history/20 holdout |
| D | 300 users C × 5 phiên × 20 candidates |
| E | 300 users C × 4 periods × 15 phản ứng; 900 rolling cases |

Chạy từ gốc project với Python 3.11+, B–E chỉ cần stdlib.
Nếu lệnh python trên Windows không hoạt động, dùng .\.venv-qwen\Scripts\python.exe.
A GPU có môi trường riêng theo [README A](../data/exp_a/README.md).
Mọi lệnh bên dưới yêu cầu dữ liệu đầu vào tương ứng đã có; fixtures test không thay silver thật.

## 1. Nhận đủ năm phần A

Mỗi part phải có `facets_silver.jsonl`, `annotation_metadata.jsonl` và `manifest.json`.
Đặt nguyên bộ vào `data/exp_a/generated/part_1` đến `part_5`. Các phần dùng cùng
corpus, prompt/guideline, policy/code, model checkpoint và sampling config;
chỉ khác output_dir, paper_range và cache_dir. Giữ parts/checkpoints để tiếp tục/audit.
Chờ các tiến trình xuất tệp xong trước khi gộp.

~~~powershell
python data/exp_a/merge_exp_a.py --dry-run
python data/exp_a/merge_exp_a.py
python scripts/validate_all.py --dataset-kind real --phase experiments
~~~

Tool kiểm tra hashes/coverage từng khoảng, provenance, runtime model/revision,
overlap và coverage toàn corpus trước khi ghi. Fallback thiếu runtime fields vẫn
được giữ cùng audit, không được dùng để bỏ qua model mismatch đã ghi.
Output mặc định ở `data/exp_a/generated/`, gồm silver + metadata + manifest complete.
Không ghi đè parts. Thiếu một phần thì dừng; không tự biến partial thành complete.
Có thể chỉ định `--parts ...` và `--output data/exp_a/<thư_mục_mới>`.

## 2. Chọn 400 bài cho human gold review

~~~powershell
python data/exp_a/select_gold_review.py --dry-run
python data/exp_a/select_gold_review.py
~~~

Không random: bỏ P000001 (ví dụ phát triển prompt), fallback/validation errors
và bài không có facet trích được. Xếp theo số facet có dữ liệu giảm dần,
rồi số concept có dẫn chứng giảm dần, cuối cùng paper_id tăng dần. Chọn 400 đầu.
Nếu chưa đủ 400 hợp lệ thì báo thiếu, không lấy bài lỗi bù số lượng.

Gold dùng để đối chiếu độc lập độ đúng và độ đầy đủ của năm facet Qwen trích:
người review đọc title/abstract, xác định facet đúng và sửa/bổ sung nhãn.
Silver tự động không trở thành gold vì được chọn. Chọn bài đầy đủ là chủ đích
của đợt review này; kết quả không đại diện ngẫu nhiên cho toàn corpus.

Output `data/exp_a/ground_truth/gold_review/`:

- `review_papers.jsonl`: ID/title/abstract, không đính kèm nhãn Qwen.
- `review_annotations.jsonl`: form pending, reviewer và năm facets để người điền.
- `silver_reference.jsonl`: silver riêng để đối chiếu **sau** review độc lập.
- `selection_ranking.jsonl`: thứ hạng và điểm đầy đủ.
- `manifest.json`: selected IDs, tiêu chí, exclusions, selection bias và hashes.

Không sinh `facets_gold.jsonl` tự động. Queue đang tồn tại không bị ghi đè;
dùng `--output` mới nếu cần đợt khác. Người review hoàn tất nhãn, ghi reviewer,
giải quyết bất đồng rồi mới xuất gold theo contract. Không dùng gold held-out
để chỉnh prompt rồi báo lại như một đánh giá độc lập.

Để xem thử trên part_1 mà không ghi hàng đợi cuối:

~~~powershell
python data/exp_a/select_gold_review.py --source data/exp_a/generated/part_1 --count 400 --dry-run --allow-partial
~~~

## 3. Sinh B → C → D → E

~~~powershell
python data/exp_b/build_exp_b.py --dry-run
python data/exp_b/build_exp_b.py
python data/exp_c/build_exp_c.py
python data/exp_d/build_exp_d.py
python data/exp_e/build_exp_e.py
python scripts/validate_all.py --dataset-kind mock --phase experiments
~~~

B/C dùng A complete. D dùng C users và logs; E dùng C users rồi tạo stream riêng.
B và C có thể chuẩn bị độc lập sau A, nhưng tên/thứ tự chuẩn là A/B/C/D/E.
Runner D tính lại đúng hàm profile của C trên C history; không yêu cầu tệp kết quả C để sinh D.

Generator có --dry-run, --validate-only, --config, --allow-shortfall.
Default configs/exp_b.json … exp_e.json; paths tính từ project root.
B/D thiếu pool ghi shortfall, status partial và exit code 2; --allow-shortfall cho phép partial,
không bỏ qua dữ liệu sai. C/E cần đủ distinct papers trong mỗi đoạn mô phỏng.

Manifest B–E là 2.0. Output cũ 1.0 bị từ chối ghi đè; sửa output_dir/truth_dir sang thư mục mới
và sửa users_path D/E tới C mới nếu cần giữ dữ liệu cũ. Không chạy đồng thời cùng output.
A code, checkpoints và silver đã có được giữ nguyên.

## 4. Chạy mô hình và đánh giá

~~~powershell
python scripts/exp_a/evaluate_exp_a.py
python scripts/exp_b/run_exp_b.py --split test --ks 5 10
python scripts/exp_c/run_exp_c.py --ks 5 10
python scripts/exp_d/run_exp_d.py --ks 5 10
python scripts/exp_e/run_exp_e.py --ks 5 10 --half-life-days 30
~~~

A evaluator cần human gold reviewed trước khi chạy.
B–E có --dry-run để validate trước, --config và --output dưới results/.
Kết quả đã tồn tại cần --overwrite hoặc --output mới. B có --split train/dev/test;
C/D/E đánh giá theo cutoff. Các phương pháp dùng chung candidate pools và metric definitions.

Output: predictions.jsonl, details.jsonl, report.json, summary.csv, report.md, manifest.json.
D có direction_macro_f1/coverage/compliance, oracle_intent được đánh dấu đặc quyền.
C/E có importance_mae cho facet models; E chia theo stable/drift và từng period.
Đặt tham số trước test, không chỉnh theo điểm test.

## 5. Kiểm tra và giới hạn

~~~powershell
python scripts/validate_all.py --dataset-kind real --phase corpus
python -B -m unittest discover -s tests
~~~

Nếu sandbox Windows chặn thư mục temp mặc định, đặt TEMP/TMP vào thư mục writable riêng trước khi chạy tests.
Fixtures được tạo và dọn trong thư mục tạm, không ghi paper/facet giả vào corpus thật.
Tests kiểm tra schema/hash, labels, exposure membership, query parents, chronology,
prefix trước từng mốc, truth separation, oracle privileges và byte-identical rebuilds/hash-seed invariance.

Mock logs chưa chứng minh hành vi người thật. Query parser và scorer hiện lexical.
B labels theo quy tắc chưa thay expert relevance; A gold review vẫn cần làm độc lập.
Xem [README từng runner](../scripts/README.md) và [giới hạn protocol](EXPERIMENT_PROTOCOL.md).
