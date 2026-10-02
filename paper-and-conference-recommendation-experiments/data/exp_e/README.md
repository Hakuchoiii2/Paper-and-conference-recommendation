# Thực nghiệm E — Theo dõi sở thích thay đổi theo thời gian

Người phụ trách: **Phú**. Trạng thái: đặc tả dữ liệu cho giai đoạn tiếp
theo; chưa sinh dataset hoặc chạy mô hình của thực nghiệm. Khải chốt quy ước chung.

## 1. Mục đích và câu hỏi thực nghiệm

E mở rộng bài toán sở thích ngầm sang tình huống mối quan tâm thay đổi. Lịch sử
rất cũ có thể phản ánh sở thích khác hiện tại. Câu hỏi thực nghiệm là hệ thống
có theo dõi được sự chuyển dịch đó và vẫn khuyến nghị phù hợp với giai đoạn mới
không, đồng thời có ổn định với người dùng không đổi sở thích không?

E dùng **cùng user IDs với D**, không tính thành thêm 300 người dùng. Luồng tương
tác E riêng để thể hiện drift; không cần giống từng byte với tương tác D.
Đây vẫn là mô phỏng, chưa phải hành vi thật hoặc mô hình temporal đã triển khai.

## 2. Định dạng đầu vào

Đọc danh tính user từ `../exp_d/generated/users.jsonl`; dùng corpus/facets chung
và lịch sử tương tác E được phép quan sát. Dữ liệu input không chứa truth của giai
đoạn tương lai. E phụ thuộc D ở danh tính user, không phụ thuộc việc dùng lại
split hoặc luồng tương tác của D.

Hiện D chưa có danh tính user và bộ mô phỏng chưa được duyệt; do đó E chưa có dataset.

Dùng `../processed/papers.jsonl` cho corpus đầy đủ;
`../fixtures/papers.jsonl` là bộ 50 bài thật tùy chọn để kiểm tra nhanh.
Tuân thủ [contract dùng chung](../../DATA_CONTRACT.md); không cấp ID riêng.

## 3. Định dạng đầu ra

| Tệp dự kiến | Vai trò |
|---|---|
| `generated/interactions_train.jsonl` | Lịch sử E, đề xuất các giai đoạn 1–3 |
| `ground_truth/interactions_test.jsonl` | Holdout E, đề xuất giai đoạn 4 |
| `ground_truth/temporal_profiles.jsonl` | Hồ sơ sở thích ẩn theo user và giai đoạn |
| Metadata giai đoạn/manifest | Boundaries, cutoff, tỷ lệ stable/drift, phiên bản simulator |

Không tạo một users.jsonl độc lập khiến danh tính lệch D. Truth từng period chỉ
dành cho generator/evaluation, không dùng làm observable profile của mô hình.

`samples/` lưu mẫu nhỏ được review khi dataset tồn tại; `generated/` lưu output
đầy đủ. Manifest ghi contract version, real/mock, seed, generator/input hashes
và số lượng thực tế. Nhãn, hồ sơ ẩn và dữ liệu tương lai tách khỏi đầu vào.

## 4. Định nghĩa trường dữ liệu

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

## 5. Ví dụ đầu vào và đầu ra

Các ID bài dưới đây lấy từ bộ mẫu thật, nhưng nhãn/hành vi/hồ sơ là **ví dụ
minh họa schema, chưa phải dữ liệu được release hoặc đáp án đã kiểm chứng**.
Giữ nguyên title/abstract nguồn trong ví dụ JSON; không dịch nội dung corpus.

Đầu vào quan sát được:

```json
{"user_id": "U0001", "paper_id": "P000054", "interaction_type": "view", "timestamp": "2026-01-10T10:00:00Z"}
```

Đơn vị đầu ra dự kiến:

```json
{"user_id":"U0001","period":1,"start_timestamp":"2026-01-01T00:00:00Z","end_timestamp":"2026-02-01T00:00:00Z","latent_preferences":{"method":{"example concept":0.8}}}
```

Với A, các list rỗng chỉ minh họa kiểu dữ liệu, không phải annotation thực tế.
Với B/C, không suy rằng ứng viên thật sự phù hợp từ nhãn ví dụ. Với D/E, user
và sở thích là minh họa; profile E nằm trong truth, không phải input mô hình.

## 6. Quy tắc tạo dữ liệu và hướng đánh giá

1. Dùng cùng danh tính D; công bố tỷ lệ user ổn định và user thay đổi trong cấu
   hình/manifest. Không để mọi khác biệt do random noise bị gọi thành drift.
2. Đề xuất 4 period: sở thích cũ → chuyển tiếp → sở thích mới → ổn định. Sinh
   latent profile từng period trước rồi sinh exposure/interaction tương ứng.
3. Nhóm stable giữ cấu trúc sở thích cơ bản qua các period; nhóm drift thay đổi
   concept/trọng số theo rule đã công bố. Mức nhiễu và độ mạnh drift cần chốt.
4. Target: cùng 300 user × 4 period = 1.200 profile, khoảng 15.000–20.000 event.
   Pilot nhỏ có thể dùng ít user, tối thiểu đủ tương tác ở mỗi period để kiểm tra.
5. Đề xuất period 1–3 là history, 4 là test. Công bố cutoff độc lập D; không tái
   sử dụng split D mà không kiểm tra timestamp. Không xây profile quan sát từ
   truth tương lai, kể cả khi generator đã biết toàn bộ kịch bản.

Đánh giá về sau cần so riêng stable và drift, xem mức theo kịp sở thích mới và
chất lượng trên holdout. Cơ chế temporal decay/model và chỉ số cụ thể chưa được
chọn ở phase dữ liệu; không thêm mô hình hoặc báo điểm chỉ để hoàn thiện README.

**Trạng thái triển khai:** chưa có generator cho thực nghiệm này. Các lệnh đang
chạy được từ thư mục gốc chỉ chuẩn bị corpus/bộ mẫu:

```powershell
python scripts/build_corpus.py
python scripts/build_fixture.py --seed 42
```

Không cần dùng bộ 50 bài để xử lý dữ liệu đầy đủ; corpus chung là nguồn chính.
Chưa annotation được facets thì không giả vờ đã sinh đủ dataset.

## 7. Quy tắc kiểm tra và điều kiện nghiệm thu

- User IDs thuộc D, không có danh tính mới; paper IDs thuộc đúng catalog.
- `(user_id,period)` duy nhất; đủ periods; boundaries liên tiếp và không chồng.
- Event trong `[start,end)` đúng period; history trước holdout theo từng user.
- Truth tương lai không lọt vào input/profile-building; không trộn E stream với D.
- Báo stable/drift ratio, profile/event counts, cutoff, nhiễu và mọi gap target.

E hoàn tất khi kịch bản/boundaries và bộ mô phỏng được duyệt, generator tái lập,
truth tách đúng, IDs thống nhất với D và validator riêng đạt. Hiện mới có đặc tả.

Lệnh hiện có `python scripts/validate_all.py --dataset-kind real --phase corpus`
chỉ kiểm tra corpus và bộ mẫu. `--phase experiments` trả lỗi vì dataset/generator
và validator đầy đủ A–E chưa được triển khai. Kiểm tra corpus đạt không thay thế
review chất lượng nhãn, ngữ nghĩa hoặc giả thuyết bộ mô phỏng.
