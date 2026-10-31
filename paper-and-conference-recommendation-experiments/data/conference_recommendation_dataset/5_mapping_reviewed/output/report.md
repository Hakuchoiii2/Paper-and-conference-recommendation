# Bản 5 — review mapping đã chốt của bản 4

Đã mở rộng từ review mẫu sang rà soát TOÀN BỘ 1.144 bài matched của bản 4 (gồm cả các bài bị sửa ở lượt mẫu). Rà soát hai trường venue/journal raw cho từng bài, đối chiếu metadata nguồn, AI phân xử các ca đặc biệt. Không phải human gold hoặc bảo đảm nguồn thư mục đúng tuyệt đối.
Không enrichment: không dùng cache S2/tập 2, không truy arXiv, không thêm bài hoặc nâng unresolved/excluded thành matched. DOI/ACL ID sẵn có dùng để xác minh nhãn. Thiếu/sai định danh thì tìm title + tác giả + proceedings trên nguồn chính thức. Không nhập DOI/năm/abstract mới vào raw. Năm raw giữ nguyên.

- Alias đã đọc rà soát: 446 (toàn bộ alias matched bản 4). Nguồn tên không chứng minh track từng bài.
- Bài đã rà soát: 1144/1144; không còn lấy mẫu. Lượt mẫu 242 bài trước đó giữ ở review/round1_sample_review.
- Chỉnh nhãn có chứng cứ: 80 bài. Xem review/paper_review_overrides.csv và review/adjudications.json.
- AI phân xử bổ sung 188 bài; paper_review.csv có venue/journal raw, kết quả nguồn và nhãn cuối.
- Sau review: {'excluded': 1119, 'unresolved': 1973, 'matched': 1090}; 163 hội nghị/joint còn matched.
- Chưa đủ căn cứ sau review: 18 bài chuyển unresolved, xem review/unresolved_after_review.csv; không giữ trong matched dùng chia tập. Không tìm thấy nguồn không có nghĩa nhãn cũ sai; đây là loại khỏi tập sử dụng vì chưa xác minh được, không yêu cầu người dùng kiểm tra tay.
- Phần matched cuối chỉ giữ bài có đồng thuận metadata nguồn hoặc kết luận AI có URL; 0 bài matched chỉ được kiểm tra alias. Các bài excluded/unresolved gốc bản 4 ngoài phạm vi lượt review này giữ nguyên.

## Kết quả đối chiếu tự động trước AI phân xử

{
  "outside_main": 30,
  "reference_agreement": 964,
  "different_conference": 27,
  "no_reference_available": 58,
  "identity_review": 16,
  "venue_or_track_unresolved": 47,
  "publication_conflict_review": 2
}

reference_agreement = metadata phù hợp danh tính và cùng hội nghị, không phải precision được người chấm đo. identity_review/no_reference không tự chứng minh mapping sai. Kết luận AI bổ sung nằm riêng trong adjudications.json.

## Kết luận cuối sau AI và lọc chứng cứ

{
  "ai_confirmed_outside_main": 36,
  "source_metadata_agreement": 956,
  "ai_corrected_existing_joint_id": 26,
  "ai_reference_agreement": 107,
  "ai_identity_conflict": 2,
  "ai_companion_track_unresolved": 4,
  "ai_evidence_unresolved": 1,
  "ai_publication_version_unresolved": 5,
  "ai_reference_agreement_with_bad_raw_doi": 1,
  "ai_conference_identity_unresolved": 3,
  "ai_publication_conflict": 2,
  "ai_main_track_unresolved": 1
}

## Các thay đổi chính

Sửa ANLP@EMNLP (Arabic NLP workshop, không phải Applied NLP conference); SIGMORPHON và LDTA; các bài workshop bị gộp vào ACL/EACL/EMNLP/IJCNLP/ICLR; xét đúng ấn bản workshop COLT 1992 và HLT 1993. FSMNLP 2017 và IWPT 2009 được giữ vì nguồn của đúng ấn bản ghi conference.
Sửa các bài bị gộp sai từ ACL/EMNLP sang ID joint ACL-IJCNLP và EMNLP-CoNLL đã có. Joint chưa có ID riêng thì unresolved, không tạo catalog mới. Record trộn title/tác giả, nhiều phiên bản công bố hoặc chưa rõ track companion chuyển unresolved theo từng bài. Nguồn tên bare conference không chứng minh main track của mọi bài.

## Khả thi chia theo năm raw — thống kê của bước review

40 hội nghị có n ≥ 5; 903 bài. Giữ thêm ≥ 3 train (≤ 2015), ≥ 1 test (2016–2019): 30 hội nghị, 602 train và 186 test dự kiến. Bài thiếu/mâu thuẫn năm không phân vào split.

## Chạy lại

python review_mapping.py  # offline, tái lập từ snapshot và kết luận đã lưu
python review_mapping.py --check  # chỉ đọc, kiểm tra hash và dựng lại mapping
python review_mapping.py --fetch  # lấy nguồn còn thiếu/lỗi tạm thời của toàn bộ matched và các URL AI đã ghi

Bản 4 và raw giữ nguyên. Bước review chỉ dựng mapping; chương trình split_temporal.py lưu train/test riêng dưới splits/temporal_2015_2016_2019. Xem manifest/README của split để biết tập đã chia thực tế. Chưa xây profile/mô hình. Phần chưa có chứng cứ đã tách unresolved. Không tuyên bố precision/recall hoặc kiểm định con người.
