# Bản 5 — review mapping bản 4

Bản 4 là đầu vào đã chốt và giữ nguyên. Bản 5 rà soát 446 alias matched và mẫu 242 bài (205 ngẫu nhiên trong 41 hội nghị có n ≥ 5, thêm 37 ca rủi ro), seed 20261031. Chứng cứ danh mục bản 4 và review cũ được kế thừa; kết luận AI mới ở `review/adjudications.json`.

Không mở rộng dataset/mapping: không thêm bài, không tìm DOI mới, không truy arXiv hoặc dùng cache enrichment tập 2. Chỉ mở DOI/ACL ID đã có trong raw để kiểm tra đúng các bài matched được chọn. AI đọc nguồn proceedings cho các ca mơ hồ; URL được lưu cùng quyết định. Không thay year raw, publication_year, title, abstract hoặc paper_id.

## Chạy

Từ thư mục bản 5:

```powershell
python -B review_mapping.py --self-test
python -B review_mapping.py
python -B review_mapping.py --check
```

Mặc định chạy offline. `--fetch` chỉ bổ sung các URL nguồn còn thiếu trong mẫu và các quyết định đã ghi; không tìm bài mới. `audit_mapping.py` và `preprocess_cube.py` là entry point tương đương cho bản 5. Code nguyên bản 4 được lưu ở `review/inherited_version4`, chỉ để đối chiếu; chạy quy trình gốc tại thư mục bản 4 nếu cần tái lập bản 4.

## Kết quả

- `output/paper_conference_links.jsonl`: mapping mới, giữ chứng cứ/năm raw và lưu nhãn trước sửa ở `pre_v5_review`.
- `venue_mapping.csv`: alias sau sửa; lịch sử đầy đủ ở `review/alias_review.csv`.
- `review/paper_sample_review.csv`: kết quả đối chiếu tự động và kết luận sau AI, tách ngẫu nhiên/rủi ro.
- `review/paper_evidence.jsonl`, `source_cache.jsonl`: metadata/chứng cứ và phản hồi nguồn (gồm lỗi, không coi lỗi tải là nhãn sai).
- `review/adjudications.json`, `paper_review_overrides.csv`: kết luận AI và thay đổi nhãn có lý do/URL.
- `review/pending_review.csv`: bài trong mẫu chưa đủ chứng cứ chốt ở cấp bài. Không đòi người dùng kiểm tra tay; chưa có căn cứ sửa thì giữ nhãn cũ và ghi rõ giới hạn.
- `output/manifest.json`: hash đầu vào/bản 4, đầu ra và kiểm tra tái lập.
- `review/temporal_split_feasibility.csv`: thống kê khả thi theo năm raw, chưa tạo train/test.

Đây là review có AI hỗ trợ và nguồn thư mục, không phải human gold hay xác minh độc lập mọi bài. Tỷ lệ đồng thuận mẫu không phải precision toàn corpus; không ước lượng recall/F1 vì không kiểm tra mẫu excluded/unresolved.

## Bước chia tập tiếp theo

Sau khi chọn dùng mapping bản 5: lọc matched, tổng n ≥ 5, train raw year ≤ 2015, test raw year 2016–2019; giữ hội nghị có ít nhất 3 train và 1 test. Không đổi năm hoặc ép bài sang phía khác để đủ số lượng. Bài thiếu/mâu thuẫn năm để ngoài split. Lưu split dưới `5_mapping_reviewed/splits/temporal_2015_2016_2019/`, gắn hash mapping bản 5 và config. Lượt review này chưa tạo splits và chưa xây profile.
