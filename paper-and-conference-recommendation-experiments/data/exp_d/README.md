# Thực nghiệm D — Suy ra sở thích ngầm từ hành vi người dùng

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

D chuẩn bị dữ liệu kiểm tra việc suy ra sở thích từ hành vi như xem, lưu, thích
hoặc không thích bài. Người dùng không cần nhập constraints như C. Mô hình về
sau chỉ thấy lịch sử; bộ đánh giá có hồ sơ sở thích ẩn để kiểm tra kết quả.

Giai đoạn đầu dùng **người dùng và hành vi giả lập trên corpus chính và nhãn
silver A năm facet**. Hành vi được sinh từ sở thích ẩn và facets A
trên cùng corpus. Mục đích
là kiểm tra pipeline và giả thuyết của bộ mô phỏng; không trình bày đây là hành
vi người dùng thực tế hoặc bằng chứng hệ thống đã hữu ích ngoài đời.

## 2. Đầu vào của generator xây dataset

Generator D nhận **bài/facets và cấu hình mô phỏng**, không yêu cầu đã có users
hoặc lịch sử tương tác. Nó sẽ tự sinh users, latent profiles và events.

| Đầu vào generator | Đường dẫn/giá trị | Vai trò |
|---|---|---|
| Corpus chính `[đã có]` | `data/processed/papers.jsonl` | Các bài user có thể được tiếp xúc |
| Facets silver A `[cần chạy Qwen3]` | `data/exp_a/generated/facets_silver.jsonl` | Vocabulary/concepts để sinh sở thích và tính affinity bài |
| Cấu hình D `[cần xây]` | Đề xuất `configs/exp_d.json` | Kind mock, seed 42, 5 users × 10 events, đề xuất 6 history/4 future; timezone/cutoff policy |
| Quy tắc simulator `[cần chốt]` | Trong config có phiên bản | Phân phối latent weights [-1,1], chọn exposure, affinity → interaction, nhiễu, sampling có/không lặp |

Users và interactions_train không phải prerequisite. Không có log người dùng thật
được cung cấp cho phase này. Nếu thêm chế độ import log thật sau này phải định
nghĩa input/protocol khác, không gọi output mô phỏng là hành vi thu thập thật.

**Các đường dẫn trong bảng tính từ thư mục gốc dự án**, không từ folder exp.
Tệp `[đã có]` có thể đọc ngay. Tệp/cấu hình `[cần xây]` là đề xuất interface cho
việc triển khai, chưa tồn tại và cần chốt trước khi viết/chạy generator.
Generator phải kiểm tra prerequisite, không âm thầm thay tệp thiếu bằng nhãn giả.
Tuân thủ [contract chung](../../DATA_CONTRACT.md), dùng cùng `paper_id`.

## 3. Đầu ra mock của generator xây dataset

| Đầu ra generator D `[chưa tạo]` | Nội dung |
|---|---|
| `data/exp_d/samples/generated/users.jsonl` | 5 ID pilot và metadata quan sát được; không chứa latent preferences |
| `data/exp_d/samples/ground_truth/latent_user_profiles.jsonl` | 5 hồ sơ sở thích ẩn đã sinh trước events |
| `data/exp_d/samples/generated/interactions_train.jsonl` | Pilot đề xuất 5 × 6 = 30 past events |
| `data/exp_d/samples/ground_truth/interactions_test.jsonl` | Pilot đề xuất 5 × 4 = 20 future events |
| `data/exp_d/samples/generated/manifest.json` | Input/rule hashes, seed, cutoff và số user/events thực tế |

Nếu cần ranking evaluation, thêm exposure/candidate pool có event linkage theo
schema đã duyệt. Hiện chưa chốt schema sự kiện exposure nên không giả vờ tệp
đã có. Không coi mọi unobserved paper là negative.

## 4. Các trường trong dataset đầu ra

| Trường | Ý nghĩa/ràng buộc |
|---|---|
| `user_id` | `U` + 4 chữ số; duy nhất trong users |
| `paper_id` | Bài thuộc đúng corpus |
| `interaction_type` | `click`, `view`, `save`, `like`, `dislike` |
| `timestamp` | ISO-8601 có timezone, ưu tiên UTC |
| `latent_preferences` | Map facet → concept → trọng số sở thích, chỉ trong truth |
| Trọng số | Số hữu hạn thuộc [-1,1]; âm có thể biểu diễn không thích |

Mỗi event là một tương tác phát sinh sau khi user được tiếp xúc với bài. Không
mặc định `view` là thích mạnh. Quy tắc affinity → interaction và mức nhiễu phải
được công bố, không giấu trong code. Hồ sơ latent không nằm trong users observable.

