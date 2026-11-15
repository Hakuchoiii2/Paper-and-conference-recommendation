# Nguồn dữ liệu gốc

[Chỉ mục dữ liệu](../README.md) · [Corpus được lọc/gộp](../processed/README.md)

## 1. Vai trò của raw

Giữ nguyên archive, bản giải nén, README, schema, giấy phép và nhãn/split nguồn. Raw không phải toàn bộ corpus được chọn cho thực nghiệm; builder còn lọc phạm vi và gộp trùng.

| Nguồn | Nội dung giữ lại | Phạm vi dùng trong dự án |
|---|---|---|
| CSFCube v1.1 | Title/abstract/metadata, nhãn facet gốc, candidate pools, guideline, split và license | Nguyên liệu bài báo; A trích lại theo năm facet |
| SciFact | Abstract corpus, claims train/dev/test, CV folds, schema và LICENSE.md | Chỉ bài có evidence phù hợp phạm vi IT |

Không tải kho ngoài khoảng 800.000 bài liên quan CSFCube. Nhãn ba facet/relevance nguồn được giữ để bảo toàn provenance, **chưa dùng làm benchmark ba facet cho hệ năm facet**.

## 2. Tải hoặc kiểm tra bản đã có

Từ gốc repository:

```powershell
python scripts/download_sources.py
```

Lần tải đầu cần mạng; script tái sử dụng bản hiện có và kiểm tra checksum. Mỗi nguồn có source_manifest.json ghi URL, release/version và SHA-256. Giữ cả archive và bản giải nén.

SciFact URL latest được khóa bằng hash archive đã tải; script không tự cập nhật đè. Nếu raw đổi, script báo lỗi. Đổi release phải giữ provenance và bản cũ, review ảnh hưởng ID/split trước khi rebuild.

## 3. License và nguồn tham chiếu

- [CSFCube v1.1](https://github.com/iesl/CSFCube/releases/tag/v1.1): giữ CC BY-NC 4.0 và thông tin citation đi kèm.
- [SciFact](https://github.com/allenai/scifact): giữ LICENSE.md và điều kiện nguồn công bố.

README gốc bên trong hai nguồn giữ nguyên ngôn ngữ/nội dung. Không chỉnh source files để khớp schema exp; xử lý bằng builder và ghi audit trong processed.

Raw/processed được phép commit/push theo quy ước dự án hiện tại; các dataset exp sinh ra, model/cache/checkpoint bị ignore. Khi chia sẻ raw vẫn phải giữ attribution/giấy phép. Xem [quản lý corpus và Git](../../docs/PROJECT_OPERATIONS.md).
