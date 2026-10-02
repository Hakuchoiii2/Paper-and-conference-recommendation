# Thực nghiệm C — Khuyến nghị theo ý định tường minh

Người phụ trách: **Quỳnh**. Trạng thái: đặc tả dữ liệu cho giai đoạn tiếp
theo; chưa sinh dataset hoặc chạy mô hình của thực nghiệm. Khải chốt quy ước chung.

## 1. Mục đích và câu hỏi thực nghiệm

C xét yêu cầu người dùng nói rõ, có thể kết hợp **nhiều facet và nhiều hướng**.
Khác với B chỉ hỏi một facet, C có thể yêu cầu “cùng vấn đề nhưng dùng phương pháp
khác”, hoặc “cùng phương pháp nhưng khác vấn đề”. Mục tiêu dữ liệu là xác định
ứng viên có thỏa toàn bộ ràng buộc không.

Ví dụ cùng vấn đề nhưng khác phương pháp: ứng viên chỉ giống vấn đề mà vẫn dùng
phương pháp cũ là một hard negative hữu ích. Chỉ tên intent không đủ định nghĩa
đáp án; phải có constraints và quy tắc so sánh được công bố.

## 2. Định dạng đầu vào

`intents.jsonl` chứa bài truy vấn, loại intent, constraints đủ năm facet và tập
ứng viên. Corpus/facets được đọc từ nguồn chung đã review hoặc có provenance
annotation rõ ràng. Không đưa `satisfies_intent` vào observable input.

Hiện chưa có facets thật theo schema toàn cục, nên chưa sinh cases hợp lệ. Ví dụ
README chỉ minh họa cấu trúc; không kết luận hai bài mẫu thật có quan hệ facet.

Dùng `../processed/papers.jsonl` cho corpus đầy đủ;
`../fixtures/papers.jsonl` là bộ 50 bài thật tùy chọn để kiểm tra nhanh.
Tuân thủ [contract dùng chung](../../DATA_CONTRACT.md); không cấp ID riêng.

## 3. Định dạng đầu ra

| Tệp dự kiến | Nội dung |
|---|---|
| `generated/intents.jsonl` | Query, loại ý định, constraints và candidate IDs |
| `ground_truth/intent_labels.jsonl` | Một nhãn thỏa/không thỏa cho mỗi candidate |
| Templates/metadata có phiên bản | Constraints theo intent type, nguồn nhãn và số case bị skip |

Đáp án tách khỏi input; lý do skip và số thiếu target phải được báo cáo. Không
bịa positive khi corpus chưa có ứng viên đủ điều kiện.

`samples/` lưu mẫu nhỏ được review khi dataset tồn tại; `generated/` lưu output
đầy đủ. Manifest ghi contract version, real/mock, seed, generator/input hashes
và số lượng thực tế. Nhãn, hồ sơ ẩn và dữ liệu tương lai tách khỏi đầu vào.

## 4. Định nghĩa trường dữ liệu

| Trường | Ý nghĩa |
|---|---|
| `intent_id` | `I` + 4 chữ số; duy nhất |
| `query_paper_id` | Bài làm mốc so sánh |
| `intent_type` | Tên template đã được duyệt và versioned |
| `constraints` | Đủ `problem/task/method/dataset/contribution` |
| Direction | `similar`: tương tự; `different`: khác; `ignore`: không xét |
| `candidate_ids` | ID chung, không trùng hoặc chứa bài truy vấn |
| `satisfies_intent` | Boolean của cặp `(intent_id,candidate_id)` |

Đề xuất cho pilot theo concept chuẩn hóa: `similar` khi có concept chung;
`different` khi hai tập concept đều có dữ liệu và không giao nhau. Tất cả facet
không ignore phải được thỏa đồng thời. Bài truy vấn/ứng viên thiếu facet đang xét
là chưa đủ điều kiện, không tự thành `different`. Đây là quy tắc pilot cần duyệt,
không khẳng định exact match thể hiện đầy đủ tương đồng ngữ nghĩa.

## 5. Ví dụ đầu vào và đầu ra

