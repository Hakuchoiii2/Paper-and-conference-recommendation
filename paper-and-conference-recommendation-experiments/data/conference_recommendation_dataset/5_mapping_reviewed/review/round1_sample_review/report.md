# Bản 5 — review mapping đã chốt của bản 4

AI review alias và đối chiếu mẫu bài bằng nguồn; không phải human gold, không phải kiểm chứng từng bài toàn corpus.
Không enrichment: không tìm DOI mới, không dùng cache S2/tập 2, không truy arXiv, không thêm bài hoặc nâng unresolved/excluded thành matched. Chỉ dùng DOI/ACL ID có sẵn trong raw để xác minh mẫu matched; năm raw giữ nguyên.

- Alias đã đọc rà soát: 446 (toàn bộ alias matched bản 4). Nguồn tên không chứng minh track từng bài.
- Mẫu mới: 205 bài ngẫu nhiên (5 bài × 41 hội nghị n ≥ 5), seed 20261031; thêm 37 ca rủi ro. Mẫu phân tầng không dùng như ước lượng precision toàn corpus.
- Chỉnh nhãn có chứng cứ: 26 bài. Xem review/paper_review_overrides.csv và review/adjudications.json.
- AI phân xử bổ sung 38 bài; kết quả trong paper_sample_review.csv có cả trạng thái tự động và kết luận sau AI.
- Sau review: {'excluded': 1100, 'unresolved': 1964, 'matched': 1118}; 169 hội nghị/joint còn matched.
- Mẫu chưa chốt ở cấp bài: 18; xem review/pending_review.csv. Giữ nhãn cũ nếu chưa có căn cứ sửa; không gọi các bài này source_verified.

## Kết quả đối chiếu tự động trước AI phân xử

{
  "random_per_conference": {
    "no_reference_available": 17,
    "reference_agreement": 173,
    "venue_or_track_unresolved": 8,
    "outside_main": 4,
    "identity_review": 3
  },
  "risk_only": {
    "outside_main": 11,
    "reference_agreement": 13,
    "venue_or_track_unresolved": 5,
    "no_reference_available": 6,
    "publication_conflict_review": 2
  }
}

reference_agreement = metadata phù hợp danh tính và cùng hội nghị, không phải precision được người chấm đo. identity_review/no_reference không tự chứng minh mapping sai. Kết luận AI bổ sung nằm riêng trong adjudications.json.

## Các thay đổi chính

Sửa ANLP@EMNLP (Arabic NLP workshop, không phải Applied NLP conference); SIGMORPHON và LDTA; các bài workshop bị gộp vào ACL/EACL/EMNLP/IJCNLP/ICLR; xét đúng ấn bản workshop COLT 1992 và HLT 1993. FSMNLP 2017 và IWPT 2009 được giữ vì nguồn của đúng ấn bản ghi conference.
Các record trộn title/tác giả, nhiều phiên bản công bố hoặc chưa rõ track companion chuyển unresolved theo từng bài. Không gán sang conference mới. Nguồn tên bare conference không chứng minh main track của mọi bài.

## Khả thi chia theo năm raw — chỉ thống kê, chưa tạo train/test

40 hội nghị có n ≥ 5; 920 bài. Giữ thêm ≥ 3 train (≤ 2015), ≥ 1 test (2016–2019): 31 hội nghị, 641 train và 196 test dự kiến. Bài thiếu/mâu thuẫn năm không phân vào split.

## Chạy lại

python review_mapping.py  # offline, tái lập từ snapshot và kết luận đã lưu
python review_mapping.py --check  # chỉ đọc, kiểm tra hash và dựng lại mapping
python review_mapping.py --fetch  # chỉ lấy URL nguồn còn thiếu của mẫu matched

Bản 4 giữ nguyên. Chưa chia train/test và chưa xây profile/mô hình. Các ca chưa xác minh và bài không nằm trong mẫu vẫn là giới hạn của review.
