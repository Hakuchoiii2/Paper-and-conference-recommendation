# Chẩn đoán timeout A/B — 18/10/2026

Kiểm tra lúc khoảng 16:56–16:58 Asia/Bangkok. Kernel:
`htnkhi/exp-a-qlora-policy-ab-v2`, version 1. Chỉ đọc Kaggle và tải bằng chứng;
không thay đổi mã chạy, cấu hình, adapter, nhãn hay khởi chạy phiên mới.

## Kết luận

Nhánh mới sinh đầu ra lặp, không tạo được JSON hợp lệ ở nhiều bài, rồi tiêu hết
ngân sách sinh ở cả ba lượt. Ngân sách thực thi 14.400 giây (4 giờ), đã được ghi
trong bản `DIAGNOSIS_2026-10-18.md` đã lưu ở ZIP lịch sử, không đủ cho khối lượng
công việc thực tế này. Người dùng báo giao diện đã timeout; API hiện trả
`KernelWorkerStatus.CANCEL_ACKNOWLEDGED`, với `failure_message` rỗng. Mã trạng
thái API này tự nó không phân biệt timeout với hủy thủ công.

## Bằng chứng từ log và checkpoint thật

| Chỉ số | old_v3_7 | new_v2_2 |
|---|---:|---:|
| Bài hoàn thành | 40/40 | 28/40 |
| Mốc hoàn thành bài cuối, tính từ đầu phiên | 2.644,48 giây (~44 phút) | 14.046,09 giây (~3 giờ 54 phút) |
| Tổng thời gian sinh của các bài hoàn thành | 2.461,85 giây | 13.864,30 giây |
| Lượt sinh | 85 | 75 |
| Lượt sinh chạm 2.048 token | 0 | 48 |
| Tổng output token | 16.590 | 107.582 |
| Bài phải dùng fallback | 3 | 19 |

- Cả 16 bài chậm của nhánh mới đều dùng **3 × 2.048 = 6.144 output token**,
  `reached_token_limit=true` và `schema_valid=false` ở cả ba lượt.
- Mỗi bài này mất khoảng 773–811 giây (~13 phút). Tổng 12.629,66 giây,
  chiếm **91,09% thời gian sinh** của nhánh mới đã hoàn thành.
- Đo cấu trúc văn bản, không đánh giá nội dung facet: các bài này có chuỗi
  10 từ lặp 6–99 lần trong một phản hồi; các bài không chạm trần tối đa 3 lần.
  11/16 bài trả đúng cùng một chuỗi đầu ra ở cả ba lượt. 17/19 bài chạy ba
  lượt trả đầu ra lượt hai và ba giống hệt nhau.
- Lỗi của nhánh mới gồm JSON bị cắt giữa chuỗi, dữ liệu thừa sau JSON và
  thiếu dấu phân cách. Đây là bằng chứng đầu ra sai cấu trúc; chưa đánh giá
  đúng/sai ngữ nghĩa so với nhãn tham chiếu.
- Kiểm tra thêm các object JSON hoàn chỉnh trong draft bị cắt cho thấy lặp
  tập trung ở `contribution`: P001892 có 111 mục hoàn chỉnh nhưng chỉ 11 mục
  khác nhau; một object giống hệt xuất hiện 101 lần. P000962 có 59 mục nhưng
  chỉ 14 mục khác nhau, một object lặp 23 lần. Đây là đếm cấu trúc và trùng
  chuỗi, không chấm nội dung facet. Generator sinh xong mới chuyển cho
  validator, nên validator không ngắt được việc nối thêm mục trùng khi đang
  sinh. Lời gọi generate không ép JSON theo grammar/schema lúc giải mã.
- Log cuối không chứa Traceback, CUDA error hay OutOfMemoryError. Bằng chứng
  hiện có xác định nút thắt ở sinh token và retry.

## Cơ chế trong mã chạy

- `policy_ab/runner.py:46–73`: bắt buộc draft và review, thêm lượt thứ ba khi
  validation còn lỗi. Review đưa phản hồi sai trước đó vào hội thoại.
- `matrix.py:233–246`: greedy decoding (`do_sample=False`), tối đa 2.048
  token/lượt; có đổi seed nhưng không có cơ chế chặn sinh lặp hoặc dừng sớm
  theo JSON hoàn chỉnh trong lời gọi này. Metadata thực tế xác nhận nhiều
  retry lặp lại cùng đầu ra.
- `policy_ab/runner.py:149–155`: mỗi GPU gắn cố định với một nhánh. Nhánh cũ
  xong sau ~44 phút, nhưng GPU đó không nhận các bài còn lại của nhánh mới.
- Adapter v1 được huấn luyện theo schema cũ; nhánh mới đổi prompt/schema sang
  nhiều `evidence_ids`. Đây là yếu tố cần thử tách riêng để xác định nguyên
  nhân gây sinh lặp; dữ liệu hiện tại chưa chứng minh riêng schema hay prompt
  là nguyên nhân duy nhất.

## Kết quả đã giữ và hướng xử lý

Kaggle xuất 131 file. Đã tải 40 checkpoint cũ, 28 checkpoint mới và settings
về thư mục `timeout_v1/`. Đã kiểm đủ 68 checksum record, experiment signature,
paper/arm, adapter manifest và hash prompt với bundle đã launch. Còn thiếu
12 bài của nhánh mới. Chỉ thống kê metadata hiệu năng và cấu trúc đầu ra;
không chấm facet hay dùng dự đoán để sửa nhãn tham chiếu.

Ưu tiên xử lý sinh lặp và retry không tiến triển, đo lại trên vài bài chậm,
rồi phân bổ công việc giữa GPU và đặt ngân sách thời gian theo số đo. Thay đổi
cơ chế sinh/retry tạo điều kiện thí nghiệm mới, cần ghi phiên bản riêng; không
gộp kết quả mới với kết quả cũ như cùng một cấu hình. Các checkpoint đã tải
giữ được bằng chứng và có thể dùng khi thiết kế lượt tiếp tục tương thích.

## Tệp bằng chứng

- `timeout_v1/cloud_status.json`: trạng thái API, thời điểm và danh sách tải.
- `timeout_v1/exp-a-qlora-policy-ab-v2.log`: log cloud cuối phiên.
- `timeout_v1/performance_summary.json`: thống kê token/lượt/thời gian, lỗi
  đã gom theo loại, số đo lặp không chứa trích dẫn nội dung dự đoán.
- `timeout_v1/policy_ab/results/{arm}/records/`: checkpoint có chữ ký/hash.

Kiểm tra assertions về 40/28 checkpoint, 16 bài và 48 lượt chạm trần,
3 lượt/bài và JSON không hợp lệ: PASS. Đây là xác minh nguyên nhân từ kết quả
phiên đã dừng; chưa sửa hoặc xác minh một lượt Kaggle mới.
