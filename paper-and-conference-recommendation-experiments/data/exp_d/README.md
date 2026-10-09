# Thực nghiệm D — Suy similar/different theo phiên

Cập nhật 2026-10-09, **contract 2.0**. Thứ tự: A → B → C → D → E.
C mới là profile (D cũ); D mới là session direction (C cũ).

## Câu hỏi và quy mô

Tách hai câu hỏi: suy hướng có đúng không, và dùng hướng đó có cải thiện ranking không. Nhận bài mốc, context facet của benchmark, C profile và phần đầu phiên; focus/direction thật không được đưa cho scorer. Cả năm facets có thể là focus. Query clear/ambiguous/none và cặp quan sát kiểm soát các facet còn lại.

300 users C × 5 phiên × 20 candidates, mục tiêu 1.500 phiên/30.000 labels; tối đa 4 cặp quan sát/phiên.

## Đầu vào và đầu ra

C users/manifest và C history/search/exposure đã sinh. Dùng paper IDs/title/abstract nguyên bản; loại A fallback/quality flags, giữ facet rỗng là thiếu evidence.
B–E là mock trên bài và silver thật. Không sinh facet giả để bù quota.

Config: `configs/exp_d.json`. generated: sessions.jsonl, interactions_train.jsonl, search_events.jsonl, exposures.jsonl. ground_truth: session_intents.jsonl, intent_labels.jsonl.
Mỗi output có generation_report.json và manifest.json (hashes/config/counts/status).

## Sinh và kiểm tra

Chạy tại gốc project, Python 3.11+ và stdlib:

~~~powershell
python data/exp_d/build_exp_d.py --dry-run
python data/exp_d/build_exp_d.py
python data/exp_d/build_exp_d.py --validate-only
~~~

Có `--config`, `--allow-shortfall`; B/D có thể partial khi thiếu pool, ghi lý do thay vì lặp bài/nhãn.
Đường dẫn config tính từ gốc project. Observable/truth tách dưới đúng folder exp.
Output cũ contract 1.0 được giữ nguyên và từ chối ghi đè; chọn output_dir/truth_dir mới cho v2.
Không chạy đồng thời hai generator cùng output.

## Chạy thực nghiệm

Các phương pháp: **fixed_similar, profile_similar, direction_behavior, direction_search; oracle_intent được evaluator thêm riêng**.

~~~powershell
python scripts/exp_d/run_exp_d.py --dry-run
python scripts/exp_d/run_exp_d.py
~~~

Xem [README runner](../../scripts/exp_d/README.md) để đọc metrics và kết quả.
Quy tắc schema, simulator, cutoffs, query parser và giới hạn nằm trong
[giao thức 2.0](../../docs/EXPERIMENT_PROTOCOL.md), [lệnh chạy](../../docs/RUN_EXPERIMENTS.md)
và [contract](../../DATA_CONTRACT.md).
