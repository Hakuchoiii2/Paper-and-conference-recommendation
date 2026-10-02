# Thực nghiệm khuyến nghị bài báo và hội nghị — DS300

Dự án chuẩn bị dữ liệu cho hệ thống khuyến nghị bài báo thuộc lĩnh vực công nghệ
thông tin (IT). Giai đoạn hiện tại tập trung vào tải dữ liệu, lọc phạm vi, gộp
corpus và thống nhất đầu vào cho năm thực nghiệm A–E. Chưa huấn luyện mô hình,
chưa chạy đánh giá thực nghiệm và chưa xây bộ nhãn khuyến nghị hội nghị.

## 1. Hiện tại đã có những gì?

| Hạng mục | Trạng thái thực tế |
|---|---|
| Dữ liệu gốc CSFCube | Đã tải bản v1.1, 4.207 bản ghi; giữ abstract, metadata, nhãn và cách chia gốc |
| Dữ liệu gốc SciFact | Đã tải 5.183 abstract; giữ claims, nhãn chứng cứ và cách chia gốc |
| Corpus IT chung | 4.210 bản ghi sau lọc phạm vi và gộp 25 bản ghi trùng |
| Đóng góp sau gộp | 4.182 bản ghi từ CSFCube và 28 bản ghi từ SciFact |
| Bộ mẫu chạy thử | 50 bài thật lấy từ corpus, giữ cùng ID và nội dung |
| Công cụ dữ liệu | Script tải, gộp corpus, lấy mẫu và kiểm tra chạy được |
| Kiểm tra | 10 kiểm tra đã đạt; chạy lại pipeline cho nội dung giống nhau |
| A–E | Có cấu trúc thư mục và đặc tả dữ liệu; chưa tạo dataset thực nghiệm |
| Silver/gold năm facet | Chưa có; cần annotation và kiểm tra bởi người phụ trách |

Số 4.210 là số bản ghi canonical hiện tại, còn mang tính tạm thời: có 5 trường hợp
cùng tiêu đề nhưng khác abstract được giữ riêng để review. SciFact còn 15 bản ghi
giáp ranh bị tạm loại. Corpus vượt mục tiêu tối thiểu 3.000 về số lượng, nhưng còn
thiếu 1.790 so với mục tiêu làm việc 6.000. Không thêm bản trùng hoặc dữ liệu giả
để lấp chỉ tiêu. Số lượng đạt mục tiêu không tự bảo đảm chất lượng thực nghiệm.

## 2. Năm thực nghiệm giải quyết những câu hỏi nào?

| Thực nghiệm | Câu hỏi chính | Dữ liệu cần chuẩn bị | Người phụ trách |
|---|---|---|---|
| [A — Trích xuất facet](data/exp_a/README.md) | Có xác định đúng vấn đề, tác vụ, phương pháp, dataset và đóng góp của bài không? | Nhãn silver tự động và gold được người kiểm tra | Kiên |
| [B — Truy hồi theo facet](data/exp_b/README.md) | Từ một bài mẫu, có tìm được bài phù hợp theo một khía cạnh cụ thể không? | Query, tập ứng viên và nhãn mức liên quan | Phi |
| [C — Ý định tường minh](data/exp_c/README.md) | Có đáp ứng yêu cầu kết hợp như cùng vấn đề nhưng khác phương pháp không? | Ý định, ràng buộc năm facet và nhãn thỏa/không thỏa | Quỳnh |
| [D — Sở thích ngầm](data/exp_d/README.md) | Có suy ra sở thích từ lịch sử tương tác thay vì yêu cầu người dùng khai báo không? | Người dùng giả lập, lịch sử, tương tác tương lai và sở thích ẩn | Phú |
| [E — Sở thích theo thời gian](data/exp_e/README.md) | Có theo dõi được sở thích thay đổi qua nhiều giai đoạn không? | Cùng người dùng D, hồ sơ từng giai đoạn và luồng tương tác riêng | Phú |

