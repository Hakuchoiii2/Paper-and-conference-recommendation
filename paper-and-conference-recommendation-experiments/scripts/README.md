# Code chạy và đánh giá thực nghiệm

Thứ tự mới: **A facet → B retrieval → C profile → D session direction → E temporal**.
Generator ở data/exp_*; runner/evaluator ở scripts/exp_*; CPU B–E chỉ cần stdlib.

| Exp | Runner | Nội dung |
|---|---|---|
| A | [README A](exp_a/README.md) | Qwen silver so với human gold |
| B | [README B](exp_b/README.md) | Whole-text / equal-facet / fixed-weight facet |
| C | [README C](exp_c/README.md) | Suy profile từ hành vi + searching; search ablation |
| D | [README D](exp_d/README.md) | Suy similar/different từ query + matched reactions; oracle riêng |
| E | [README E](exp_e/README.md) | Static/recent/decay, rolling periods 2/3/4 |

baseline_common.py chứa biểu diễn, query parsing, profile/direction và metrics.
experiment_runner.py kiểm tra dataset, lọc mọi log theo cutoff, gọi scorer và xuất results/exp_*.
Mọi public scorer nhận observable prefixes. D oracle được evaluator thêm riêng và đánh dấu đặc quyền.
Contract/generator/evaluation B–E là 2.0; dữ liệu 1.0 cần rebuild ở output phù hợp.

Xem [protocol](../docs/EXPERIMENT_PROTOCOL.md), [lệnh chạy](../docs/RUN_EXPERIMENTS.md)
và [đánh giá A](../docs/EVALUATE_QWEN.md). Chưa có benchmark người dùng thật.
