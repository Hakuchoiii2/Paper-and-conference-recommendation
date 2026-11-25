# Thử reviewer ngữ nghĩa local — 25/10/2026

**Kết quả: reviewer hiện tại chưa phù hợp để tự sửa annotation.** Nó tìm được một số cảnh báo hợp lý nhưng đồng thời bắt nhầm item có hỗ trợ nguồn, áp dụng sai định nghĩa contribution/method, và có lý do mâu thuẫn chính câu trích. Đây là kết quả của cấu hình/prompt thử nghiệm dưới đây, không phải kết luận mọi semantic reviewer đều không dùng được.

## Phạm vi thực sự đã chạy

- Local RTX 4060 Laptop 8 GB; Qwen3-4B-Instruct-2507 revision `cdbee75f17c01a7cc42f958dc650907174af0554`, NF4 double + FP16, greedy, SDPA; offline. Không gọi API ngoài, không chạy Kaggle, không training.
- Đầu vào: output R2a-full đã tải, 8 bài / 74 item. Bốn ca đã biết: P001181, P001211, P002471, P003211. Bốn bài lấy mẫu bằng seed 20261025: P001506, P001604, P002380, P002652.
- Mỗi bài một call, tối đa 2048 output tokens; không retry, không sửa prompt sau khi xem kết quả. Tổng generation 227,53 giây, 7.781 input tokens, 3.784 output tokens; không reply nào chạm trần token.
- Model chỉ nhận câu nguồn, concept, facet và item ID. Không nhận reference, F1, fallback, audit lỗi cũ hay các ghi chú đánh giá của Codex.
- Script chỉ lưu warning; không có chức năng áp dụng sửa. Hash của 8 record gốc và file nguồn giữ nguyên sau chạy.

## Hai loại lỗi cần tách

**Định dạng:** 8/8 trả JSON đọc được nhưng chỉ **1/8** đúng toàn bộ schema/ID/quote. Có 23/24 warning dùng ID sai; đa số thêm tiền tố `facet:`, riêng P002380 thiếu cả index. Có hai câu trích không phải substring chính xác của source ID đã chọn, đều ở P001604. Tất cả reply không đạt vẫn bị từ chối; không tự chấp nhận sau khi sửa ID.

**Nội dung:** raw replies có **15 flag và 9 uncertain**. Để đọc nội dung, bản diagnostic chỉ bỏ tiền tố ID thừa; không ánh xạ các ID thiếu index và không thay đổi output gốc. Trong 15 flag:

- 7 flag trỏ vào item được ghi chú nguồn trước chạy đánh giá là có hỗ trợ.
- 6 flag trỏ vào item ghi chú trước chạy cho là có vấn đề, nhưng trỏ đúng item không chứng minh lý do đúng.
- 1 flag ở item còn tranh luận; 1 không xác định được item vì thiếu index.

Sau khi đọc từng lý do đối chiếu câu nguồn, đánh giá tạm thời của Codex: **2 flag có lý do đúng rõ, 1 có phần hợp lý nhưng lập luận quá rộng, 10 có lý do sai, 1 chưa kết luận, 1 không xác định được item**. Chín uncertain gồm tám cảnh báo quá khắt khe trên item được ghi chú là có hỗ trợ và một cảnh báo không xác định được item. Đây là đánh giá định tính của Codex, không phải precision/recall từ human gold độc lập.

## Các ví dụ quyết định kết luận

