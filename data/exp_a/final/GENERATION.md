# Script chính thức — QLoRA gold400 V-recall

Entrypoint: `generate.py`. Cấu hình và adapter: [README](README.md).

Từ **gốc project** chạy kiểm tra bản đóng gói, không cần GPU:

```powershell
python -B data/exp_a/final/generate.py --check
python -B data/exp_a/final/test_generate.py -v
```

Sinh dữ liệu trên GPU CUDA, mỗi process thấy đúng một GPU:

```bash
CUDA_VISIBLE_DEVICES=0 python -B data/exp_a/final/generate.py
```

Đọc mặc định `data/processed/papers.jsonl`; ghi `data/exp_a/final/generated/`. Để chạy một mẫu riêng:

```bash
CUDA_VISIBLE_DEVICES=0 python -B data/exp_a/final/generate.py --limit 10 --output data/exp_a/final/results/Qwen8B/smoke10
```

Hoặc chỉ định JSONL nguồn mới:

```bash
CUDA_VISIBLE_DEVICES=0 python -B data/exp_a/final/generate.py --input papers.jsonl --output data/exp_a/final/results/Qwen8B/new_corpus
```

Input phải có `paper_id` dạng P +6 chữ số duy nhất, `title` và `abstract` không rỗng. Các trường khác bị bỏ trước khi đưa vào model. Đổi nguồn/cấu hình/adapter phải dùng output directory mới; chạy lại cùng lệnh để tiếp tục từ signed records. Chỉ một process ghi vào một output directory. Cần output riêng cho mỗi shard nếu chia GPU.

## Runtime

`runtime/` giữ policy, validator, trainer và helper từ release v5. Runtime điều phối Qwen ở `orchestration/Qwen8B/runtime.py`. Hai builder đọc chung `runtime/`, `prompts/` và `reference/` qua `package.py`. Entrypoint sinh corpus gọi trực tiếp `annotate_fresh` đã dùng trong kernel. Bundle gốc và kernel gốc vẫn được giữ để tái lập tại `source_bundle.zip.bin` và `orchestration/Qwen8B/provenance/kernel/`.

Môi trường GPU đã xác nhận ở kernel gốc: Linux, Tesla T4, Python3.13, torch2.11.0+cu128, transformers4.57.6, peft0.18.1, accelerate1.15.0, bitsandbytes0.50.2. File `requirements.txt` giữ các version thư viện chính; cài PyTorch CUDA phù hợp trước. Base Qwen3-8B được tải theo revision ghim; loader gốc dùng cache `/tmp/exp_a_huggingface`. Đóng gói này chưa chạy GPU mới trên Windows.

## Output

- `records/Pxxxxxx.json`: kết quả đầy đủ, raw attempts, coverage, audit, chi phí và checksum.
- `drafts/`: draft đầu tiên để tiếp tục khi gián đoạn.
- `facets_silver.jsonl`: `paper_id` và năm danh sách concept, phục vụ các bước B–E.
- `annotation_metadata.jsonl`: bằng chứng nguồn, trạng thái silver/unreviewed, audit và checkpoint.
- `run.json`, `manifest.json`: signature đầu vào, coverage, trạng thái partial/complete và checksum output.

Mỗi bài xuất checkpoint ngay khi hoàn tất. Các phép kiểm tra CPU thay model decoder bằng phản hồi cố định; chúng thực thi pipeline ba lượt và kiểm tra export/resume/checksum/input, không đo lại chất lượng model.
