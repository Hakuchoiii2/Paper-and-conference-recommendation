# Qwen3-4B rồi Qwen3-14B

**Trạng thái cập nhật 03/11/2026:** Qwen4B đã hoàn tất, chọn `checkpoint-105`, test micro-F1 **60,99%**. Qwen14B trong lượt gốc bị OOM; lượt riêng [Qwen14B hai T4](../qwen14b/README.md) đã hoàn tất và được lưu vào bộ final. Xem [CSV metrics 5 LLM](../../results/llm_experiment_metrics.csv). Các đoạn dưới mô tả thiết kế kernel gốc.

Kernel riêng tư `htnkhi/exp-a-qwen4b-14b-gold400` chạy tuần tự Qwen4B → lưu adapter/results/ZIP → Qwen14B. Mỗi model train một GPU, sinh validation/test bằng hai GPU chia bài. Dùng public Hugging Face downloads với token=False; không cần HF_TOKEN.

Code dùng cùng runtime/policy và điều phối đã kiểm tra của các lượt trước. Cấu hình model ở `../../configs/qwen4b-14b.json`. Giữ split280/60/60, seed42, 3epochs, LR1e-4, effective batch8, LoRA rank16/alpha32/dropout0.05, NF4 double/FP16, completion-only loss, non-thinking, greedy2048 token mỗi lượt V-recall. Chọn trong ba checkpoint bằng validationF1 rồi test một adapter; không chạy base test.

Dataset Kaggle dùng lại `htnkhi/exp-a-llama-gemma-gold400-inputs`, SHA6259ddb570c4c208d0aeb2e8a17d5ac984701f391f65f08964145bd6a710b510. Builder đối chiếu từng file train/valid/test/split với reference hiện tại. Chỉ code mới được đưa vào script kernel; không upload bản dữ liệu mới. Tên dataset giữ nguyên để không nhân đôi dữ liệu, không có nghĩa lượt này chạy Llama/Gemma.

```powershell
.\.venv-qwen\Scripts\python.exe -X utf8 -B data/exp_a/final/orchestration/qwen4b-14b/test_qwen_scales.py -v
.\.venv-qwen\Scripts\python.exe -X utf8 -B data/exp_a/final/orchestration/qwen4b-14b/prepare.py
kaggle kernels push -p data/exp_a/final/orchestration/qwen4b-14b/release_20261030_v1/kernel
```

Kernel mặc định T4x2 và InternetON. Cả hai revision được resolve thành SHA cụ thể trước training và khóa vào model_revisions.json/settings. Trước training, tokenizer kiểm tra đủ train/valid, không truncate hoặc đưa test references vào model. Nếu input, checkpoint hoặc revision khác khi resume thì dừng.

Output ở `/kaggle/working/exp_a_qwen_scales/{Qwen4B,Qwen14B}/`, kèm Qwen4B_completed.zip và Qwen14B_completed.zip. Tải ZIP về và giải nén trong `data/exp_a/final/results/`. Adapter mỗi model nằm trong thư mục model tương ứng. Lưu toàn bộ working project/train_state/revision lock để resume training dở giữa các phiên. Qwen14B đã được xử lý bằng release riêng hai GPU; không chạy lại lượt gốc để lấy kết quả Qwen14B hiện tại. Adapter dùng chính ở `../../adapter/<model>/`; hướng dẫn tải nằm trong [README final](../../README.md).

Không thay code hay submit lại kernel Llama–Gemma của người dùng.