Ví dụ xuyên suốt: người dùng đang đọc một bài về hệ thống khuyến nghị. A xác định
bài nghiên cứu vấn đề gì và dùng phương pháp nào; B tìm các bài tương tự theo
phương pháp; C tìm bài cùng vấn đề nhưng dùng phương pháp khác; D suy ra người dùng
thường quan tâm chủ đề nào từ lịch sử; E xét việc mối quan tâm đó thay đổi theo thời
gian. Đây là ví dụ giải thích mục tiêu, không phải kết quả mô hình đã chạy.

**Quan hệ dữ liệu:** corpus và ID chung phục vụ tất cả thực nghiệm. A cung cấp
facet cho các bộ dữ liệu tùy chỉnh B/C và bộ mô phỏng D/E. B có thể khảo sát benchmark
gốc CSFCube trước, nhưng phải giữ đúng facet và quy trình đánh giá của nguồn.
C dùng facet để xác định ràng buộc; D sinh hồ sơ sở thích trước rồi mới sinh hành
vi; E dùng cùng danh tính người dùng D nhưng tạo kịch bản thay đổi sở thích riêng.
Không cần chờ silver toàn corpus hoàn tất: một tập bài thật có facet đã review
cũng đủ để bắt đầu pilot B–E.

## 3. Năm facet dùng chung

| Khóa trong dữ liệu | Ý nghĩa | Cần phân biệt |
|---|---|---|
| `problem` | Vấn đề hoặc hạn chế nghiên cứu muốn giải quyết | Không đồng nhất với thao tác của hệ thống |
| `task` | Tác vụ cần thực hiện, như truy hồi hoặc phân loại | Không phải tên thuật toán |
| `method` | Thuật toán hoặc kỹ thuật thực sự được sử dụng | Không tự động là đóng góp mới |
| `dataset` | Tên bộ dữ liệu/tài nguyên được dùng và có bằng chứng | Không suy từ lĩnh vực hay tên hội nghị |
| `contribution` | Đóng góp mới được bài khẳng định và có căn cứ | Không sao chép chung chung từ phương pháp |

Mỗi facet là danh sách chuỗi; không có bằng chứng thì dùng `[]`. Tuy nhiên,
**chưa annotation** khác với **đã annotation nhưng không tìm thấy giá trị**.
Hiện chưa tạo `facets.jsonl` để tránh biến danh sách rỗng thành nhãn giả.
Facet gốc `background/method/result` của CSFCube là một hệ khác, chưa có quy tắc
chuyển sang năm facet trên được duyệt. Nhãn SUPPORT/CONTRADICT của SciFact là nhãn
kiểm chứng phát biểu, không phải nhãn khuyến nghị bài báo.

## 4. Quy mô đề xuất và điều kiện mở từng phần

| Phần | Mục tiêu làm việc | Điều kiện cần trước khi sinh dataset |
|---|---|---|
| Corpus | 6.000 bài; tối thiểu 3.000 | Review phạm vi IT, provenance, ID và trường hợp nghi trùng |
| A | 400 bài gold; silver trên corpus đủ điều kiện | Guideline, từ vựng và quy trình review được Khải chốt |
| B | 300 query × 100 ứng viên | Nguồn nhãn và quy tắc facet/relevance được duyệt |
| C | 1.500 trường hợp, khoảng 5–10 loại ý định | Facet đầu vào và ràng buộc từng loại ý định được chốt |
| D | 300 người dùng × 50 tương tác | Quy tắc hồ sơ ẩn, tiếp xúc bài và nhiễu được công bố |
| E | Cùng 300 người dùng × 4 giai đoạn; khoảng 15.000–20.000 tương tác | Danh tính D, khoảng thời gian, tỷ lệ ổn định/thay đổi và cutoff được chốt |

Đây là mục tiêu workload từ tài liệu bàn giao, không phải số đã tạo và không phải
bảo đảm nguồn nhãn thật đủ số lượng. Riêng D/E là hành vi mô phỏng nếu không có
dữ liệu người dùng thật; phải ghi rõ giới hạn này trong mọi báo cáo.