Các ID bài dưới đây lấy từ bộ mẫu thật, nhưng nhãn/hành vi/hồ sơ là **ví dụ
minh họa schema, chưa phải dữ liệu được release hoặc đáp án đã kiểm chứng**.
Giữ nguyên title/abstract nguồn trong ví dụ JSON; không dịch nội dung corpus.

Đầu vào quan sát được:

```json
{"intent_id": "I0001", "query_paper_id": "P000054", "intent_type": "same_problem_different_method", "constraints": {"problem": "similar", "task": "ignore", "method": "different", "dataset": "ignore", "contribution": "ignore"}, "candidate_ids": ["P000205"]}
```

Đơn vị đầu ra dự kiến:

```json
{"intent_id":"I0001","candidate_id":"P000205","satisfies_intent":true}
```

Với A, các list rỗng chỉ minh họa kiểu dữ liệu, không phải annotation thực tế.
Với B/C, không suy rằng ứng viên thật sự phù hợp từ nhãn ví dụ. Với D/E, user
và sở thích là minh họa; profile E nằm trong truth, không phải input mô hình.

## 6. Quy tắc tạo dữ liệu và hướng đánh giá

1. Chốt constraints cụ thể cho từng loại trước khi dùng. Danh sách đề xuất gồm
   `same_problem`, `same_problem_different_method`, `same_method_different_problem`,
   `similar_task`, `different_dataset`, `same_problem_same_method`,
   `similar_contribution`, `mixed_intent`.
2. Dùng code và facets đầu vào để chọn ứng viên, gán nhãn theo cùng rule/version.
   Không chỉ gán nhãn dựa trên tên template; không cần chọn embedding lúc này.
3. Mỗi case có candidate thỏa và không thỏa. Ưu tiên hard negative chỉ vi phạm
   một constraint nếu corpus cho phép; nếu không có positive/negative đủ điều
   kiện thì skip và báo lý do/số lượng.
4. Target 1.500 cases; phân bổ đề xuất 6 loại × 200 và 2 loại × 150. Loại ý định
   và số phân bổ chỉ được áp dụng sau khi owner/Khải chốt.
5. Seed mặc định 42; sort đầu vào trước sampling. Nhiều intent cùng một query
   không tương đương nhiều query độc lập. Chia split theo nhóm bài truy vấn.

Đánh giá về sau có thể xét tỷ lệ ứng viên trong top-k thỏa toàn bộ constraints
và lỗi theo từng intent/facet. Trước khi chạy cần chốt k, tập eligible và quy tắc
nhãn; hiện chưa có generator hoặc kết quả C.

**Trạng thái triển khai:** chưa có generator cho thực nghiệm này. Các lệnh đang
chạy được từ thư mục gốc chỉ chuẩn bị corpus/bộ mẫu:

```powershell
python scripts/build_corpus.py
python scripts/build_fixture.py --seed 42
```

Không cần dùng bộ 50 bài để xử lý dữ liệu đầy đủ; corpus chung là nguồn chính.
Chưa annotation được facets thì không giả vờ đã sinh đủ dataset.

## 7. Quy tắc kiểm tra và điều kiện nghiệm thu

- IDs resolve; constraints đúng năm khóa và enums, khớp template đã duyệt.
- Mỗi pair có đúng một boolean label; candidate sets không trùng/self-candidate.
- Đáp án khớp rule đã công bố; missing facet không bị xem là khác một cách mặc định.
- Có positive/negative hợp lệ hoặc case bị skip có lý do; báo coverage từng loại.
- Nhãn không vào observable inputs; cùng anchor không xuất hiện ở nhiều split.

C hoàn tất khi có facets đầu vào phù hợp, templates/rules được duyệt, generator,
labels/manifests và validator riêng đạt. Số dòng đạt 1.500 chưa đủ nghiệm thu.

Lệnh hiện có `python scripts/validate_all.py --dataset-kind real --phase corpus`
chỉ kiểm tra corpus và bộ mẫu. `--phase experiments` trả lỗi vì dataset/generator
và validator đầy đủ A–E chưa được triển khai. Kiểm tra corpus đạt không thay thế
review chất lượng nhãn, ngữ nghĩa hoặc giả thuyết bộ mô phỏng.
