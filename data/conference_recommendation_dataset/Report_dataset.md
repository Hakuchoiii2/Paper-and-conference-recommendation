# Tổng hợp dataset cho Conference Recommendation

Phạm vi: chỉ CSFCube, dùng title + abstract để gợi ý hội nghị. Bản 5 đã review mapping và chia train/test theo năm raw; chưa tạo dev, bổ sung rank hoặc xây profile hội nghị.

## Cách tạo các phiên bản

Dùng phần CSFCube đã tiền xử lý chung: làm sạch văn bản, gộp trùng và giữ ID. Nối từng bài về các bản ghi raw bằng source ID; giữ nguyên văn bản và thông tin nguồn.

1. **1_raw_mapping:** đọc venue có sẵn, chuẩn hóa/mapping tên hội nghị; tách journal/workshop/ấn phẩm phụ và các bài chưa rõ.
2. **2_mapping_enriched:** mở rộng alias, nối metadata theo DOI hoặc CorpusId → DOI; đối chiếu title và tác giả khi có, rồi xét lại venue. Trường hợp mâu thuẫn hoặc không đủ căn cứ được giữ chưa rõ.
3. **3_mapping_reviewed:** kế thừa bản 1, đối chiếu 223 alias và mẫu 169 bài với nguồn; sửa hai quy tắc tên và ba trường hợp cụ thể. Chưa hợp nhất enrichment của bản 2.
4. **4_catalog_mapping:** kế thừa bản 3, mở rộng tên venue raw bằng danh mục ICORE, ACL Anthology và tên journal Crossref khớp đầy đủ; không tìm thêm bài hoặc lần ngược arXiv.
5. **5_mapping_reviewed:** review toàn bộ 1.144 bài matched và 446 alias matched của bản 4: đọc venue/journal raw, đối chiếu danh tính bài và venue/track với nguồn; AI xét các trường hợp cần phân xử. Sửa 26 ID joint, chuyển 36 bài ngoài đích và 18 bài chưa đủ căn cứ; giữ 1.090 matched. Không mở rộng tập mapping, không đổi năm/văn bản raw. Chi tiết: [phương pháp review bản 5](5_mapping_reviewed/METHOD_REVIEW_V5.md).

## Thống kê

| Tập dữ liệu | Tổng bản ghi/bài | Conference | Ngoài đích | Chưa rõ | Hội nghị/joint | Có năm raw chốt được |
|---|---:|---:|---:|---:|---:|---:|
| Raw CSFCube | 4,207 | — | — | — | — | 4,204 |
| 1_raw_mapping | 4,182 | 884 | 809 | 2,489 | 34 | 4,173 |
| 2_mapping_enriched | 4,182 | 1,150 | 985 | 2,047 | 74 | 4,173 |
| 3_mapping_reviewed | 4,182 | 882 | 810 | 2,490 | 36 | 4,173 |
| 4_catalog_mapping | 4,182 | 1,144 | 1,083 | 1,955 | 171 | 4,173 |
| 5_mapping_reviewed | 4,182 | 1,090 | 1,119 | 1,973 | 163 | 4,173 |

Raw đếm bản ghi nguồn; các bản xử lý đếm bài sau gộp trùng (25 bản ghi dư). Dấu — nghĩa là chưa áp quy tắc phân loại trên raw, không phải số lượng bằng 0.

Năm được nối trực tiếp từ `metadata.year` của mọi alias raw thành `year` (số nguyên 1000–2100). Raw có 2 bản ghi thiếu năm và 1 giá trị không hợp lệ. Sau gộp, mỗi bản có 4,173 bài chốt được năm, 2 bài thiếu và 7 bài có các năm nguồn mâu thuẫn; hai nhóm cuối để `year=null`. Các năm khác nhau được giữ trong `year_candidates` và thông tin nguồn trong `evidence`.

Bài conference chốt được năm: bản 1: 883/884; bản 2: 1149/1150; bản 3: 881/882; bản 4: 1143/1144; bản 5: 1089/1090.

`year` là năm từ dataset gốc, không mặc định là năm tổ chức hội nghị. `publication_year` là trường riêng cho năm được metadata xuất bản ủng hộ; bước nối raw không ghi đè trường này. Nhãn hội nghị không thay đổi khi nối năm.

## Lưu ý khi chọn cách dựng dataset

