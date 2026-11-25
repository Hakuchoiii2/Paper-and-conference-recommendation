# QLoRA v2 — kết quả training, 19/10/2026

**Train hoàn tất và adapter đã được kiểm chứng. Chọn checkpoint epoch 2 (`checkpoint-118`); chưa có kết quả generation/F1 của adapter v2.**

Kaggle: [htnkhi/exp-a-qwen-qlora-v2](https://www.kaggle.com/code/htnkhi/exp-a-qwen-qlora-v2). Trạng thái API lúc thu thập: `KernelWorkerStatus.COMPLETE`. Bản launch version 1; settings tải từ output khớp chính xác build và chữ ký đã launch. Không push run mới trong lần kiểm tra này.

## Diễn biến loss

| Epoch | Optimizer step | Dev loss | Kết quả |
|---:|---:|---:|---|
| 1 | 59 | 0.09211858 | |
| 2 | 118 | 0.08514727 | Thấp nhất, được chọn |
| 3 | 177 | 0.08884508 | Tăng lại |

- Đủ 3 epoch, 177/177 bước; 467 train / 100 dev.
- Thời gian Trainer: **3 giờ 53 phút 34 giây** (14014.3845 giây), gồm các lượt đánh giá dev; không phải thời gian chờ Kaggle. Log toàn phiên kết thúc ở khoảng 3 giờ 57 phút.
- Train loss tổng do Trainer báo: **0.07728106**. Cửa sổ train loss cuối ở step 175: **0,0322**; không đồng nhất hai chỉ số này.
- Dev loss giảm **7,57%** từ epoch 1 sang 2 rồi tăng **4,34%** ở epoch 3 trong khi train loss tiếp tục giảm. Đây là dấu hiệu phù hợp với bắt đầu overfit sau epoch 2; mới có ba điểm dev nên không khẳng định rộng hơn.
- Adapter cuối thực sự có SHA-256 trùng weights của `checkpoint-118`, khác weights `checkpoint-177`. Cơ chế chọn lowest dev loss đã hoạt động đúng. Không có bằng chứng từ loss này để tiếp tục tăng epoch.

## Kiểm chứng bản chạy và artifact

**24/24 kiểm tra PASS**; chi tiết trong `data/exp_a/finetuning/v2/build/training_result_checks_2026-10-19.json`.

- Chữ ký release: `3875d3d25d83d48170e26a97b07fb2338388b7ba3b557ff261396578f5207550`. Cloud settings khớp build, launch và provenance; model/revision, hyperparameters, trainer code hash, train/dev IDs và SHA-256, split/data manifest đều khớp bản local đã seal. Train/dev không giao nhau.
- Base: `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`; Tesla T4; Torch `2.11.0+cu128`, Transformers `4.57.6`, PEFT `0.18.1`, Accelerate `1.15.0`, bitsandbytes `0.50.2`. Attention `matrix_efficient_no_gqa`, NF4 double FP16, thinking off, LoRA r16 / alpha32 / dropout0.05 / all-linear; LR 2e-4, accumulation 8, seed42.
- Max sequence runtime: train **3007**, dev **2789**, trong giới hạn **4096** và khớp preflight. Loss chỉ trên assistant completion và EOS theo signature.
- Đã tải đầy đủ **10/10 file adapter**, kiểm SHA-256 từng file. Weights **174.655.536 byte**, **504 tensor / 43,646,976 tham số LoRA**; kiểm trực tiếp CPU xác nhận tất cả tensor hữu hạn, không NaN/Inf. Hash weights: `fa80cb7e26a1ca34ec98ce1f967b095659779b1f45b3ea4963e6f12167c0ccc7`.
- Run manifest có status complete và ký đúng metadata/adapter files. Checkpoint manifests và trainer state nhất quán với metadata, dev loss và checkpoint được chọn. Các metric đã ghi đều hữu hạn.
- Kiểm lại **38/38 artifact v1**: checksum không đổi. Không đọc nội dung test source/reference, không sinh dự đoán test hoặc thay nhãn trong lần kiểm tra này.

Log có cảnh báo pip về `gradio`/`diffusers` trong image Kaggle cần phiên bản `huggingface-hub` khác. Các thư viện training quan sát đúng bản pin và train hoàn tất; chưa thấy lỗi runtime do cảnh báo này. Không suy rộng rằng cả image Kaggle không còn xung đột. Ngoài ra có cảnh báo deprecation/tokenizer và notebook export, không làm run thất bại.

## Kết luận và giới hạn

Training ổn về mặt thực thi, tính toàn vẹn và chọn checkpoint. Dev loss thấp chỉ đo dự đoán token trên nhãn dev; chưa chứng minh JSON/grounding/role/coverage đúng khi model tự sinh, hết lặp, hoặc tốt hơn base/v1. Không so trực tiếp loss v1 với v2 vì policy/schema và target đã thay đổi.

Nhãn vẫn là **AI reference, human review pending**: **98/567** bài được review độc lập, **469/567** bài source-authored chưa review độc lập. Review sample có chủ đích nên không phải ước lượng tỷ lệ lỗi toàn bộ. `training_only=true`, `evaluation_performed=false` nghĩa là chưa chạy đánh giá generation/F1; **100 dev vẫn đã được tính eval loss** ở mỗi epoch.

Bước kế tiếp là paired inference base–adapter v2 bằng cùng prompt/policy/decoding đã đóng băng, kiểm JSON, grounding, lặp và chất lượng facet trên held-out. Chưa chạy thêm GPU, chưa publish adapter/dataset và chưa thay đổi automation PAUSED.

## Artifact local

- Output: `data/exp_a/finetuning/v2/downloads/training_v1_20261019/` (log, metadata, state/manifests; không tải optimizer hoặc weights checkpoint trung gian).
- Adapter đã xác minh: `data/exp_a/finetuning/v2/downloads/training_v1_20261019/exp_a_qlora_v2/adapters/qwen3-8b-facets-qlora-v2/`.
- Tóm tắt: `data/exp_a/finetuning/v2/build/training_result_summary_2026-10-19.json`.
- Hash file tải về: `data/exp_a/finetuning/v2/build/training_download_manifest_2026-10-19.json`.
- Kiểm tensor/file adapter: `data/exp_a/finetuning/v2/build/training_adapter_audit_2026-10-19.json`.

Thu thập UTC: 2026-10-19T16:40:16.778963+00:00; ngày báo cáo theo Asia/Bangkok.
