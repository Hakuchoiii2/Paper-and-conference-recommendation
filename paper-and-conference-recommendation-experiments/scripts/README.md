# Script thực nghiệm A–E

Thư mục này chứa runner và evaluator. Mỗi README bên dưới giải thích chi tiết đầu vào, scorer, ground truth, chỉ số, lệnh chạy, output và cách bổ sung phương pháp cho đúng thực nghiệm.

| Exp | Nội dung chi tiết | Chuẩn bị dữ liệu |
|---|---|---|
| A | [Đánh giá extraction Qwen](exp_a/README.md) | [Dữ liệu A](../data/exp_a/README.md) |
| B | [Retrieval theo bài mốc](exp_b/README.md) | [Dữ liệu B](../data/exp_b/README.md) |
| C | [Suy profile từ hành vi và tìm kiếm](exp_c/README.md) | [Dữ liệu C](../data/exp_c/README.md) |
| D | [Suy hướng tương tự/khác biệt trong phiên](exp_d/README.md) | [Dữ liệu D](../data/exp_d/README.md) |
| E | [Cập nhật profile theo thời gian](exp_e/README.md) | [Dữ liệu E](../data/exp_e/README.md) |

## Tài liệu dùng chung

- [Giao diện scorer, evaluator và output B–E](BASELINE_GUIDE.md).
- [Lệnh chạy nhanh A–E](../docs/RUN_EXPERIMENTS.md).
- [Protocol và định nghĩa thực nghiệm](../docs/EXPERIMENT_PROTOCOL.md).
- [Kế hoạch bổ sung model cho từng exp](../docs/EXPERIMENT_PLAN_FINAL.md).
- [Chỉ mục dữ liệu và phụ thuộc](../data/README.md).
- [Tổng quan dự án](../README.md).

`baseline_common.py` chứa cách biểu diễn/chấm điểm dùng chung; `experiment_runner.py` điều phối dữ liệu và output; `evaluate_experiments.py` đọc đáp án để đánh giá. Hướng dẫn phát triển nằm trong tài liệu dùng chung và README của exp tương ứng.
