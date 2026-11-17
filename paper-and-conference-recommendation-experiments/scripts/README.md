# Script nghiên cứu A/B/conference

Phạm vi hiện tại là đánh giá LLM trích facet, paper ranking và khuyến nghị hội nghị. [README gốc](../README.md) mô tả câu hỏi nghiên cứu; [đề cương hiện hành](../docs/PAPER_STRUCTURE_SHARED_FACET_WEIGHTS_2026-10-23.md) phân biệt B với phép thử thay extractor dưới downstream cố định.

## Entrypoint và kết quả hiện tại

| Phần | Code và hướng dẫn |
|---|---|
| A — bộ final | [Code/prompt/config và kết quả 5 LLM](../data/exp_a/final/README.md); sinh corpus bằng `data/exp_a/final/generate.py` với Qwen8B đã chọn |
| A — evaluator và lịch sử | [Đánh giá bằng embedding hoặc khớp chữ](exp_a/README.md) |
| B — baseline hiện có | [Runner/evaluator B](exp_b/README.md), [chuẩn bị dữ liệu B](../data/exp_b/README.md) |
| Conference | [Thiết kế và các quyết định còn mở](../docs/PAPER_STRUCTURE_SHARED_FACET_WEIGHTS_2026-10-23.md); chưa có runner thực nghiệm riêng |

A đã hoàn tất QLoRA/test60 cho Qwen3-4B/8B/14B, Llama3.1-8B và Gemma2-9B; xem [CSV metrics](../data/exp_a/final/results/llm_experiment_metrics.csv). B hiện là scorer lexical trên candidate pool và nhãn mock; semantic ranking/shared weights vẫn cần triển khai và kiểm chứng trên relevance labels độc lập.

## Code của hướng cũ

Các runner [C — profile](exp_c/README.md), [D — ý định phiên](exp_d/README.md), [E — thích ứng thời gian](exp_e/README.md) được giữ để tra cứu và tái lập. Chúng nằm ngoài phạm vi chính A/B/conference; conference không được đổi tên thành C cũ.

`baseline_common.py` giữ biểu diễn/scoring chung; `experiment_runner.py` điều phối dữ liệu/output; `evaluate_experiments.py` đọc nhãn đánh giá cho baseline B–E. Các module này vẫn phục vụ code hiện có.

## Tài liệu dùng chung

- [Chỉ mục dữ liệu](../data/README.md).
- [Giao diện scorer và evaluator baseline B–E](BASELINE_GUIDE.md).
- [Lệnh chạy A–E hiện có](../docs/RUN_EXPERIMENTS.md) và [protocol A–E](../docs/EXPERIMENT_PROTOCOL.md): mô tả triển khai lịch sử.
- [Kế hoạch A–E ngày 10/10](../docs/EXPERIMENT_PLAN_FINAL.md): tài liệu lịch sử, không thay thế đề cương A/B/conference.
