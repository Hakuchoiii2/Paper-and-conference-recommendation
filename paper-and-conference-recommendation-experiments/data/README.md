# Dữ liệu nghiên cứu A/B/conference

Phạm vi hiện tại là so sánh LLM trích năm facet, paper ranking và manuscript-based conference recommendation. Xem [tổng quan đề tài](../README.md) và [đề cương hiện hành](../docs/PAPER_STRUCTURE_SHARED_FACET_WEIGHTS_2026-10-23.md).

## Dữ liệu đang dùng

| Phần | Vai trò | Đọc tiếp |
|---|---|---|
| `raw/` | Nguồn tải, giấy phép và checksum | [Nguồn gốc](raw/README.md) |
| `processed/` | Corpus canonical 4.210 title/abstract và metadata | [Corpus và rebuild](processed/README.md) |
| A | Trích problem/task/method/dataset/contribution cùng evidence | [Dữ liệu và lịch sử A](exp_a/README.md) |
| `exp_a/final/` | Code/prompt/config chung, reference400, kết quả và adapter theo model | [Bộ final](exp_a/final/README.md) |
| B | Bài mốc, candidates, relevance labels và split | [Generator baseline B](exp_b/README.md) |
| Conference | Cần chốt catalog, metadata venue/year, cutoff và nhãn; chưa có pipeline riêng | [Thiết kế conference](../docs/PAPER_STRUCTURE_SHARED_FACET_WEIGHTS_2026-10-23.md) |

## Trạng thái thực nghiệm

- A đã hoàn tất QLoRA và đánh giá cho Qwen3-4B/8B/14B, Llama3.1-8B và Gemma2-9B; cùng 280 bài train, 60 valid, 60 test. [Bảng metrics 5 LLM](exp_a/final/results/llm_experiment_metrics.csv) dùng thang 0–1.
- Reference400 hiện hành ở [human_gold.jsonl](exp_a/ground_truth/gold_review/human_gold.jsonl): nhãn AI-assisted đã được người dùng kiểm tra/chấp nhận. Cohort từng được dùng trong phát triển pipeline; test60 chưa phải external holdout độc lập.
- Facet mới do model sinh vẫn là silver/unreviewed. Fine-tune trên reference được chấp nhận không tự biến output mới thành human gold.
- B hiện có baseline lexical và dữ liệu mock: manifest ghi 18 query/1.800 cặp có nhãn, trong khi quota cấu hình là 300 query ×100 candidates. Nhãn weighted overlap chưa thay thế relevance labels độc lập.

## Chuẩn bị cho hướng nghiên cứu hiện tại

1. Giữ cùng paper IDs, văn bản nguồn, prompt/schema, split và provenance để đối chiếu các extractor.
2. Chọn và đóng băng bộ facet tham chiếu `F_ref` cho B. B không cần đợi A chọn model có điểm test cao nhất.
3. Chọn encoder, scorer, trọng số và missing policy trên train/dev B; khóa cấu hình trước test và dùng chung giữa các extractor trong phép thử kết nối.
4. Chuẩn bị lịch sử hội nghị trước cutoff, catalog và nhãn venue riêng cho conference.

## Dữ liệu và quy trình lịch sử

C/D/E thuộc hướng cũ, được giữ để tra cứu và tái lập:

| Phần | Nội dung lịch sử |
|---|---|
| [C](exp_c/README.md) | Users, profile, lịch sử/search/exposure và holdout |
| [D](exp_d/README.md) | Ý định trong phiên và ranking theo hướng |
| [E](exp_e/README.md) | Profile thay đổi theo thời gian và rolling holdout |

Generator baseline B–E hiện dùng silver A đã gộp và lọc cờ chất lượng; D/E còn phụ thuộc danh tính hoặc lịch sử C. Đây là phụ thuộc của code mô phỏng cũ, không phải yêu cầu phải hoàn tất C/D/E cho đề tài mới. Quota và hướng dẫn lịch sử nằm trong README từng exp, [data contract](../DATA_CONTRACT.md) và [protocol A–E](../docs/EXPERIMENT_PROTOCOL.md).

Đọc tiếp: [chỉ mục scripts](../scripts/README.md), [quản lý corpus và bàn giao](../docs/PROJECT_OPERATIONS.md). Bài báo là dữ liệu thật; silver extraction và nhãn/hành vi mô phỏng cần được phân biệt rõ khi báo cáo.
