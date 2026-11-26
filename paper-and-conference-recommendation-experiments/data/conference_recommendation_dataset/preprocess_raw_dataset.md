# Hướng dẫn xử lý CSFCube cho Conference Recommendation

Mục tiêu: dùng title + abstract để gợi ý hội nghị. Chỉ xử lý CSFCube; dùng corpus đã tiền xử lý chung, giữ nguyên ID và văn bản.

## Đầu vào và luồng chung

Đầu vào gồm raw tại `data/raw/csfcube`, `papers.jsonl` và `id_map.jsonl` tại `data/processed`, cùng bảng mapping và hồ sơ metadata/đối chiếu nguồn đi kèm.

1. Chọn alias active của CSFCube và nối về bài sau gộp trùng.
2. Đọc venue raw, chuẩn hóa tên và mapping về ID hội nghị; nhánh danh mục đối chiếu tên với ICORE/ACL Anthology/Crossref. Tách loại ngoài đích, giữ tên thiếu/mơ hồ ở unresolved.
3. Khi có bước enrichment, nối đúng DOI hoặc CorpusId → DOI, kiểm tra title/tác giả rồi xét metadata nơi công bố.
4. Gom năm từ mọi alias raw thành year; thiếu hoặc mâu thuẫn thì giữ null và danh sách năm nguồn.
5. Sinh mapping từng bài, catalog, nhóm bài và manifest; kiểm tra ID, nhãn, năm, tổng đếm và khả năng chạy lại.

Phương pháp và số lượng của từng thư mục nằm trong [Report_dataset.md](E:/08_Project/Paper-and-conference-recommendation/paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/Report_dataset.md); cấu trúc trường nằm trong [schema_conference.md](E:/08_Project/Paper-and-conference-recommendation/paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/schema_conference.md).

## Chạy lại

Mở terminal tại thư mục chứa hướng dẫn. Dựng lại toàn bộ dữ liệu và hồ sơ đối chiếu từ các đầu vào đi kèm:

```powershell
python 1_raw_mapping/preprocess_cube.py
python run_pipeline.py --audit
```

Chỉ kiểm tra, đồng thời thử dựng lại dữ liệu enrichment trong thư mục tạm, chặn mạng và kết quả cũ:

```powershell
python run_pipeline.py --check --check-isolated
```

Chạy thông thường bằng `python run_pipeline.py` sẽ kiểm tra baseline đã lưu, dựng lại các bản còn lại và cập nhật báo cáo tổng hợp. Mặc định offline; không cần chạy hay đọc kết quả của thư mục thử nghiệm cũ.

## Đọc kết quả và tài liệu

| Vị trí | Dùng để làm gì |
|---|---|
| `Report_dataset.md` | tổng quan, so sánh phương pháp và số lượng |
| `schema_conference.md` | schema chung, định nghĩa trường và trạng thái |
| `preprocessing_common.md` | phần tiền xử lý chung được kế thừa |
| `restriction.md` | hạn chế và việc cần làm trước khi chốt thực nghiệm |
| `output/` trong từng thư mục | dữ liệu đầu ra và báo cáo thống kê riêng |
| `review/` nếu có | kết quả đối chiếu nguồn và các trường hợp cần kiểm tra |

Các báo cáo trong output/review được code sinh lại; sửa quy tắc hoặc hồ sơ nguồn rồi chạy lại thay vì sửa tay báo cáo. Lệnh `--help` của script tương ứng mô tả các tùy chọn mở rộng.

Danh mục tên được dựng lại offline bằng `python 4_catalog_mapping/audit_mapping.py`. Chỉ khi cần lấy nguồn danh mục còn thiếu mới dùng `--download-sources`; đây là tra tên venue, không tìm bài hoặc lần ngược arXiv.

Hiện chưa chia train/dev/test, xây profile hoặc thêm rank; chỉ dùng bài train để xây profile khi bước thực nghiệm được triển khai.
