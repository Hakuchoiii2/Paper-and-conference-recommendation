# Tập train/test hội nghị — chia theo năm raw của bản 5

Đầu vào là mapping đã review toàn bộ nhóm matched của bản 4, được chốt tại bản 5. Phương pháp và giới hạn: ../../METHOD_REVIEW_V5.md. Nhãn có chứng cứ nguồn và AI review; không phải human gold hoặc bảo đảm độ chính xác tuyệt đối.

## Số lượng

| Phần | Số lượng |
|---|---:|
| Bài matched của bản 5 | 1090 |
| Hội nghị matched | 163 |
| Hội nghị ứng viên có n ≥ 5 matched | 40 |
| Hội nghị đáp ứng đủ điều kiện chia | 30 |
| Train | 602 |
| Test | 186 |
| Tổng bài được chọn | 788 |
| Bài không vào split trên toàn corpus | 3394 |

## Quy tắc

Chỉ dùng mapping_status=matched và mapping_review_v5.usable_for_split=true. Đếm n trên toàn bộ matched của mỗi conference_id, giữ ứng viên n ≥ 5. Sau đó chia bằng year raw trong mapping: train ≤ 2015; test 2016–2019. Giữ hội nghị có ít nhất 3 train và 1 test; nếu không đạt thì cả hội nghị không vào hai tập. Thiếu/mâu thuẫn năm hoặc ngoài cửa sổ để ngoài split. Không suy năm, không chia ngẫu nhiên, không ép tỷ lệ và không bớt bài ở hội nghị lớn.

Trong mỗi hội nghị, bài được sắp theo năm tăng dần, cùng năm dùng paper_id để có thứ tự tái lập. Chỉ train được dùng xây profile K-Medoids. Test là bài mới để đánh giá và không được đưa vào xây profile, chọn medoid hoặc điều chỉnh mô hình theo kết quả test.

## Sử dụng

- train.jsonl, test.jsonl: đầy đủ title, abstract, year raw và nhãn; không phải chỉ danh sách ID.
- Dùng title/abstract làm nội dung đầu vào, conference_id làm ground truth. Các trường conference_name, label_index và mapping_review_status là thông tin nhãn/provenance, không đưa chúng vào nội dung văn bản đầu vào.
- label_index từ 0 tới 29, theo conference_id tăng dần. label_map.json ánh xạ chỉ số về ID/tên hội nghị, dùng thống nhất cho train và test.
- conference_catalog.jsonl: đúng tập hội nghị ứng viên recommendation của split này. Không dùng toàn bộ catalog 163 hội nghị nếu đang đánh giá theo thiết kế tập đóng này.
- conference_split_statistics.csv: thống kê mọi hội nghị matched, kể cả hội nghị không được chọn, và lý do.
- excluded_from_split.csv: mọi bài không được chọn, gồm excluded/unresolved của mapping, năm không hợp lệ và hội nghị thiếu bài.
- split_config.json và manifest.json: quy tắc, hash đầu vào/đầu ra, số lượng và kiểm tra.

Đã kiểm tra: không trùng paper_id, raw source_id, title chuẩn hóa hoặc abstract chuẩn hóa giữa train/test; mọi hội nghị có đủ 3 train/1 test; max năm train < min năm test; văn bản giữ nguyên corpus chung; toàn bộ 4182 bài được hạch toán đúng một lần vào train/test/danh sách loại. Không tạo dev hoặc chạy mô hình.

## Tái lập

Từ thư mục 5_mapping_reviewed, chạy `python -B split_temporal.py`; kiểm tra chỉ đọc bằng `python -B split_temporal.py --check`. Chương trình kiểm tra mapping bản 5 trước khi dựng tập, không gọi mạng. Nếu mapping/corpus/phương pháp thay đổi thì check phát hiện hash thay đổi; cần chủ động dựng lại split theo phiên bản đầu vào mới.
