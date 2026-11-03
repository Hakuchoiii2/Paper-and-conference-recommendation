# Exp A — Bộ final và kết quả 5 LLM

Cập nhật 03/11/2026. Bộ này chứa code, prompt/guideline, cấu hình, dữ liệu tham chiếu và kết quả so sánh Qwen3-4B/8B/14B, Llama3.1-8B và Gemma2-9B. Tất cả đã hoàn tất QLoRA và đánh giá test60.

Cấu hình được chọn để **sinh corpus** từ ngày 28/10 vẫn là **Qwen/Qwen3-8B + QLoRA gold400 checkpoint-105 + V-recall ba lượt + validator `source_attributed_paraphrase_v1`**. Việc có thêm kết quả 4 model không tự thay đổi cấu hình này hoặc xác nhận model tốt nhất cho paper/conference ranking. Xem [hướng đề tài A/B/conference](../../../README.md).

## Cấu trúc

```text
final/
  adapter/
    Qwen4B/                 # khôi phục từ Google Drive
    Qwen8B/
    Qwen14B/
    Llama8B/
    Gemma9B/
  orchestration/
    Qwen8B/                 # runtime điều phối, builder và provenance Qwen8B
    gemma-llama/            # lượt Llama8B rồi Gemma9B
    qwen4b-14b/             # lượt gốc: Qwen4B hoàn tất, Qwen14B bị OOM
    qwen14b/                # lượt riêng Qwen14B đã hoàn tất trên hai T4
  runtime/                  # policy, validator, trainer và helper dùng chung
  prompts/                  # prompt/guideline đã đóng băng
  configs/                  # danh sách model/revision cho các lượt so sánh
  reference/                # settings, split và train/valid/test đã khóa
  results/
    Qwen4B/
    Qwen8B/
    Qwen14B/
    Llama8B/
    Gemma9B/
    llm_experiment_metrics.csv
  config.json               # cấu hình sinh corpus bằng Qwen8B
  package.py                # đóng gói nguồn và dữ liệu chung
  generate.py               # entrypoint sinh corpus
  manifest.json             # provenance và SHA-256 của bộ đóng băng
  source_bundle.zip.bin     # bundle Qwen8B v5 gốc để kiểm tra/tái lập
```

- `prompts/extraction_gold_v1.md` và `prompts/guideline_gold_v1.md` là hai tệp chỉ dẫn đang dùng.
- `reference/` gồm nguồn title/abstract, split280/60/60, SFT train/valid, gold valid/test và settings; không có SFT test. Entrypoint sinh corpus không đưa gold vào model.
- `results/<model>/results/experiment_summary.json` là nguồn điểm từng model. CSV tổng hợp dùng thang **0–1**, chỉ lấy dòng QLoRA trên test, không lấy baseline base của Qwen8B.
- `adapter/<model>/` là vị trí adapter dùng chính; base model tải riêng theo revision đã ghim trong metadata.
- `source_bundle.zip.bin` vẫn được `package.py` sử dụng. Các snapshot `history/release_20261028_v1–v3/project/` đã bỏ bản bung trùng; ZIP trong `input-dataset/` của từng release vẫn giữ nguyên.

## Tải adapter từ Google Drive

**Trọng số adapter không được push lên Git. Adapter sẽ được cung cấp qua Google Drive; tải riêng sau khi clone repo.**

**Link Google Drive: TODO — chủ repo sẽ chèn link tại đây.**

1. Mở link Drive ở trên sau khi được bổ sung, tải adapter của model cần dùng. Chạy entrypoint sinh corpus hiện tại chỉ cần **Qwen8B**; tải cả 5 khi cần dùng toàn bộ các model đã fine-tune.
2. Giải nén để có đúng đường dẫn từ gốc repo: `data/exp_a/final/adapter/<model>/`. Tránh lồng thêm một cấp như `adapter/Qwen8B/Qwen8B/`.
3. Giữ đầy đủ adapter, tokenizer và metadata trong cùng thư mục:

   ```text
   adapter/Qwen8B/
     adapter_model.safetensors
     adapter_config.json
     training_metadata.json
     tokenizer.json
     tokenizer_config.json
     chat_template.jinja
     ...                     # giữ các tệp tokenizer khác đi kèm gói
   ```

4. Đối chiếu checkpoint, base model/revision và SHA-256 trong `training_metadata.json`. Với Qwen8B, file `adapter_model.safetensors` đúng bản đã chọn có **174.655.536 byte**, SHA-256 **`8ad6a822145bc23ee7ff5f952f88ab2df2900ddc1682c575af229ff537a4ab3d`**.
5. Kiểm tra bộ đóng băng từ gốc repo trước khi sinh:

   ```powershell
   python -B data/exp_a/final/generate.py --check
   ```

