# Exp A — Đánh giá Qwen trích facet

Người phụ trách A đối chiếu silver Qwen với human gold trên cùng 400 bài.
Script đánh giá chạy CPU bằng Python 3.11+, chỉ cần thư viện chuẩn.

## Chuẩn bị

Giữ bản dự án đầy đủ, gồm code, configs, docs và corpus `data/processed/`.
Cần silver/metadata/manifest ở `data/exp_a/generated/` và bộ gold tại
`data/exp_a/ground_truth/gold_review/review_annotations.jsonl`.

Gold phải có đúng 400 bài đã review, `review_status: "reviewed"`, tên reviewer
và đủ năm list facet. Việc chọn 400 IDs hoặc copy silver chưa tạo human gold.
Người review hoàn tất nhãn độc lập trước khi xem silver reference.

Sinh annotation, gộp các phần A và chọn hàng đợi review thuộc bước dữ liệu:
xem [README dữ liệu A](../../data/exp_a/README.md) và
[hướng dẫn chuẩn bị dataset](../../docs/RUN_EXPERIMENTS.md).
Silver phải chứa toàn bộ IDs gold; evaluator cho phép silver partial và báo coverage.

## Chạy

Mở terminal tại gốc `paper-and-conference-recommendation-experiments`:

```powershell
python scripts/exp_a/evaluate_exp_a.py
```

Chỉ định nguồn hoặc thư mục báo cáo khác khi cần:

```powershell
python scripts/exp_a/evaluate_exp_a.py --source data/exp_a/generated --gold data/exp_a/ground_truth/gold_review/review_annotations.jsonl --output data/exp_a/evaluation/gold_400
```

`--expected-count` mặc định 400. Chỉ đổi khi chủ động đánh giá một cohort khác.
Pending gold, thiếu reviewer, sai số lượng/schema/IDs sẽ bị từ chối.

## Kết quả bàn giao

Thư mục `data/exp_a/evaluation/gold_400/`:

- `report.md`: bảng Precision/Recall/F1 từng facet và giới hạn.
- `summary.json`: TP/FP/FN, micro/macro và corpus audit.
- `per_paper.jsonl`: đối chiếu gold/silver, nhãn dư/thiếu và dẫn chứng.
- `manifest.json`: hashes input/code/output để kiểm tra lại.

Gửi cả thư mục kết quả khi bàn giao; output này bị Git bỏ qua. Chạy lại cùng
input/code cho cùng báo cáo. Evaluator không inference Qwen hoặc sửa gold.

Điểm là lexical agreement sau chuẩn hóa Unicode/case/khoảng trắng, chưa tự
nhận biết từ đồng nghĩa. Cohort được ưu tiên độ đầy đủ nên chưa đại diện toàn
corpus. Xem [quy trình review và cách đọc điểm](../../docs/EVALUATE_QWEN.md).
