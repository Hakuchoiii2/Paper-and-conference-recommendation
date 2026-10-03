# Pilot thực nghiệm A

Dùng trực tiếp `data/processed/papers.jsonl`; không có catalog paper mẫu.
Facet chung là `data/exp_a/generated/facets_silver.jsonl` trích từ bài thật.
Pilot Qwen local A dùng `--limit 10`, chỉ chọn bài trong `paper_range` của config
và lưu tại `output_dir` của phần đó để tiếp tục. Toàn bộ 4.210 bài chia cho
5 người, mỗi phần 842 bài; xem bảng khoảng và thư mục tại [README A](../README.md).
Kiểm tra offline chỉ dùng dữ liệu tạm, không xuất nhãn mock vào folder này.
