# Thực nghiệm B — Truy hồi bài báo theo một facet

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

B kiểm tra khả năng tìm bài liên quan theo **một khía cạnh được chỉ định** khi
đầu vào là một bài mẫu. Hai bài cùng lĩnh vực chưa chắc giống phương pháp; hai bài
khác ứng dụng vẫn có thể dùng phương pháp tương tự. Vì vậy relevance phải gắn
với facet của query, không chỉ với chủ đề chung.

Ví dụ: người đọc muốn tìm các bài dùng phương pháp tương tự bài đang đọc.
Dataset B cần bài truy vấn, tập ứng viên cố định và mức liên quan của từng ứng
viên. Chất lượng thứ tự xếp hạng là bước đánh giá mô hình về sau.

## 2. Đầu vào của generator xây dataset

Generator B đọc **corpus chính + năm facet silver A + cấu hình sampling/relevance**,
rồi tạo query, candidates và labels. Dùng facets silver A; không cần
human gold A hoặc judgments CSFCube để bắt đầu.

| Đầu vào | Đường dẫn | Vai trò |
|---|---|---|
| Corpus chính `[đã có]` | `data/processed/papers.jsonl` | Bài truy vấn và ứng viên dùng cùng IDs |
| Facets silver A `[cần chạy Qwen3]` | `data/exp_a/generated/facets_silver.jsonl` | Năm facet được trích từ title/abstract, có dẫn chứng |
| Cấu hình B `[cần xây]` | `configs/exp_b.json` | `dataset_kind: mock`, seed 42, 5 queries × 10 candidates, facet, rule version và split policy |

`target_facet` chỉ nhận `problem`, `task`, `method`, `dataset`, `contribution`.
Generator không đọc `retrieval_queries.jsonl` như nguyên liệu có sẵn: đây là output.
Tuân thủ [contract chung](../../DATA_CONTRACT.md); loader chọn đúng corpus chính.
Thiếu prerequisite thì báo lỗi; không tự chuyển giữa mock và real.

Ba facet `background/method/result` và nhãn 0–3 của CSFCube giữ ở raw. Benchmark
native chỉ là hướng bổ sung về sau nếu nhóm cần, không thay B năm facet và không
nằm trên luồng mock hiện tại. SciFact SUPPORT/CONTRADICT không phải relevance B.

## 3. Đầu ra của generator xây dataset

| Output mock `[chưa tạo]` | Nội dung |
|---|---|
| `data/exp_b/samples/generated/retrieval_queries.jsonl` | query_id, query_paper_id, target_facet, candidate_ids |
| `data/exp_b/samples/ground_truth/retrieval_labels.jsonl` | Nhãn 0/1/2 cho mỗi cặp query/candidate |
| `data/exp_b/samples/ground_truth/label_provenance.jsonl` | Nguồn synthetic, rule version và input facets |
| `data/exp_b/samples/generated/splits.json` | Chia theo nhóm bài truy vấn |
| `data/exp_b/samples/generated/manifest.json` | Kind mock, seed, hashes, số query/pair, skipped và gap |

Mốc đầu: 5 query × 10 candidates = 50 cặp, ưu tiên phủ đủ năm target facets.
Query và nhãn đều do builder tạo. Nhãn phục vụ kiểm thử, không phải người gán.
Khi mở rộng, giữ corpus/facets A; output chuyển về
`data/exp_b/generated/` và `data/exp_b/ground_truth/`. Mục tiêu mở rộng
300 query × 100 candidates chỉ áp dụng khi có đủ bài và nhãn hợp lệ.

## 4. Các trường trong dataset đầu ra

| Trường | Ý nghĩa/ràng buộc |
|---|---|
| `query_id` | `Q` + 4 chữ số; duy nhất trong bộ |
| `query_paper_id` | ID bài làm ví dụ truy vấn |
| `target_facet` | Một trong năm khóa `problem/task/method/dataset/contribution` |
| `candidate_ids` | List ID canonical; không trùng; không chứa query paper |
| `candidate_id` trong nhãn | Phải thuộc candidate set của query đó |
| `relevance` nội bộ | Đề xuất 0: không liên quan, 1: một phần, 2: cao |

