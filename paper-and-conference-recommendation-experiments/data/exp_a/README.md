# Thực nghiệm A — Trích năm facet bằng Qwen3 local

Cả nhóm 5 người cùng chạy trích facet trên 4.210 title/abstract, chia thành
5 phần không trùng nhau, mỗi người 842 bài. Chạy Qwen3 trên máy, không dùng
API key. Corpus thật và schema năm facet vẫn dùng chung B–E.

## 1. Mục đích

Trích problem, task, method, dataset, contribution từ title/abstract thật.
Output tự động là silver, cần review chất lượng; không tự tạo human gold.
Không thay năm facet bằng ba nhãn câu gốc CSFCube hoặc facet mock.

## 2. Đầu vào

| Input | Đường dẫn/giá trị |
|---|---|
| Corpus | `data/processed/papers.jsonl`, toàn bộ 4.210 bài |
| Config | `data/exp_a/config.json` |
| Khoảng bài | `paper_range: [bài_đầu, bài_cuối]`, mặc định `[1, 842]` |
| Thư mục kết quả | `output_dir`, mặc định `data/exp_a/generated/part_1` |
| Model | `Qwen/Qwen3-4B-Instruct-2507`, revision cố định trong config |
| Thiết bị | `cuda`; đã kiểm tra máy có RTX 4060 Laptop 8 GB |
| Prompt/guideline | `docs/ANNOTATION_PROMPT.md`, `docs/FACET_GUIDELINE.md` |
| Trọng số/cache | `models/huggingface/`, Git bỏ qua |

Trọng số tải từ Hugging Face lần đầu. Suy luận chạy trên máy; title/abstract
không gửi tới dịch vụ annotation. Bản Instruct này không có thinking. Dùng NF4 4-bit (bitsandbytes), tính toán float16 trên GPU.

### Chia 4.210 bài cho 5 người

Số thứ tự bắt đầu từ **1**, sau khi sắp corpus tăng dần theo `paper_id`;
**lấy cả bài đầu và bài cuối**. Giữ nguyên corpus, không cắt thành năm tệp.

| Phần chạy | `paper_range` | Paper IDs | Số bài | `output_dir` |
|---|---|---|---|---|
| Phần 1 | `[1, 842]` | `P000001`–`P000842` | 842 | `data/exp_a/generated/part_1` | Khải
| Phần 2 | `[843, 1684]` | `P000843`–`P001684` | 842 | `data/exp_a/generated/part_2` | Quỳnh
| Phần 3 | `[1685, 2526]` | `P001685`–`P002526` | 842 | `data/exp_a/generated/part_3` | Kiên
| Phần 4 | `[2527, 3368]` | `P002527`–`P003368` | 842 | `data/exp_a/generated/part_4` | Phi
| Phần 5 | `[3369, 4210]` | `P003369`–`P004210` | 842 | `data/exp_a/generated/part_5` | Phú

Mỗi người chọn một phần và sửa **hai giá trị** `paper_range`, `output_dir`
trong config trên máy mình. Ví dụ phần 2 (chỉ trích hai trường cần sửa):

```json
{
  "paper_range": [843, 1684],
  "output_dir": "data/exp_a/generated/part_2"
}
```

Giữ các trường config còn lại. `[1, null]` chọn toàn corpus; `[3369, null]`
chọn từ bài 3.369 tới cuối. Bỏ `paper_range` cũng chọn toàn corpus để tương thích
config cũ. Khoảng đảo ngược, ngoài corpus hoặc không phải số nguyên sẽ báo lỗi
trước khi nạp model. Khi corpus thay đổi phải chia lại khoảng theo số bài thực tế.

## 3. Đầu ra

Tệp của từng phần nằm trong `output_dir` tương ứng, ví dụ
`data/exp_a/generated/part_1/`:

| Tệp | Vai trò |
|---|---|
| `facets_silver.jsonl` | ID và đúng năm list concept string |
| `annotation_metadata.jsonl` | Câu dẫn chứng nguyên văn, model/revision/runtime, token count, seed/attempt |
| `manifest.json` | Hashes, coverage, missing IDs, partial/complete |
| `.exp_a_checkpoint.sqlite3` | Lưu từng bài hợp lệ để tiếp tục; không commit Git |
| `last_failure.json` nếu fallback | Paper ID, output được chọn, điểm và lỗi của từng lượt để rà lại |

