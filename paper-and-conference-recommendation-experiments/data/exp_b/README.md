# Dữ liệu B — Bài mốc × 100 ứng viên

[Chỉ mục dữ liệu](../README.md) · [Scorer B](../../scripts/exp_b/README.md) · [Protocol](../../docs/EXPERIMENT_PROTOCOL.md)

## 1. Generator phục vụ câu hỏi nào?

B kiểm tra biểu diễn whole-text và năm facet khi xếp bài theo bài đang đọc X. Generator tạo **query, candidate pool, nhãn relevance cho mọi cặp và split**. Nó chưa chạy model ranking.

Quy mô config chính: 300 queries × 100 candidates = 30.000 cặp. Cùng paper có thể là ứng viên của nhiều query; không cần 30.000 bài riêng.

## 2. Đầu vào cần có

| Input | Mặc định | Điều kiện |
|---|---|---|
| Corpus | `data/processed/papers.jsonl` | Canonical IDs/title/abstract, manifest hợp lệ |
| Silver A | `data/exp_a/generated/facets_silver.jsonl` | Đủ corpus, metadata và complete manifest |
| Config | `configs/exp_b.json` | dataset_kind mock, seed 42, quota và label rule |

Bài A fallback/còn validation errors bị loại khỏi pool. Không điền facet rỗng bằng nhãn giả. Gold review A không phải prerequisite của B.

## 3. Chọn bài mốc X thế nào?

1. Chuẩn hóa concept thành sets để kiểm tra bằng nhau/giao nhau.
2. Lấy anchor có ít nhất hai facet không rỗng.
3. Xáo danh sách bằng seed, mỗi anchor chỉ được dùng một lần.
4. Với anchor X, xét các bài hợp lệ khác X và tính relevance.
5. Nếu không đủ positive/negative/pool 100, bỏ anchor đó và thử bài khác.
6. Dừng khi đủ 300 queries hoặc hết anchor; ghi shortfall thực tế.

Không đặt 100 bài thành một “profile” của X. X là bài mốc, 100 bài là danh sách cần xếp hạng.

## 4. Ground truth cho từng X–Y

Theo problem/task/method/dataset/contribution, fixed_weights = **[.4,.2,.2,.1,.1]**:

```text
grade_f = 2 nếu tập concept X và Y bằng nhau, không rỗng
          1 nếu có giao
          0 nếu không giao hoặc thiếu facet
relevance = Σ weight_f × grade_f
```

Ví dụ grades [2,1,0,0,1] → relevance 1.1. Nếu chỉ method có giao [0,0,1,0,0] → .2.

Đáp án có trước prediction và lưu trong ground_truth; label_source/rule_version ghi rõ synthetic rule. Đây là nhãn sinh từ silver, **không phải expert relevance độc lập**.

## 5. Lấy 100 candidates thế nào?

Chia pool theo `positive_grade: .6`:

| Pool | Điều kiện |
|---|---|
| High | Relevance ≥ .6 |
| Low | Relevance < .6 |
| Hard low | 0 < relevance < .6: có điểm giao nhưng chưa đủ high |

Mục tiêu lấy 20% high, phần còn lại low. Trong số low, 50% được ưu tiên lấy từ hard pool nếu đủ; phần low còn lại cũng có thể chứa hard. Vì vậy không khẳng định luôn có đúng 20 high + 40 hard + 40 easy.

Số lấy được điều chỉnh theo pool thực tế nhưng phải có cả high và low, đủ 100 IDs khác nhau, không chứa anchor. Xáo thứ tự candidates; không để thứ tự file tiết lộ nhãn.

Ở evaluator, **relevance > 0 là positive** cho Recall/Precision/MRR. Low .2 vẫn positive; chữ low/negative trong sampling không đồng nghĩa mọi nhãn đều bằng 0.

## 6. Split theo bài mốc

Xáo anchors theo seed rồi chia 70/15/15. Đủ 300 queries có 210 train, 45 dev, 45 test. Cùng anchor không qua hai split; ứng viên có thể qua nhiều split.

Baseline TF-IDF không training bằng labels. Thành viên thêm model trainable dùng train để fit, dev để chọn tham số, test để báo điểm; chi tiết ở [scorer B](../../scripts/exp_b/README.md).

## 7. Tệp được tạo

| Thư mục | Tệp | Đơn vị/ý nghĩa |
|---|---|---|
| generated | `retrieval_queries.jsonl` | Query ID, anchor, candidate_ids |
| generated | `splits.json` | Danh sách query IDs từng split |
| ground_truth | `retrieval_labels.jsonl` | query_id/candidate_id/relevance |
| ground_truth | `label_provenance.jsonl` | Nguồn và phiên bản rule |

Output có generation_report và manifest ghi config, seed, hashes, số lượng thực tế, shortfall và trạng thái. Với đủ quota: 300 query records, 30.000 label pairs.

Runner chuyển query_id thành case_id cho giao diện scorer. Scorer chỉ nhận query/candidates và nguyên liệu bài; evaluator đọc labels sau khi có ranking.

## 8. Sinh, kiểm tra, bàn giao

Chạy từ gốc repository, Python 3.11+:

```powershell
python data/exp_b/build_exp_b.py --dry-run
python data/exp_b/build_exp_b.py
python data/exp_b/build_exp_b.py --validate-only
```

`--config` chọn config khác; paths tính từ project root. Thiếu quota tạo partial và exit code 2; `--allow-shortfall` chấp nhận partial để khảo sát, không biến thành complete. Runner chính cần dataset hợp lệ, complete.

Output contract 1.0 không được ghi đè bằng 2.0; chọn output_dir/truth_dir mới. Không chạy hai generator vào cùng output.

Bàn giao cả generated + ground_truth + config/manifest. [Pilot B](samples/README.md) hướng dẫn giảm quota riêng. Sau đó đọc [runner B](../../scripts/exp_b/README.md) để chạy model và so điểm.
