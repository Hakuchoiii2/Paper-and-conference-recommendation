# Danh sách bài báo tham khảo sát đề tài DS300

Ngày tra cứu: 2026-10-23. Phạm vi: khuyến nghị bài báo và hội nghị theo problem, task, method, dataset, contribution; profile dài hạn và ý định theo phiên.

Đây là danh sách đọc có chọn lọc dựa trên nguồn công bố chính thức và abstract/phần công khai, chưa phải systematic review hoặc tái lập thực nghiệm. Phần áp dụng là đề xuất cho nhóm, không phải kết luận của tác giả. Không có giả định rằng các bài dùng đúng hệ năm facet của nhóm.

## 1. ASPIRE — nền tảng biểu diễn và matching theo facet

- Sheshera Mysore và cộng sự. **Multi-Vector Models with Textual Guidance for Fine-Grained Scientific Document Similarity**. NAACL 2022.
- [Bài gốc và PDF](https://aclanthology.org/2022.naacl-main.331/).
- NAACL: **A**, CORE2023 và ICORE2026: [hồ sơ chính thức](https://portal.core.edu.au/conf-ranks/1648/).
- Học biểu diễn nhiều vector, tận dụng câu đồng trích dẫn để học các khía cạnh liên quan giữa bài báo.
- Áp dụng: đối chứng semantic cho B; tham khảo cách matching theo khía cạnh thay vì chỉ cosine của một vector toàn bài.
- Giới hạn: không tự giải quyết profile thay đổi theo thời gian hoặc yêu cầu khác method.

## 2. LACE — profile concept có thể đọc và chỉnh sửa

- Sheshera Mysore, Mahmood Jasim, Andrew McCallum, Hamed Zamani. **Editable User Profiles for Controllable Text Recommendations**. SIGIR 2023, 993–1003.
- [DOI bản hội nghị](https://doi.org/10.1145/3539618.3591677); [bản tác giả miễn phí](https://arxiv.org/abs/2304.04250); [chương trình hội nghị](https://sigir.org/sigir2023/wp-content/uploads/2023/07/Technical-Program-1.pdf).
- SIGIR: **A***, CORE2023 và ICORE2026: [hồ sơ chính thức](https://portal.core.edu.au/conf-ranks/29/).
- Profile gồm concept dễ đọc, với biểu diễn cá nhân hóa học từ tài liệu người dùng đã tương tác; hỗ trợ điều chỉnh khuyến nghị qua chỉnh profile.
- Áp dụng: C về profile, D về điều khiển nhu cầu. Nên đọc sớm để phân biệt đóng góp của nhóm với tiền lệ concept profile.
- Giới hạn: controllability không đồng nghĩa đã suy được hướng similar/different hoặc xử lý temporal drift như mục tiêu của nhóm.

## 3. FaBle — dữ liệu huấn luyện theo facet bằng LLM

- Heejin Do, Sangwon Ryu, Jonghwi Kim, Gary Lee. **Multi-Facet Blending for Faceted Query-by-Example Retrieval**. ACL 2025, 28577–28590.
- [Bài gốc và PDF](https://aclanthology.org/2025.acl-long.1388/).
- ACL: **A***, CORE2023 và ICORE2026: [hồ sơ chính thức](https://portal.core.edu.au/conf-ranks/196/).
- Tách tài liệu thành các đơn vị facet, sinh cặp liên quan/không liên quan bằng LLM, rồi tổ hợp lại thành dữ liệu huấn luyện phù hợp từng facet.
- Áp dụng: A/B và thiết kế training pairs cho D; đặc biệt hữu ích khi nhóm có ít relevance labels.
- Giới hạn: nhãn tổng hợp phục vụ huấn luyện không thay thế đánh giá độc lập bằng người; facet của bài không mặc định trùng năm facet của nhóm.

## 4. mCTRL — khuyến nghị paper có thể điều khiển theo aspect

- Kehan Long, Shasha Li, Jintao Tang, Ting Wang. **Leveraging multiple control codes for aspect-controllable related paper recommendation**. Information Processing & Management 62, 103879, 2025.
- [DOI](https://doi.org/10.1016/j.ipm.2024.103879); [abstract và phần phương pháp công khai của nhà xuất bản](https://www.sciencedirect.com/science/article/abs/pii/S0306457324002383).
- Dùng control codes để học đồng thời biểu diễn toàn bài và nhiều aspect; hierarchical loss liên kết hai mức.
- Áp dụng: B và D; đây là đối chiếu trực tiếp khi trình bày vì sao cần biểu diễn đa facet.
- Tạp chí **Q1 theo SJR 2024, Library and Information Sciences**: [bảng SCImago](https://www.scimagojr.com/journalrank.php?category=3309&ord=desc&order=h&page=1&total_size=70). Kết quả tìm kiếm nguồn này hiển thị Q1; mở trực tiếp bị chặn. [Bảng trường Comillas](https://www.iit.comillas.edu/publicacion/info_revista/es/659/Information_Processing_%26_Management) đối chiếu Q1 năm 2024. Không ghi đây là đã đăng nhập kiểm chứng JCR.
- Chưa đọc đủ toàn văn do giới hạn truy cập.

## 5. HASVRec — nhánh khuyến nghị hội nghị/tạp chí

- Tribikram Pradhan, Abhinav Gupta, Sukomal Pal. **HASVRec: A modularized Hierarchical Attention-based Scholarly Venue Recommender system**. Knowledge-Based Systems 204, 106181, 2020.
- [DOI](https://doi.org/10.1016/j.knosys.2020.106181); [abstract nhà xuất bản](https://www.sciencedirect.com/science/article/abs/pii/S0950705120304135).
- Kết hợp Bi-LSTM và hierarchical attention; dùng title, abstract, keywords, field of study, tác giả và lịch sử công bố để khuyến nghị scholarly venues. Đánh giá trên DBLP-Citation-Network V11.
- Áp dụng: C4; tham khảo cách định nghĩa đầu vào, danh sách venue và đánh giá ranking.
- Knowledge-Based Systems: **Q1 theo thông tin Scopus 2024, Artificial Intelligence**, [thư viện Wageningen](https://library.wur.nl/WebQuery/utbrowser?issn=1872-7409). Nguồn trực tiếp SCImago bị 403 nên trạng thái Q1 được đối chiếu qua thư viện đại học; không đánh đồng CiteScore quartile với SJR quartile.
- Giới hạn: không phải mô hình năm facet. Nhãn venue đã xuất bản cũng không cho biết mọi venue phù hợp khác; không suy thành khả năng được nhận bài.
- Chưa đọc đủ toàn văn do giới hạn truy cập.

## 6. SciRepEval / SPECTER2 — đối chứng scientific embeddings

- Amanpreet Singh, Mike D’Arcy, Arman Cohan, Doug Downey, Sergey Feldman. **SciRepEval: A Multi-Format Benchmark for Scientific Document Representations**. EMNLP 2023, 5548–5566.
- [Bài gốc và PDF](https://aclanthology.org/2023.emnlp-main.338/).
- EMNLP: **A***, CORE2023 và ICORE2026: [hồ sơ chính thức](https://portal.core.edu.au/conf-ranks/448/).
- Benchmark 24 tác vụ thuộc classification, regression, ranking và search; giới thiệu họ mô hình SPECTER2 với biểu diễn theo dạng tác vụ.
- Áp dụng: baseline B; đối chiếu embedding scientific toàn bài với biểu diễn năm facet của nhóm.
- Giới hạn: biểu diễn theo dạng tác vụ không phải năm facet nội dung nghiên cứu.

## 7. Profile ngôn ngữ tự nhiên — tham khảo bổ sung cho C

- Jerome Ramos, Hossein A. Rahmani, Xi Wang, Xiao Fu, Aldo Lipani. **Transparent and Scrutable Recommendations Using Natural Language User Profiles**. ACL 2024, 13971–13984.
- [Bài gốc và PDF](https://aclanthology.org/2024.acl-long.753/).
- ACL: **A***, theo các phiên bản CORE2023 và ICORE2026 nêu trên.
- Dùng LLM tổng hợp preferences từ reviews thành profile ngôn ngữ tự nhiên, đánh giá ảnh hưởng của chỉnh sửa profile tới khuyến nghị.
- Áp dụng: phương án biểu diễn/giải thích profile; độ sát miền khoa học thấp hơn LACE và ASPIRE.
- Không dùng bài này làm bằng chứng rằng temporal drift trong E đã được giải quyết.

## 8. Bài rất sát ba facet task/method/dataset — hạng hiện tại chưa xác nhận

- Malte Ostendorff, Till Blume, Terry Ruas, Bela Gipp, Georg Rehm. **Specialized Document Embeddings for Aspect-based Similarity of Research Papers**. JCDL 2022.
- [Nguồn viện nghiên cứu DFKI, kèm PDF](https://www.dfki.de/web/forschung/projekte-publikationen/publikation/12495); [DOI](https://doi.org/10.1145/3529372.3530912).
- Học các không gian embedding chuyên biệt theo task, method, dataset trên Papers with Code; đối chiếu biểu diễn generic và specialized.
- Áp dụng: B; đặc biệt hữu ích vì ba aspect trùng tên với ba facet của nhóm.
- Không gán A/A* hiện tại cho bài này. Portal có mục JCDL lịch sử CORE2018 A*, nhưng chưa xác minh hạng hiện tại và quan hệ tên bản ghi đủ chắc để đưa vào danh sách đạt bộ lọc chính.

## Gợi ý thứ tự đọc và viết related work

1. ASPIRE → Specialized Document Embeddings: hiểu cách so khớp và biểu diễn theo facet.
2. LACE: hiểu profile người dùng và điều khiển khuyến nghị.
3. mCTRL → FaBle: đối chiếu phương pháp đa aspect và tạo dữ liệu facet.
4. HASVRec: thiết kế nhánh conference riêng.
5. SciRepEval và profile ngôn ngữ tự nhiên: bổ sung baseline/giải thích.

Nhóm nên đối chiếu tính mới trực tiếp với ASPIRE, LACE, mCTRL, FaBle. Hạng A/A* là hạng venue theo phiên bản bảng; Q1 là hạng tạp chí theo năm/chuyên ngành/hệ đo, không phải điểm của riêng bài báo. Danh sách chưa có công trình chuyên biệt đủ sát về temporal drift trong scholarly recommendation đạt bộ lọc đã kiểm chứng; không coi phần E đã được bao phủ đầy đủ.
