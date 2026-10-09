# Thực nghiệm C — Suy profile từ hành vi đọc và searching

Cập nhật 2026-10-09, **contract 2.0**. Thứ tự: A → B → C → D → E.
C mới là profile (D cũ); D mới là session direction (C cũ).

## Câu hỏi và quy mô

Khôi phục concept preferences và facet importance từ tương tác/search trước cutoff, rồi xếp hạng các bài holdout. Profile thật được sinh trước hành vi và giữ trong ground_truth. Tỷ lệ search là xác suất mô phỏng.

300 users × 50 phản ứng: 30 history/20 holdout mỗi user, tổng 15.000. C sở hữu users dùng chung cho D/E.

## Đầu vào và đầu ra

Corpus và full silver A đã qua kiểm tra. Dùng paper IDs/title/abstract nguyên bản; loại A fallback/quality flags, giữ facet rỗng là thiếu evidence.
B–E là mock trên bài và silver thật. Không sinh facet giả để bù quota.

Config: `configs/exp_c.json`. generated: users.jsonl, interactions_train.jsonl, search_events.jsonl, exposures.jsonl, cases.jsonl. ground_truth: latent_user_profiles.jsonl, interactions_test.jsonl, search_events_test.jsonl, exposures_test.jsonl.
Mỗi output có generation_report.json và manifest.json (hashes/config/counts/status).

## Sinh và kiểm tra

Chạy tại gốc project, Python 3.11+ và stdlib:

~~~powershell
python data/exp_c/build_exp_c.py --dry-run
python data/exp_c/build_exp_c.py
python data/exp_c/build_exp_c.py --validate-only
~~~

Có `--config`, `--allow-shortfall`; B/D có thể partial khi thiếu pool, ghi lý do thay vì lặp bài/nhãn.
Đường dẫn config tính từ gốc project. Observable/truth tách dưới đúng folder exp.
Output cũ contract 1.0 được giữ nguyên và từ chối ghi đè; chọn output_dir/truth_dir mới cho v2.
Không chạy đồng thời hai generator cùng output.

## Chạy thực nghiệm

Các phương pháp: **popularity, text_history (có search), facet_no_search, facet_history (có search)**.

~~~powershell
python scripts/exp_c/run_exp_c.py --dry-run
python scripts/exp_c/run_exp_c.py
~~~

Xem [README runner](../../scripts/exp_c/README.md) để đọc metrics và kết quả.
Quy tắc schema, simulator, cutoffs, query parser và giới hạn nằm trong
[giao thức 2.0](../../docs/EXPERIMENT_PROTOCOL.md), [lệnh chạy](../../docs/RUN_EXPERIMENTS.md)
và [contract](../../DATA_CONTRACT.md).
