# Phương pháp kiểm tra mapping hội nghị — bản 5

## Mục tiêu và phạm vi

Bản 5 kiểm tra chất lượng nhãn hội nghị đã được chốt ở bản 4, không mở rộng corpus hay tìm nơi công bố để nâng các bài chưa mapping thành matched. Giữ nguyên bản 4 làm đối chứng. Đơn vị kiểm tra là paper_id canonical sau gộp trùng, không phải số dòng raw.

Phạm vi gồm **toàn bộ 1.144 bài matched của bản 4 và 446 chuỗi tên venue tạo nhãn matched**. Lượt đầu dùng mẫu 242 bài được lưu riêng trong review/round1_sample_review; kết quả cuối bản 5 đã mở rộng sang toàn bộ nhóm matched. Các bài excluded/unresolved gốc của bản 4 giữ nguyên và nằm ngoài phạm vi kiểm định nhãn này.

## Quy trình thực hiện

1. **Nối về metadata gốc.** Dùng paper_id và source_ids để nối bài canonical về các bản ghi CSFCube tương ứng. Đọc đồng thời metadata.venue, metadata.journal, title, tác giả và định danh sẵn có của mọi alias raw. Trường journal có thể chứa tên proceedings, workshop hoặc ấn phẩm phụ, không chỉ tên tạp chí. Giữ nguyên title/abstract từ corpus chung.
2. **Rà soát tên venue.** Kiểm tra alias, viết tắt, tên dễ trùng, tên đổi theo thời gian, hội nghị joint và nhầm workshop với hội nghị chủ nhà. Tận dụng nguồn tên/danh mục và chứng cứ kế thừa từ các bản trước. Đối chiếu tên chỉ xác nhận series, không mặc nhiên xác nhận danh tính hoặc track của từng bài.
3. **Đối chiếu nguồn ở cấp bài cho toàn bộ 1.144 bài.** Ưu tiên ACL ID/DOI đã có trong raw để đọc ACL Anthology, Crossref và nguồn xuất bản. Đọc container-title và event.name khi có. Thiếu hoặc sai định danh thì tìm tiếp từ title, tác giả và tên proceedings trên publisher, chương trình hội nghị, DBLP hoặc kho chính thức của tác giả/tổ chức. URL và phản hồi nguồn, bao gồm lỗi truy cập, được giữ để truy vết.
4. **Kiểm tra danh tính.** Lượt tự động chuẩn hóa Unicode, dấu câu, khoảng trắng và các trường hợp title/subtitle trước khi so title. Khi có thông tin tác giả, kiểm tra sự trùng khớp họ tác giả; đây không phải phép xác minh toàn bộ đồng tác giả. DOI/ACL ID có sẵn không tự chứng minh đúng bài. Các trường hợp khác title, khác tác giả hoặc nhiều phiên bản được AI xem lại; có thể đối chiếu abstract để nhận diện đổi tiêu đề khi xuất bản. Không dùng một ngưỡng tương đồng lỏng để tự chốt mọi bài.
5. **Phân biệt loại công bố và track.** Giữ main conference, short paper/poster thuộc main khi có căn cứ. Tách workshop, system/software demonstration, tutorial, shared-task overview và abstract phụ đã xác nhận ngoài phạm vi main research. Không loại mọi paper có chữ poster, mọi ID bắt đầu W trong ACL Anthology hoặc mọi tên có chữ journal. Xét đúng ấn bản: một series có thể từng là workshop; TOG hoặc Procedia cũng có thể xuất bản proceedings/technical papers của hội nghị. Companion chưa rõ track không được tự coi là main.
6. **AI phân xử và sửa nhãn có nguồn.** Ghi lý do và URL cho từng quyết định đặc biệt. Nếu bài thuộc joint đã có ID trong catalog thì sửa sang ID joint; không gộp vào hội nghị thành phần. Joint chưa có ID riêng hoặc record trộn danh tính/phiên bản được giữ unresolved, không tạo thêm catalog trong lượt này.
7. **Chốt tập đủ căn cứ.** Chỉ giữ matched khi có đồng thuận metadata nguồn hoặc quyết định AI có chứng cứ. Bài còn mâu thuẫn hoặc chưa xác minh được được chuyển unresolved và để ngoài dữ liệu dùng thực nghiệm. Unresolved có nghĩa chưa chốt, không có nghĩa nhãn âm hoặc chắc chắn không thuộc hội nghị.
8. **Kiểm tra và đóng băng.** Kiểm tra ID duy nhất, nguồn/alias, nhóm conference, số lượng, hash đầu vào/đầu ra và dựng lại kết quả offline. So với bản 4 để xác nhận không thay năm, chứng cứ raw, paper_id, source_ids hoặc văn bản corpus; không thay các bài ngoài phạm vi review.