| Ca | Reviewer nói gì | Đối chiếu nguồn |
|---|---|---|
| P002471 problem:0 | “students struggle…” không được nguồn nói rõ | Cảnh báo hợp lý: abstract chỉ mô tả tutor và kết quả đánh giá |
| P001506 problem:0 | Nguồn khác biệt về hai latent spaces không chứng minh mọi VAE cũ thiếu syntax | Cảnh báo hợp lý về suy diễn quá nguồn |
| P001181 problem:0 | Prior finding không được làm problem | Bắt nhầm theo policy đã nêu: hạn chế prior work có thể là problem; prompt cũng cho phép |
| P002471 contribution:1 | Không hiệu quả hơn text là limitation nên không phải contribution | Sai: kết quả âm/null/comparative vẫn là finding |
| P001211 contribution:1 | Vulnerability là negative observation, không phải positive contribution | Tự thêm điều kiện contribution phải tích cực, trái định nghĩa finding |
| P001604 method:2 | Approach mới là contribution nên không thể là method | Sai: một approach có thể mang cả hai vai trò khi nguồn hỗ trợ |
| P002652 method:0 | Exact exponential DP algorithm chỉ là complexity result | Sai: A2 nêu rõ algorithm for the problem, dù đứng cùng câu với kết quả NP-hard |
| P003211 contribution:0 | “more potential” không có trong nguồn | Mâu thuẫn câu trích của chính nó, vốn chứa “hardcore brainwave has more potential”; annotation được audit cũng không chứa cụm này. Không phát hiện đúng lỗi bỏ điều kiện channel/frequency |

Một ca đặc biệt: P001211 contribution:3 đúng là gộp hai finding độc lập, nhưng reviewer lại phản đối vì cho rằng experimental result không phải contribution. Không tính đây là phát hiện đúng lỗi. Tương tự, P001604 contribution:3 cần giữ comparator, nhưng reviewer bắt lỗi gộp context/metric và còn nói ER/VD không có trong nguồn dù có ngay trong quote.

Các lỗi rõ vẫn bỏ sót gồm generic resource bị gán dataset (P003211, P001604), caveat của finding P002471 contribution:0, và contribution quá chung “discuss advantages” ở P002652. Việc reviewer không cảnh báo một item không chứng nhận item đúng.

## Hướng tiếp theo

1. Giữ R2a output nguyên vẹn; chưa nối reviewer này vào repair tự động.
2. Nếu thử v2: dùng ID số đơn giản, schema ràng buộc khi decode nếu runtime hỗ trợ; giữ kiểm quote độc lập. Điều này chỉ xử lý giao thức, không sửa được suy luận.
3. Làm rõ bằng ví dụ cân bằng: negative/null finding là contribution; method có thể mới và cũng là contribution; problem có thể là hạn chế từ prior work; mục tiêu phụ vẫn có thể là task. Dùng ca v1 làm regression, không dùng lại để tuyên bố độ chính xác tổng quát.
4. Cần người đánh giá nguồn xác nhận các ca tranh luận, rồi đo trên bài mới. Reviewer 4B trong phép thử này khác model 8B trên Kaggle; chưa thể suy ra chất lượng reviewer 8B từ kết quả này.

## Hồ sơ và kiểm tra

- [Script spike](../semantic_review_local/spike.py) và [README](../semantic_review_local/README.md).
- [Manifest](../semantic_review_local/run_20261025_v1/manifest.json), [input packets](../semantic_review_local/run_20261025_v1/packets.json), [prompt](../semantic_review_local/run_20261025_v1/prompt.txt), [runtime log](../semantic_review_local/run_20261025_v1/runtime.log).
- [Ghi chú nguồn lập trước inference](../semantic_review_local/run_20261025_v1/source_first_notes.json): 58 supported, 11 issue, 5 ambiguous; không phải human gold. Các ca known có lịch sử đã được xem trước, nên không coi phép thử là đánh giá mù hoàn toàn.
- [Summary](../semantic_review_local/run_20261025_v1/summary.json), [diagnostic warnings](../semantic_review_local/run_20261025_v1/diagnostic_warnings.json), [đối chiếu từng lý do](../semantic_review_local/run_20261025_v1/rationale_adjudication.json).

Đã chạy self-check cho schema, item identity và exact quote; xác minh đủ 8 reply, không truncation, ghi chú nguồn bao phủ đủ 74 item không trùng nhóm, hash đầu vào giữ nguyên. Không đánh giá sửa annotation vì phép thử không tạo bản sửa; không có kiểm định thống kê hoặc đánh giá human độc lập.
