# Gemma–Llama: kết quả tải ngày 02/11/2026

Kernel `htnkhi/exp-a-llama-gemma-gold400`: COMPLETE. Log kết thúc bằng DONE: both models finished.

Đã kiểm CRC ZIP, SHA-256 toàn bộ manifest completion và adapter, prediction seals, đủ60 records mỗi checkpoint validation và test, metadata train105 steps/3 epochs, cấu trúc safetensors. Không chạy lại GPU inference tại máy.

| Model | Checkpoint | Valid F1 | Test precision | Test recall | Test F1 | Macro F1 | Fallback |
|---|---|---:|---:|---:|---:|---:|---:|
| Llama8B | checkpoint-105 | 68.40% | 63.51% | 65.54% | 64.51% | 65.28% | 1/60 |
| Gemma9B | checkpoint-105 | 70.00% | 67.45% | 68.92% | 68.18% | 70.39% | 0/60 |

Llama fallback: P000144. Đây là fallback xử lý output của pipeline, không phải kernel crash. Gemma không có fallback test.

Kết quả đầy đủ: `results/Llama8B/`, `results/Gemma9B/`. Adapter đã chọn + tokenizer + metadata được lưu riêng tại `adapter/Llama8B/`, `adapter/Gemma9B/`, và giữ nguyên bản trong gói kết quả.

Bản ZIP gốc: `Thực hành/output/kaggle_llama_gemma_20261102/exp_a_compare/`. Provenance và báo cáo checksum: `orchestration/gemma-llama/download_20261102/`.

Đây là kiểm tra tính toàn vẹn và tính nhất quán của artifacts đã chạy, không phải đánh giá lại chất lượng nhãn bằng tay hay benchmark độc lập. Giữ nguyên giới hạn gold400 của thí nghiệm gốc.