Chương trình đối chiếu metadata được áp dụng cho toàn bộ 1.144 bài; **188 bài có kết luận AI bổ sung** được lưu tường minh. Việc này không có nghĩa AI đã đọc toàn văn 1.144 bài. Không yêu cầu đọc PDF hàng loạt; chỉ dùng PDF/trang chương trình cho các trường hợp cần làm rõ.

## Kết quả cuối

| Kết quả đối với 1.144 bài matched đầu vào | Số bài |
|---|---:|
| Giữ matched, conference_id không đổi | 1.064 |
| Giữ matched, sửa sang ID joint đã có | 26 |
| Chuyển excluded do ngoài phạm vi đích | 36 |
| Chuyển unresolved do chưa đủ căn cứ | 18 |
| Tổng | 1.144 |

Như vậy có **1.090 bài matched tại 163 hội nghị/joint**, và **80 bài thay đổi nhãn hoặc conference_id** so với bản 4. Trong 1.090 bài giữ lại, 956 bài chốt bằng đồng thuận metadata tự động và 134 bài bằng kết luận AI có nguồn. Toàn corpus bản 5 vẫn gồm 4.182 bài: 1.090 matched, 1.119 excluded, 1.973 unresolved.

Không thêm bài; không dùng enrichment/cache S2 của tập 2; không truy arXiv để tìm venue. Định danh hoặc năm mới thấy trên nguồn không được ghi ngược vào raw. **Năm dùng để chia tập là year từ raw đã chuẩn hóa trong mapping**, không phải publication_year tra trên mạng.

## Mức độ tin cậy và giới hạn

Bản 5 đủ căn cứ vận hành để tạo một tập thực nghiệm có thể truy vết và tái lập theo policy trên. Đây là **review có AI hỗ trợ và nguồn thư mục**, không phải human gold hoặc bảo đảm nhãn đúng 100%. Metadata nguồn vẫn có thể sai, thông tin track có thể thiếu, và quyết định AI vẫn có khả năng nhầm. Các kiểm tra kỹ thuật chứng minh tính nhất quán/tái lập, không chứng minh độ chính xác học thuật tuyệt đối.

Độ phủ review 1.144/1.144 không phải precision=100%. Không báo precision/recall/F1 của nhãn vì chưa có gold độc lập, và không kiểm định mẫu từ excluded/unresolved gốc để đo bỏ sót. Tỷ lệ giữ matched cũng không phải precision. 18 bài chưa chốt đã được tách khỏi tập sử dụng, không để chúng trở thành công việc bắt người dùng kiểm tra tay trước khi chia tập.

## Hồ sơ kiểm tra và tái lập

- review/paper_review.csv: từng bài, venue/journal raw, kết quả nguồn, kết luận và nhãn cuối.
- review/paper_evidence.jsonl và source_cache.jsonl: quan sát và phản hồi nguồn đã lưu.
- review/adjudications.json: 188 quyết định AI có lý do/URL.
- review/paper_review_overrides.csv: 80 thay đổi nhãn/conference_id.
- review/unresolved_after_review.csv: 18 ca chưa chốt và lý do.
- review/coverage.json, output/manifest.json: độ phủ, số lượng và hash.

Chạy `python -B review_mapping.py --check` để kiểm tra hash và dựng lại offline; `--self-test` kiểm tra các quy tắc phân biệt dễ nhầm. Lệnh check không gọi mạng và không ghi lại dữ liệu.

## Quy tắc chia tập sau review

1. Chỉ dùng matched của bản 5 với cờ usable_for_split=true.
2. Đếm tổng matched từng conference_id; giữ ứng viên có n ≥ 5.
3. Dùng year raw: train nếu year ≤ 2015, test nếu 2016 ≤ year ≤ 2019. Không suy năm từ venue hay nguồn online; thiếu/mâu thuẫn năm để ngoài split.
4. Giữ hội nghị có ít nhất 3 bài train và 1 bài test; không chuyển bài qua mốc năm để đủ số lượng.
5. Giữ nguyên toàn bộ bài thỏa điều kiện trong các hội nghị được chọn, không lấy ngẫu nhiên hoặc ép tỷ lệ 80/20. Sắp theo conference_id, year tăng dần, paper_id để phân xử các bài cùng năm.
6. Kiểm tra train/test không trùng paper_id, source_id, tiêu đề hoặc abstract chuẩn hóa. Chỉ dùng title+abstract làm nội dung đầu vào, conference_id làm nhãn. Chỉ train được dùng xây profile K-Medoids; test giữ để đánh giá.

Tập chia lưu riêng dưới splits/temporal_2015_2016_2019 trong bản 5, gắn hash mapping, corpus và cấu hình. Không tạo một phiên bản mapping mới chỉ vì chia tập.
