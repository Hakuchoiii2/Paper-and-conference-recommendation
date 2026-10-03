# Thực nghiệm E — Theo dõi sở thích thay đổi theo thời gian

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

E mở rộng bài toán sở thích ngầm sang tình huống mối quan tâm thay đổi. Lịch sử
rất cũ có thể phản ánh sở thích khác hiện tại. Câu hỏi thực nghiệm là hệ thống
có theo dõi được sự chuyển dịch đó và vẫn khuyến nghị phù hợp với giai đoạn mới
không, đồng thời có ổn định với người dùng không đổi sở thích không?

E dùng **cùng user IDs với D**, pilot dùng lại 5 users mock D; khi mở rộng dùng lại 300 users D. Luồng tương
tác E riêng để thể hiện drift; không cần giống từng byte với tương tác D.
Đây vẫn là mô phỏng, chưa phải hành vi thật hoặc mô hình temporal đã triển khai.

## 2. Đầu vào của generator xây dataset

Generator E nhận **users do D tạo + corpus/facets + kịch bản thời gian**, rồi
sinh profiles và một luồng events E mới. Nó không cần lịch sử E có sẵn.

| Đầu vào generator | Đường dẫn/giá trị | Vai trò |
|---|---|---|
| Users D `[chưa có]` | `data/exp_d/samples/generated/users.jsonl` | Danh tính dùng chung; E không tạo user IDs mới |
| Corpus chính `[đã có]` | `data/processed/papers.jsonl` | Pool bài theo đúng ID chung |
| Facets silver A `[cần chạy Qwen3]` | `data/exp_a/generated/facets_silver.jsonl` | Vocabulary cho profiles theo period và tính affinity |
| Cấu hình E `[cần xây]` | Đề xuất `configs/exp_e.json` | Seed, 4 periods/boundaries, stable/drift ratio, drift rule, noise/exposure và số events |
| Latent profiles D `[tùy chọn, chưa có]` | `data/exp_d/samples/ground_truth/latent_user_profiles.jsonl` | Chỉ nếu config yêu cầu dùng làm sở thích period đầu; đây là input của simulator, không phải input mô hình |

Không mặc định đọc interactions_train/test của D để đổi tên thành E. E tạo stream
riêng. Nếu cần kế thừa D profile, khai báo rõ mode/input version; nếu không thì
sinh profile khởi đầu từ cùng vocabulary bằng rule E đã công bố.

**Các đường dẫn trong bảng tính từ thư mục gốc dự án**, không từ folder exp.
Tệp `[đã có]` có thể đọc ngay. Tệp/cấu hình `[cần xây]` là đề xuất interface cho
việc triển khai, chưa tồn tại và cần chốt trước khi viết/chạy generator.
Generator phải kiểm tra prerequisite, không âm thầm thay tệp thiếu bằng nhãn giả.
Tuân thủ [contract chung](../../DATA_CONTRACT.md), dùng cùng `paper_id`.

## 3. Đầu ra mock của generator xây dataset

| Đầu ra generator E `[chưa tạo]` | Nội dung |
|---|---|
| `data/exp_e/samples/ground_truth/temporal_profiles.jsonl` | Pilot 5 users × 4 periods = 20 profiles ẩn |
| `data/exp_e/samples/generated/interactions_train.jsonl` | E events thuộc periods 1–3 theo policy đề xuất |
| `data/exp_e/samples/ground_truth/interactions_test.jsonl` | E events period 4 làm holdout |
| `data/exp_e/samples/ground_truth/period_metadata.json` `[đề xuất]` | Boundaries và scenario/group information dành cho generator/evaluation |
| `data/exp_e/samples/generated/manifest.json` | Stable/drift counts, seed, source users/facet hashes, cutoff và actual events |

Mốc mock: cùng 5 users D × 4 periods, ít nhất 2 events/user/period (ít nhất 40 events).
Target mở rộng: 300 users, 1.200 profiles và tổng 15.000–20.000 events; phân bổ events/period và tỷ lệ
stable/drift chưa chốt, phải ghi trong config. Không nhân đôi số user khi cộng D/E.
Profiles/boundaries đã được generator biết không được lộ future truth cho model.

## 4. Các trường trong dataset đầu ra

| Trường | Ý nghĩa/ràng buộc |
|---|---|
| `user_id` | Phải có trong users của D |
| `period` | Chỉ số giai đoạn; đề xuất 1–4 |
| `start_timestamp`, `end_timestamp` | Khoảng nửa kín `[start,end)`, timezone rõ ràng |
| `latent_preferences` | Cùng cấu trúc trọng số facet/concept của D, chỉ trong truth |
| Event fields | `user_id`, `paper_id`, `interaction_type`, `timestamp` như D |

Khóa duy nhất profile: `(user_id,period)`. Các period liên tiếp, không overlap.
Event đúng tại `end` thuộc period tiếp theo, không thuộc period vừa kết thúc.
Trọng số phải hữu hạn trong [-1,1]. Nhóm stable/drift cần provenance cho đánh giá,
không tự động trở thành đặc trưng mô hình biết trước.

