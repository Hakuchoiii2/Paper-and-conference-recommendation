# Thực nghiệm B — Truy hồi bài báo theo một facet

Người phụ trách: **Phi**. Trạng thái: đặc tả dữ liệu cho giai đoạn tiếp
theo; chưa sinh dataset hoặc chạy mô hình của thực nghiệm. Khải chốt quy ước chung.

## 1. Mục đích và câu hỏi thực nghiệm

B kiểm tra khả năng tìm bài liên quan theo **một khía cạnh được chỉ định** khi
đầu vào là một bài mẫu. Hai bài cùng lĩnh vực chưa chắc giống phương pháp; hai bài
khác ứng dụng vẫn có thể dùng phương pháp tương tự. Vì vậy relevance phải gắn
với facet của query, không chỉ với chủ đề chung.

Ví dụ: người đọc muốn tìm các bài dùng phương pháp tương tự bài đang đọc.
Dataset B cần bài truy vấn, tập ứng viên cố định và mức liên quan của từng ứng
viên. Chất lượng thứ tự xếp hạng là bước đánh giá mô hình về sau.

## 2. Định dạng đầu vào

Đầu vào quan sát được là `retrieval_queries.jsonl`, gồm ID query, ID bài truy vấn,
facet đích và danh sách ứng viên. Title/abstract và facet đã được phép dùng đọc từ
catalog chung. Nhãn relevance chỉ evaluation loader được đọc.

Có hai hướng cần phân biệt: benchmark gốc CSFCube giữ `background/method/result`
và giao thức gốc; dataset tùy chỉnh của đồ án dùng năm facet toàn cục đã duyệt.
Chưa có mapping được duyệt giữa hai hệ này. Có thể khảo sát benchmark gốc trước
khi A hoàn tất, nhưng không gắn nhãn lại ngầm thành dataset năm facet.

Dùng `../processed/papers.jsonl` cho corpus đầy đủ;
`../fixtures/papers.jsonl` là bộ 50 bài thật tùy chọn để kiểm tra nhanh.
Tuân thủ [contract dùng chung](../../DATA_CONTRACT.md); không cấp ID riêng.

## 3. Định dạng đầu ra

| Tệp dự kiến | Vai trò |
|---|---|
| `generated/retrieval_queries.jsonl` | Query và ứng viên, đầu vào mô hình |
| `ground_truth/retrieval_labels.jsonl` | Mức liên quan cho từng cặp query–candidate |
| Metadata nhãn/mapping | Giữ raw label, nguồn và quy tắc chuyển nếu có |

Một query chứa nhiều ứng viên; một bản ghi nhãn tương ứng một cặp. Không đặt
nhãn trong tệp query. Lưu riêng thống kê native, synthetic và human judgments.

`samples/` lưu mẫu nhỏ được review khi dataset tồn tại; `generated/` lưu output
đầy đủ. Manifest ghi contract version, real/mock, seed, generator/input hashes
và số lượng thực tế. Nhãn, hồ sơ ẩn và dữ liệu tương lai tách khỏi đầu vào.

## 4. Định nghĩa trường dữ liệu

| Trường | Ý nghĩa/ràng buộc |
|---|---|
| `query_id` | `Q` + 4 chữ số; duy nhất trong bộ |
| `query_paper_id` | ID bài làm ví dụ truy vấn |
| `target_facet` | Một khóa facet toàn cục cho dataset tùy chỉnh |
| `candidate_ids` | List ID canonical; không trùng; không chứa query paper |
| `candidate_id` trong nhãn | Phải thuộc candidate set của query đó |
| `relevance` nội bộ | Đề xuất 0: không liên quan, 1: một phần, 2: cao |

Khóa duy nhất của nhãn: `(query_id,candidate_id)`. Nhãn CSFCube gốc có scale 0–3;
phải giữ raw label, không tự ép sang 0–2. Nhãn SciFact SUPPORT/CONTRADICT không
được coi là relevance khuyến nghị. Chưa judged khác với relevance bằng 0.

## 5. Ví dụ đầu vào và đầu ra

