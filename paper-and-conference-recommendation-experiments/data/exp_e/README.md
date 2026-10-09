# Thực nghiệm E — Thích ứng sở thích theo thời gian

Cập nhật 2026-10-09, **contract 2.0**. Thứ tự: A → B → C → D → E.
C mới là profile (D cũ); D mới là session direction (C cũ).

## Câu hỏi và quy mô

So sánh static/recent/decay trên cùng nguồn searching và phản ứng; chấm ở đầu periods 2/3/4. Runner lọc toàn bộ log theo từng cutoff. Stable/drift và hidden profiles chỉ evaluator dùng.

Cùng users C, stream riêng: 4 periods × 15 phản ứng/user = 18.000; 1.200 profiles và 900 cases rolling periods 2/3/4.

## Đầu vào và đầu ra

C users/manifest đã sinh; E tự sinh stream riêng. Dùng paper IDs/title/abstract nguyên bản; loại A fallback/quality flags, giữ facet rỗng là thiếu evidence.
B–E là mock trên bài và silver thật. Không sinh facet giả để bù quota.

Config: `configs/exp_e.json`. generated: interactions_train.jsonl, search_events.jsonl, exposures.jsonl, cases.jsonl. ground_truth: temporal_profiles.jsonl, interactions_test.jsonl, search_events_test.jsonl, exposures_test.jsonl, period_metadata.json.
Mỗi output có generation_report.json và manifest.json (hashes/config/counts/status).

## Sinh và kiểm tra

Chạy tại gốc project, Python 3.11+ và stdlib:

~~~powershell
python data/exp_e/build_exp_e.py --dry-run
python data/exp_e/build_exp_e.py
python data/exp_e/build_exp_e.py --validate-only
~~~

Có `--config`, `--allow-shortfall`; B/D có thể partial khi thiếu pool, ghi lý do thay vì lặp bài/nhãn.
Đường dẫn config tính từ gốc project. Observable/truth tách dưới đúng folder exp.
Output cũ contract 1.0 được giữ nguyên và từ chối ghi đè; chọn output_dir/truth_dir mới cho v2.
Không chạy đồng thời hai generator cùng output.

## Chạy thực nghiệm

Các phương pháp: **popularity, static, recent, decay (half-life mặc định 30 ngày)**.

~~~powershell
python scripts/exp_e/run_exp_e.py --dry-run
python scripts/exp_e/run_exp_e.py
~~~

Xem [README runner](../../scripts/exp_e/README.md) để đọc metrics và kết quả.
Quy tắc schema, simulator, cutoffs, query parser và giới hạn nằm trong
[giao thức 2.0](../../docs/EXPERIMENT_PROTOCOL.md), [lệnh chạy](../../docs/RUN_EXPERIMENTS.md)
và [contract](../../DATA_CONTRACT.md).
