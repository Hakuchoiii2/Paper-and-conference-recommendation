# EXP-B Paper Ranking

EXP-B so sánh ba cách tìm bài báo liên quan từ một bài truy vấn: Full-text Embedding, Equal-weight Facet Ranking và Weighted Facet Ranking. Cả ba dùng BERT Base Uncased và cùng tập query. DEV có 15 query để chọn cấu hình Weighted. TEST có 35 query để so sánh kết quả sau khi khóa trọng số.

## 1. Ranking nhận dữ liệu gì?

Các đường dẫn bên dưới tính từ thư mục gốc repo và được khai báo trong [ranking_config.json](config/ranking_config.json).

| File | Vai trò |
|---|---|
| `data/exp_b/data_preparation/output/validated_silver.jsonl` | Xác định corpus ứng viên theo `paper_id`. Cung cấp nội dung và trạng thái cho 5 facet. |
| `data/exp_b/data_preparation/input/papers.jsonl` | Cung cấp title và abstract gốc. Full-text dùng hai trường này để tạo embedding. Qwen dùng chúng để chấm mức liên quan. |
| `ground_truth_generation/output/query_split.json` | Cung cấp ID của 15 query DEV và 35 query TEST. Các query lấy dữ liệu bài báo theo ID. |
| `ground_truth_generation/human_review/initial_human_qrels.jsonl` | Cung cấp 100 cặp có nhãn ban đầu cho mỗi query trong luồng DEV/TEST. |
| `ground_truth_generation/intermediate/facet_similarity_results.jsonl` | Cung cấp điểm facet MiniLM để quy tắc chấm tự động gán nhãn cho các cặp bổ sung trong pool DEV/TEST. |
| `ranking/input/human_qrels.jsonl` | File nhãn mà runner tổng quát và script đánh giá trực tiếp đọc. Mỗi nhãn chứa ID query, ID candidate và grade 0–3. |

Năm facet gồm `problem` (vấn đề nghiên cứu), `task` (nhiệm vụ), `method` (phương pháp), `dataset` (bộ dữ liệu) và `contribution` (đóng góp). Ranker xét corpus ứng viên theo từng query và loại chính bài query khỏi kết quả. Danh sách 100 ứng viên ban đầu dùng để xây pool đánh giá.

## 2. BERT tạo embedding như thế nào?

| Cấu hình | Giá trị | Tác dụng |
|---|---|---|
| `model.name` | `google-bert/bert-base-uncased` | Checkpoint dùng chung cho ba phương pháp. |
| `model.embedding_dim` | `768` | Kích thước mỗi vector. Script kiểm tra kích thước encoder trả về. |
| `model.pooling` | `mean` | Trung bình vector token, bỏ qua token padding theo attention mask. |
| `model.batch_size` | `16` | Số văn bản đưa vào mỗi batch. |
| `model.normalize_embeddings` | `true` | Khai báo chuẩn hóa L2. Script hiện truyền trực tiếp `normalize_embeddings=True` khi encode. |

Với mỗi bài, script tạo **một vector từ title và abstract** cho Full-text. Sau đó script encode **riêng nội dung từng facet** có text và trạng thái `PRESENT`. Một bài có đủ dữ liệu sẽ có tối đa năm vector facet, mỗi vector 768 chiều. Mỗi loại facet có một ma trận vector và một mask đi kèm. Mask xác định hàng nào có facet dùng được khi tính điểm.

Ví dụ, bài query về phát hiện tin giả có `problem = Fake news detection` và `method = Deep learning`. Ranker so vector `problem` của query với vector `problem` của candidate, rồi làm tương tự cho `method` và các facet chung còn lại. Với vector đã chuẩn hóa L2, tích vô hướng cho ra cosine similarity.

## 3. Ba phương pháp tính điểm

