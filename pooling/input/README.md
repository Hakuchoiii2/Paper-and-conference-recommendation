# Pooling Input Data Directory

Thư mục này chứa 4 nguồn Candidate đầu vào bắt buộc để thực hiện quy trình Pooling:

1. **`ground_truth_candidates.jsonl`**:
   - Chứa Top 100 ứng viên từ Giai đoạn 2 (Ground Truth Candidate Generation / Full-text MiniLM).
   - Cấu trúc:
     ```json
     {"query_id": "P000001", "ranking": [{"candidate_id": "P000042", "rank": 1, "score": 0.85}, ...]}
     ```

2. **`fulltext_ranking.jsonl`**:
   - Chứa kết quả xếp hạng từ Method 1 (Full-text Ranking). Lấy Top 20 ứng viên cho mỗi query.
   - *Tự động fallback:* Có thể lấy trực tiếp từ `ranking/output/fulltext_ranking.jsonl`.

3. **`equal_weight_ranking.jsonl`**:
   - Chứa kết quả xếp hạng từ Method 2 (Equal-weight Facet Ranking). Lấy Top 20 ứng viên cho mỗi query.
   - *Tự động fallback:* Có thể lấy trực tiếp từ `ranking/output/equal_weight_ranking.jsonl`.

4. **`weighted_ranking.jsonl`**:
   - Chứa kết quả xếp hạng từ Method 3 (Weighted Facet Ranking - 0.4 Problem). Lấy Top 20 ứng viên cho mỗi query.
   - *Tự động fallback:* Có thể lấy trực tiếp từ `ranking/output/weighted_ranking.jsonl`.
