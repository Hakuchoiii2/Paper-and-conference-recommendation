# Hạn chế và việc cần làm tiếp

Đã có đối chiếu tên/mẫu bằng nguồn và kiểm tra tái lập; chưa có bộ nhãn được người chấm độc lập xác nhận toàn bộ hoặc phép đo precision/recall nhãn. Số lượng và khác biệt giữa các bản xem [Report_dataset.md](E:/08_Project/Paper-and-conference-recommendation/paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/Report_dataset.md).

## Hiểu đúng trạng thái

- **matched:** quy tắc đã nhận diện hội nghị; không mặc định nhãn từng bài đều đúng.
- **excluded:** đã nhận diện loại ngoài đích, như journal/workshop/ấn phẩm phụ.
- **unresolved:** chưa đủ căn cứ chốt nhãn hoặc loại ngoài đích; có thể do thiếu venue, chỉ có preprint, tên chưa ánh xạ được, định danh không khớp hoặc nguồn mâu thuẫn.

`unknown` là giá trị của venue_type, còn unresolved là mapping_status; chúng không phải một khái niệm. Unresolved không phải nhãn âm “bài không thuộc hội nghị” và không nên dùng như một hội nghị riêng.

## Hạn chế theo công đoạn

| Công đoạn | Giới hạn và cách xử lý |
|---|---|
| Gộp trùng chung | Kế thừa quyết định sẵn có; các bài cùng title nhưng khác abstract vẫn cần xem riêng khi ảnh hưởng tập thực nghiệm |
| Mapping tên | Danh mục ngoài giúp tăng độ phủ nhưng chưa bao hết mọi venue; tên đúng chưa chứng minh bài thuộc main, cần kiểm tra volume/track, joint và tên dễ nhầm |
| Metadata theo định danh | Có thể thiếu hoặc trỏ khác bài/phiên bản; kiểm tra title, tác giả và nguồn xuất bản, giữ mâu thuẫn ở unresolved |
| Năm | Năm raw có thể là năm preprint; thiếu/mâu thuẫn giữ null, không suy năm tổ chức từ năm đăng bài |
| Độ phủ và cân đối | Hội nghị ít bài khó chia tập; ưu tiên chốt catalog khả thi và báo rõ phần bị loại/chưa rõ |
| Đánh giá recommendation | Chưa chia tập hoặc xây profile; tránh bài trùng qua các tập và không dùng dev/test để xây profile |
| Kiểm tra kỹ thuật | Hash, ID và dựng lại chứng minh tính nhất quán/tái lập, không chứng minh độ chính xác học thuật của toàn bộ nhãn |
| Rank | Tùy mục tiêu thực nghiệm; nếu bổ sung cần nguồn và phiên bản, không thay thế độ phù hợp nội dung |

## Cách 2: vì sao chưa nên dùng nguyên trạng để chốt dataset?

Enrichment theo định danh là cách có thể dùng trong nghiên cứu khi có chứng cứ và đánh giá chất lượng, không phải phương pháp mặc nhiên không hợp lệ. Bản 2 hiện nối DOI gốc hoặc CorpusId → DOI → Crossref; chưa tra trực tiếp arXiv ID. Nếu sau này thêm arXiv ID → DOI/journal reference thì đó là bước mở rộng riêng.

Chưa nên lấy nguyên bản 2 làm nhãn chuẩn: còn các rule cũ chưa hợp nhất sửa từ bản 3/4, chưa kiểm định độc lập toàn bộ phần enrichment, và việc khớp định danh/tên vẫn có thể sai bài hoặc sai phiên bản. Metadata dễ truy xuất cũng tạo thiên lệch về độ phủ; số bài tăng không tự chứng minh nhãn tốt hơn.

Khi dùng cách này cần:

