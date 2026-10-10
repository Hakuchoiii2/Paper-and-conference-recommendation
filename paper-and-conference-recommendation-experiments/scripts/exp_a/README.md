# Exp A — Đánh giá Qwen trích năm facet

[Chỉ mục script](../README.md) · [Generator A](../../data/exp_a/README.md) · [Quy trình review](../../docs/EVALUATE_QWEN.md)

## 1. A kiểm tra điều gì?

A có hai bước: Qwen đọc title/abstract để trích facet silver; evaluator đối chiếu silver với nhãn do người review độc lập. README này giải thích bước đánh giá. Chia bài cho năm thành viên, GPU, retry, checkpoint và gộp nằm trong README generator.

Qwen là **model đã có trong A**. Evaluator chạy CPU, không gọi lại Qwen, không học tham số và không sửa gold. Điểm chọn lượt sinh 0–100 chỉ đo bám nguồn/schema; không thay thế Precision/Recall/F1 so với gold.

## 2. Đầu vào và điều kiện chạy

| Đầu vào | Mặc định | Vai trò |
|---|---|---|
| Corpus | `data/processed/papers.jsonl` | Title/abstract và ID |
| Silver source | `data/exp_a/generated/` | Silver, metadata/evidence, manifest có hash hợp lệ |
| Human gold | `data/exp_a/ground_truth/gold_review/review_annotations.jsonl` | Đáp án người review hoàn tất |
| Gold cohort manifest | Thư mục gold review | Xác nhận IDs đã chọn |
| Expected count | 400 | Kiểm tra số bài đánh giá |

Gold phải có đúng năm list facet, ID duy nhất, `review_status: reviewed` và tên reviewer. Selector mới tạo form pending, **chưa tạo ground truth hoàn chỉnh**. Người review đọc bài và điền nhãn trước khi xem silver reference.

Silver phải chứa mọi ID gold. Evaluator cho phép source partial nếu cohort có đủ và báo coverage; điều đó không làm source partial đủ điều kiện bàn giao B–E. P000001 đã dùng phát triển prompt nên bị loại khỏi held-out gold.

## 3. Generator tạo gì trước khi chấm?

```text
title/abstract → Qwen → concept + evidence_id
→ kiểm tra schema/bám nguồn, retry có giới hạn
→ facets_silver + annotation_metadata + manifest
→ selector chọn cohort → form pending
→ người review hoàn tất → human gold
```

Không cần chạy lại extraction để chấm A nếu silver và metadata/evidence hợp lệ đã có. Gold kiểm tra **đúng và đủ**: người review có thể xóa nhãn sai, sửa facet và bổ sung ý bị bỏ sót.

Selector ưu tiên bài nhiều facet/concept hợp lệ, không lấy mẫu ngẫu nhiên toàn corpus. Điểm A chỉ có phạm vi cohort đó.

## 4. Evaluator chạy từng bước

1. Kiểm tra source manifest, hash, corpus, metadata và gold cohort.
2. Từ chối gold pending, thiếu reviewer, sai số lượng/schema/IDs hoặc có P000001.
3. Chuẩn hóa concept bằng Unicode NFKC, casefold và khoảng trắng; giữ dấu câu.
4. Với mỗi paper/facet, chuyển nhãn thành tập rồi tính TP/FP/FN.
5. Tổng hợp P/R/F1 từng facet, micro/macro và tỷ lệ paper cả năm facet khớp hoàn toàn.
6. Xuất nhãn dư/thiếu và evidence để người đọc phân tích lỗi.

Không tự gộp từ đồng nghĩa. `C++` và `C#` vẫn khác nhau. Hai cách diễn đạt cùng nghĩa nhưng không khớp sau chuẩn hóa có thể bị tính khác; cần đọc per-paper để diễn giải.

## 5. Ví dụ tính điểm

Ví dụ minh họa facet method:

```text
Gold   = {graph neural networks, contrastive learning}
Silver = {graph neural networks, support vector machines}
TP = 1, FP = 1, FN = 1
Precision = TP / (TP+FP) = 0.5
Recall    = TP / (TP+FN) = 0.5
F1        = 2TP / (2TP+FP+FN) = 0.5
```

Precision thấp: trích thêm nhãn không có trong gold. Recall thấp: bỏ sót nhãn gold. **Micro** cộng counts rồi tính điểm chung; **macro** lấy trung bình F1 của các facet có điểm xác định. Mẫu số bằng 0 báo N/A.

Exact match paper đòi cả năm tập nhãn giống nhau. Chẩn đoán “có thể nhầm facet” hỗ trợ rà lỗi, không tự sửa/công nhận nhãn.

## 6. Chạy và đọc kết quả

Từ gốc repository, Python 3.11+:

```powershell
python scripts/exp_a/evaluate_exp_a.py
python scripts/exp_a/evaluate_exp_a.py --source data/exp_a/generated --gold data/exp_a/ground_truth/gold_review/review_annotations.jsonl --output data/exp_a/evaluation/gold_400
```

`--expected-count` mặc định 400; chỉ đổi khi chủ động đánh giá cohort khác. A không dùng split/ks của B–E.

| Tệp dưới `data/exp_a/evaluation/gold_400/` | Cách đọc |
|---|---|
| `report.md` | P/R/F1 từng facet và giới hạn |
| `summary.json` | TP/FP/FN, micro/macro và corpus audit |
| `per_paper.jsonl` | Nhãn dư/thiếu, gold/silver, evidence |
| `manifest.json` | Hash input/code/output |

Bàn giao cả thư mục. Báo cáo cần nêu cohort, cách chọn, phiên bản model/prompt/policy và việc dùng lexical agreement.

## 7. Thành viên A phát triển gì tiếp?

So prompt, extraction policy hoặc model extraction khác trên cùng năm facet và gold cohort. Dùng tập phát triển riêng để chỉnh prompt; không chỉnh theo gold held-out rồi báo như test độc lập.

Encoder retrieval/reranker của B–E không phải điều kiện chạy A. Evidence có thật vẫn cần người đọc kiểm tra có hỗ trợ đúng concept/facet không.