Manifest giữ `corpus_count: 4210` và coverage của **toàn corpus**; một phần đủ
842 bài vẫn có `status: partial`, các ID ngoài khoảng vẫn nằm trong `missing_ids`.
Kiểm tra từng phần bằng `--validate-only --allow-partial`; đối chiếu các ID còn
thiếu **trong khoảng được giao** để biết phần đó đã xong chưa. Khi gom năm phần,
ghép cả silver và metadata theo `paper_id`, kiểm tra không trùng/thiếu và tạo
manifest cho bộ đầy đủ ở `data/exp_a/generated/` trước khi bàn giao B–E.
Không dùng manifest của một phần làm manifest toàn corpus.

Lượt gọi API cũ chưa tạo annotation nào; checkpoint/output lỗi được giữ tại
`generated/api_attempt_backup/`. Qwen không trộn provenance API vào silver mới. Pilot v1.3 bị loại do nhãn
chép định nghĩa; giữ để audit ở `generated/pilot_rejected_v13/`. Các pilot trước khi chỉnh prompt/feedback nằm trong `pilot_rejected_v14/` và `pilot_before_feedback/`; không trộn vào silver hiện tại.

## 4. Quy tắc nhãn

Qwen chọn concept và evidence_id từ các câu đánh số T0/A0/A1... của bài.
Code lấy nguyên văn câu đã chọn và xác định source title/abstract, không yêu cầu
model chép lại câu dài. Metadata giữ cả sentence selections. Concept phải bám vào từ trong câu đã chọn
(so khớp sau chuẩn hóa case/dấu câu và biến thể động từ có quy tắc như representing/represent,
extracting/extract, running/run). Cho phép rút gọn bằng cách bỏ từ,
nhưng phải giữ thứ tự từ và ít nhất **70% số từ trong đoạn nguồn ngắn nhất chứa concept**;
không so độ dài concept với toàn bộ câu. Cụm ngắn được chép nguyên văn luôn đạt ngưỡng.
Không thêm từ mới hoặc dùng từ đồng nghĩa không có trong câu dẫn chứng.
Ngoặc ví dụ được ghi rõ bằng `e.g.`, `for example`, `for instance` hoặc `such as`
có thể bỏ qua khi tính tỷ lệ giữ từ. Ngoặc chứa viết tắt, định nghĩa, điều kiện hoặc phủ định
vẫn được tính; câu dẫn chứng trong metadata luôn giữ nguyên văn. Nếu concept trích từ chính
ngoặc ví dụ, vẫn kiểm tra với toàn bộ câu gốc để không làm mất dẫn chứng hợp lệ.
Code kiểm tra
đúng ID/khóa/list, không trùng concept và câu dẫn chứng có trong bài. Không có
bằng chứng dùng `[]`; chưa xử lý không được chèn nhãn rỗng giả. Metadata ghi
`annotator_type: qwen_local`, `tier: silver`, `review_status: unreviewed`.

JSON được yêu cầu bằng prompt và kiểm tra sau sinh; không có bảo đảm schema từ
dịch vụ API. Mỗi lượt được chấm điểm và thu thập **tất cả lỗi concept** để model sửa
cùng lúc. Khi có kết quả đạt kiểm tra và đã rà các facet trống theo quy tắc dưới,
lưu ngay. **Hết lượt vẫn lỗi thì lưu kết quả có điểm cao nhất**, giữ cả concept
chưa đạt kiểm tra, thay vì bỏ cả paper. Ngưỡng 70% là tiêu chí retry, không phải điều
kiện loại paper ở lượt cuối. Metadata ghi `fallback_used: true`, `validation_errors`,
`selected_score`, `attempt` được chọn, `attempts_used` và `attempt_scores` của mọi lượt
(gồm raw output, seed, điểm, lỗi và usage). Tổng usage tính cả các lượt retry.
`manifest.fallback_annotations` liệt kê các paper còn lỗi; `missing_ids` chỉ chứa
paper chưa có bản ghi. Chạy lại tiếp tục các ID còn thiếu, không sinh lại fallback đã lưu.
Lỗi môi trường/GPU vẫn dừng tiến trình.

Điểm từ **0–100** là thước đo bám nguồn theo quy tắc, không phải xác suất đúng ngữ nghĩa:

| Thành phần | Điểm tối đa |
|---|---:|
| Số facet có ít nhất một concept đạt kiểm tra / 5 | 60 |
| Số concept đạt kiểm tra / tổng số item model sinh | 25 |
| Tỷ lệ giữ từ trung bình của các concept | 5 |
| JSON đúng ID, đủ khóa, đúng list/item/evidence_id | 10 |

