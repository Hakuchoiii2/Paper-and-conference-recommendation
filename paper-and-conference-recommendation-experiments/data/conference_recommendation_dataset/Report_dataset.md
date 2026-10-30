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

## Lưu ý khi chọn cách dựng dataset

- **Cách 2 — enrichment:** có thể dùng khi nối đúng bài/phiên bản, xác minh venue/track và đánh giá riêng nhãn bổ sung; chưa nên dùng nguyên bản 2 làm nhãn chuẩn vì rule cũ chưa hợp nhất các sửa mới và chưa có kiểm định độc lập. Luồng hiện tại là DOI gốc hoặc CorpusId → DOI → Crossref, chưa tra trực tiếp arXiv ID.
- DOI của preprint arXiv không chứng minh đã xuất bản ở conference; phải phân biệt với DOI bản xuất bản và giữ chứng cứ nguồn. Xem [hướng dẫn DOI arXiv](https://info.arxiv.org/help/doi.html).
- **Cách 3 — kiểm tra mapping:** đủ làm baseline thử nghiệm ban đầu, chưa đủ tuyên bố toàn bộ nhãn đã đúng; phần tên mở rộng ở bản 4 cũng cần đánh giá. Để chốt tập thực nghiệm cần chọn hội nghị đủ dữ liệu, kiểm tra mẫu độc lập, xử lý trùng/phiên bản và chốt split; profile chỉ dùng train.
- Không cần ép giải quyết hết unresolved: có thể chốt một tập con đủ căn cứ và báo rõ phần loại/thiếu. Chi tiết điều kiện dùng enrichment và kiểm định ở [restriction.md](E:/08_Project/Paper-and-conference-recommendation/paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/restriction.md).

## Tái lập

Giữ bộ raw, corpus chung, bảng mapping và hồ sơ metadata/đối chiếu nguồn đi kèm. Chạy tại thư mục chứa báo cáo; mặc định không truy cập mạng và không dùng kết quả của các thư mục thử nghiệm cũ:

```powershell
python 1_raw_mapping/preprocess_cube.py
python run_pipeline.py --audit
python run_pipeline.py --check --check-isolated
```

Báo cáo này được lệnh chung tạo lại từ output thực tế. Có kiểm tra nguồn/ID, năm, tổng đếm, nhãn, hash và khả năng tái lập. Bản 3 dùng làm baseline đã sửa theo nguồn; chưa phải nhãn được người chấm độc lập xác nhận toàn bộ, chưa đo precision/recall nhãn.

## Phân bố số bài theo hội nghị — tập 4

Chỉ đếm paper_id duy nhất có mapping_status=matched; mỗi ID hội nghị/joint được tính là một nhóm.

Danh sách đầy đủ tên hội nghị và số bài, sắp giảm dần: [conference_statistics.csv](E:/08_Project/Paper-and-conference-recommendation/paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/4_catalog_mapping/output/conference_statistics.csv).

Tập 4 có **171 hội nghị/joint**, **1,144 bài conference**; mỗi hội nghị có **1–176 bài**.

| Số bài/hội nghị | Số hội nghị/joint | Tổng số bài |
|---|---:|---:|
| 1–4 | 130 | 204 |
| 5–9 | 20 | 136 |
| 10–19 | 11 | 153 |
| 20–49 | 6 | 186 |
| 50–99 | 2 | 141 |
| Từ 100 | 2 | 324 |
| **Tổng** | **171** | **1,144** |

Có **21 hội nghị từ 10 bài trở lên**, tương ứng **804 bài**; đây là thống kê mô tả, chưa áp ngưỡng chọn hội nghị thực nghiệm.

Chạy riêng phần thống kê và cập nhật báo cáo: `python run_pipeline.py --stats-only`.
