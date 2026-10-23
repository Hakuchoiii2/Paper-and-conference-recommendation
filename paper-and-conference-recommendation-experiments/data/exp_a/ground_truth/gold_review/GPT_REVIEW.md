# Nhãn tham chiếu AI — Exp A: bản hiện hành

Bản mới nhất: `codex_source_audit_revision_v2`, ngày 2026-10-14,
400 bài, **3.322 concept**. Lượt này sửa **18 bài / 21 trường facet** theo nguồn
sau audit 29 bài. Các nhãn còn lại giữ bản AI trước; chưa rà lại toàn bộ 400 bài.
`review_annotations.jsonl` và `gpt_review_evidence.jsonl` là cặp dữ liệu hiện hành.

- `gpt_review_manifest.json`: nguồn nhãn, thống kê và hash hiện hành.
- `gpt_semantic_revision_summary.json`: phạm vi sửa và năm trường hợp pending nguồn.
- `manifest.json`: cohort và hash các file hiện hành.
- `review_papers.jsonl`: title/abstract; `selection_ranking.jsonl`: cách chọn cohort.
- `silver_reference.jsonl`: snapshot Qwen lúc chọn cohort, được giữ nguyên.
- Lý do sửa, nhãn/evidence trước–sau và metadata cũ được gộp tại
  `data/exp_a/evaluation/reference_revision/`; không giữ nhiều bản gold cạnh nhau.

Output Qwen cho 4.210 bài không đổi. Các kết quả đánh giá cũ là lịch sử, gắn với
hash reference cũ; kết quả mới phải ghi hash bản v2. Việc sửa reference dựa trên
abstract và guideline, không thay nhãn chỉ để khớp cách viết của Qwen.

P000042, P001758, P002171, P003362 và P004138 vẫn cần xác minh nguồn; không đoán
tên nghi vấn hoặc nội dung abstract bị cắt. Nhãn vẫn là **AI reference**,
`human_review_status: pending`, chưa phải human gold độc lập. Cohort ưu tiên
silver đầy đủ và không đại diện ngẫu nhiên cho toàn corpus.
