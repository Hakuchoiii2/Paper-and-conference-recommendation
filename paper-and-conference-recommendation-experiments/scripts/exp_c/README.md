# Chạy Exp C — Suy profile từ hành vi đọc và searching

Thiết kế 2.0 ngày 2026-10-09. Khôi phục concept preferences và facet importance từ tương tác/search trước cutoff, rồi xếp hạng các bài holdout. Profile thật được sinh trước hành vi và giữ trong ground_truth. Tỷ lệ search là xác suất mô phỏng.

## Chuẩn bị

Corpus và full silver A đã qua kiểm tra. Dataset `data/exp_c/generated/manifest.json` phải đúng config và hashes hiện tại.
300 users × 50 phản ứng: 30 history/20 holdout mỗi user, tổng 15.000. C sở hữu users dùng chung cho D/E.

Sinh dữ liệu theo [README generator](../../data/exp_c/README.md).
Các phương pháp CPU/stdlb: **popularity, text_history (có search), facet_no_search, facet_history (có search)**.

## Chạy

~~~powershell
python scripts/exp_c/run_exp_c.py --dry-run
python scripts/exp_c/run_exp_c.py --ks 5 10
~~~

Có `--config`, `--output` dưới results/, `--overwrite`, `--allow-shortfall`.
C/D/E dùng cutoff thời gian; --split chỉ có ý nghĩa với B.

Mỗi scorer chỉ nhận log trước cutoff; labels/latent truth được evaluator đọc riêng.

## Kết quả và diễn giải

Ranking @5/10; importance_mae chỉ cho các model trả facet importance, model khác là N/A.

Output mặc định `results/exp_c/holdout/`:
predictions.jsonl, details.jsonl, report.json, summary.csv, report.md và manifest.json.
Manifest ghi code/input hashes; tệp đã tồn tại cần --overwrite hoặc output mới.
Report ghi denominator; case không có positive có nDCG/Recall/MRR=N/A.




Mock + lexical scoring chỉ kiểm tra giả thuyết mô phỏng, chưa chứng minh user intent thật hoặc tính mới.
Xem [giao thức chi tiết](../../docs/EXPERIMENT_PROTOCOL.md) và [lệnh chạy](../../docs/RUN_EXPERIMENTS.md).
