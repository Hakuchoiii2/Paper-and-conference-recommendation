# Exp D — Suy similar/different trong phiên

[Chỉ mục script](../README.md) · [Generator D](../../data/exp_d/README.md) · [Profile C](../exp_c/README.md) · [Giao diện chung](../BASELINE_GUIDE.md)

## 1. D khác C ở đâu?

C suy sở thích dài hạn; D suy **trong phiên này** user muốn tương tự hay khác bài mốc ở một facet, rồi kiểm tra hướng đó giúp ranking không.

D dùng helper profile C để lấy importance. Phần riêng là tín hiệu phiên, direction estimator và intent-aware scorer. Runner D tự tính profile từ dữ liệu C, không cần chạy scorer C trước.

## 2. Scorer thấy gì và giấu gì?

| Quan sát | Vai trò |
|---|---|
| Corpus/full silver A | Biểu diễn năm facet |
| C users/history/search/exposure + complete manifest | Importance dài hạn |
| `sessions.jsonl` | case_id, user_id, query_paper_id, context_facet, candidates, cutoff |
| D logs trước cutoff | Tín hiệu phần đầu phiên |

Context được benchmark cung cấp, có thể là bất kỳ facet nào. D **chưa chấm tự chọn context**.

True focus/directions/importance/query_mode và intent_labels ở ground_truth, không truyền vào scorer. Mỗi phiên có một context similar và một focus khác context muốn similar/different; nhiều focus đồng thời chưa thuộc thiết kế này.

## 3. Generator tạo tín hiệu thế nào?

Mục tiêu 300 users × 5 sessions × 20 candidates = 1.500 cases. Generator chọn anchor, context/focus, hướng và nhãn trước; sau đó sinh query/phản ứng.

Query có clear/ambiguous/none. Tối đa bốn cặp same/different ở focus, giữ các facet còn lại tương đương theo overlap/missing states. Bài quan sát không nằm trong 20 bài được chấm.

Scorer không thấy phản ứng của chính ứng viên cần xếp. Nếu thiếu cặp hợp lệ, giữ số thực tế; estimator có thể abstain. [Generator D](../../data/exp_d/README.md) giải thích chi tiết.

## 4. Estimator hướng hoạt động thế nào?

Khởi tạo năm facet unknown; context similar, confidence 1.

**Phản ứng:** xét exposure đúng hai bài, cả hai có phản ứng và các facet khác so sánh được; xác định bài same/different với anchor. Feedback weights −1/0/1/2/3 như C:

```text
delta = Σ(feedback_different − feedback_same) / (số cặp + 2)
```

Cần ít nhất hai cặp và |delta| ≥ .25. Dương → different; âm → similar; không rõ/thiếu → unknown. Hai cặp cùng save different (+2), view same (0): delta = 4/4 = 1 → different.

**Thêm search:** query cùng phiên được đọc theo thời gian. Exclude concept anchor, ví dụ `method: alternatives to GNN` → different; include anchor `method: more papers using GNN` → similar. Query rõ mới nhất có thể cập nhật hướng cũ.

Tên concept khác đơn thuần chưa đủ kết luận different. Parser lexical phục vụ mock; confidence chưa phải xác suất hiệu chuẩn.

## 5. Scorer theo intent tính thế nào?

D dùng **TF-IDF concept text từng facet**, so anchor/candidate. Profile C hiện chỉ cung cấp importance, không cộng trực tiếp concept preference vào score D.

```text
similar   → term = S
different → term = 1 − S
unknown   → term = S khi ranking
ignore    → bỏ facet
score = Σ weight_f × term_f / Σ weight_f đang dùng
```

S là cosine clip về [0,1]. Unknown vẫn giữ unknown trong prediction để chấm hướng.

Gate theo **context_facet của phiên**: anchor/candidate thiếu context hoặc context cosine ≤ 0 → score −1. Candidate thiếu facet active cũng −1, không được thưởng “khác”; facet thiếu phía anchor bỏ qua. Hết weights dùng context similarity.

