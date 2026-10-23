# Exp B — Xếp hạng ứng viên theo bài mốc

[Chỉ mục script](../README.md) · [Generator B](../../data/exp_b/README.md) · [Giao diện chung](../BASELINE_GUIDE.md)

## 1. B kiểm tra điều gì?

Khi đang đọc bài X, hệ thống xếp các bài khác theo độ phù hợp với X. B so toàn văn, năm facet ngang nhau và năm facet có trọng số cố định.

Baseline có **random, text_tfidf, equal_facets, weighted_facets**. Đây là scorer lexical chạy CPU; chưa có encoder pretrained/reranker. B chấm **100 ứng viên cố định mỗi bài mốc**, chưa đo retrieval lấy ứng viên từ toàn corpus.

## 2. Đầu vào của một case

| Thành phần | Vai trò |
|---|---|
| Corpus + full silver A + metadata/manifest | Title/abstract, concept và provenance |
| `retrieval_queries.jsonl` | Bài mốc và candidate_ids |
| `splits.json` | Train/dev/test theo anchor |
| `configs/exp_b.json` | Trọng số, seed, đường dẫn |
| `retrieval_labels.jsonl` | Nhãn từng cặp; evaluator đọc |

Case có case_id/query_id, query_paper_id là X và 100 candidate_ids khác X. Không có target_facet do user chọn trong B hiện tại.

Generator **tạo cả query và ground truth**. Cách lấy anchor/high/low/hard candidates nằm trong README dữ liệu B.

## 3. Split có nghĩa gì? Model học thế nào?

300 anchors chia 70/15/15: mục tiêu 210 train, 45 dev, 45 test. Một anchor chỉ ở một split; ứng viên có thể lặp giữa query/split.

Baseline **không học tham số từ nhãn train**. TF-IDF tính thống kê từ văn bản chưa gán nhãn toàn corpus; trọng số cố định; random có seed. Đây là thiết lập transductive về văn bản.

Model trainable bổ sung phải fit trên train, chọn tham số trên dev, freeze rồi chấm test. Encoder pretrained freeze chỉ tạo/cache vector, không cần gradient training. Không chọn model/trọng số bằng điểm test.

## 4. Scorer biểu diễn bài thế nào?

Whole-text document nối title + abstract; mỗi facet document nối các concept, tạo năm documents/bài. Cả hai dùng **một bộ TF-IDF/IDF** chung.

Token chuẩn hóa và có ít nhất hai ký tự. Công thức:

```text
idf(t) = log((1 + số documents) / (1 + số documents chứa t)) + 1
vector[t] = số lần xuất hiện(t) × idf(t)
vector → chuẩn hóa L2 về độ dài 1
similarity(X,Y) = dot(vector_X, vector_Y)
```

Dot của unit vectors là cosine. Facet rỗng cho similarity 0. Evidence dùng kiểm tra A; B hiện chưa đưa câu evidence vào scorer.

## 5. Bốn phương pháp tính điểm

| Model | Score ứng viên Y |
|---|---|
| `random` | Ngẫu nhiên tái lập theo seed + case_id |
| `text_tfidf` | Cosine whole-text X–Y |
| `equal_facets` | Trung bình cosine cả năm facet |
| `weighted_facets` | Tổng cosine × fixed weight |

Weights theo problem/task/method/dataset/contribution: **[.4,.2,.2,.1,.1]**. Facet rỗng vẫn đóng góp 0, không tự học lại weights.

Ví dụ similarity minh họa:

| Candidate | Problem | Task | Method | Dataset | Contribution | Equal | Weighted |
|---|---:|---:|---:|---:|---:|---:|---:|
| Y1 | .9 | .8 | .6 | .2 | .6 | .62 | .72 |
| Y2 | .5 | .7 | .9 | .8 | .4 | .66 | .64 |

Equal xếp Y2 trước; weighted xếp Y1 trước vì ưu tiên problem. Whole-text có score riêng từ title/abstract.

Scorer tính đủ 100 điểm, sắp giảm dần, hòa điểm theo paper_id tăng dần. Các công thức này đã là **ranker baseline**, nên chưa có reranker vẫn có tiêu chí sắp xếp.

## 6. Ground truth khác score thế nào?

```text
grade_f(X,Y) = 2 nếu hai concept sets bằng nhau và không rỗng
             = 1 nếu có giao
             = 0 nếu không giao hoặc thiếu facet
relevance(X,Y) = Σ fixed_weight_f × grade_f
```

Ground truth là concept overlap từ 0 đến 2. Prediction là similarity TF-IDF; scorer không đọc labels. Cùng dùng silver nên phép so vẫn có bias chung về định nghĩa facet.

Grades [2,1,0,0,1] → relevance **1.1**. Grades [0,0,1,0,0] → **.2**.

Ngưỡng .6 chỉ dùng sampling high/low. Recall/Precision/MRR coi **relevance > 0 là positive**, kể cả .2.

## 7. Runner, lệnh chạy và chỉ số

```text
kiểm tra manifests → chọn split → tạo vectors
→ case × model: scores → ranking
→ evaluator đọc relevance → điểm từng case → tổng hợp model
```

```powershell
python data/exp_b/build_exp_b.py --dry-run
python data/exp_b/build_exp_b.py
python data/exp_b/build_exp_b.py --validate-only
python scripts/exp_b/run_exp_b.py --dry-run
python scripts/exp_b/run_exp_b.py --split test --ks 5 10
```

Output mặc định dưới `results/exp_b/`, runner in đường dẫn cụ thể. Dùng `--output` riêng hoặc `--overwrite`. Đủ 45 test cases tạo 180 predictions.

So **nDCG/Recall/Precision@5/10 và MRR** trên cùng pool. nDCG ưu tiên relevance cao ở đầu; MRR chú ý positive đầu tiên. Đây là điểm trên pool được chọn, chưa chứng minh candidate retrieval toàn corpus.

Đọc report.md và details.jsonl; sáu tệp output/công thức tại [baseline guide](../BASELINE_GUIDE.md).

## 8. Phát triển phương pháp mới

Thêm whole-text embedding, facet embedding và weighted facet embedding, giữ bốn baseline đối chứng. Encoder pretrained freeze là hướng so biểu diễn ngữ nghĩa; **chưa tích hợp hiện tại**.

Reranker có thể là phép thử tiếp theo để chấm sâu X–Y/facet/evidence. Retrieval toàn corpus cần đo candidate recall/tốc độ riêng; đổi scorer trên pool 100 không tự tạo phép thử đó.

Khung `scripts/exp_b/run_my_method.py`; tự cài đặt `score_new_method` trả dictionary điểm đủ candidate_ids:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baseline_common import ranked
from exp_b.run_exp_b import predict as baseline_predict
from experiment_runner import main

def predict(papers, facets, cases, history, options):
    predictions = baseline_predict(papers, facets, cases, history, options)
    for case in cases:
        scores = score_new_method(papers, facets, case, history, options)
        predictions.append(ranked(case, 'my_method', scores))
    return predictions

if __name__ == '__main__':
    main('b', predict)
```

```powershell
python scripts/exp_b/run_my_method.py --split test --output results/exp_b/my_method/test
```

Lệnh cuối chỉ chạy sau khi đã tạo tệp/cài scorer. Dùng cùng dataset/pool/split/evaluator; không đọc ground_truth trong predict. [Kế hoạch A–E](../../docs/EXPERIMENT_PLAN_FINAL.md) phân biệt baseline bàn giao với phần nghiên cứu thêm.