## 5. Ví dụ generator: nguyên liệu → các tệp dataset

Builder đọc U0001 từ D, tạo hồ sơ period 1 rồi sinh một event dựa trên hồ sơ đó.
Hai records dưới đều là đầu ra E, không phải generator đọc một event rồi suy
ngược ra temporal truth. Concept và trọng số chỉ là minh họa schema.

**Đầu vào generator: các đường dẫn và một phần config dự kiến** (chưa phải
config hoàn chỉnh/chưa đảm bảo rule đã được chốt):

```json
{
  "users_path": "data/exp_d/samples/generated/users.jsonl",
  "corpus_path": "data/processed/papers.jsonl",
  "facets_path": "data/exp_a/generated/facets_silver.jsonl",
  "dataset_kind": "mock",
  "seed": 42,
  "num_periods": 4,
  "history_periods": [
    1,
    2,
    3
  ],
  "holdout_period": 4
}
```

**Records generator sẽ ghi vào các tệp đầu ra:**

```json
{
  "user_id": "U0001",
  "period": 1,
  "start_timestamp": "2026-01-01T00:00:00Z",
  "end_timestamp": "2026-02-01T00:00:00Z",
  "latent_preferences": {
    "method": {
      "example concept": 0.8
    }
  }
}
```

```json
{
  "user_id": "U0001",
  "paper_id": "P000002",
  "interaction_type": "view",
  "timestamp": "2026-01-10T10:00:00Z"
}
```

## 6. Các bước generator phải thực hiện

1. Đọc users D và join corpus/facets; kiểm tra IDs/version và config periods.
2. Kiểm tra bốn khoảng [start,end) liên tiếp, không overlap; chia nhóm stable
   và drift theo ratio config và seed.
3. Sinh latent profile trước cho từng user/period. Stable giữ sở thích cơ bản;
   drift đi qua cũ → chuyển tiếp → mới → ổn định theo rule/intensity đã chốt.
4. Trong mỗi period, sinh exposure và events từ profile period đó + seeded
   noise; timestamps phải thuộc đúng [start,end).
5. Tách periods 1–3 history và 4 test theo policy đề xuất; không reuse cutoff D
   ngầm. Event đúng boundary thuộc period tiếp theo.
6. Ghi temporal_profiles, hai stream events, metadata và manifest. Không ghi
   một users catalog độc lập khiến E lệch D.
7. Validate user refs về D, paper refs, profile uniqueness, boundaries/time,
   actual quota/group counts và future leakage.

Target mở rộng 1.200 profiles và 15.000–20.000 events là dữ liệu mô phỏng. Phân biệt hiệu
ứng drift với noise bằng rule rõ và nhóm stable, không diễn giải mọi biến động
ngẫu nhiên là đổi sở thích.


**Chưa có generator mock E.** Bộ chạy A đã có; cần chạy Qwen3 để bàn giao silver.

### Khi cập nhật facets A

Giữ corpus/IDs; khi facets hoặc alias/rule thay đổi, chạy lại generator
để sinh lại labels/splits/events và cập nhật input hashes. Cả pilot và
bộ mở rộng vẫn công bố phần nhãn/hành vi synthetic, không tự đổi thành real.

## 7. Kiểm tra dataset và nghiệm thu

**Mốc hiện tại là nghiệm thu mock:** manifest ghi `dataset_kind: mock`, references
thuộc cùng catalog, generator tái lập và các kiểm tra bên dưới đạt. Human
gold A và số lượng mục tiêu đầy đủ không phải điều kiện bắt đầu mock;
facet silver A đủ coverage là đầu vào cần có.

- User IDs thuộc D, không có danh tính mới; paper IDs thuộc đúng catalog.
- `(user_id,period)` duy nhất; đủ periods; boundaries liên tiếp và không chồng.
- Event trong `[start,end)` đúng period; history trước holdout theo từng user.
- Truth tương lai không lọt vào input/profile-building; không trộn E stream với D.
- Báo stable/drift ratio, profile/event counts, cutoff, nhiễu và mọi gap target.

E hoàn tất khi kịch bản/boundaries và bộ mô phỏng được duyệt, generator tái lập,
truth tách đúng, IDs thống nhất với D và validator riêng đạt. Hiện mới có đặc tả.

Lệnh hiện có `python scripts/validate_all.py --dataset-kind real --phase corpus`
chỉ kiểm tra corpus chính. `--phase experiments` trả lỗi vì dataset/generator
và validator đầy đủ A–E chưa được triển khai. Kiểm tra corpus đạt không thay thế
review chất lượng nhãn, ngữ nghĩa hoặc giả thuyết bộ mô phỏng.

### Tách riêng: mô hình dùng dataset đã tạo thế nào?

Mô hình E đọc shared users + E history + corpus/facets. Generator được biết profiles tất cả periods; model không biết future profile/test events hoặc scenario group truth trước.
