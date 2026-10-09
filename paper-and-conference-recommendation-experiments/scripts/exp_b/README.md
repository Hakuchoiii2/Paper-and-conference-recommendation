# Chạy Exp B — Truy xuất bằng biểu diễn năm facet

Thiết kế 2.0 ngày 2026-10-09. So sánh whole-text với năm facet cùng trọng số và trọng số cố định. Labels là weighted concept overlap, không phải nhãn expert. Query chỉ có bài mốc và candidates; trọng số lấy từ config, không yêu cầu user chọn facet.

## Chuẩn bị

Corpus và full silver A đã qua kiểm tra. Dataset `data/exp_b/generated/manifest.json` phải đúng config và hashes hiện tại.
300 query × 100 candidates = 30.000 cặp; chia theo anchor 70/15/15.

Sinh dữ liệu theo [README generator](../../data/exp_b/README.md).
Các phương pháp CPU/stdlb: **random, text_tfidf, equal_facets, weighted_facets**.

## Chạy

~~~powershell
python scripts/exp_b/run_exp_b.py --dry-run
python scripts/exp_b/run_exp_b.py --ks 5 10
~~~

Có `--config`, `--output` dưới results/, `--overwrite`, `--allow-shortfall`.
B mặc định --split test; có train/dev/test và cùng anchor không qua hai split.

Mỗi scorer chỉ nhận log trước cutoff; labels/latent truth được evaluator đọc riêng.

## Kết quả và diễn giải

nDCG/Recall/Precision/MRR @5/10. Labels là grade liên tục từ weighted overlap.

Output mặc định `results/exp_b/test/`:
predictions.jsonl, details.jsonl, report.json, summary.csv, report.md và manifest.json.
Manifest ghi code/input hashes; tệp đã tồn tại cần --overwrite hoặc output mới.
Report ghi denominator; case không có positive có nDCG/Recall/MRR=N/A.




Mock + lexical scoring chỉ kiểm tra giả thuyết mô phỏng, chưa chứng minh user intent thật hoặc tính mới.
Xem [giao thức chi tiết](../../docs/EXPERIMENT_PROTOCOL.md) và [lệnh chạy](../../docs/RUN_EXPERIMENTS.md).
