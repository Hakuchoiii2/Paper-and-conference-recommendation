# Làm rõ quy tắc sau pilot — bản để đối chiếu

Không thay policy/hash của hai lượt trích đã khóa. Các điểm này cần đi vào
phiên bản quy tắc kế tiếp và được thử trên nguồn train/dev chưa dùng trước khi
mở rộng. Không phải chứng nhận cả cohort đã ổn định.

## Method trong survey, so sánh và bài trình bày phương pháp

- Survey: giữ thao tác thực sự làm như review, synthesis, taxonomy hoặc phân
  tích tiêu chí. Không đưa mọi mô hình được nhắc/giới thiệu trong tổng quan vào
  method như thể tác giả đã chạy chúng. P003879 là trường hợp này.
- So sánh thực nghiệm là mục tiêu: các kỹ thuật được tác giả thực sự chạy/đánh
  giá được ghi method, kể cả khi chỉ dùng để so sánh. P001860 có đo performance
  trên benchmark nên khác việc chỉ liệt kê phương pháp trong survey.
- Bài trình bày/demonstration: có thể giữ thủ tục được tác giả trình bày bằng
  ví dụ/cách vận hành cụ thể. Ghi vai trò `methodological_demonstration` trong
  audit; không mô tả như đã triển khai một thử nghiệm thực địa.
- Mục tiêu “discuss/demonstrate” một mình chưa chứng minh đã làm. Với P002633,
  cần đối chiếu A0 cùng A7/A10 về review/personal examples/practical examples;
  `may choose a reflexive diary` ở A11 vẫn là khuyến nghị, không phải method
  đã dùng. Khi chỉ có thảo luận đề tài, giữ procedure review thực sự được nêu.

## Dataset và resource có cấu trúc

Ontology/knowledge graph có tên là resource khi nguồn trình bày một tài nguyên
tri thức có cấu trúc và nói rõ việc dùng hoặc giới thiệu nó. P004130 giới thiệu
Klout Topics như ontology; không suy từ số người dùng ra một dataset có tên.
Một khung khái niệm, software/platform hoặc chủ đề ontology đơn thuần chưa đủ.

Availability/link đơn thuần không tự chứng minh resource được dùng hoặc do tác
giả giới thiệu. Nếu title/abstract không hỗ trợ vai trò ấy, để [] và ghi thiếu
thông tin ở audit. Full text xác nhận thực tế sử dụng có thể giải thích nguồn,
nhưng không bổ sung một quan hệ chỉ có ngoài input vào nhãn trích từ abstract.
Quy tắc này áp dụng cùng nhau cho mọi nhóm nguồn, không chọn theo điểm mô hình.

## Finding và đồng tham chiếu

Thêm câu antecedent vào evidence_ids khi chủ thể/đối tượng/điều kiện của finding
nằm ở đó. Nhãn cuối cần tự rõ nghĩa; việc thêm nhiều ID không tự sửa một nhãn
vẫn chỉ ghi “these quantities/these techniques/the same pattern”.

Giữ bằng chứng cho mức khẳng định (`suggests`, `may`, `tend`) và phạm vi của
thí nghiệm. Phân biệt nguồn kết luận trong speech experiment với khả năng dùng
framework trong mọi ứng dụng. Một kết quả corroboration trong event data có
điều kiện riêng nên không mất đi chỉ vì đã giữ finding chung.

Nếu nguồn đầu vào nêu một tỷ lệ nhưng không xác định comparator/denominator,
không đoán từ full text hoặc hiểu thành accuracy tuyệt đối. Giữ nguyên câu
ở audit, đánh dấu finding chưa đủ thông tin và chỉ giữ kết luận khác đã rõ.
Đây là tiêu chí cần kiểm tra ở phát biểu 97% của P003168.