## 5. Ví dụ generator: nguyên liệu → các tệp dataset

Builder tự tạo U0001, sinh latent preferences rồi mới chọn paper và event.
Một record trong users và một history event được minh họa dưới; latent profiles
và future events cũng là output, nằm riêng trong ground_truth. Không phải đưa
U0001 hoặc history file vào trước để generator đoán ra tương tác.

**Đầu vào generator: các đường dẫn và một phần config dự kiến** (chưa phải
config hoàn chỉnh/chưa đảm bảo rule đã được chốt):

```json
{
  "corpus_path": "data/processed/papers.jsonl",
  "facets_path": "data/exp_a/generated/facets_silver.jsonl",
  "dataset_kind": "mock",
  "seed": 42,
  "num_users": 5,
  "events_per_user": 10,
  "history_events_per_user": 6,
  "future_events_per_user": 4
}
```

**Records generator sẽ ghi vào các tệp đầu ra:**

```json
{
  "user_id": "U0001"
}
```

```json
{
  "user_id": "U0001",
  "paper_id": "P000002",
  "interaction_type": "like",
  "timestamp": "2026-01-10T10:00:00Z"
}
```

## 6. Các bước generator phải thực hiện

1. Join corpus với facets theo ID; xác định vocabulary eligible và đọc config.
2. Tạo 5 users mock U0001–U0005; chỉ ghi metadata observable vào users.
3. Sinh latent profile cho mỗi user trước: concept nào thích/không thích và
   trọng số finite [-1,1] theo phân phối simulator đã duyệt.
4. Sinh exposure: user được nhìn thấy các paper nào. Tính affinity từ latent
   preferences và paper facets theo rule được công bố.
5. Thêm noise có seed; chuyển affinity thành click/view/save/like/dislike theo
   rule đã chốt. Không random behavior rồi gán ngược latent profile.
6. Gán timestamps có timezone và sort từng user; chia 6 past/4 future trong pilot theo
   cutoff policy. Các event cùng timestamp cùng phía; thiếu quota hợp lệ báo gap.
7. Ghi users, latent profiles và hai tệp events; ghi manifest rồi validate IDs,
   range/time/counts và sự tách observable/hidden/future.

Sau pilot 5 users × 10 events, target mở rộng 300 users × 50 = 15.000 events là 9.000 history + 6.000 holdout. Đây là số event, không phải
15.000 bài hoặc 300 người dùng thật. Bộ mô phỏng phải công bố cả noise/exposure.


**Chưa có generator mock D.** Bộ chạy A đã có; cần chạy Qwen3 để bàn giao silver.

### Khi cập nhật facets A

Giữ corpus/IDs; khi facets hoặc alias/rule thay đổi, chạy lại generator
để sinh lại labels/splits/events và cập nhật input hashes. Cả pilot và
bộ mở rộng vẫn công bố phần nhãn/hành vi synthetic, không tự đổi thành real.

## 7. Kiểm tra dataset và nghiệm thu

**Mốc hiện tại là nghiệm thu mock:** manifest ghi `dataset_kind: mock`, references
thuộc cùng catalog, generator tái lập và các kiểm tra bên dưới đạt. Human
gold A và số lượng mục tiêu đầy đủ không phải điều kiện bắt đầu mock;
facet silver A đủ coverage là đầu vào cần có.

- User/paper refs resolve; observable users không chứa latent weights.
- Trọng số hữu hạn và đúng range; timestamps có timezone; enum hành vi hợp lệ.
- Mỗi user có lịch sử và holdout; latest train < earliest test một cách nghiêm ngặt.
- Không dùng tương tác test hoặc hidden truth để sinh profile đầu vào mô hình.
- Báo số user/events, exposure policy, mức nhiễu và phân phối hành vi thực tế.

D hoàn tất khi bộ mô phỏng có quy tắc được duyệt, generator tái lập, các tệp tách
đúng vai trò, manifests và validator riêng đạt; chưa tạo dữ liệu D ở phase hiện tại.

Lệnh hiện có `python scripts/validate_all.py --dataset-kind real --phase corpus`
chỉ kiểm tra corpus chính. `--phase experiments` trả lỗi vì dataset/generator
và validator đầy đủ A–E chưa được triển khai. Kiểm tra corpus đạt không thay thế
review chất lượng nhãn, ngữ nghĩa hoặc giả thuyết bộ mô phỏng.

### Tách riêng: mô hình dùng dataset đã tạo thế nào?

Mô hình D đọc users observable + history + corpus/facets. Simulator được dùng latent truth để sinh behavior, nhưng model/profile-building không đọc latent profiles hoặc future events.