- **Phân biệt DOI preprint với DOI bản xuất bản.** DOI của arXiv định danh bản arXiv, không chứng minh đã xuất bản ở conference; DOI/journal reference bên ngoài là thông tin riêng. Thiếu các trường bên ngoài chưa đủ kết luận chưa công bố. [DOI arXiv](https://info.arxiv.org/help/doi.html), [tham chiếu xuất bản](https://info.arxiv.org/help/jref.html).
- **Kiểm tra đúng bài và phiên bản:** đối chiếu title, tác giả, định danh và nguồn nhà xuất bản/ACL; title gần giống hoặc một DOI tìm được chưa đủ. Bản 2 có thể nhận DOI gốc khi thiếu authors và title đủ điều kiện; cần giữ dấu thiếu tác giả, ưu tiên kiểm tra nhóm này.
- **Chốt đúng venue/track:** phân biệt main, workshop, journal và joint; tên bộ sách/proceedings chung chưa xác định được conference. Nhiều bản công bố mâu thuẫn tiếp tục unresolved, không chọn nhãn chỉ để tăng số bài.
- **Giữ bằng chứng và chống rò rỉ:** lưu nguồn, thời điểm, phiên bản, nhãn trước/sau; nhận diện các phiên bản cùng bài trước khi chia tập. Venue dùng làm nhãn đánh giá không được đưa vào đầu vào của query; profile chỉ dùng train.
- **Đánh giá riêng phần bổ sung:** lấy mẫu độc lập theo hội nghị/nguồn nhãn; không sao chép toàn bộ nhãn bản 2 sang bản 4. LLM chỉ hỗ trợ tìm ứng viên hoặc đọc nguồn, không tự quyết định nhãn nơi công bố.

## Cách 3: kiểm tra mapping đã đủ hoàn tất data chưa?

Kiểm tra tên và mẫu ở bản 3 đã giúp sửa lỗi, đủ làm baseline cho thử nghiệm ban đầu; chưa chứng minh mọi bài thuộc đúng main conference. Bản 4 mở rộng tên cũng cần đánh giá phần mới, không tự kế thừa chất lượng của mẫu đã xét ở bản 3.

### Kiểm định mapping ở hai mức

1. **Tên venue → hội nghị:** review các alias tạo nhãn trong tập hội nghị định dùng; kiểm tra viết tắt, đổi tên theo năm, joint và workshop/host.
2. **Bài → đúng hội nghị, đúng track:** lấy mẫu bài, mở trang bài/proceedings chính thức để đối chiếu title, tác giả và main/workshop; tên trong danh mục chưa đủ cho mức này.

Quy trình đánh giá đề xuất, chưa phải kết quả kiểm định đã hoàn tất cho phần mở rộng bản 4:

- Chọn mẫu ngẫu nhiên theo hội nghị và nguồn nhãn **cũ/mở rộng**, lưu seed; tách riêng các ca khó được chọn có chủ đích.
- Có người kiểm tra độc lập, ghi **đúng / sai / chưa xác minh được**, kèm URL chứng cứ; dùng mẫu mới chưa được dùng để sửa rule.
- Báo **độ đúng ở mức alias và mức bài**, cỡ mẫu, tỷ lệ chưa xác minh và khoảng tin cậy; nếu lấy mẫu không đều thì tính trọng số phù hợp.
- Muốn đo **recall/F1**, phải kiểm tra thêm cả bài bị loại và unresolved; chỉ kiểm tra nhóm matched chưa đủ.

### Chốt tập thực nghiệm

Trước khi chốt tập thực nghiệm cần:

1. Chọn hội nghị đủ bài cho thiết kế chia tập; thống nhất chính sách main/short/joint và loại ngoài đích.
2. Hoàn thành kiểm định hai mức theo quy trình trên cho phạm vi đã chọn; không bắt buộc đọc tay mọi bài.
3. Xử lý trùng và các phiên bản cùng bài qua các tập; chốt năm khi dùng split theo thời gian, giữ dev/test độc lập và xây profile từ train.
4. Đóng băng catalog, nhãn, split, code và bằng chứng để chạy lại được; kiểm tra kỹ thuật đã có không thay thế đánh giá độ đúng của nhãn.

**Không cần giải quyết hết unresolved mới được chốt một tập con thực nghiệm.** Có thể chọn tập có căn cứ đủ tốt, nêu rõ tiêu chí chọn/loại và độ phủ; không gán phần còn thiếu thành conference hoặc nhãn âm. Chi tiết đối chiếu nguồn nằm trong review của từng thư mục; hiện chưa có bộ nhãn độc lập để tuyên bố benchmark đã hoàn thiện.