Lệnh trên kiểm tra cả manifest của code/config và adapter, không nạp model GPU. Ngày 03/11/2026, manifest đã được đồng bộ sau khi đối chiếu bootstrap/compat với release logging đã lưu và chạy 15 test Gemma–Llama. Các checksum vẫn được kiểm tra đầy đủ; không bỏ qua bước xác minh khi khôi phục adapter.

Gói Drive là adapter PEFT cùng tokenizer/metadata, không phải toàn bộ trọng số base LLM. Quyền tải base model và môi trường CUDA vẫn cần được chuẩn bị theo model tương ứng. Không cần train lại chỉ để dùng adapter đã tải.

## Protocol và kết quả đã lưu

Cùng train280/valid60/test60, seed42; 3 epochs/105 optimizer steps, learning rate1e-4, effective batch8, LoRA rank16/alpha32/dropout0,05, NF4 double/FP16 và completion-only loss. Chọn một trong ba epoch checkpoint bằng **validation V-recall micro-F1**, rồi recall và epoch sớm hơn nếu hòa; dùng adapter đã chọn để đánh giá test60.

V-recall dùng ba lượt: trích năm facet → review/sửa có kiểm tra nguồn → bổ sung task/method. Giữ greedy decoding, `enable_thinking=False`, tối đa2.048 token/lượt và matching embedding threshold0,85. Dùng chat template phù hợp từng model; Qwen14B train một process chia model lên hai GPU T4. Xem các README điều phối để biết khác biệt runtime theo model.

| Model | Checkpoint đã chọn | Precision | Recall | Micro F1 | Macro F1 | Fallback |
|---|---|---:|---:|---:|---:|---:|
| Qwen4B | checkpoint-105 | 59,32% | 62,75% | 60,99% | 62,93% | 2 |
| Qwen8B | checkpoint-105 | 63,17% | 70,72% | 66,73% | 67,67% | 3 |
| Qwen14B | checkpoint-70 | 61,21% | 66,33% | 63,67% | 65,62% | 0 |
| Llama8B | checkpoint-105 | 63,51% | 65,54% | 64,51% | 65,28% | 1 |
| Gemma9B | checkpoint-105 | 67,45% | 68,92% | 68,18% | 70,39% | 0 |

Nguồn: [CSV metrics](results/llm_experiment_metrics.csv) và `results/<model>/results/experiment_summary.json`. Training summary có thể ghi checkpoint provisional theo dev loss; checkpoint export cuối theo validation F1 nằm trong `results/<model>/results/checkpoint_selection.json` và `adapter/<model>/training_metadata.json`.

Qwen8B có thêm paired base test: precision22,55%, recall30,28%, micro-F1 25,85%, macro-F1 25,97%. Dòng base này không nằm trong bảng so sánh QLoRA ở trên. Bộ final chưa có kết quả downstream để suy ra thứ hạng paper/conference ranking từ F1 extraction.

## Sinh corpus và tái lập

Entrypoint là [generate.py](generate.py); xem [GENERATION.md](GENERATION.md) về môi trường, input, output và resume. Cấu hình mặc định đọc `data/processed/papers.jsonl`, ghi `data/exp_a/final/generated/` bằng Qwen8B. Chưa xác nhận đã sinh lại toàn bộ corpus bằng các adapter final.

Các bộ điều phối train/evaluate: [Qwen8B](orchestration/Qwen8B/README.md), [Llama–Gemma](orchestration/gemma-llama/README.md), [Qwen4B/14B lượt gốc](orchestration/qwen4b-14b/README.md), [Qwen14B hai T4](orchestration/qwen14b/README.md). Chúng dùng nguồn/prompt/reference đã đóng băng trong bộ final và các bundle release được giữ để tái lập.

Máy hiện tại dùng hard link cho các file adapter trùng giữa `adapter/` và gói `results/`, cùng một số bản lịch sử: các đường dẫn giữ nguyên, dùng chung dữ liệu trên đĩa. Khi sao chép hoặc giải nén trên máy khác, chúng có thể trở thành file độc lập. Nếu cần kiểm tra `complete.json` của gói kết quả, khôi phục đủ `results/<model>/adapter/` với nội dung giống adapter đã chọn. Các artifact này được giữ đóng băng; thay file bằng bản mới riêng thay vì sửa trực tiếp nội dung file liên kết.

## Nguồn nhãn và giới hạn

Gold400 có nguồn GPT hỗ trợ và đã được người dùng kiểm tra/chấp nhận; giữ nguyên nguồn nhãn, audit và cặp SOAP gần trùng được chấp nhận. Cohort được chọn có chủ đích và từng được xem trong quá trình phát triển pipeline; split theo bài mới không biến test60 thành external holdout độc lập. Matching embedding là phép ghép nhãn xấp xỉ.

Mỗi model mới có một seed; chưa có phép so độ bất định hoặc tìm hyperparameter riêng. Kết quả bảng là extraction trên protocol này, chưa xác nhận model tốt nhất nói chung. Output mới vẫn là **silver/unreviewed**, không tự trở thành human gold vì model đã fine-tune.
