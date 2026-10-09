# Thực nghiệm B — Truy xuất bằng biểu diễn năm facet

Cập nhật 2026-10-09, **contract 2.0**. Thứ tự: A → B → C → D → E.
C mới là profile (D cũ); D mới là session direction (C cũ).

## Câu hỏi và quy mô

So sánh whole-text với năm facet cùng trọng số và trọng số cố định. Labels là weighted concept overlap, không phải nhãn expert. Query chỉ có bài mốc và candidates; trọng số lấy từ config, không yêu cầu user chọn facet.

300 query × 100 candidates = 30.000 cặp; chia theo anchor 70/15/15.

## Đầu vào và đầu ra

Corpus và full silver A đã qua kiểm tra. Dùng paper IDs/title/abstract nguyên bản; loại A fallback/quality flags, giữ facet rỗng là thiếu evidence.
B–E là mock trên bài và silver thật. Không sinh facet giả để bù quota.

Config: `configs/exp_b.json`. generated: retrieval_queries.jsonl, splits.json. ground_truth: retrieval_labels.jsonl, label_provenance.jsonl.
Mỗi output có generation_report.json và manifest.json (hashes/config/counts/status).

## Sinh và kiểm tra

Chạy tại gốc project, Python 3.11+ và stdlib:

~~~powershell
python data/exp_b/build_exp_b.py --dry-run
python data/exp_b/build_exp_b.py
python data/exp_b/build_exp_b.py --validate-only
~~~

Có `--config`, `--allow-shortfall`; B/D có thể partial khi thiếu pool, ghi lý do thay vì lặp bài/nhãn.
Đường dẫn config tính từ gốc project. Observable/truth tách dưới đúng folder exp.
Output cũ contract 1.0 được giữ nguyên và từ chối ghi đè; chọn output_dir/truth_dir mới cho v2.
Không chạy đồng thời hai generator cùng output.

## Chạy thực nghiệm

Các phương pháp: **random, text_tfidf, equal_facets, weighted_facets**.

~~~powershell
python scripts/exp_b/run_exp_b.py --dry-run
python scripts/exp_b/run_exp_b.py
~~~

Xem [README runner](../../scripts/exp_b/README.md) để đọc metrics và kết quả.
Quy tắc schema, simulator, cutoffs, query parser và giới hạn nằm trong
[giao thức 2.0](../../docs/EXPERIMENT_PROTOCOL.md), [lệnh chạy](../../docs/RUN_EXPERIMENTS.md)
và [contract](../../DATA_CONTRACT.md).
