# Bố trí thư mục Exp A

Quy ước chốt ngày 2026-10-18: test Exp A, gồm test mới, đặt trong
`scripts/exp_a/`; dùng xong phải dọn thư mục tạm. Giữ nguyên README gốc.

## Code, test và báo cáo

| Thư mục | Nội dung |
|---|---|
| `scripts/exp_a/core/` | Test generator, retry, resume, chọn attempt và bàn giao A |
| `scripts/exp_a/pilot/` | Test các phiên bản prompt/pipeline pilot |
| `scripts/exp_a/matrix/` | Test matrix và policy matrix |
| `scripts/exp_a/finetuning/` | Test chuẩn bị dữ liệu, review, training, collection, schema và policy A/B |
| `scripts/exp_a/test_qwen_evaluation.py` | Test evaluator dùng chung |
| `scripts/exp_a/docs/` | Thiết kế, quy trình, báo cáo và quyết định |

Từ gốc project, chạy toàn bộ test A:

```powershell
.venv-qwen/Scripts/python.exe -X utf8 -B -m unittest discover -s scripts/exp_a -t . -v
```

Các test dùng chung cho ingestion và thực nghiệm B–E tiếp tục ở `tests/`.
Không thêm test Exp A mới vào đó.

## Dữ liệu và các lượt chạy

| Thư mục | Nội dung cần giữ |
|---|---|
| `data/exp_a/prompts/`, `ground_truth/`, `pilot50/`, `samples/` | Prompt, nguồn, tham chiếu và mẫu |
| `data/exp_a/generated/` | Baseline đang dùng chung với B–E |
| `data/exp_a/generated_v3_5_pilot50/` trở đi | Output pilot lịch sử đã giữ theo quyết định trước |
| `data/exp_a/evaluation/` | Kết quả, manifest và cache encoder |
| `data/exp_a/.kaggle/pilot/`, `.kaggle/matrix/` | Entrypoint/bundle của các lượt Kaggle |
| `data/exp_a/finetuning/data/`, `teacher/`, `adapter-dataset/` | Split v1, nguồn/nhãn và adapter đã seal |
| `data/exp_a/finetuning/build/`, `downloads/` | Bằng chứng build, output gốc, scores và publication |
| `data/exp_a/finetuning/label_revision_v2/` | Policy/schema, pilot và audit nhãn |
| `data/exp_a/finetuning/policy_ab/` | Runner, bundle và quyết định cho A/B policy trên v1 |

Các đường dẫn trong bundle/manifest đã niêm phong được giữ để checksum và khả
năng tái lập còn đúng. Không mở dự đoán policy A/B trước khi nhãn nguồn được seal.

`tmp/` chỉ dùng cho file test/preflight/cache tạm; dọn sau khi tác vụ và tiến
trình liên quan kết thúc. Log cần lưu để đối chiếu phải chuyển vào thư mục
build/báo cáo tương ứng trước khi dọn. `__pycache__/` có thể xóa sau khi kiểm tra.