| Phương pháp | Cách tính |
|---|---|
| Full-text Embedding | Cosine giữa hai vector title + abstract. |
| Equal-weight Facet | Trung bình cosine của các facet chung. Mỗi facet có trọng số 0,2. |
| Weighted Facet | Tổng cosine nhân trọng số, chia cho tổng trọng số của các facet chung. |

Với tập facet chung là `V`, điểm facet được tính bằng `sum(w[f] * cosine[f] for f in V) / sum(w[f] for f in V)`. Ví dụ, Weighted A dùng trọng số `0.4 / 0.2 / 0.2 / 0.1 / 0.1` theo thứ tự năm facet. Nếu chỉ thiếu `dataset`, tổng trọng số còn `0.9`. Cả hai ranker facet loại cặp thiếu toàn bộ facet chung khỏi Top-K. Điểm của các cặp hợp lệ được giữ kể cả khi cosine âm.

Ranker sắp xếp theo điểm giảm dần và lưu tối đa **100 bài mỗi query** theo mặc định. Mỗi dòng JSONL mô tả kết quả của một query, gồm `query_id`, `method`, `split`, `candidate_count` và mảng `ranking`. Mỗi phần tử trong mảng có `candidate_id`, `rank` và `score`. Bản ghi Weighted có thêm `weights`. Điểm `score` dùng để sắp xếp, còn grade 0–3 nằm trong qrels.

## 4. Chạy DEV, TEST và Evaluation

Chạy các lệnh sau từ thư mục gốc repo. Môi trường Python cần NumPy và Sentence Transformers. Lần đầu tạo cache cần checkpoint BERT trong cache Hugging Face hoặc kết nối để tải checkpoint. Bước chấm Qwen cần Ollama chạy cục bộ và có model `qwen3:4b`.

```powershell
python .\ranking\scripts\02_prepare_embeddings.py
python .\ranking\run_dev_test.py dev
python .\ranking\run_dev_test.py test
python .\ranking\run_independent_test.py
```

1. **Tạo cache BERT.** Script tạo vector Full-text và vector riêng cho năm facet. Thêm `--force` nếu cần làm mới cache sau khi thay đổi corpus hoặc cấu hình embedding.
2. **Chạy DEV.** Script chạy Full-text, Equal-weight, Weighted A và Weighted B trên cùng 15 query. Weighted B dùng `0.3 / 0.25 / 0.25 / 0.1 / 0.1`. Script chọn A hoặc B theo nDCG@10 trên DEV và lưu `locked_weights.json`.
3. **Chạy TEST.** Script đọc trọng số đã khóa và chạy đủ ba phương pháp trên cùng 35 query. Lượt DEV/TEST gộp 100 cặp có nhãn ban đầu với Top 20 mỗi phương pháp, loại trùng theo cặp query–candidate và chấm cặp bổ sung theo quy tắc MiniLM. Báo cáo từ lượt này phản ánh các nhãn tự động dựa trên facet.
4. **Chấm TEST bằng Qwen.** Script gộp Top 10 của ba bảng xếp hạng TEST đã lưu. Qwen chấm theo title, abstract và rubric 0–3. Kết quả dùng nhãn `AI` và báo cáo nDCG, Precision ở Top 5/10 cùng độ phủ nhãn Top 10. Sau khi đủ nhãn, chạy lại với `--evaluate-only` để tính metric từ qrels đã lưu.

## 5. Vai trò từng file trong thư mục Ranking

### Code và cấu hình

