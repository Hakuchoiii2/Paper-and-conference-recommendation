# Thực nghiệm <ký hiệu> — <tên tiếng Việt>

Trạng thái triển khai và các quy ước cần chốt.

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

## 1. Mục đích và câu hỏi thực nghiệm

Giải thích câu hỏi cần kiểm chứng, ví dụ sử dụng, quan hệ với A–E khác và giới hạn
dữ liệu thật/mô phỏng. Không mô tả kết quả mô hình chưa chạy.

## 2. Đầu vào của generator xây dataset

Mọi exp đọc `data/processed/papers.jsonl` đã có. Facet A trích từ bài thật ở
`data/exp_a/generated/facets_silver.jsonl`; E đọc thêm users mock D.
Giữ nguyên paper_id/title/abstract. Không tạo catalog mẫu hoặc ID mock riêng.
Ghi từng tệp nguyên liệu generator phải đọc (corpus, ID map, facets, source labels,
users từ exp khác), config/rule/version và mục đích. Phân biệt đã có/cần tạo/tùy
chọn; ghi prerequisite còn thiếu. Không coi query/intents/users/events mà generator
phải sinh là đầu vào có sẵn. Liên kết DATA_CONTRACT.md và dùng ID chung.

## 3. Đầu ra của generator xây dataset

Output mock ở `data/exp_<x>/samples/generated/` và `samples/ground_truth/`,
manifest ghi `dataset_kind: mock` cho queries/nhãn/hành vi synthetic; A silver ghi real. Output mở rộng ở `generated/` và
`ground_truth/` trực tiếp dưới exp; không ghi đè hoặc trộn hai loại.
Bảng tên tệp generator phải tạo, đường dẫn và đơn vị bản ghi. Giải thích nguồn
nhãn, bản nào cần human review, số lượng/quota/gap. Tách observable inputs, nhãn đánh giá, latent
truth và dữ liệu tương lai. Manifest ghi version/kind, seed, hashes và actual counts.

## 4. Định nghĩa trường dữ liệu

Ý nghĩa, kiểu, enum, missing values, khóa duy nhất và foreign keys. Giải thích các
điểm dễ nhầm, nguồn nhãn và mapping chưa duyệt; không tự đổi nhãn native.

## 5. Ví dụ generator: nguyên liệu → dataset

Ví dụ nguyên liệu/config generator đọc và records nó xuất ra từng tệp. JSON dùng ID corpus chính; ví dụ chỉ minh họa schema; label generator phải dùng facets A thực tế. Đánh dấu rõ nhãn minh họa, không coi
ví dụ schema là đáp án đã kiểm chứng. Giữ nguyên tên trường và nội dung bài nguồn.

## 6. Các bước generator phải thực hiện

Nguồn, seed, sampling, positives/negatives, sizes, splits, quy tắc ngữ nghĩa và
giới hạn mô phỏng. Chỉ ghi lệnh generator đang chạy được. Nếu chưa triển khai thì
ghi rõ prerequisite và trạng thái; không bịa lệnh. Chỉ số đề xuất cần chốt trước
khi chạy, không trình bày như kết quả hiện có.

## 7. Quy tắc kiểm tra và điều kiện nghiệm thu

Tách nghiệm thu mock (không cần gold thật) khỏi nghiệm thu dataset dùng nhãn đã kiểm chứng.
Khi facets A/alias/rule thay đổi, giữ corpus/IDs và sinh lại labels/splits/manifests.
Silver không tính vào gold; bộ mở rộng có hành vi synthetic vẫn ghi mock.
Structural/semantic checks, chống leakage, actual counts, review chất lượng và
tiêu chí nghiệm thu riêng. Phân biệt corpus validation hiện có với validator
thực nghiệm chưa xây; không silent-pass khi dữ liệu bắt buộc thiếu.

Cách mô hình sử dụng dataset đã tạo ghi riêng ở cuối; không thay hướng dẫn xây
dataset bằng mô tả query → ranking/scores của mô hình.
