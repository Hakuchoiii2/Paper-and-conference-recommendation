# Code chạy và đánh giá thực nghiệm

- Generator và chuẩn bị dữ liệu của A–E nằm trong `data/exp_*`.
  A gồm Qwen annotation, gộp năm phần và chọn 400 bài để người review.
- `scripts/exp_a/evaluate_exp_a.py` đối chiếu Qwen silver với human gold.
  Chạy từ gốc dự án: `python scripts/exp_a/evaluate_exp_a.py`.
- `scripts/exp_b/` đến `scripts/exp_e/` dành cho code chạy và đánh giá mô hình
  từng thực nghiệm. Hiện chưa triển khai các bộ chạy này.
- Tiện ích dùng chung vẫn ở gốc `scripts/`: tải/xây corpus, I/O và validators.
  Bộ điều phối generator B–E ở `data/build_experiments.py`, rule sinh dữ liệu
  dùng chung ở `data/experiment_common.py`.

Lệnh sinh dữ liệu: [RUN_EXPERIMENTS.md](../docs/RUN_EXPERIMENTS.md).
Đánh giá Qwen: [EVALUATE_QWEN.md](../docs/EVALUATE_QWEN.md).