Score là ưu tiên mềm, chưa đảm bảo mọi điều kiện AND; compliance được đo riêng.

## 6. Ví dụ thứ tự thay đổi vì hướng

Chỉ minh họa problem weight .6, method .4; context problem, focus method different:

| Candidate | Problem cosine | Method cosine | Method different | Tất cả similar |
|---|---:|---:|---:|---:|
| Y1 | .90 | .95 | .6×.90 + .4×.05 = .56 | .92 |
| Y2 | .85 | .20 | .6×.85 + .4×.80 = .83 | .59 |
| Y3 | 0 | .10 | −1 do gate | −1 |

Muốn đổi method và giữ problem → Y2 lên trước. Muốn tương tự → Y1 lên trước. Đây là ví dụ score liên tục; nhãn thật dùng overlap concept.

## 7. Các model và oracle

| Model | Importance | Direction |
|---|---|---|
| `fixed_similar` | Năm weights 1/5 | Tất cả similar |
| `profile_similar` | C profile | Tất cả similar |
| `direction_behavior` | Cùng C profile | Phản ứng phiên |
| `direction_search` | Cùng C profile | Phản ứng + search |
| `oracle_intent` | True session weights | True session directions |

Fixed vs profile_similar kiểm tra weights cá nhân hóa. Profile_similar vs direction_behavior kiểm tra suy hướng bằng hành vi. Behavior vs search kiểm tra lợi ích query.

Oracle do **evaluator thêm riêng**, đánh dấu privileged_information, không đưa true intent cho public scorer. Dùng cùng scorer nhưng có thông tin đặc quyền; không đảm bảo trần điểm toán học.

## 8. Nhãn và chỉ số

| Grade | Ý nghĩa |
|---|---|
| 2 | Context overlap và thỏa hướng focus |
| 1 | Có context overlap nhưng sai hướng |
| 0 | Ngoài context hoặc thiếu facet cần xét |

Similar ở focus là có concept overlap; different là không overlap khi có dữ liệu. Ground truth không lấy cosine prediction làm đáp án.

So **direction macro-F1/accuracy/coverage**, **nDCG/Recall/Precision/MRR** và **compliance@5/10**. F1 gộp confusion trên active context/focus; unknown gây miss; true ignore không tham gia.

Grade 1 vẫn positive cho Recall/MRR và có gain nDCG. Ranking tốt chưa chắc tuân thủ intent; compliance chỉ nhận grade 2.

Importance MAE so C weights được dùng với true session weights. Ba model cùng C weights sẽ cùng MAE.

## 9. Runner và lệnh

```text
kiểm tra A + C handoff + D
→ cắt C profile logs và D session logs trước cutoff
→ dựng importance + facet vectors
→ suy direction → ranking 20 candidates × 4 public methods
→ evaluator thêm oracle, đọc intents/labels → báo cáo
```

```powershell
python data/exp_d/build_exp_d.py --dry-run
python data/exp_d/build_exp_d.py
python data/exp_d/build_exp_d.py --validate-only
python scripts/exp_d/run_exp_d.py --dry-run
python scripts/exp_d/run_exp_d.py --ks 5 10
```

Đủ quota có 7.500 predictions gồm oracle. Output dưới `results/exp_d/`; report.md/details.jsonl và [sáu tệp chung](../BASELINE_GUIDE.md).

## 10. Thành viên D nghiên cứu gì?

Cải thiện suy hướng bằng parser ngữ nghĩa/query/reactions/confidence; giữ unknown khi thiếu tín hiệu. Encoder freeze cho facet similarity là phép thử biểu diễn riêng.

Chỉ thay encoder ranking **không tự cải thiện direction F1** nếu estimator giữ nguyên. Reranker có thể nhận directions dự đoán và evidence, không nhận intent thật. Giữ profile C cố định khi so hướng để xác định nguồn cải thiện.

D phụ thuộc dataset C, không phụ thuộc tiến độ nghiên cứu scorer C. Không cần bộ profile kiểm duyệt để chạy mock; người dùng/relevance thật là bước kiểm chứng sau.
