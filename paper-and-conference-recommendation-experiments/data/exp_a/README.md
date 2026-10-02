# Thực nghiệm A — Gán nhãn các khía cạnh của bài báo

Người phụ trách: **Kiên**. Trạng thái: đặc tả dữ liệu cho giai đoạn tiếp
theo; chưa sinh dataset hoặc chạy mô hình của thực nghiệm. Khải chốt quy ước chung.

## 1. Mục đích và câu hỏi thực nghiệm

A chuẩn bị và đánh giá chất lượng thông tin năm facet được trích từ title/abstract.
Câu hỏi là: nhãn tự động có xác định đúng `problem`, `task`, `method`, `dataset`,
`contribution` so với nhãn được người kiểm tra không? Đây là nguồn facet cho
dataset tùy chỉnh B/C và bộ mô phỏng D/E, không phải thực nghiệm xếp hạng bài.

Ví dụ: cần phân biệt “giải quyết thiếu dữ liệu người dùng mới” là vấn đề,
“khuyến nghị” là tác vụ, và một thuật toán cụ thể là phương pháp. Tên phương pháp
không tự chứng minh bài có đóng góp mới. Tất cả phải có căn cứ trong văn bản.

## 2. Định dạng đầu vào

Dùng corpus chung hoặc bộ mẫu thật, cùng phiên bản guideline/prompt đã chốt.
Đầu vào dự đoán là `paper_id`, `title`, `abstract`; ID dùng liên kết, không mang ý
nghĩa nhãn. Xem [guideline](../../docs/FACET_GUIDELINE.md) và
[prompt dự thảo](../../docs/ANNOTATION_PROMPT.md). Không đưa gold, nhãn relevance
hoặc kết quả kiểm tra của nguồn vào prompt dự đoán. Giữ abstract gốc trong raw.

Dùng `../processed/papers.jsonl` cho corpus đầy đủ;
`../fixtures/papers.jsonl` là bộ 50 bài thật tùy chọn để kiểm tra nhanh.
Tuân thủ [contract dùng chung](../../DATA_CONTRACT.md); không cấp ID riêng.

## 3. Định dạng đầu ra

| Tệp dự kiến | Nội dung và vai trò |
|---|---|
| `generated/facets_silver.jsonl` | Nhãn facet tự động, chưa mặc định được con người duyệt |
| `generated/facets_gold.jsonl` | Nhãn facet đã được người review, trên một subset của corpus |
| `generated/annotation_metadata.jsonl` | Nguồn nhãn, tier, phiên bản guideline/prompt và trạng thái review |

Mỗi tệp facet có một bản ghi cho mỗi bài. Silver và gold có thể trùng `paper_id`
để so sánh; không chép lại abstract. Dữ liệu gán nhãn tự động không được đổi tên
thành gold để đủ chỉ tiêu.

`samples/` lưu mẫu nhỏ được review khi dataset tồn tại; `generated/` lưu output
đầy đủ. Manifest ghi contract version, real/mock, seed, generator/input hashes
và số lượng thực tế. Nhãn, hồ sơ ẩn và dữ liệu tương lai tách khỏi đầu vào.

## 4. Định nghĩa trường dữ liệu

| Trường | Kiểu/ý nghĩa |
|---|---|
| `paper_id` | ID canonical `P` + 6 chữ số; thuộc corpus đang dùng |
| `problem`, `task`, `method`, `dataset`, `contribution` | Mỗi trường là list string; nhiều giá trị nếu có bằng chứng; thiếu = `[]` |
| `tier` trong metadata | Phân biệt silver/gold |
| `dataset_kind` | Phân biệt real/mock; không tính nhãn mock vào gold thật |
| `annotator_type`, `review_status` | Nguồn gán nhãn và mức kiểm tra thực tế |
| `guideline_version`, `prompt_version` | Truy được quy tắc đã dùng để annotation |

Khóa duy nhất: `paper_id` trong mỗi tier; metadata liên kết theo `(paper_id,tier)`.
Không có tệp annotation khác với có bản ghi toàn `[]`. Các nhãn câu gốc của
CSFCube không được chép trực tiếp sang năm danh sách concept này.

## 5. Ví dụ đầu vào và đầu ra

Các ID bài dưới đây lấy từ bộ mẫu thật, nhưng nhãn/hành vi/hồ sơ là **ví dụ
minh họa schema, chưa phải dữ liệu được release hoặc đáp án đã kiểm chứng**.
Giữ nguyên title/abstract nguồn trong ví dụ JSON; không dịch nội dung corpus.

