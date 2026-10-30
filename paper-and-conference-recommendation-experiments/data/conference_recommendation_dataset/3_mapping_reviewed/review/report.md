# Kiểm tra nguồn cho mapping bản 1

**Đây là kiểm tra tên và đối chiếu mẫu bằng nguồn thư mục, có AI hỗ trợ; chưa phải human gold hoặc review độc lập bởi người chấm.**

- Đã xét **223 chuỗi venue matched** thuộc **34 conference IDs** của bản 1; **0 chuỗi** còn thiếu nguồn tên truy xuất được.
- Mẫu ngẫu nhiên: tối đa 5 bài/hội nghị, seed 20261030; **163 bài**. Thêm **6 ca rủi ro** ngoài mẫu ngẫu nhiên.
- Mẫu rủi ro được thống kê riêng, không trộn để ước lượng độ chính xác.
- Crossref/ACL Anthology được truy vấn theo DOI/ACL ID; DOI gợi ý từ cache S2 chỉ dùng tìm nguồn. Không đọc nhãn kết quả cũ làm đáp án.
- Snapshot giữ **294 phản hồi URL** (gồm lỗi); lượt lấy nguồn mới trong lần ghi báo cáo này: 0. Chạy lại không refresh dùng nguyên snapshot.
- Một số nguồn ICLR được tìm bằng web để xác định trang chương trình chính thức; kết luận lấy từ danh sách main/workshop trong trang nguồn, không lấy câu trả lời/tóm tắt của LLM làm nhãn.

## Kết quả đối chiếu mẫu

| Kết quả | Mẫu ngẫu nhiên | Thêm ca rủi ro |
|---|---:|---:|
| different_conference | 2 | 0 |
| identity_review | 22 | 0 |
| no_reference_available | 18 | 2 |
| outside_main | 1 | 0 |
| publication_conflict_review | 1 | 0 |
| reference_agreement | 107 | 4 |
| venue_or_track_unresolved | 12 | 0 |

Ý nghĩa: reference_agreement = nguồn cùng conference; different_conference = nguồn chỉ conference khác; outside_main = nguồn chỉ workshop/ấn phẩm ngoài đích; publication_conflict_review = nhiều bản công bố chưa chốt; identity_review = title/tác giả chưa khớp; venue_or_track_unresolved = chưa rõ venue/track; no_reference_available = chưa lấy được nguồn phù hợp.


reference_agreement chỉ là đồng thuận với metadata đạt điều kiện title/tác giả, không phải precision đã được người chấm đo. Ngoài main hoặc khác conference là tín hiệu cần sửa nhãn/raw hoặc policy; nguồn thiếu/khác title không tự coi là nhãn sai.

## Lỗi quy tắc đã sửa trong bản 3

- PRIME 2013 có tên kéo dài sau “Pattern Recognition”; quy tắc cũ gán nhầm ICPR. Bản 3 giữ CONF_PRIME riêng, có DOI/publisher metadata làm căn cứ.
- Joint SIGDAT EMNLP/VLC được giữ CONF_EMNLP_VLC riêng để nhất quán chính sách joint, thay vì âm thầm gộp EMNLP.
- Giữ short papers thuộc main khi nguồn chỉ rõ; không tự loại poster sessions thuộc main. Tên conference trần chưa chứng minh từng bài là main.
- Bản 1 và 2 được giữ nguyên nhãn. Bản 3 sửa rule tên và áp dụng **3 chỉnh sửa từng bài có căn cứ** trong paper_review_overrides.csv; không mở rộng tra nhãn cho toàn corpus.

## Theo hội nghị

| ID bản 1 | Số kiểm tra | Đồng thuận nguồn | Ngoài main | Khác conference | Còn cần review |
|---|---:|---:|---:|---:|---:|
| CONF_AAAI | 4 | 1 | 0 | 0 | 3 |
| CONF_ACL | 5 | 4 | 0 | 1 | 0 |
| CONF_ACL_IJCNLP | 5 | 5 | 0 | 0 | 0 |
| CONF_ACM_MM | 5 | 3 | 0 | 0 | 2 |
| CONF_CHI | 5 | 2 | 0 | 0 | 3 |
| CONF_CICLING | 3 | 0 | 0 | 0 | 3 |
| CONF_CIKM | 5 | 2 | 0 | 0 | 3 |
| CONF_COLING | 5 | 5 | 0 | 0 | 0 |
| CONF_COLING_ACL | 5 | 5 | 0 | 0 | 0 |
| CONF_CONLL | 5 | 5 | 0 | 0 | 0 |
| CONF_CVPR | 5 | 3 | 0 | 0 | 2 |
| CONF_EACL | 5 | 3 | 0 | 0 | 2 |
| CONF_ECCV | 2 | 0 | 0 | 0 | 2 |
| CONF_ECML_PKDD | 4 | 3 | 0 | 0 | 1 |
| CONF_EMNLP | 6 | 5 | 0 | 0 | 1 |
| CONF_EMNLP_CONLL | 5 | 5 | 0 | 0 | 0 |
| CONF_ICALP | 5 | 0 | 0 | 0 | 5 |
| CONF_ICASSP | 5 | 5 | 0 | 0 | 0 |
| CONF_ICCV | 5 | 4 | 0 | 0 | 1 |
| CONF_ICLR | 5 | 2 | 1 | 0 | 2 |
| CONF_ICML | 6 | 4 | 0 | 0 | 2 |
| CONF_ICPR | 5 | 3 | 0 | 1 | 1 |
| CONF_IJCAI | 5 | 4 | 0 | 0 | 1 |
| CONF_IJCNLP | 5 | 4 | 0 | 0 | 1 |
| CONF_KDD | 5 | 2 | 0 | 0 | 3 |
| CONF_LREC | 5 | 3 | 0 | 0 | 2 |
| CONF_NAACL | 9 | 9 | 0 | 0 | 0 |
| CONF_NEURIPS | 5 | 0 | 0 | 0 | 5 |
| CONF_RANLP | 5 | 4 | 0 | 0 | 1 |
| CONF_SIGDIAL | 5 | 5 | 0 | 0 | 0 |
| CONF_SIGIR | 5 | 4 | 0 | 0 | 1 |
| CONF_SIGMOD | 5 | 3 | 0 | 0 | 2 |
| CONF_WSDM | 5 | 4 | 0 | 0 | 1 |
| CONF_WWW | 5 | 0 | 0 | 0 | 5 |

## Việc còn lại

- Kiểm tra bằng người chấm/nguồn bài thực tế đối với các ca bất đồng, danh tính hoặc track chưa rõ, đặc biệt các alias quá rộng.
- Chốt tập hội nghị thực nghiệm rồi chọn mẫu kiểm định độc lập lớn hơn nếu muốn công bố precision/recall/độ tin cậy.
- Chưa thể gọi toàn bộ nhãn bản 3 là human_verified. Việc sửa hai rule không giải quyết mọi sai lệch metadata raw.
- Bước này kiểm định bản 1; chưa kiểm định độc lập toàn bộ phần enrichment của bản 2.