Khóa duy nhất của nhãn: `(query_id,candidate_id)`. Đề xuất rule mock: trên facet
đích có dữ liệu, hai tập concept bằng nhau → 2; giao nhau nhưng khác tập → 1;
không giao nhau → 0. Thiếu facet đích ở anchor/candidate → ineligible.
Ghi rule/alias version trong config trước khi sinh. Đây là đáp án của kịch
bản mock, chưa đại diện đầy đủ cho tương đồng ngữ nghĩa trên bài thật.
Hard negative có facet khác giống anchor nhưng facet đích không giao nhau;
easy negative khác cả facet đích lẫn các facet được rule dùng để chọn mẫu.

## 5. Ví dụ generator: nguyên liệu → các tệp dataset

Giả sử facets A thực tế có method `["matrix factorization"]` cho cả `P000001`
và `P000002`, rule mock cho relevance 2. Ví dụ này chỉ minh họa schema;
chỉ dùng cặp bài đó khi nhãn A thực tế xác nhận, không hardcode vào generator. Title/abstract/IDs giữ nguyên từ
corpus chính. Ví dụ hiển thị một candidate; pilot dự kiến có 10 candidates/query.

**Đầu vào generator: các đường dẫn và một phần config dự kiến** (chưa phải
config hoàn chỉnh/chưa đảm bảo rule đã được chốt):

```json
{
  "corpus_path": "data/processed/papers.jsonl",
  "facets_path": "data/exp_a/generated/facets_silver.jsonl",
  "dataset_kind": "mock",
  "seed": 42,
  "num_queries": 5,
  "candidates_per_query": 10,
  "label_rule_version": "requires-rule-review"
}
```

**Records generator sẽ ghi vào các tệp đầu ra:**

```json
{
  "query_id": "Q0001",
  "query_paper_id": "P000001",
  "target_facet": "method",
  "candidate_ids": [
    "P000002"
  ]
}
```

```json
{
  "query_id": "Q0001",
  "candidate_id": "P000002",
  "relevance": 2
}
```

## 6. Các bước generator phải thực hiện

1. Đọc corpus chính và facets silver A, config và rule version; join theo paper_id.
2. Chọn anchor có facet đích; tạo positive, partial, hard/easy negative theo rule.
3. Chọn 5 queries × 10 candidates bằng seed 42; loại self-candidate và ID trùng.
4. Sinh đủ nhãn cho chính candidate set đã chọn; chưa có nhãn không tự bằng 0.
5. Chia theo nhóm anchor để cùng bài truy vấn không tràn các split.
6. Ghi query, labels, provenance và manifest; kiểm tra refs, positives và leakage.
7. Chạy lại cùng input/seed để kiểm tra tái lập. Thiếu candidates thì báo gap.

Khi mở rộng hoặc cập nhật facets A, sinh lại candidates/labels/splits theo
input version đã ghi. Nhãn sinh bằng rule vẫn ghi synthetic; chất lượng đánh giá
thật cần review riêng.

**Chưa có generator mock B hoặc lệnh chạy nó.** Việc cập nhật README chưa tạo dataset.

## 7. Kiểm tra dataset và nghiệm thu

- Query/candidate resolve trong đúng catalog; không self-candidate hoặc trùng ID.
- Nhãn không thừa/thiếu/nhân đôi so với chính sách judged đã công bố.
- Positive tồn tại; nguồn/scale/mapping relevance có giải thích, không trộn ngầm.
- Query anchors không tràn các split tùy chỉnh; nhãn không nằm trong input dự đoán.
- Manifest ghi mock/synthetic, actual counts, rule version và mọi pair còn unjudged.

Mốc mock B hoàn tất khi generator tái lập trên corpus chính kèm facets silver A năm facet, đủ mẫu hợp lệ,
manifest ghi mock và kiểm tra cấu trúc/rule/leakage đạt. Mốc này dùng silver A nhưng không yêu cầu
human gold A hoặc native CSFCube. Đánh giá B với nhãn được kiểm chứng là bước tiếp theo.

Lệnh hiện có `python scripts/validate_all.py --dataset-kind real --phase corpus`
chỉ kiểm tra corpus chính. `--phase experiments` trả lỗi vì dataset/generator
và validator đầy đủ A–E chưa được triển khai. Kiểm tra corpus đạt không thay thế
review chất lượng nhãn, ngữ nghĩa hoặc giả thuyết bộ mô phỏng.

### Tách riêng: mô hình dùng dataset đã tạo thế nào?

Mô hình B đọc retrieval_queries và corpus/facets được phép; nhãn relevance giữ cho evaluation. Mô hình tạo ranking/scores, không tạo candidate catalog/ground truth thay generator.
