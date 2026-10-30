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

## Mở rộng dữ liệu và kiểm định

Ưu tiên tên/alias rõ từ nguồn đã có, rồi tra đúng DOI/ID cho nhóm cần thiết. Chưa có bước tra arXiv trong luồng hiện tại; có thể bổ sung tra đúng arXiv ID → DOI/journal reference → kiểm tra bản xuất bản. Thiếu thông tin xuất bản trên arXiv chưa đủ kết luận bài chưa công bố.

LLM có thể hỗ trợ tìm ứng viên hoặc đọc nguồn khó; không lấy tên hội nghị do LLM tự trả lời làm nhãn. Quyết định cuối cần nguồn đúng bài, đúng phiên bản và đúng track, có thể đối chiếu lại.

Trước khi chốt benchmark: chọn hội nghị đủ dữ liệu → kiểm tra mẫu độc lập theo hội nghị/nguồn nhãn → sửa và hợp nhất các thay đổi có căn cứ → chia tập và xây profile từ train. Tách mẫu ngẫu nhiên khỏi ca rủi ro chọn có chủ đích; nếu đo recall/F1 nhãn cần đánh giá cả bài bị loại/chưa rõ, không chỉ nhóm matched.

Báo cáo đối chiếu chi tiết nằm trong review của từng thư mục; kết quả đối chiếu nguồn có AI hỗ trợ chưa phải đánh giá độc lập bởi người chấm.
