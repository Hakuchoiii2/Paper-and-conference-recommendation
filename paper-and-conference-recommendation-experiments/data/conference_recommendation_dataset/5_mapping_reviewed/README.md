# Bản 5 — review toàn bộ mapping matched của bản 4

Bản 4 và raw giữ nguyên. Lượt đầu kiểm tra mẫu 242 bài được lưu riêng ở `review/round1_sample_review/`. Theo yêu cầu tiếp theo, bản 5 kiểm tra toàn bộ **1.144 bài matched của bản 4**, bao gồm các bài đã sửa ở lượt đầu, và 446 alias. Đây không còn là review lấy mẫu.

## Dữ liệu và nguồn kiểm tra

Mỗi bài được đọc đồng thời `metadata.venue` và `metadata.journal` trong raw; trường journal có thể chứa tên proceedings, workshop, demo hoặc journal. Đối chiếu source ID và title/tác giả bằng ACL Anthology, Crossref và các proceedings chính thức. Crossref event.name và container-title đều được đọc khi có. Thiếu/sai định danh thì AI tìm tiếp từ title, tác giả và proceedings, lưu URL cùng kết luận. Chứng cứ tên venue không được coi là chứng minh track từng bài.

Không thêm bài, không mở rộng nhãn cho unresolved/excluded của bản 4, không dùng enrichment/cache S2 tập 2 và không truy arXiv. Không ghi DOI mới vào raw; không đổi năm raw, title, abstract hay paper_id. Được sửa conference thành phần sang ID joint ĐÃ CÓ khi nguồn xác nhận; joint chưa có ID riêng được để unresolved.

## Kết luận và dữ liệu dùng được

- `output/paper_conference_links.jsonl`: đầy đủ 4.182 bài canonical; lọc mapping_status=matched để lấy phần đủ căn cứ dùng thực nghiệm.
- Mọi bài matched cuối đều có đồng thuận metadata nguồn hoặc kết luận AI có URL. Bài thiếu/mâu thuẫn chứng cứ sau rà soát được chuyển unresolved, không lặng lẽ giữ matched. Không cần người dùng xử lý thủ công để hoàn tất lượt review.
- `mapping_review_v5` giữ trạng thái review, cờ raw và usable_for_split. `pre_v5_review` giữ nhãn trước khi sửa.
- `venue_mapping.csv` chỉ là ánh xạ tên. Alias có ngoại lệ từng bài được đánh dấu paper_context_required; phải áp dụng paper-level overrides để dựng nhãn cuối.
- Review nguồn không bảo đảm metadata publisher hoàn toàn đúng, không phải human gold và không cung cấp precision/recall do người chấm đo.

## Hồ sơ kết quả

- `review/coverage.json`: độ phủ toàn bộ 1.144 bài và số chưa chốt.
- `review/paper_review.csv`: kết quả từng bài, raw venue/journal, trạng thái nguồn, nhãn cuối.
- `review/paper_evidence.jsonl`: quan sát nguồn và kiểm tra venue/journal raw cho từng bài.
- `review/source_cache.jsonl`: phản hồi nguồn, kể cả lỗi; mặc định chạy lại offline.
- `review/adjudications.json`: quyết định AI có lý do và URL; source metadata gốc vẫn được giữ riêng.
- `review/paper_review_overrides.csv`: mọi thay đổi so với bản 4, gồm sửa joint và tách unresolved.
- `review/unresolved_after_review.csv`: phần đã kiểm tra nhưng chưa đủ bằng chứng; nằm ngoài phần matched dùng thực nghiệm. pending_review.csv là bản tương thích, không phải công việc bắt người dùng kiểm tra tay.
- `review/paper_sample_review.csv`: tên tương thích cũ, hiện chứa toàn bộ review; bản mẫu ban đầu đã lưu riêng.
- `review/report.md`, `output/report.md`: báo cáo và thống kê sau review.
- `output/manifest.json`: hash đầu vào, đầu ra và độ phủ; chạy check để kiểm tra lại.

## Chạy lại

```powershell
python -B review_mapping.py --self-test
python -B review_mapping.py
python -B review_mapping.py --check
```

Mặc định chạy offline. `--fetch` chỉ bổ sung URL còn thiếu và thử lại lỗi tạm thời theo danh sách hiện có, không tự tìm bài mới. audit_mapping.py và preprocess_cube.py gọi cùng entry point bản 5. Code nguyên bản 4 ở review/inherited_version4 chỉ để đối chiếu, không chạy tại đó.

## Phương pháp và chia tập

Phương pháp và giới hạn review được ghi đầy đủ trong [METHOD_REVIEW_V5.md](METHOD_REVIEW_V5.md). Không tuyên bố nhãn đúng tuyệt đối; 18 ca chưa đủ căn cứ đã để ngoài matched.

Chỉ dùng matched sau review; mỗi hội nghị n ≥ 5, train năm raw ≤ 2015 và test 2016–2019; giữ hội nghị có ít nhất 3 train và 1 test. Bài thiếu/mâu thuẫn năm để ngoài split. Chương trình `split_temporal.py` lưu dữ liệu dưới `splits/temporal_2015_2016_2019/`, gắn hash mapping/corpus, cấu hình, nhãn, thống kê và lý do loại. Xem README của thư mục split để biết số lượng thực tế. Chưa xây profile hoặc chạy mô hình.

```powershell
python -B split_temporal.py
python -B split_temporal.py --check
```
