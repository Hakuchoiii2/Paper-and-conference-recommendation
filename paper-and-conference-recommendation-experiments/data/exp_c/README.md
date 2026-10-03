# Thực nghiệm C — Khuyến nghị theo ý định tường minh

Trạng thái: ưu tiên dựng mock data để kiểm thử trước;
chưa sinh dataset hoặc chạy mô hình của thực nghiệm.

**README này mô tả cách xây dataset.** Generator đọc nguyên liệu/cấu hình,
tạo cả dữ liệu quan sát được và nhãn/truth. Đầu vào mô hình là một phần của
dataset đã tạo, được nói riêng ở cuối; không coi output generator là prerequisite.

**Dùng trực tiếp corpus chính cho mọi exp:** `data/processed/papers.jsonl`
(4.210 bài hiện có), giữ nguyên title/abstract và `paper_id`. Generator đọc catalog
này rồi chọn query/candidates theo config; không dựng bộ bài 50 mẫu hoặc catalog
mock riêng. Các mốc pilot dưới đây chỉ giới hạn số query/case/user/events đầu ra.

**Facet dùng chung là silver do A trích từ bài thật:**
`data/exp_a/generated/facets_silver.jsonl`, kèm metadata/dẫn chứng và manifest
có `status: complete`. Năm facet: `problem`, `task`, `method`, `dataset`,
`contribution`. Không sinh facet giả hoặc thay title/abstract để khớp nhãn.
Mock của B–E là queries/intents/nhãn theo rule/users/hành vi; không phải mock corpus
hay mock facet. B/C/D không cần kết quả của nhau hoặc human gold A; E cần users D.

Output pilot ở `samples/generated/` và `samples/ground_truth/`; bộ mở rộng ở
`generated/` và `ground_truth/` trực tiếp dưới exp. Cả hai vẫn ghi
`dataset_kind: mock` nếu query/nhãn/hành vi được sinh tự động. Manifest ghi hash
corpus và facets A, seed 42, rule version và actual counts. Generator B–E chưa
được triển khai; A đã có bộ chạy Qwen3 local. Facet `[]` là thiếu bằng chứng, không phải
bài chưa annotation; chỉ chọn bài đủ thông tin cho rule đang xét.

## 1. Mục đích của dataset

C xét yêu cầu người dùng nói rõ, có thể kết hợp **nhiều facet và nhiều hướng**.
Khác với B chỉ hỏi một facet, C có thể yêu cầu “cùng vấn đề nhưng dùng phương pháp
khác”, hoặc “cùng phương pháp nhưng khác vấn đề”. Mục tiêu dữ liệu là xác định
ứng viên có thỏa toàn bộ ràng buộc không.

Ví dụ cùng vấn đề nhưng khác phương pháp: ứng viên chỉ giống vấn đề mà vẫn dùng
phương pháp cũ là một hard negative hữu ích. Chỉ tên intent không đủ định nghĩa
đáp án; phải có constraints và quy tắc so sánh được công bố.

## 2. Đầu vào của generator xây dataset

Generator C nhận **catalog/facets và templates**, rồi tự tạo các yêu cầu/đáp án.
`intents.jsonl` chưa có sẵn: đó là một trong các output phải sinh.

| Đầu vào generator | Đường dẫn/giá trị | Vai trò |
|---|---|---|
| Corpus chính `[đã có]` | `data/processed/papers.jsonl` | Bài làm anchor và tập bài eligible |
| Facets silver A `[cần chạy Qwen3]` | `data/exp_a/generated/facets_silver.jsonl` | Biết concept của các bài để chọn và chấm ứng viên |
| Intent templates `[cần xây]` | Đề xuất `configs/intent_templates.json` | Mỗi loại intent định nghĩa đủ năm directions, không chỉ tên loại |
| Rule/alias đã duyệt `[cần chốt]` | Theo contract/guideline và config version | Định nghĩa similar/different/ignore và xử lý missing |
| Cấu hình C `[cần xây]` | Đề xuất `configs/exp_c.json` | Kind mock, seed, 20 cases thử nhỏ; sau đó mục tiêu 1.500 cases, phân bổ types, số candidates/case, sampling và split policy |

Số candidates/case C chưa được chốt; không suy từ B rằng C luôn có 100 candidates.
Không cần đọc labels B để tạo C. Nếu muốn dùng nguồn nhãn khác phải công bố mode
và provenance riêng. Facet missing làm bài ineligible ở constraint đó.

**Các đường dẫn trong bảng tính từ thư mục gốc dự án**, không từ folder exp.
Tệp `[đã có]` có thể đọc ngay. Tệp/cấu hình `[cần xây]` là đề xuất interface cho
việc triển khai, chưa tồn tại và cần chốt trước khi viết/chạy generator.
Generator phải kiểm tra prerequisite, không âm thầm thay tệp thiếu bằng nhãn giả.
Tuân thủ [contract chung](../../DATA_CONTRACT.md), dùng cùng `paper_id`.

## 3. Đầu ra mock của generator xây dataset

| Đầu ra generator C `[chưa tạo]` | Nội dung |
|---|---|
| `data/exp_c/samples/generated/intents.jsonl` | Case ID, query paper, type, constraints, candidate IDs |
| `data/exp_c/samples/ground_truth/intent_labels.jsonl` | Mỗi candidate có satisfies_intent boolean |
| `data/exp_c/samples/generated/splits.json` `[đề xuất]` | Mapping case theo nhóm query paper |
| `data/exp_c/samples/generated/generation_report.json` `[đề xuất]` | Số case/type và lý do skip khi không đủ ứng viên |
| `data/exp_c/samples/generated/manifest.json` | Input facet/template/rule hashes, seed và actual counts |