Các ID bài dưới đây lấy từ bộ mẫu thật, nhưng nhãn/hành vi/hồ sơ là **ví dụ
minh họa schema, chưa phải dữ liệu được release hoặc đáp án đã kiểm chứng**.
Giữ nguyên title/abstract nguồn trong ví dụ JSON; không dịch nội dung corpus.

Đầu vào quan sát được:

```json
{"query_id": "Q0001", "query_paper_id": "P000054", "target_facet": "method", "candidate_ids": ["P000205"]}
```

Đơn vị đầu ra dự kiến:

```json
{"query_id":"Q0001","candidate_id":"P000205","relevance":2}
```

Với A, các list rỗng chỉ minh họa kiểu dữ liệu, không phải annotation thực tế.
Với B/C, không suy rằng ứng viên thật sự phù hợp từ nhãn ví dụ. Với D/E, user
và sở thích là minh họa; profile E nằm trong truth, không phải input mô hình.

## 6. Quy tắc tạo dữ liệu và hướng đánh giá

1. Phi kiểm tra nhãn/pool/split nguồn và đề xuất mapping; Khải review cách liên
   kết canonical ID và ý nghĩa facet trước khi chuyển nhãn.
2. Query tùy chỉnh cần positive, hard negative và easy negative. Hard negative
   giống ở khía cạnh khác nhưng không đáp ứng facet đang hỏi; easy negative có
   ít liên quan. Chưa cần embedding để hoàn thiện interface dữ liệu.
3. Tập judged phải có đủ nhãn hoặc chính sách unjudged rõ ràng; giữ ít nhất một
   positive cho mỗi query được release. Nếu nguồn không đủ, báo gap và bổ sung
   annotation có provenance, không coi ứng viên chưa chấm là negative.
4. Mục tiêu làm việc: 300 query × 100 ứng viên, khoảng 30.000 cặp. Đây không phải
   số query native chắc chắn có sẵn; không nhân bản query để đủ target.
5. Giữ giao thức split native; split tùy chỉnh nhóm theo bài truy vấn. Candidate
   corpus có thể được dùng chung nếu protocol cho phép, không mặc định phải rời
   nhau giữa train/test như query anchors.

Chỉ số xếp hạng như nDCG@k/Recall@k là hướng đánh giá đề xuất sau khi chốt ý nghĩa
positive, scale nhãn và cutoff k. Nếu giữ benchmark gốc, tuân thủ giao thức nguồn.
Hiện chưa huấn luyện, xếp hạng hoặc báo cáo chỉ số.

**Trạng thái triển khai:** chưa có generator cho thực nghiệm này. Các lệnh đang
chạy được từ thư mục gốc chỉ chuẩn bị corpus/bộ mẫu:

```powershell
python scripts/build_corpus.py
python scripts/build_fixture.py --seed 42
```

Không cần dùng bộ 50 bài để xử lý dữ liệu đầy đủ; corpus chung là nguồn chính.
Chưa annotation được facets thì không giả vờ đã sinh đủ dataset.

## 7. Quy tắc kiểm tra và điều kiện nghiệm thu

- Query/candidate resolve trong đúng catalog; không self-candidate hoặc trùng ID.
- Nhãn không thừa/thiếu/nhân đôi so với chính sách judged đã công bố.
- Positive tồn tại; nguồn/scale/mapping relevance có giải thích, không trộn ngầm.
- Query anchors không tràn các split tùy chỉnh; nhãn không nằm trong input dự đoán.
- Báo native/synthetic/human counts riêng và mọi pair còn unjudged.

B hoàn tất khi có generator, mapping/label policy được duyệt, candidate sets hợp
lệ, manifests và kiểm tra cấu trúc/ngữ nghĩa/leakage; hiện chưa có dataset B.

Lệnh hiện có `python scripts/validate_all.py --dataset-kind real --phase corpus`
chỉ kiểm tra corpus và bộ mẫu. `--phase experiments` trả lỗi vì dataset/generator
và validator đầy đủ A–E chưa được triển khai. Kiểm tra corpus đạt không thay thế
review chất lượng nhãn, ngữ nghĩa hoặc giả thuyết bộ mô phỏng.
