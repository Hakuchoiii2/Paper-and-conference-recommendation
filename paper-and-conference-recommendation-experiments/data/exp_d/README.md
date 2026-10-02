# Thực nghiệm D — Suy ra sở thích ngầm từ hành vi người dùng

Người phụ trách: **Phú**. Trạng thái: đặc tả dữ liệu cho giai đoạn tiếp
theo; chưa sinh dataset hoặc chạy mô hình của thực nghiệm. Khải chốt quy ước chung.

## 1. Mục đích và câu hỏi thực nghiệm

D chuẩn bị dữ liệu kiểm tra việc suy ra sở thích từ hành vi như xem, lưu, thích
hoặc không thích bài. Người dùng không cần nhập constraints như C. Mô hình về
sau chỉ thấy lịch sử; bộ đánh giá có hồ sơ sở thích ẩn để kiểm tra kết quả.

Giai đoạn dự kiến dùng **người dùng và hành vi giả lập trên bài thật**. Mục đích
là kiểm tra pipeline và giả thuyết của bộ mô phỏng; không trình bày đây là hành
vi người dùng thực tế hoặc bằng chứng hệ thống đã hữu ích ngoài đời.

## 2. Định dạng đầu vào

`users.jsonl` chỉ chứa ID và metadata quan sát được. `interactions_train.jsonl`
chứa lịch sử được phép dùng để suy ra sở thích; nội dung bài/facets đọc từ catalog
chung. Loader phải dùng đường dẫn rõ ràng, không đọc latent profiles hay tương tác
tương lai để xây hồ sơ.

Hiện chưa có người dùng, facets đầu vào hoặc bộ mô phỏng được duyệt. ID U0001
trong ví dụ là minh họa format, không khẳng định đã có user thật.

Dùng `../processed/papers.jsonl` cho corpus đầy đủ;
`../fixtures/papers.jsonl` là bộ 50 bài thật tùy chọn để kiểm tra nhanh.
Tuân thủ [contract dùng chung](../../DATA_CONTRACT.md); không cấp ID riêng.

## 3. Định dạng đầu ra

| Tệp dự kiến | Vai trò |
|---|---|
| `generated/users.jsonl` | Danh tính và metadata quan sát được |
| `generated/interactions_train.jsonl` | Lịch sử phục vụ profile-building |
| `ground_truth/interactions_test.jsonl` | Tương tác tương lai chỉ để đánh giá |
| `ground_truth/latent_user_profiles.jsonl` | Sở thích ẩn đã dùng để sinh hành vi |

Nếu đánh giá ranking, cần lưu exposure/candidate pool từng sự kiện. Không coi
mọi bài người dùng chưa tương tác là negative; có thể họ chưa được nhìn thấy.

`samples/` lưu mẫu nhỏ được review khi dataset tồn tại; `generated/` lưu output
đầy đủ. Manifest ghi contract version, real/mock, seed, generator/input hashes
và số lượng thực tế. Nhãn, hồ sơ ẩn và dữ liệu tương lai tách khỏi đầu vào.

## 4. Định nghĩa trường dữ liệu

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

## 5. Ví dụ đầu vào và đầu ra

Các ID bài dưới đây lấy từ bộ mẫu thật, nhưng nhãn/hành vi/hồ sơ là **ví dụ
minh họa schema, chưa phải dữ liệu được release hoặc đáp án đã kiểm chứng**.
Giữ nguyên title/abstract nguồn trong ví dụ JSON; không dịch nội dung corpus.

Đầu vào quan sát được:

```json
{"user_id": "U0001"}
```

Đơn vị đầu ra dự kiến:

```json
{"user_id":"U0001","paper_id":"P000205","interaction_type":"like","timestamp":"2026-01-10T10:00:00Z"}
```

Với A, các list rỗng chỉ minh họa kiểu dữ liệu, không phải annotation thực tế.
Với B/C, không suy rằng ứng viên thật sự phù hợp từ nhãn ví dụ. Với D/E, user
và sở thích là minh họa; profile E nằm trong truth, không phải input mô hình.

## 6. Quy tắc tạo dữ liệu và hướng đánh giá

1. Sinh hồ sơ sở thích ẩn trước, trên vocabulary/facet đã chốt. Chọn exposure
   và sinh tương tác theo độ phù hợp với hồ sơ cộng nhiễu có seed.
2. Không random toàn bộ tương tác rồi gán sở thích ngược lại để có vẻ khớp.
   Công bố phân phối hồ sơ, cơ chế chọn bài, loại hành vi và ảnh hưởng của nhiễu.
3. Target 300 user × 50 tương tác = 15.000: đề xuất mỗi user 30 quá khứ và 20
   tương lai. Đây là target mô phỏng, không phải 300 người dùng thật.
4. Chia theo thời gian từng user; event cùng timestamp phải ở cùng phía cutoff.
   Không random split khiến tương tác tương lai xuất hiện trong lịch sử.
5. Người dùng và ID của D là nguồn danh tính cho E. Ghi seed, input facets/version,
   simulator/version, cutoff và actual counts vào manifest.

Đánh giá về sau có thể kiểm tra độ khớp hồ sơ suy ra với truth và khả năng dự
đoán/xếp hạng trên holdout. Ranking chỉ có ý nghĩa khi candidate/exposure protocol
rõ ràng. Kết quả mô phỏng phải được tách khỏi kết luận về người dùng thực tế.

**Trạng thái triển khai:** chưa có generator cho thực nghiệm này. Các lệnh đang
chạy được từ thư mục gốc chỉ chuẩn bị corpus/bộ mẫu:

```powershell
python scripts/build_corpus.py
python scripts/build_fixture.py --seed 42
```

Không cần dùng bộ 50 bài để xử lý dữ liệu đầy đủ; corpus chung là nguồn chính.
Chưa annotation được facets thì không giả vờ đã sinh đủ dataset.

## 7. Quy tắc kiểm tra và điều kiện nghiệm thu

- User/paper refs resolve; observable users không chứa latent weights.
- Trọng số hữu hạn và đúng range; timestamps có timezone; enum hành vi hợp lệ.
- Mỗi user có lịch sử và holdout; latest train < earliest test một cách nghiêm ngặt.
- Không dùng tương tác test hoặc hidden truth để sinh profile đầu vào mô hình.
- Báo số user/events, exposure policy, mức nhiễu và phân phối hành vi thực tế.

D hoàn tất khi bộ mô phỏng có quy tắc được duyệt, generator tái lập, các tệp tách
đúng vai trò, manifests và validator riêng đạt; chưa tạo dữ liệu D ở phase hiện tại.

Lệnh hiện có `python scripts/validate_all.py --dataset-kind real --phase corpus`
chỉ kiểm tra corpus và bộ mẫu. `--phase experiments` trả lỗi vì dataset/generator
và validator đầy đủ A–E chưa được triển khai. Kiểm tra corpus đạt không thay thế
review chất lượng nhãn, ngữ nghĩa hoặc giả thuyết bộ mô phỏng.