- **Cách 2 — enrichment:** có thể dùng khi nối đúng bài/phiên bản, xác minh venue/track và đánh giá riêng nhãn bổ sung; chưa nên dùng nguyên bản 2 làm nhãn chuẩn vì rule cũ chưa hợp nhất các sửa mới và chưa có kiểm định độc lập. Luồng hiện tại là DOI gốc hoặc CorpusId → DOI → Crossref, chưa tra trực tiếp arXiv ID.
- DOI của preprint arXiv không chứng minh đã xuất bản ở conference; phải phân biệt với DOI bản xuất bản và giữ chứng cứ nguồn. Xem [hướng dẫn DOI arXiv](https://info.arxiv.org/help/doi.html).
- **Bản 5 — tập thực nghiệm:** đã rà soát toàn bộ matched của bản 4, giữ chứng cứ và tách các ca chưa chắc chắn; đủ dùng tiếp cho thực nghiệm và mô tả phương pháp trong bài báo. Đây là nhãn đối chiếu nguồn kết hợp AI review, chưa phải gold do người chấm độc lập xác nhận; chưa đo precision/recall nhãn. Profile chỉ dùng train.
- Không cần ép giải quyết hết unresolved: có thể chốt một tập con đủ căn cứ và báo rõ phần loại/thiếu. Chi tiết điều kiện dùng enrichment và kiểm định ở [restriction.md](E:/08_Project/Paper-and-conference-recommendation/paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/restriction.md).

## Tái lập

Giữ bộ raw, corpus chung, bảng mapping và hồ sơ metadata/đối chiếu nguồn đi kèm. Chạy tại thư mục chứa báo cáo; mặc định không truy cập mạng và không dùng kết quả của các thư mục thử nghiệm cũ:

```powershell
python 1_raw_mapping/preprocess_cube.py
python run_pipeline.py --audit
python run_pipeline.py --check --check-isolated
python 5_mapping_reviewed/review_mapping.py --check
python 5_mapping_reviewed/split_temporal.py --check
```

Báo cáo tạo lại từ output thực tế; các lệnh kiểm tra bản 5 xác nhận hồ sơ review, hash và split tái lập được. Kết quả kiểm tra kỹ thuật không thay thế đánh giá độ chính xác nhãn độc lập.

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

## Phân bố số bài theo hội nghị — tập 5

Chỉ đếm bài `matched`, mỗi `paper_id` một lần và mỗi ID hội nghị/joint một nhóm: **163 hội nghị/joint, 1,090 bài**, từ **1–153 bài/nhóm**. Chi tiết từng hội nghị: [conference_statistics.csv](5_mapping_reviewed/output/conference_statistics.csv).

| Số bài/hội nghị | Số hội nghị/joint | Tổng số bài |
|---|---:|---:|
| 1–4 | 123 | 187 |
| 5–9 | 18 | 118 |
| 10–19 | 11 | 149 |
| 20–49 | 7 | 212 |
| 50–99 | 2 | 137 |
| Từ 100 | 2 | 287 |
| **Tổng** | **163** | **1,090** |

Ngưỡng **n ≥ 5** cho **40 hội nghị, 903 bài** (82.8% số bài matched); đây là tập ứng viên trước khi lọc năm và kiểm tra tối thiểu train/test.

### Chia train/test của tập 5

Chỉ dùng `matched` đã review, lấy năm từ `raw.metadata.year`: **train ≤ 2015**, **test 2016–2019**. Hội nghị phải có tổng ≥ 5 bài matched và ít nhất **3 train + 1 test**; không đủ thì loại cả hội nghị. Bỏ bài thiếu/mâu thuẫn năm hoặc ngoài khoảng năm; không chia ngẫu nhiên, không bổ sung năm từ web.

| Phần dữ liệu | Số hội nghị | Số bài |
|---|---:|---:|
| Train | 30 | 602 |
| Test | 30 | 186 |
| **Tổng, cùng tập hội nghị** | **30** | **788** |

Còn 302 bài matched không vào split. Chi tiết số train/test từng hội nghị: [conference_split_statistics.csv](5_mapping_reviewed/splits/temporal_2015_2016_2019/conference_split_statistics.csv). Dữ liệu nằm trong `5_mapping_reviewed/splits/temporal_2015_2016_2019/`; chỉ dùng train xây profile K-Medoids, test để đánh giá. Chưa tạo dev.
