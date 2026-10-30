# Tổng hợp dataset cho Conference Recommendation

Phạm vi: chỉ CSFCube, dùng title + abstract để gợi ý hội nghị. Chưa bổ sung rank, chia train/dev/test hoặc xây profile hội nghị.

## Cách tạo các phiên bản

Dùng phần CSFCube đã tiền xử lý chung: làm sạch văn bản, gộp trùng và giữ ID. Nối từng bài về các bản ghi raw bằng source ID; giữ nguyên văn bản và thông tin nguồn.

1. **1_raw_mapping:** đọc venue có sẵn, chuẩn hóa/mapping tên hội nghị; tách journal/workshop/ấn phẩm phụ và các bài chưa rõ.
2. **2_mapping_enriched:** mở rộng alias, nối metadata theo DOI hoặc CorpusId → DOI; đối chiếu title và tác giả khi có, rồi xét lại venue. Trường hợp mâu thuẫn hoặc không đủ căn cứ được giữ chưa rõ.
3. **3_mapping_reviewed:** kế thừa bản 1, đối chiếu 223 alias và mẫu 169 bài với nguồn; sửa hai quy tắc tên và ba trường hợp cụ thể. Chưa hợp nhất enrichment của bản 2.
4. **4_catalog_mapping:** kế thừa bản 3, mở rộng tên venue raw bằng danh mục ICORE, ACL Anthology và tên journal Crossref khớp đầy đủ; không tìm thêm bài hoặc lần ngược arXiv.

## Thống kê

| Tập dữ liệu | Tổng bản ghi/bài | Conference | Ngoài đích | Chưa rõ | Hội nghị/joint | Có năm raw chốt được |
|---|---:|---:|---:|---:|---:|---:|
| Raw CSFCube | 4,207 | — | — | — | — | 4,204 |
| 1_raw_mapping | 4,182 | 884 | 809 | 2,489 | 34 | 4,173 |
| 2_mapping_enriched | 4,182 | 1,150 | 985 | 2,047 | 74 | 4,173 |
| 3_mapping_reviewed | 4,182 | 882 | 810 | 2,490 | 36 | 4,173 |
| 4_catalog_mapping | 4,182 | 1,144 | 1,083 | 1,955 | 171 | 4,173 |

Raw đếm bản ghi nguồn; các bản xử lý đếm bài sau gộp trùng (25 bản ghi dư). Dấu — nghĩa là chưa áp quy tắc phân loại trên raw, không phải số lượng bằng 0.

Năm được nối trực tiếp từ `metadata.year` của mọi alias raw thành `year` (số nguyên 1000–2100). Raw có 2 bản ghi thiếu năm và 1 giá trị không hợp lệ. Sau gộp, mỗi bản có 4,173 bài chốt được năm, 2 bài thiếu và 7 bài có các năm nguồn mâu thuẫn; hai nhóm cuối để `year=null`. Các năm khác nhau được giữ trong `year_candidates` và thông tin nguồn trong `evidence`.

Bài conference chốt được năm: bản 1: 883/884; bản 2: 1149/1150; bản 3: 881/882; bản 4: 1143/1144.

`year` là năm từ dataset gốc, không mặc định là năm tổ chức hội nghị. `publication_year` là trường riêng cho năm được metadata xuất bản ủng hộ; bước nối raw không ghi đè trường này. Nhãn hội nghị không thay đổi khi nối năm.

## Tái lập

Giữ bộ raw, corpus chung, bảng mapping và hồ sơ metadata/đối chiếu nguồn đi kèm. Chạy tại thư mục chứa báo cáo; mặc định không truy cập mạng và không dùng kết quả của các thư mục thử nghiệm cũ:

```powershell
python 1_raw_mapping/preprocess_cube.py
python run_pipeline.py --audit
python run_pipeline.py --check --check-isolated
```

Báo cáo này được lệnh chung tạo lại từ output thực tế. Có kiểm tra nguồn/ID, năm, tổng đếm, nhãn, hash và khả năng tái lập. Bản 3 dùng làm baseline đã sửa theo nguồn; chưa phải nhãn được người chấm độc lập xác nhận toàn bộ, chưa đo precision/recall nhãn.