Đầu vào quan sát được:

```json
{"abstract": "We propose a hybrid model for automatically acquiring a policy for a complex game, which combines online learning with mining knowledge from a corpus of human game play. Our hypothesis is that a player that learns its policies by combining (online) exploration with biases towards human behaviour that's attested in a corpus of humans playing the game will outperform any agent that uses only one of the knowledge sources. During game play, the agent extracts similar moves made by players in the corpus in similar situations, and approximates their utility alongside other possible options by performing simulations from its current state. We implement and assess our model in an agent playing the complex win-lose board game Settlers of Catan, which lacks an implementation that would challenge a human expert. The results from the preliminary set of experiments illustrate the potential of such a joint model.", "domain": "information_technology", "paper_id": "P000054", "scope_evidence": ["CSFCube datasheet: ACL query papers and candidate papers sampled from computer-science arXiv papers in S2ORC."], "source": "csfcube", "source_id": "1030020", "title": "Online learning and mining human play in complex games", "year": 2015}
```

Đơn vị đầu ra dự kiến:

```json
{"paper_id":"P000054","problem":[],"task":[],"method":[],"dataset":[],"contribution":[]}
```

Với A, các list rỗng chỉ minh họa kiểu dữ liệu, không phải annotation thực tế.
Với B/C, không suy rằng ứng viên thật sự phù hợp từ nhãn ví dụ. Với D/E, user
và sở thích là minh họa; profile E nằm trong truth, không phải input mô hình.

## 6. Quy tắc tạo dữ liệu và hướng đánh giá

1. Chọn một pilot bài thật có abstract đủ dùng; hai người review độc lập một
   subset chung để phát hiện nhầm problem/task và method/contribution.
2. Kiên đề xuất định nghĩa và alias; Khải chốt vocabulary/contract trước khi nhóm
   mở rộng. Chỉ chuẩn hóa tên concept, không sửa abstract nguồn.
3. Sinh silver theo prompt/guideline có phiên bản; ghi đúng annotator/model và
   metadata. Chưa gọi API hàng loạt khi chưa có cấu hình và ngân sách.
4. Gold cần human review và quy trình giải quyết bất đồng. Giữ split gold độc lập
   với việc chỉnh prompt; không dùng held-out gold làm ví dụ hoặc tối ưu prompt.
5. Mục tiêu: 400 bài gold, khoảng 300–500; silver trên toàn corpus đủ điều kiện.
   Corpus hiện có 4.210 bản ghi tạm thời, nên không tự ghi đã có 6.000 silver.

Khi thực nghiệm mô hình được triển khai, có thể so độ đúng/đủ của concept theo
từng facet và mức thống nhất giữa người gán nhãn. Quy tắc matching concept,
alias và chỉ số cụ thể phải được chốt trước khi đánh giá; hiện chưa có điểm số.

**Trạng thái triển khai:** chưa có generator cho thực nghiệm này. Các lệnh đang
chạy được từ thư mục gốc chỉ chuẩn bị corpus/bộ mẫu:

```powershell
python scripts/build_corpus.py
python scripts/build_fixture.py --seed 42
```

Không cần dùng bộ 50 bài để xử lý dữ liệu đầy đủ; corpus chung là nguồn chính.
Chưa annotation được facets thì không giả vờ đã sinh đủ dataset.

## 7. Quy tắc kiểm tra và điều kiện nghiệm thu

- Mỗi ID tồn tại, không trùng trong cùng tier; đủ đúng năm facet list string.
- Nhãn chỉ chứa concept có bằng chứng; không bịa dataset/contribution bị thiếu.
- Gold là subset corpus và thực sự được human review; metadata khớp tier/kind.
- Prompt tuning không dùng held-out gold; corpus input không chứa nhãn đánh giá.
- Báo số silver/gold thực tế, facet còn thiếu và bất đồng chưa giải quyết.

A hoàn tất khi có generator annotation chạy được, metadata, gold được duyệt,
quy tắc đánh giá và validator riêng đạt; các thư mục/README hiện tại chưa đủ.

Lệnh hiện có `python scripts/validate_all.py --dataset-kind real --phase corpus`
chỉ kiểm tra corpus và bộ mẫu. `--phase experiments` trả lỗi vì dataset/generator
và validator đầy đủ A–E chưa được triển khai. Kiểm tra corpus đạt không thay thế
review chất lượng nhãn, ngữ nghĩa hoặc giả thuyết bộ mô phỏng.
