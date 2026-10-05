# Đánh giá cách Qwen trích năm facet

400 bài gold có thể dùng để đối chiếu silver trên **chính 400 bài đó**, sau khi
người review hoàn tất nhãn. Việc chọn 400 IDs chưa tạo gold. Bộ chọn hiện ưu tiên
silver đầy đủ và sạch, nên điểm trên cohort này chưa đại diện ngẫu nhiên toàn corpus.

## 1. Hoàn tất gold độc lập

Đọc `review_papers.jsonl` và guideline; điền năm facet trong
`data/exp_a/ground_truth/gold_review/review_annotations.jsonl`. Người review
xác định nhãn từ title/abstract, gồm cả ý Qwen có thể bỏ sót. Giữ `[]` khi thiếu
bằng chứng; không suy từ kiến thức ngoài bài. Chưa xem `silver_reference.jsonl`
trước khi hoàn tất bản review độc lập.

Mỗi record đã hoàn tất phải có `review_status: "reviewed"`, tên `reviewer` và
đủ năm list concept strings. Ví dụ **chỉ minh họa định dạng**, không phải gold thật:

```json
{
  "paper_id": "P000002",
  "reviewer": "Tên người đã kiểm tra",
  "review_status": "reviewed",
  "facets": {
    "problem": ["concept được title/abstract hỗ trợ"],
    "task": [],
    "method": [],
    "dataset": [],
    "contribution": []
  }
}
```

Theo guideline, hai người review độc lập một phần chung, trao đổi các bất đồng
problem/task hoặc method/contribution và chốt nghĩa nhãn. Dùng cách đặt concept
nhất quán theo nguồn; không sửa gold theo output Qwen để làm tăng điểm.
File manifest của queue lưu nguồn/IDs lúc chọn; hashes form ban đầu không còn
là hashes gold sau review. Evaluator ghi checksum của bản gold thực sự được chấm.

## 2. Chạy đối chiếu

Từ gốc dự án, dùng Python 3.11+; script chỉ cần thư viện chuẩn:

```powershell
python scripts/exp_a/evaluate_exp_a.py
```

Mặc định đọc silver/metadata/manifest đã kiểm tra tại `data/exp_a/generated/`,
và 400 forms reviewed tại đường dẫn trên. Có `--source`, `--gold`, `--output`
để chỉ định bản khác. `--expected-count` mặc định 400; chỉ đổi khi chủ động đánh
giá một cohort khác và ghi rõ kích thước đó.

Evaluator từ chối pending, thiếu người review, sai schema/count, concept trống
hoặc trùng, ID trùng/ngoài silver, ID lệch cohort và P000001 là ví dụ prompt.
Không tự bỏ records chưa review để cho ra điểm trên phần còn lại.
Silver partial được phép cho bước đánh giá nếu toàn bộ IDs gold đã có annotation;
report vẫn công bố số corpus/annotations/missing. Điều này không nới gate B–E.
Không sửa input, không gọi Qwen chấm lại chính nó, không chạy GPU inference.

Output mặc định `data/exp_a/evaluation/gold_400/` được Git bỏ qua:

| Tệp | Vai trò |
|---|---|
| `report.md` | Báo cáo dễ đọc với bảng Precision/Recall/F1 và giới hạn |
| `summary.json` | TP/FP/FN, per-facet và micro metrics, macro F1, exact papers, corpus audit |
| `per_paper.jsonl` | Bài, gold/silver, matched/extra/missing, dẫn chứng và possible_cross_facet |
| `manifest.json` | Hash gold, silver/cohort manifest, evaluator và các tệp báo cáo |

Chạy lại cùng input/code cho báo cáo giống nhau. Rebuild chỉ ghi vào thư mục
evaluation; không ghi đè queue human review hoặc các A parts.
Thư mục báo cáo không được trùng, chứa hoặc nằm trong thư mục silver nguồn.

## 3. Đọc kết quả

So sánh tập concepts **trong cùng paper và facet**:

| Chỉ số | Cách tính | Câu hỏi trả lời |
|---|---|---|
| TP | Nhãn silver khớp gold | Qwen đã trích được những nhãn gold nào? |
| FP | Nhãn silver dư so với gold | Nhãn nào cần rà xem dư, sai hoặc khác cách viết? |
| FN | Nhãn gold thiếu trong silver | Qwen đã bỏ sót nhãn nào theo quy tắc so khớp? |
| Precision | TP / (TP + FP) | Bao nhiêu nhãn Qwen đưa ra khớp gold? |
| Recall | TP / (TP + FN) | Bao nhiêu nhãn gold được Qwen tìm thấy? |
| F1 | 2TP / (2TP + FP + FN) | Tổng hợp khả năng trích khớp và hạn chế bỏ sót |

Report có từng problem/task/method/dataset/contribution; micro cộng TP/FP/FN
toàn bộ, macro F1 lấy trung bình các facet có mẫu. `N/A` nghĩa là mẫu số bằng 0,
không tự bằng 100%. Exact papers yêu cầu cả năm tập nhãn khớp, tính cả hai list rỗng.

Ví dụ thuần minh họa: Qwen trích method A/B, người review trích A/C →
TP=1, FP=1, FN=1; Precision=Recall=F1=0.5. Đây chưa phải điểm Qwen trên dữ liệu thật.

Công thức và cách cộng micro/lấy trung bình macro theo
[tài liệu metrics scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html).
Evaluator tính trực tiếp bằng stdlib, không cần cài thư viện này.

`per_paper.jsonl` giúp phân tích lỗi: đọc nội dung/dẫn chứng, xem extra và missing;
`possible_cross_facet` chỉ gợi ý khi nhãn dư xuất hiện trong facet gold khác,
không tự kết luận nhầm facet. Người review phân biệt nhãn sai, gán nhầm facet,
trích quá rộng/hẹp, bỏ sót hoặc hai cách diễn đạt cùng nghĩa.

## 4. Giới hạn cần giữ cùng kết quả

So khớp `nfkc_casefold_whitespace_v1`: chuẩn hóa Unicode, hoa/thường và khoảng
trắng, **giữ dấu câu** để C/C++/C# không bị gộp. Không tự coi từ đồng nghĩa hoặc
viết tắt là bằng nhau. Vì vậy đây là **lexical agreement với human gold**, chưa
là phép chấm ngữ nghĩa tự động. Những chênh lệch cùng nghĩa cần được review bằng
quy tắc thống nhất và ghi lại; không diễn giải mọi FP/FN máy tính là lỗi thật.

400 bài ưu tiên đầy đủ sẽ cho biết chất lượng trên nhóm đó. Nếu mục tiêu sau này
là ước lượng chất lượng toàn corpus, cần một đợt gold đánh giá đại diện được chọn
độc lập; không đổi cách chọn 400 bài hiện được yêu cầu mà không ghi rõ.
Không dùng cùng held-out gold để chỉnh prompt rồi báo điểm như đánh giá độc lập.

Corpus audit gồm coverage, fallback/quality flags và phân bố facet trống trên
toàn bộ silver đang có. Các số này không đo semantic accuracy ngoài gold.
Điểm `selected_score` 0–100 sẵn có của A đo bám nguồn/cấu trúc để chọn lượt sinh;
không phải độ chính xác, Precision/F1 hay xác suất nhãn đúng.
