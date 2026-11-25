# Human gold400 — accepted ngày 26/10/2026

Người dùng đã chấp nhận bản reference v3 sau khi xem kết quả rà soát và sửa nhãn. File chính: **human_gold.jsonl**, đủ **400 bài /3.346 concept**; toàn bộ human_review_status=accepted, reviewer_type=human, reviewer=user. Nhãn được AI hỗ trợ soạn và rà; annotation_author_type=ai giữ rõ nguồn gốc, không mô tả đây là hai lượt human annotation độc lập.

Lượt chấp nhận này chỉ đổi tên file và metadata, **không sửa concept, nguồn hay evidence**. Các ghi chú về15 bài cần xác minh/độ chi tiết trong audit trước vẫn được giữ để truy vết; chấp nhận không tự xác minh lại nguồn ngoài title/abstract.

Cặp dữ liệu: `human_gold.jsonl` và `gpt_review_evidence.jsonl`. `gpt_review_manifest.json` và `manifest.json` trỏ tới file mới, lưu trạng thái accepted và checksum tương ứng.

[Biên nhận chấp nhận và backup trước đổi tên](../../evaluation/reference_gold_acceptance_20261026_v1/acceptance_report.json) · [Thống kê chỉnh nhãn v3](../../evaluation/reference_gold_audit_20261026_v1/report_vi.md) · [Nhật ký sửa nhãn](../../evaluation/reference_gold_audit_20261026_v1/changes.jsonl).

Các release/split huấn luyện, pilot và kết quả đánh giá cũ giữ nguyên, gắn với hash lúc chạy. Evaluator hiện mặc định đọc human_gold.jsonl; không chạy lại điểm trong bước này.
