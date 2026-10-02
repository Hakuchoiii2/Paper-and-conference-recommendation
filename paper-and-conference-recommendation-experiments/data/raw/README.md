# Dữ liệu gốc từ hai nguồn

Giữ nguyên các bản tải, không sửa nội dung. Từ thư mục gốc có thể tải hoặc kiểm tra
bản đã có bằng:

```powershell
python scripts/download_sources.py
```

- `csfcube/`: bản v1.1, title/abstract/metadata, nhãn facet gốc, candidate pools,
  split đánh giá, guideline và giấy phép. Không tải kho ngoài khoảng 800.000 bài.
- `scifact/`: corpus abstract, claims train/dev/test và các fold cross-validation;
  kèm README, giấy phép và mô tả schema chính thức.

Mỗi nguồn có `source_manifest.json` ghi URL, phiên bản và checksum; giữ cả archive
lẫn bản giải nén. URL `latest` của SciFact được xác định bằng hash archive đã tải,
không tự cập nhật đè. Script tái sử dụng bản đã có và báo lỗi nếu dữ liệu gốc đổi.

Lưu raw đầy đủ **không có nghĩa toàn bộ được đưa vào corpus IT**. Bộ gộp lọc phạm
vi rồi ghi quyết định vào `../processed/scope_audit.jsonl`. Nhãn và split gốc được
giữ để không mất provenance/quy trình đánh giá, chưa chuyển sang nhãn khuyến nghị.
README gốc trong từng nguồn giữ nguyên ngôn ngữ để bảo toàn bản gốc. Dữ liệu raw
và output lớn được ignore khi commit Git về sau.