Builder tạo cả yêu cầu và nhãn bằng facets/rules đầu vào. Nhãn như vậy là
rule-based/synthetic, không mặc nhiên là người thật xác nhận ý định; ghi provenance.
Mốc mock đầu: 20 cases. Mục tiêu mở rộng 1.500 cases không có nghĩa có 1.500 anchor papers độc lập.

## 4. Các trường trong dataset đầu ra

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

Tám intent types đề xuất: same_problem, same_problem_different_method,
same_method_different_problem, similar_task, different_dataset,
same_problem_same_method, similar_contribution, mixed_intent. Exact templates
và quota chưa duyệt; tên loại không tự định nghĩa labels.

## 5. Ví dụ generator: nguyên liệu → các tệp dataset

Đầu vào builder là catalog/facets, config và template, chưa phải danh sách
intents. Giả sử template same_problem_different_method đã được duyệt, builder
chọn anchor và ứng viên, kiểm tra concept, rồi sinh một case và nhãn dưới đây.
Trong kịch bản mock minh họa, hai bài chung problem và có method khác nhau; ví dụ chỉ minh họa schema; builder phải kiểm tra quan hệ trên facets A thực tế.

**Đầu vào generator: các đường dẫn và một phần config dự kiến** (chưa phải
config hoàn chỉnh/chưa đảm bảo rule đã được chốt):

```json
{
  "corpus_path": "data/processed/papers.jsonl",
  "facets_path": "data/exp_a/generated/facets_silver.jsonl",
  "templates_path": "configs/intent_templates.json",
  "dataset_kind": "mock",
  "seed": 42,
  "num_cases": 20
}
```

**Records generator sẽ ghi vào các tệp đầu ra:**

```json
{
  "intent_id": "I0001",
  "query_paper_id": "P000001",
  "intent_type": "same_problem_different_method",
  "constraints": {
    "problem": "similar",
    "task": "ignore",
    "method": "different",
    "dataset": "ignore",
    "contribution": "ignore"
  },
  "candidate_ids": [
    "P000003"
  ]
}
```

```json
{
  "intent_id": "I0001",
  "candidate_id": "P000003",
  "satisfies_intent": true
}
```

## 6. Các bước generator phải thực hiện

1. Đọc config, corpus, facets, templates/rule versions; join theo paper_id và
   kiểm tra template có đủ năm directions hợp lệ.
2. Chọn intent type theo quota, sau đó chọn anchor đủ facet cho type đó.
3. So facet anchor với các bài eligible theo từng constraint. Pilot đề xuất
   similar = có concept chung, different = hai tập nonempty không giao nhau,
   ignore = không xét; phải chốt rule/alias trước khi dùng.
4. Candidate positive phải thỏa mọi constraint. Negative vi phạm ít nhất một;
   hard negative ưu tiên vi phạm đúng một constraint khi khả thi.
5. Sample candidates theo config và seed, bỏ self/trùng; thiếu positive/negative
   thì skip case và báo lý do, không bịa satisfaction label.
6. Cấp intent_id; ghi intents và nhãn cho từng pair. Chia nhóm theo anchor,
   không random các case cùng anchor sang train/test khác nhau.
7. Ghi report/manifest, kiểm tra labels khớp rule, refs và coverage types.

Sau mock 20 cases, target mở rộng 1.500: phân bổ đề xuất 6 types × 200 + 2 types × 150. Tám types được đề
xuất trong phần field/rules trước; chốt exact templates/quota trước release.


**Chưa có generator mock C.** Bộ chạy A đã có; cần chạy Qwen3 để bàn giao silver.

### Khi cập nhật facets A

Giữ corpus/IDs; khi facets hoặc alias/rule thay đổi, chạy lại generator
để sinh lại labels/splits/events và cập nhật input hashes. Cả pilot và
bộ mở rộng vẫn công bố phần nhãn/hành vi synthetic, không tự đổi thành real.

## 7. Kiểm tra dataset và nghiệm thu

**Mốc hiện tại là nghiệm thu mock:** manifest ghi `dataset_kind: mock`, references
thuộc cùng catalog, generator tái lập và các kiểm tra bên dưới đạt. Human
gold A và số lượng mục tiêu đầy đủ không phải điều kiện bắt đầu mock;
facet silver A đủ coverage là đầu vào cần có.

- IDs resolve; constraints đúng năm khóa và enums, khớp template đã duyệt.
- Mỗi pair có đúng một boolean label; candidate sets không trùng/self-candidate.
- Đáp án khớp rule đã công bố; missing facet không bị xem là khác một cách mặc định.
- Có positive/negative hợp lệ hoặc case bị skip có lý do; báo coverage từng loại.
- Nhãn không vào observable inputs; cùng anchor không xuất hiện ở nhiều split.

C hoàn tất khi có facets đầu vào phù hợp, templates/rules được duyệt, generator,
labels/manifests và validator riêng đạt. Số dòng đạt 1.500 chưa đủ nghiệm thu.

Lệnh hiện có `python scripts/validate_all.py --dataset-kind real --phase corpus`
chỉ kiểm tra corpus chính. `--phase experiments` trả lỗi vì dataset/generator
và validator đầy đủ A–E chưa được triển khai. Kiểm tra corpus đạt không thay thế
review chất lượng nhãn, ngữ nghĩa hoặc giả thuyết bộ mô phỏng.

### Tách riêng: mô hình dùng dataset đã tạo thế nào?

Mô hình C đọc intents + corpus/facets; intent_labels chỉ đánh giá. Dataset generator được dùng facet rules để sinh labels, model evaluation không được đọc labels đó.
