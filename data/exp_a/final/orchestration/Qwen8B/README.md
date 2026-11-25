# Điều phối Qwen8B

- `runtime.py`: train → validation bằng hai GPU → chọn checkpoint theo F1 → paired test base/QLoRA → lưu kết quả. Giữ nguyên runtime đã dùng cho kết quả Qwen8B hiện tại.
- `prepare.py`: đóng gói từ `../../package.py`; dùng chung `../../runtime/`, `../../prompts/` và `../../reference/` với lượt Llama–Gemma.
- `bootstrap.py`: cài thư viện, kiểm tra bundle và khởi động runtime trên Kaggle.
- `provenance/kernel/`: script và metadata của kernel đã chạy thật.
- `history/`: các release28/10, source chuẩn bị gốc và báo cáo lịch sử. Bản bung `project/` của v1–v3 đã xóa vì khớp hoàn toàn ZIP đi kèm; ZIP, kernel và báo cáo lịch sử vẫn giữ. Đây là snapshot, không phải nơi sửa policy/config hiện tại.

Từ gốc project:

```powershell
.\.venv-qwen\Scripts\python.exe -X utf8 -B data/exp_a/final/orchestration/Qwen8B/prepare.py
```

Bundle mới ở `release_20261030_v1/` trong thư mục này. Lệnh chỉ build tại máy, không upload hoặc chạy Kaggle. Kết quả đã có giữ tại `../../results/Qwen8B/`; không cần train lại khi chạy lượt Llama–Gemma.

Cấu hình chung: `../../reference/settings.json`. Cấu hình sinh corpus Qwen final: `../../config.json`. Prompt ở `../../prompts/`; policy/validator/trainer ở `../../runtime/`.