Concept trùng không tăng điểm và được gộp trong output; bản raw vẫn giữ nguyên.
Hòa điểm ưu tiên JSON đọc được, rồi ít lỗi hơn, rồi lượt sớm hơn. Concept có evidence_id
không tồn tại vẫn được giữ trong fallback nhưng ghi `source: unresolved`, `evidence: ""`;
không gán dẫn chứng khác cho nó. Nếu mọi lượt đều không đọc được JSON, vẫn xuất đúng
paper_id và năm list rỗng, có lỗi và raw output để rà lại. Bản ghi này biểu thị model
không tạo được nhãn, không khẳng định paper không có facet.
`max_attempts: 3` là **tổng ba lần sinh**, bao gồm lần đầu, retry và lượt rà lại.
Nếu kết quả hợp lệ có **ít nhất 3/5 facet trống**, model phải rà lại title T0 và
từng câu abstract một lần. Sau lượt rà lại, facet thiếu bằng chứng vẫn được giữ `[]`;
không ép model điền nhãn. Nếu chỉ tới lần sinh cuối mới nhận được kết quả cần rà lại,
dùng fallback có điểm cao nhất và ghi lỗi thiếu lượt rà lại. Rút gọn quá 30% hoặc chọn
sai evidence_id cũng retry trong ngân sách này.
Quy tắc này thuộc extraction policy 2.3, được thêm sau prompt 1.5 và thay thế yêu cầu
chép cụm liên tục của prompt gốc. Metadata ghi `extraction_policy_version`,
`sparse_reviewed` và ngưỡng kiểm tra trong `request_parameters`.
Câu trích có thật vẫn có thể không hỗ trợ concept: cần người review ngữ nghĩa.

## 5. Cách chạy

Môi trường riêng `.venv-qwen` dùng Python 3.11, PyTorch CUDA và Transformers.
Nếu đã có môi trường này, lệnh quen thuộc tự chuyển sang đúng Python. Từ folder
`data/exp_a`:

```powershell
python build_exp_a.py --dry-run
python build_exp_a.py --limit 2
python build_exp_a.py
python build_exp_a.py --validate-only --allow-partial
```

Không cần `.env`. `--dry-run` hiển thị khoảng, IDs, số bài được chọn và thư mục
kết quả để kiểm tra trước khi chạy. Mặc định chỉ xử lý bài còn thiếu **trong
`paper_range`**; `--limit` là số bài mới tối đa trong khoảng đó, không thay đổi
ranh giới phần chạy. Config hiện chọn phần 1; đổi khoảng/thư mục trước khi chạy
phần khác. Chạy lại cùng config sẽ tiếp tục checkpoint của phần đó.

Khi bắt đầu, code hiển thị số bài đã lưu, còn thiếu và cần rà lại **trong khoảng
được chọn**. Dò theo `paper_id` nên bài thiếu ở giữa vẫn được xử lý; bài đã lưu
không tính vào `--limit`. Nếu mất checkpoint, code phục hồi từ
`annotation_metadata.jsonl` và `manifest.json` đã kiểm tra hash/provenance,
đối chiếu với `facets_silver.jsonl` nếu tệp này còn. Nếu chỉ thiếu tệp silver,
dẫn chứng trong metadata đủ để tạo lại mà không nạp model. Khi checkpoint còn,
các tệp JSONL/manifest bị thiếu được xuất lại từ checkpoint. Mất cả checkpoint
và metadata hoặc manifest thì cần khôi phục bản sao trước khi chạy tiếp.

Nếu thiết lập lại máy, từ thư mục gốc dự án dùng Python 3.11:

```powershell
python -m venv .venv-qwen
.\.venv-qwen\Scripts\python.exe -X utf8 -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
.\.venv-qwen\Scripts\python.exe -X utf8 -m pip install -r data/exp_a/requirements.txt
```

## 6. Tiến độ và tái lập

Model được nạp một lần mỗi tiến trình, xử lý tuần tự và lưu từng bài sau khi đạt
kiểm tra hoặc chọn fallback tốt nhất. Năm người chạy trên máy riêng với cùng corpus/model/prompt; mỗi phần
có output/checkpoint riêng. OS lock chặn hai lượt chạy cùng output. Dừng rồi chạy lại cùng lệnh
tiếp tục bài thiếu. Checkpoint chưa có annotation nào được khởi tạo lại khi đổi cấu hình.
Nếu đã có annotation, đổi khoảng bài, model/revision/prompt/thiết bị/tham số
sampling hoặc code generator thì dùng output mới;
max_new_tokens/max_attempts có thể tăng để tiếp tục checkpoint.
Riêng bản bổ sung phục hồi JSONL giữ nguyên policy 2.3 và chấp nhận fingerprint
của generator 2.3 trước đó; không cần đổi `output_dir` cho nâng cấp này.
Riêng bản generator 2.0, 2.1 và 2.2 có fingerprint đã biết được nâng lên policy 2.3 tự động
khi corpus, config, prompt và guideline không đổi. Các bài cũ có ít nhất 3 facet
trống chưa được rà lại được xử lý lại; bài đã có `sparse_reviewed: true` được giữ nguyên.
Chỉ thay kết quả cũ khi kết quả mới hợp lệ; nếu lượt rà lại chỉ có fallback, giữ kết quả
đã nhận. Các ID bị REJECTED ở bản cũ còn thiếu sẽ được sinh lại bằng cơ chế chấm điểm mới.
Việc rà lại bài đã có trong checkpoint không tính vào số bài mới của `--limit`.
Nhấn Ctrl+C để dừng có lưu kết quả, rồi chạy lại cùng lệnh để dùng code mới.
Seed/phiên bản được ghi để truy nguồn, không bảo đảm kết quả giống hệt trên GPU khác.

