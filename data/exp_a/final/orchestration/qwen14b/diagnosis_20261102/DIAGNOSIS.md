# Qwen14B: chẩn đoán OOM ngày 02/11/2026

Kernel `htnkhi/exp-a-qwen14b-gold400` có trạng thái ERROR. Log thực tế nằm ở `kernel.log`, cấu hình thực tế ở `settings.json`. Không chạy lại kernel trong lượt kiểm tra này.

## Nguyên nhân đã xác nhận

Load đủ 8 weight shards thành công. Sau đó `train.py:270` → `prepare_adapter` → `prepare_model_for_kbit_training` bị OOM khi `param.data.to(torch.float32)`. Chưa bắt đầu optimizer step nào; chưa có adapter Qwen14B đã train để tải về.

GPU0: tổng 14,56 GiB, còn trống 2,17 GiB; allocation mới cần 2,90 GiB; PyTorch allocated 10,72 GiB, reserved nhưng chưa allocated 1,56 GiB. Training hiện dùng một GPU (`CUDA_VISIBLE_DEVICES=0`, `device_map={'': 0}`); T4 thứ hai được dành cho hai worker inference về sau. Hai T4 không tự cộng VRAM cho một model.

PEFT 0.18.1 chuyển các parameter FP16/BF16 không phải Params4bit sang FP32. Qwen3-14B có vocab151936, hidden5120 và embedding/head không tied: một ma trận FP32 cỡ này chiếm khoảng 2,90 GiB, trùng kích thước allocation lỗi. Log chưa in tên parameter nên chưa khẳng định là embedding hay lm_head.

## Hướng giải quyết

1. Nếu tiếp tục dùng T4 x2: dùng **một process train với model phân bố rõ ràng trên hai GPU**, giữ NF4/FP16 compute và quy tắc FP32 preparation của PEFT. Cho train process thấy cả hai GPU; đổi guard single-GPU chỉ trong release Qwen14B; dùng device map tường minh chia các decoder layer, embedding/head cân bằng. Không bật DDP hoặc DataParallel vì các cách này có thể nhân bản model. `completion_loss` hiện tạo targets trên GPU input, nên cần chuyển targets và mẫu số loss sang device của logits nếu head nằm ở GPU khác. Cần kiểm tra Trainer/Accelerate nhận model parallel và LoRA gradients trên cả hai GPU. Không chỉ sửa `device_map='auto'` rồi xem là hoàn tất.
2. GPU VRAM lớn hơn: thử smoke test trên GPU24 GiB trở lên, GPU40 GiB có dư địa hơn. Đây là phương án ít sửa trainer nhất; dung lượng cụ thể vẫn phải đo bằng dữ liệu thật.
3. Nếu bắt buộc một T4: cân nhắc giữ frozen embedding/lm_head ở FP16, layernorm và adapter ở FP32, đồng thời giữ freeze base và gradient checkpointing. Cần thay preparation có kiểm soát; cast về FP16 **sau** hàm PEFT sẽ quá muộn vì OOM đã xảy ra bên trong hàm. Cách này đổi precision so với thí nghiệm gốc và chưa chắc đủ cho activations/backward; phải ghi rõ trong provenance và kiểm chứng loss/gradients.

`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` có thể giảm phân mảnh, nhưng không bảo đảm giải quyết tổng bộ nhớ sống hoặc peak khi cast. Giảm batch từ1 không khả thi; giảm sequence không sửa allocation lỗi trước forward. Không tự cắt input hoặc đổi rank/nhãn/split để che OOM.

## Kiểm chứng trước khi chạy đủ

- Session GPU sạch, in peak allocated/reserved trên từng GPU sau load, FP32 preparation, LoRA và một forward/backward/optimizer step với train example dài nhất.
- Giữ nguyên split280/60/60, effective batch8, rank16, LR1e-4, 3 epochs và loss completion-only.
- Smoke test validation/generation và lưu/reload adapter; xác nhận base frozen, LoRA gradients hữu hạn, dữ liệu không bị cắt.
- Chỉ khi smoke test qua mới chạy105 steps và đánh giá3 checkpoint. Các phương án trên chưa được kiểm chứng bằng một lượt train Qwen14B thành công.

## Nguồn chính thức

- PEFT0.18.1: https://github.com/huggingface/peft/blob/v0.18.1/src/peft/utils/other.py#L121-L199
- Qwen3-14B config: https://huggingface.co/Qwen/Qwen3-14B/blob/main/config.json
- PyTorch CUDA memory: https://docs.pytorch.org/docs/stable/notes/cuda.html#memory-management