## 5. Cấu trúc thư mục và vị trí dữ liệu

```text
configs/                 Cấu hình seed, đường dẫn và quy tắc lọc IT
docs/                    Guideline, prompt, tài liệu phạm vi và báo cáo
schemas/                 Schema các bản ghi đang dùng
data/raw/csfcube/         Bản gốc CSFCube, nhãn, split và tài liệu nguồn
data/raw/scifact/         Bản gốc SciFact, claims, split và tài liệu nguồn
data/processed/          Corpus chung, ánh xạ ID, audit và manifest
data/fixtures/           Bộ mẫu 50 bài thật để kiểm tra nhanh
data/exp_a/ ... exp_e/    README và các thư mục dữ liệu riêng của A–E
scripts/                 Các script dữ liệu đang chạy được
tests/                   Kiểm tra dữ liệu hợp lệ và các trường hợp lỗi
```

- `data/processed/papers.jsonl`: **corpus đầy đủ duy nhất**; dùng cho xử lý dữ liệu
  thật. Các thực nghiệm cùng tham chiếu `paper_id`, không lập corpus/ID riêng.
- `data/processed/id_map.jsonl`: ID nguồn → ID chung; giữ mọi nguồn gốc và nguồn
  đại diện của từng bài. ID đã cấp không đổi khi thêm nguồn hoặc đổi thứ tự.
- `data/processed/scope_audit.jsonl`: quyết định giữ/loại từng bản ghi và bằng chứng.
- `data/fixtures/papers.jsonl`: 50 bài thật cho kiểm tra nhanh, **không phải dataset
  cuối hoặc tập train/test**. Có thể làm trực tiếp trên corpus đầy đủ; không bắt
  buộc mọi xử lý phải đi qua 50 bài mẫu.
- `data/exp_a/generated/facets_silver.jsonl`: vị trí dự kiến nhãn tự động.
- `data/exp_a/generated/facets_gold.jsonl`: vị trí dự kiến nhãn đã được người review.
- `samples/` của mỗi exp: mẫu nhỏ sau khi có dữ liệu hợp lệ; hiện chỉ có hướng dẫn.
- `generated/`: dữ liệu đầy đủ của exp; `ground_truth/`: nhãn/hồ sơ ẩn/tương lai
  chỉ dành cho đánh giá. Không đưa chúng vào đầu vào dự đoán hoặc xây hồ sơ.

Silver/gold chỉ chứa nhãn và tham chiếu ID, không chép lại abstract. Một bài có thể
có cả silver và gold để so sánh. Nội dung thật không làm nhãn giả trở thành gold.

## 6. Chạy công cụ hiện có

Python 3.11 trở lên và thư viện chuẩn là đủ. Mở terminal tại thư mục dự án và chạy
lần lượt:

```powershell
python scripts/download_sources.py
python scripts/build_corpus.py
python scripts/build_fixture.py --seed 42
python scripts/validate_all.py --dataset-kind real --phase corpus
python tests/test_data_validation.py
```

Lệnh tải cần internet; dữ liệu đã có được tái sử dụng và kiểm tra checksum, không
tự tải đè bản mới. Các bước còn lại chạy offline. `seed 42` giúp lấy mẫu tái lập
khi đầu vào và code không đổi; số 42 là quy ước, không phải yêu cầu thuật toán.
Lệnh lấy mẫu chỉ cần cho bộ kiểm tra nhanh. Validator hiện kiểm tra cả corpus và
bộ mẫu đã bàn giao. Không có script `build_exp_a.py`–`build_exp_e.py` ở giai đoạn
này; chưa xây chức năng thì không tạo script rỗng.

`--phase corpus` kiểm tra phần đã triển khai. `--phase experiments` và
`--dataset-kind mock` trả lỗi rõ ràng vì các bộ đó chưa được xây dựng; không được
hiểu lần kiểm tra corpus đạt là cả A–E đã đạt nghiệm thu.

## 7. Phạm vi IT, nhãn, split và trách nhiệm review

