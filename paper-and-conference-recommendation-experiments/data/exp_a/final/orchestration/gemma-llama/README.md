# Exp A: Llama8B rồi Gemma9B

Chạy tuần tự `meta-llama/Llama-3.1-8B-Instruct` → `google/gemma-2-9b-it`.
Cấu hình model ở `../../configs/models.json`; cấu hình thí nghiệm chung ở `../../reference/settings.json`. Prompt ở `../../prompts/`, policy/validator/trainer ở `../../runtime/`. Builder dùng `../../package.py`, cùng nguồn với bộ điều phối Qwen8B.
Mỗi model: QLoRA trên GPU0 → ba checkpoint được đánh giá trên valid60 bằng V-recall → chọn bằng micro F1/recall/epoch sớm → test60 một lần với adapter được chọn → lưu kết quả và ZIP → model tiếp theo.
Generation cho từng checkpoint/test chạy hai process, mỗi process một GPU và 30 bài. Không train hai model cùng lúc. Training hiện dùng một GPU như Qwen8B.

## Kết quả hiện tại

Tất cả kết quả theo model nằm chung trong `data/exp_a/final/results/`:

```text
data/exp_a/final/results/
  Qwen8B/results/...
  Llama8B/             # đã tải và kiểm tra checksum ngày 02/11/2026
  Gemma9B/             # đã tải và kiểm tra checksum ngày 02/11/2026
```

Llama8B và Gemma9B đã hoàn tất, cùng chọn `checkpoint-105`; test micro-F1 lần lượt **64,51%** và **68,18%**. Adapter được lưu tại `../../adapter/Llama8B/` và `../../adapter/Gemma9B/`. Xem [bảng kết quả và hướng dẫn tải adapter](../../README.md), [CSV metrics 5 LLM](../../results/llm_experiment_metrics.csv).

`Qwen8B/` chứa kết quả hiện tại, config, training metadata và manifest nguồn. Adapter Qwen ở `data/exp_a/final/adapter/Qwen8B/`. Khi tải `Llama8B_completed.zip` và `Gemma9B_completed.zip`, giải nén vào **`data/exp_a/final/results/`**; ZIP đã chứa thư mục tên model. Input bundle cũng giữ kết quả Qwen8B để output Kaggle mang đủ tên model.

## Build ở gốc project

```powershell
.\.venv-qwen\Scripts\python.exe -B data/exp_a/final/orchestration/gemma-llama/prepare.py
.\.venv-qwen\Scripts\python.exe -B data/exp_a/final/orchestration/gemma-llama/test_compare.py -v
```

Release: `data/exp_a/final/orchestration/gemma-llama/release_20261030_v1/`.

- `input-dataset/llama_gemma_bundle.zip.bin`: dữ liệu và runtime, không có base weights hay token.
- `input-dataset/dataset-metadata.json`: cấu hình dataset riêng tư để upload.
- `kernel/run_llama_gemma.py`: script Kaggle có ghim SHA-256 bundle.
- `kernel/kernel-metadata.json`: cấu hình kernel riêng tư, Internet, GPU T4 x2.

Build chỉ tạo file tại máy; không upload, không submit và không dùng quota Kaggle.

## Chạy trên Kaggle

Theo lựa chọn hiện tại, có thể điền token trực tiếp vào `HF_TOKEN = ""` gần đầu script kernel trong **editor Kaggle riêng tư**, chọn T4 x2 và Save & Run All. Token trực tiếp được ưu tiên và truyền qua environment cho các process train/generation. Nó nằm trong source/history của phiên bản được lưu; source trong repo chỉ giữ chuỗi rỗng. Không rebuild/push từ repo sau khi điền trên Kaggle vì thao tác đó sẽ thay source bằng bản token rỗng. Vẫn cần tài khoản Hugging Face có quyền tải cả hai model.

Cách dùng Secrets thay cho điền trực tiếp vẫn được hỗ trợ:

1. Tài khoản Hugging Face phải được cấp quyền [Llama3.1-8B](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) và chấp nhận quyền truy cập [Gemma2-9B](https://huggingface.co/google/gemma-2-9b-it).
2. Tạo Kaggle secret **HF_TOKEN**, bật quyền dùng secret cho notebook/kernel. Không dán token vào source.
3. Upload `input-dataset` thành **private dataset**, thêm vào kernel. Dùng script đã build; chọn **GPU T4 x2**, **Internet ON**.
4. Chạy **Save & Run All**. Kernel kiểm tra quyền tải cả hai model và toàn bộ train/valid bằng tokenizer thật trước khi train.

Có thể upload bằng Kaggle CLI sau khi tài khoản đã cấu hình:

```powershell
kaggle datasets create -p data/exp_a/final/orchestration/gemma-llama/release_20261030_v1/input-dataset
kaggle kernels push -p data/exp_a/final/orchestration/gemma-llama/release_20261030_v1/kernel
```

Kiểm tra secret HF_TOKEN đã được bật cho kernel trên giao diện Kaggle trước khi submit. Metadata một mình không cấp quyền secret.

## Output và resume

```text
/kaggle/working/exp_a_compare/
  Qwen8B/results/...
  Llama8B/
    adapter/                  # selected checkpoint + tokenizer + training metadata
    train_state/              # optimizer, scheduler, RNG, epoch checkpoints để resume
    results/valid/checkpoint-*/records/...
    results/test/QLoRA-V-recall/records/...
    results/test/QLoRA-V-recall/facets_silver.jsonl
    results/experiment_summary.json
    complete.json             # output checksums
  Llama8B_completed.zip
  Gemma9B/...
  Gemma9B_completed.zip
  model_revisions.json
  batch_status.json
```

Khi Llama xong, ZIP của Llama được tạo trước khi bắt đầu Gemma. Generation ghi từng paper ngay; cùng phiên chạy lại bootstrap để tiếp tục các record còn thiếu. Training tự tìm epoch checkpoint đầy đủ gần nhất, kiểm tra signature/checksum rồi resume; phần của epoch chưa được lưu có thể phải chạy lại. Không tự train lại model có `complete.json` hợp lệ.

Để resume ở **phiên Kaggle khác**, lưu/download toàn bộ `exp_a_compare/` (bao gồm `train_state`, `model_revisions.json`, settings và runtime), thêm output cũ làm input rồi copy vào `/kaggle/working/exp_a_compare/` trước khi chạy lại cùng bootstrap. Chỉ ZIP `_completed.zip` đủ để lưu model đã xong, không đủ để resume training dở. Giữ cả revision lock khi resume; không tự resolve lại Gemma mới hơn. Đây là lưu file/checkpoint vào working output, không phải tự động upload backup ra ngoài phiên Kaggle.

## Điều kiện so sánh và giới hạn

Giữ nguyên gold400/split280/60/60, seed42, 3 epochs, LR1e-4, effective batch8, LoRA rank16/alpha32/dropout0.05/all-linear, NF4 double/FP16, max sequence4096, greedy max2048 token mỗi lượt, V-recall ba lượt và evaluator/threshold0.85 của Qwen final. Không chạy test base model. Test labels chỉ được đọc ở bước scoring sau khi predictions được seal.

Gemma2 không nhận system role: ghép nguyên system instruction vào đầu user message đầu tiên, giống nhau khi train và sinh. Dùng đúng end-of-turn của từng model; không thêm BOS lần hai. Gemma2 dùng eager attention để giữ softcapping; do đó có thể chậm/tốn bộ nhớ hơn Qwen/Llama. Llama dùng attention tiết kiệm bộ nhớ đã có trong release, với chat template gốc. Phiên bản thư viện chính giữ như Qwen final.

Llama ghim revision `0e9e39f249a16976918f6564b8830bc894c89659`. Gemma được resolve thành SHA cụ thể trong authenticated preflight và lưu vào revision lock/settings/signature **trước training**. Token không được lưu vào config/output.

Chỉ có một seed và không tìm hyperparameter riêng từng model. Gold400 có lịch sử phát triển pipeline, không phải external holdout độc lập. Các test CPU không xác nhận thời gian chạy hoặc training đầy đủ trên T4 của hai model mới. Dữ liệu và kết quả phải được giữ riêng tư theo yêu cầu nguồn và quyền truy cập model.
