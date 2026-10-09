# Chạy Exp D — Suy similar/different theo phiên

Thiết kế 2.0 ngày 2026-10-09. Tách hai câu hỏi: suy hướng có đúng không, và dùng hướng đó có cải thiện ranking không. Nhận bài mốc, context facet của benchmark, C profile và phần đầu phiên; focus/direction thật không được đưa cho scorer. Cả năm facets có thể là focus. Query clear/ambiguous/none và cặp quan sát kiểm soát các facet còn lại.

## Chuẩn bị

C users/manifest và C history/search/exposure đã sinh. Dataset `data/exp_d/generated/manifest.json` phải đúng config và hashes hiện tại.
300 users C × 5 phiên × 20 candidates, mục tiêu 1.500 phiên/30.000 labels; tối đa 4 cặp quan sát/phiên.

Sinh dữ liệu theo [README generator](../../data/exp_d/README.md).
Các phương pháp CPU/stdlb: **fixed_similar, profile_similar, direction_behavior, direction_search; oracle_intent được evaluator thêm riêng**.

## Chạy

~~~powershell
python scripts/exp_d/run_exp_d.py --dry-run
python scripts/exp_d/run_exp_d.py --ks 5 10
~~~

Có `--config`, `--output` dưới results/, `--overwrite`, `--allow-shortfall`.
C/D/E dùng cutoff thời gian; --split chỉ có ý nghĩa với B.

Mỗi scorer chỉ nhận log trước cutoff; labels/latent truth được evaluator đọc riêng.

## Kết quả và diễn giải

Ranking @5/10, pooled macro-F1 direction, accuracy, coverage và intent_compliance@k. Unknown được chấm là abstention/missed prediction, không phải ignore. Oracle dùng true intent/importance, được đánh dấu privileged_information.

Output mặc định `results/exp_d/holdout/`:
predictions.jsonl, details.jsonl, report.json, summary.csv, report.md và manifest.json.
Manifest ghi code/input hashes; tệp đã tồn tại cần --overwrite hoặc output mới.
Report ghi denominator; case không có positive có nDCG/Recall/MRR=N/A.

Các ablation direction dùng cùng C profile/trọng số, candidates và missing-facet policy. Unknown giữ ranking ngữ cảnh mặc định, nhưng không được đổi nhãn prediction thành similar. Score soft không bảo đảm constraint AND; compliance được đo riêng.


Mock + lexical scoring chỉ kiểm tra giả thuyết mô phỏng, chưa chứng minh user intent thật hoặc tính mới.
Xem [giao thức chi tiết](../../docs/EXPERIMENT_PROTOCOL.md) và [lệnh chạy](../../docs/RUN_EXPERIMENTS.md).