CSFCube được nhận theo phạm vi lấy mẫu computer science đã mô tả trong tài liệu
nguồn. SciFact chỉ được nhận khi có bằng chứng rõ về kỹ thuật tính toán/phần mềm.
Ứng dụng AI/IT trong y sinh có thể phù hợp; bài sinh học thông thường có từ
“model”, “network” hoặc “imaging” chưa đủ điều kiện. Bộ lọc từ khóa có thể bỏ sót
hoặc nhận nhầm, nên quyết định hiện tại còn chờ Khải review.

Xem [quy tắc phạm vi IT](docs/IT_SCOPE.md), [contract dữ liệu](DATA_CONTRACT.md),
[báo cáo ingestion](docs/INGESTION_REPORT.md) và [trạng thái kiểm tra](docs/VALIDATION_STATUS.md).
Mỗi quyết định ghi đè bộ lọc phải có người review và lý do; review phạm vi bởi
Codex không được tính là gold facet do con người gán nhãn.

Giữ nhãn và split gốc để không mất đáp án/quy trình đánh giá. Split query/claim
của nguồn không phải cách chia train/dev/test chung cho tất cả bài trong corpus.
Chưa chia lại corpus ở bước ingestion. Khi xây B/C, chia theo nhóm bài truy vấn để
tránh cùng anchor xuất hiện ở nhiều tập. D/E chia theo thời gian từng người dùng;
không để nhãn hay dữ liệu tương lai lọt vào đầu vào mô hình.

Khải phụ trách contract, corpus, tích hợp và phê duyệt quy ước chung. Kiên/Phi/Quỳnh/
Phú phụ trách chất lượng dataset tương ứng. Mỗi owner bổ sung generator, manifest,
nhãn và kiểm tra thực nghiệm trước khi gọi phần của mình là hoàn tất.

## 8. Hướng triển khai tiếp

1. Khải review scope, 5 trường hợp nghi trùng và contract trước khi freeze dataset.
2. Kiên thực hiện pilot annotation năm facet trên bài thật; thống nhất từ vựng và
   xử lý bất đồng trước khi mở rộng silver/gold.
3. Phi khảo sát nhãn CSFCube và quy tắc benchmark; Quỳnh chốt templates/ràng buộc;
   Phú chốt bộ mô phỏng D/E dùng chung người dùng.
4. Xây generator từng exp trên pilot facets, kiểm tra schema/leakage, rồi mở rộng
   theo số liệu thực tế và chất lượng nguồn. Không cần chờ toàn corpus được gán nhãn.
5. Sau khi dữ liệu và giao thức đánh giá được duyệt mới triển khai embedding,
   ranking/model và báo cáo kết quả; chưa chọn model hoặc dimension ở bước này.

Khuyến nghị hội nghị hiện mới là hướng của dự án. A–E trong tài liệu bàn giao tập
trung vào bài báo; metadata hội nghị có thể thiếu và chưa có catalog/nhãn hội nghị
độc lập. Không suy rằng đã có dataset khuyến nghị hội nghị chỉ từ tên folder.
Bản kế hoạch DS300 gốc chưa được đối chiếu trực tiếp; tài liệu bàn giao đã lưu ở
`docs/DATA_FIRST_REFERENCE.md`.

## 9. Nguồn và quản lý tệp

- [CSFCube v1.1](https://github.com/iesl/CSFCube/releases/tag/v1.1): giữ giấy phép
  CC BY-NC 4.0 và thông tin trích dẫn đi kèm.
- [SciFact](https://github.com/allenai/scifact): giữ nguyên LICENSE.md và điều kiện
  sử dụng cho corpus/claims được nguồn công bố.

README gốc của hai nguồn trong `data/raw/` giữ nguyên để bảo toàn provenance.
`source_manifest.json` ghi URL và checksum SHA-256. `.gitignore` loại dữ liệu thô,
output lớn, API keys, môi trường, cache và model khỏi commit sau này. Chưa tạo
repository GitHub, commit hay push. Trước khi chia sẻ dữ liệu thật, review nguồn,
giấy phép và attribution cùng với code/tài liệu.