| File | Vai trò |
|---|---|
| [config/ranking_config.json](config/ranking_config.json) | Khai báo encoder, cache, input/output, trọng số mặc định và thông số đánh giá. |
| [run_dev_test.py](run_dev_test.py) | Chạy DEV/TEST, chọn và khóa trọng số, tạo pool và báo cáo cho từng split. |
| [run_independent_test.py](run_independent_test.py) | Chấm pool Top 10 TEST bằng Qwen và tính lại metric trên ba bảng xếp hạng đã lưu. |
| [run_ranking_pipeline.py](run_ranking_pipeline.py) | Runner tổng quát cho bảy script. Có `--check-only`, `--dev-only`, `--test-only`, `--skip-embeddings` và `--top-k`. Các lượt của runner này dùng chung đường dẫn output. |
| [scripts/01_load_ranking_data.py](scripts/01_load_ranking_data.py) | Kiểm tra Validated Silver, split query và file qrels của runner tổng quát. |
| [scripts/02_prepare_embeddings.py](scripts/02_prepare_embeddings.py) | Tạo và cache vector Full-text, vector facet, mask và danh sách ID. |
| [scripts/03_fulltext_ranking.py](scripts/03_fulltext_ranking.py) | Xếp hạng bằng vector title + abstract. |
| [scripts/04_equal_weight_ranking.py](scripts/04_equal_weight_ranking.py) | Xếp hạng bằng trung bình cosine của các facet chung. |
| [scripts/05_weighted_ranking.py](scripts/05_weighted_ranking.py) | Xếp hạng bằng cosine có trọng số và ghi thêm file gộp các kết quả. |
| [scripts/06_evaluate_ranking.py](scripts/06_evaluate_ranking.py) | Tính metric từ thứ hạng và qrels. DEV/TEST và bước chấm Qwen dùng lại các hàm tính metric ở đây. |
| [scripts/07_analyze_results.py](scripts/07_analyze_results.py) | Tạo báo cáo Markdown từ metrics của runner tổng quát. |
| [input/README.md](input/README.md) | Mô tả các file đầu vào của module Ranking. |
| `input/query_split.template.json`, `input/human_qrels.template.jsonl` | Mẫu cấu trúc split và qrels. Đường dẫn dữ liệu thực tế nằm trong config. |

### Cache và đầu ra

| File hoặc nhóm file | Nội dung |
|---|---|
| `intermediate/bert_base_uncased/paper_embeddings/fulltext_embeddings.npy` | Ma trận vector BERT của title và abstract. |
| `intermediate/bert_base_uncased/facet_embeddings/facet_<facet>_embeddings.npy` | Một ma trận vector riêng cho mỗi loại facet. |
| `intermediate/bert_base_uncased/facet_embeddings/facet_<facet>_mask.npy` | Mask cho biết bài nào có facet hợp lệ trong ma trận tương ứng. |
| `paper_ids.json` trong mỗi thư mục cache | Ánh xạ vị trí hàng của ma trận sang `paper_id`. |
| `reports/bert_base_uncased/dev_test/locked_weights.json` | Trọng số được chọn và điểm DEV dùng để chốt cấu hình. |
| `reports/bert_base_uncased/dev_test/{dev,test}/` | `fulltext.jsonl`, `equal_weight.jsonl` và file Weighted theo từng lượt. `combined.jsonl` do ranker Weighted ghi. `qrels.jsonl` lưu nhãn của pool và `metrics.json` lưu kết quả đánh giá. |
| `reports/bert_base_uncased/dev_test/independent_test/` | `qrels.jsonl` do Qwen chấm và `metrics.json` của đánh giá độc lập trên TEST. |
| `output/fulltext_ranking.jsonl`, `output/equal_weight_ranking.jsonl`, `output/weighted_ranking.jsonl` | Ba bảng xếp hạng theo đường dẫn mặc định của runner tổng quát. |
| `output/final_ranking_results.jsonl` | Các bản ghi xếp hạng của ba phương pháp được ghép chung. |
| `reports/ranking_metrics.json`, `reports/ranking_comparison.csv`, `reports/RANKING_ANALYSIS.md` | Báo cáo JSON, bảng so sánh CSV và phân tích Markdown của runner tổng quát. |

Các thư mục cache `intermediate/paper_embeddings/` và `intermediate/facet_embeddings/` thuộc lượt MiniLM trước đó. Cấu hình BERT đọc cache trong `intermediate/bert_base_uncased/`.
