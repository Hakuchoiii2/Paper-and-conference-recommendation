# Chạy Exp E — Thích ứng sở thích theo thời gian

Thiết kế 2.0 ngày 2026-10-09. So sánh static/recent/decay trên cùng nguồn searching và phản ứng; chấm ở đầu periods 2/3/4. Runner lọc toàn bộ log theo từng cutoff. Stable/drift và hidden profiles chỉ evaluator dùng.

## Chuẩn bị

C users/manifest đã sinh; E tự sinh stream riêng. Dataset `data/exp_e/generated/manifest.json` phải đúng config và hashes hiện tại.
Cùng users C, stream riêng: 4 periods × 15 phản ứng/user = 18.000; 1.200 profiles và 900 cases rolling periods 2/3/4.

Sinh dữ liệu theo [README generator](../../data/exp_e/README.md).
Các phương pháp CPU/stdlb: **popularity, static, recent, decay (half-life mặc định 30 ngày)**.

## Chạy

~~~powershell
python scripts/exp_e/run_exp_e.py --dry-run
python scripts/exp_e/run_exp_e.py --ks 5 10
~~~

Có `--config`, `--output` dưới results/, `--overwrite`, `--allow-shortfall`.
C/D/E dùng cutoff thời gian; --split chỉ có ý nghĩa với B.
Có --half-life-days 30; đặt tham số trước test.
Mỗi scorer chỉ nhận log trước cutoff; labels/latent truth được evaluator đọc riêng.

## Kết quả và diễn giải

Ranking @5/10; importance_mae chỉ cho các model trả facet importance, model khác là N/A. Report chia stable/drift và periods 2/3/4.

Output mặc định `results/exp_e/holdout/`:
predictions.jsonl, details.jsonl, report.json, summary.csv, report.md và manifest.json.
Manifest ghi code/input hashes; tệp đã tồn tại cần --overwrite hoặc output mới.
Report ghi denominator; case không có positive có nDCG/Recall/MRR=N/A.


Periods 2/3 xuất hiện trong truth để chấm mốc hiện tại, rồi trong history cho mốc sau; runner luôn lọc prefix trước khi gọi model.

Mock + lexical scoring chỉ kiểm tra giả thuyết mô phỏng, chưa chứng minh user intent thật hoặc tính mới.
Xem [giao thức chi tiết](../../docs/EXPERIMENT_PROTOCOL.md) và [lệnh chạy](../../docs/RUN_EXPERIMENTS.md).
