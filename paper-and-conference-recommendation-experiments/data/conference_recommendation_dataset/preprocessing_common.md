# Tiền xử lý chung được kế thừa

Nhánh hội nghị chỉ đọc phần CSFCube từ corpus chung tại `data/processed`, nối về `data/raw/csfcube`; không chạy lại bước xây corpus.

| Phần đã có | Cách sử dụng |
|---|---|
| Title/abstract sạch, abstract đã nối câu | giữ nguyên văn bản |
| Gộp trùng và paper_id | giữ ID và kết quả gộp, không gộp lại chỉ theo title |
| id_map với alias active | nối mọi bản ghi raw về đúng bài |
| Định danh nguồn và metadata gốc | dùng để mapping, đối chiếu và truy vết |

Tiền xử lý chung gộp 4.207 bản ghi thành 4.182 bài CSFCube; còn 5 trường hợp cùng title nhưng khác abstract được giữ riêng để review.

Phần riêng của nhánh hội nghị là chuẩn hóa venue, tách main/joint/workshop/journal, tổng hợp năm từ mọi alias raw và nhóm bài theo hội nghị. Năm tổng hợp có thể khác năm của bản ghi canonical; corpus chung được giữ nguyên. Split nguồn chưa được dùng làm split hội nghị; facet chưa được bổ sung trong bước này.

Chi tiết nguồn: [README corpus chung](E:/08_Project/Paper-and-conference-recommendation/paper-and-conference-recommendation-experiments/data/processed/README.md) và [code xây corpus](E:/08_Project/Paper-and-conference-recommendation/paper-and-conference-recommendation-experiments/scripts/build_corpus.py). Quy trình và số lượng hiện tại xem [Report_dataset.md](E:/08_Project/Paper-and-conference-recommendation/paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/Report_dataset.md).