## 7. Nghiệm thu

Chạy tests, corpus gate và validator từng phần. Chỉ bộ đã gom đủ 4.210 IDs,
metadata tương ứng và manifest toàn corpus hợp lệ với `status: complete` mới
được bàn giao cho B–E. B/C dùng facet A; C tạo users/history để D/E sử dụng theo thứ tự mới. Không cần chờ gold; đánh giá chất lượng
A vẫn cần human-reviewed gold riêng, không tự chấm bằng chính silver. Prompt v1.5 dùng P000001 làm ví dụ phát triển prompt; bài này không được đưa vào held-out gold.

Các tệp JSONL/manifest được xuất khi lượt chạy kết thúc hoặc dừng có xử lý;
tiến độ bền vững nằm trong checkpoint riêng của mỗi phần. Output/checkpoint
của lượt toàn corpus cũ ở `generated/` không phải output của năm phần mới.
Không chạy hai tiến trình cùng `output_dir`. Kiểm tra dẫn chứng không bảo đảm
chọn đúng facet hoặc trích đủ ý; các nhãn vẫn là silver chưa review.

Nguồn: [model card Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507),
[PyTorch CUDA 12.4](https://pytorch.org/get-started/previous-versions/#v260).

## 8. Gộp năm phần và chọn 400 bài review

Từ gốc dự án, sau khi nhận đủ parts 1–5:

~~~powershell
python data/exp_a/merge_exp_a.py --dry-run
python data/exp_a/merge_exp_a.py
python data/exp_a/select_gold_review.py --dry-run
python data/exp_a/select_gold_review.py
~~~

Tool gộp kiểm tra coverage từng khoảng/toàn corpus, không trùng ID, input/config
provenance và model/revision thực tế được ghi trong metadata. Chỉ khi đủ 4.210 bài
mới ghi silver, metadata và manifest complete ở `data/exp_a/generated/`.

Tool review chọn mặc định 400 IDs, không random: số facet có dữ liệu giảm dần,
rồi số concept có dẫn chứng giảm dần, rồi paper_id tăng dần. Bỏ P000001,
fallback/validation errors và bài không có facet trích được. Nếu thiếu 400 bài
hợp lệ thì báo thiếu. Không ghi đè queue review đã có.

Gold là đáp án người kiểm tra dùng để đánh giá **độ đúng và độ đầy đủ** của facet A,
độc lập với Qwen silver. Output selector chỉ là form pending và danh sách bài,
không tự tạo `facets_gold.jsonl`. Nhãn silver nằm trong tệp tham chiếu riêng để
đối chiếu sau review. Cách chọn này ưu tiên silver đầy đủ, không đại diện ngẫu nhiên
cho toàn corpus. Xem [hướng dẫn chạy](../../docs/RUN_EXPERIMENTS.md) để biết tệp,
preview part_1 và quy trình review.

## 9. Đánh giá silver bằng human gold

Sau khi 400 forms được người review hoàn tất (`review_status: reviewed`, có tên
reviewer), từ gốc dự án chạy `python scripts/exp_a/evaluate_exp_a.py`. Tool xuất
Precision/Recall/F1 từng facet, micro/macro, nhãn dư/thiếu, dẫn chứng và gợi ý
có thể nhầm facet ở từng bài. Output tại `data/exp_a/evaluation/gold_400/`.

Đây là so khớp concept sau chuẩn hóa Unicode/hoa thường/khoảng trắng, giữ dấu câu;
nhãn cùng nghĩa khác cách viết vẫn cần người đối chiếu. 400 bài ưu tiên đầy đủ
không tự đại diện toàn corpus. Điểm chọn lượt sinh 0–100 của A không phải accuracy.
Xem [quy trình và cách đọc kết quả](../../docs/EVALUATE_QWEN.md).
