# Ranking Input Data Directory

Thư mục này chứa 3 tệp dữ liệu đầu vào bắt buộc để thực hiện quy trình Ranking:

1. **`validated_silver.jsonl`**:
   - Được sinh ra từ Giai đoạn 1 (Data Preparation) sau khi audit & repair.
   - Chứa thông tin 4,210 bài báo với các trường: `paper_id`, `facets` (`problem`, `task`, `method`, `dataset`, `contribution`), `facet_status`, `evidence`, `provenance`.
   - *Lưu ý:* Có thể sao chép hoặc tạo symbolic link từ `data_preparation/output/validated_silver.jsonl`.

2. **`query_split.json`**:
   - Định nghĩa phân chia 50 bài báo làm query:
     - `dev`: 15 queries (dùng để kiểm thử & chọn trọng số).
     - `test`: 35 queries (dùng để báo cáo kết quả cuối cùng đúng 1 lần).
   - Cấu trúc:
     ```json
     {
       "dev": ["P000001", "P000003", ... 15 queries],
       "test": ["P000016", "P000020", ... 35 queries]
     }
     ```

3. **`human_qrels.jsonl`**:
   - Chứa tập nhãn đánh giá độ liên quan được gán bởi Con người (Human Qrels) từ Giai đoạn 2 & Giai đoạn 4.
   - Thang điểm đánh giá:
     - `0`: Không liên quan.
     - `1`: Có liên quan nhẹ, giá trị sử dụng hạn chế.
     - `2`: Có liên quan đáng kể.
     - `3`: Rất liên quan, có giá trị tham khảo trực tiếp.
   - Mỗi dòng là một cặp Query-Candidate:
     ```json
     {"query_id": "P000001", "candidate_id": "P000042", "grade": 3, "notes": "Cùng giải bài toán factual argument"}
     ```
   - *Lưu ý:* `human_qrels.jsonl` chỉ dùng làm nhãn đánh giá ở Bước 6 (`06_evaluate_ranking.py`), tuyệt đối không được sử dụng để huấn luyện hay tính điểm ranking.
