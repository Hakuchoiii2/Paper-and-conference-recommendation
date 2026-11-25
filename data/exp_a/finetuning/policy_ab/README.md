# So sánh policy trên adapter QLoRA v1

2026-10-18 10:07 Asia/Bangkok: Kaggle xác nhận **RUNNING**, kernel version 1,
private: https://www.kaggle.com/code/htnkhi/exp-a-qlora-policy-ab-v2

Chỉ suy luận, không huấn luyện lại. Cả hai nhánh dùng cùng adapter đã niêm phong
`htnkhi/exp-a-qwen3-8b-facets-qlora-v1`, Qwen/Qwen3-8B revision
`b968826d9c46dd6066d109eabc6255188de91218`, NF4/FP16, greedy decoding,
enable_thinking=False, output tối đa 2048 token, seed 42 và tối đa 3 lượt/bài.
Hai worker chạy song song trên 2 T4, mỗi worker thấy một GPU.

- `old_v3_7`: instruction đóng băng và pipeline v3.7 nguyên bản, evidence_id đơn.
- `new_v2_2`: prompt v2.2 candidate, schema nhiều evidence_ids, draft và review
  bắt buộc; có lượt sửa thứ ba khi validation còn lỗi. Lưu toàn bộ phản hồi thô,
  lỗi, lựa chọn, từng câu evidence chính xác, token, thời gian và runtime.

Đây là thay đổi kết hợp policy/schema/cơ chế review và validation. Khi đánh giá
phải tách lỗi định dạng, grounding, vai trò/nội dung và thiếu facet; tổng điểm
không tự xác định riêng hiệu ứng của policy. Validation từ vựng chưa chứng minh
entailment hoặc đúng tham chiếu đại từ.

Mẫu nguồn mới 40 bài: seed 20261019, 10 bài trong mỗi ô train/dev ×
existing/additional AI reference. Không trùng test100, pilot50 hoặc pilot40
policy trước; cũng kiểm tra trùng title và toàn văn đầu vào đã normalize.
Đây là chẩn đoán trên train/dev mà adapter đã tiếp xúc, không phải benchmark
held-out mới. Cả 40 bài là CSFCube: ba bài SciFact train/dev đủ điều kiện đã
thuộc pilot40 trước. Không chọn mẫu theo nhãn hoặc lỗi của student.

Kaggle nhận nguồn và mã chạy, không nhận nhãn tham chiếu, target train/dev hoặc
test. Mẫu nguồn và lựa chọn cố định nằm ở `build/source_papers.jsonl` và
`build/build_manifest.json`. Tệp nguồn tham chiếu cho vòng mới còn phải được
GPT/Codex đọc độc lập và niêm phong **trước khi mở dự đoán student**. Chưa mở
output/log chứa nội dung dự đoán; chưa có F1 mới. Human review vẫn pending.
Không lấy output student làm nhãn. Mốc test v1 59.28 và tất cả tệp v1 giữ nguyên.

`build/push_report.json`: bằng chứng push, trạng thái RUNNING và xác nhận code
đã tải lại từ cloud trùng bootstrap local; metadata private, nguồn adapter và
dataset chính xác. `build/preflight.json`: import bundle độc lập, checksum nguồn,
adapter, 38 tệp v1 không đổi, token đầu vào tối đa old2685/new1916, không cắt nguồn.
`build/project_tests.log` có 88 tests PASS; `build/finetuning_tests.log` có 43 tests
PASS. Bảy tests mới gồm review bắt buộc, nhiều câu evidence, lỗi schema, giữ nhãn
hợp lệ khi fallback, ngăn checkpoint sai arm/paper/adapter/prompt và bundle nguồn.
Reviewer độc lập đã kiểm tra lại hai lỗi fallback/checkpoint sau khi sửa và kết
luận không còn launch blocker. GPU inference chưa được kiểm tra bằng output.

Experiment signature:
`825fecb2556d886d754af96fffe2f70f08d3209a9b30f63bc7bfc0f8d4188427`

Bundle SHA256:
`38e77ec72990909c9dfe9dae3be4421af4e1c2313adb0d8904a6964399032b35`

Sau khi nhãn nguồn vòng mới đã được rà và seal, tải output về thư mục mới,
kiểm tra signature/hash/đủ 40 IDs ở mỗi arm; dùng cùng nhãn tham chiếu để so cặp.
Giữ nguyên threshold evaluator 0.85 và ghi riêng các bất đồng semantic cần review.
Việc chuẩn hóa toàn bộ dữ liệu, fine-tune v2 và trích lại corpus phụ thuộc vào
các bước kiểm chứng trong quyết định dưới đây.

## Quyết định đã chốt với người dùng — 2026-10-18

Mục tiêu là chuẩn trích xuất đúng theo nguồn. Adapter v1 là công cụ thử khả năng
thực hiện chuẩn, không phải căn cứ để định nghĩa nhãn đúng. Policy quy định ý
nghĩa/role, granularity, điều kiện/phủ định và evidence; prompt là cách truyền đạt
policy cho model. Không sửa policy chỉ để tăng điểm hoặc chiều theo lỗi của v1.

1. Dùng 40 bài mới của lượt Kaggle này làm tập phát triển policy/prompt trên
   adapter v1. So với nhãn trích độc lập từ nguồn đã seal trước khi mở dự đoán;
   dự đoán chỉ gợi ý ca cần kiểm tra, không được dùng làm nhãn tham chiếu.
   Giữ lịch sử từng phiên bản policy/prompt/nhãn và lý do sửa theo bằng chứng.
2. Khi các bất đồng đã được xử lý, đóng băng policy/prompt/schema và kiểm tra
   trên mẫu dev chưa dùng để chỉnh. Điểm trên pilot đã dùng tối ưu chỉ là chẩn
   đoán phát triển, không chứng minh khả năng tổng quát hóa.
3. Chuẩn hóa toàn bộ train/dev thành phiên bản v2 theo chuẩn đã kiểm chứng,
   giữ split và bản v1. Fine-tune adapter v2 từ cùng base model đã pin, dùng
   prompt/schema và target mới nhất quán. Không mặc định tiếp tục train adapter
   v1 bằng nhãn mới. Nhãn AI vẫn có provenance và trạng thái human review pending.
4. Kiểm tra lại cách diễn đạt prompt trên dev khi có v2. Nếu phải sửa prompt,
   chạy lại cả v1 và v2 bằng cùng prompt đã chốt để so sánh; không thay đổi định
   nghĩa nhãn nhằm khớp hành vi của adapter mới.
5. Đánh giá cặp v1/v2 trên cùng test IDs, prompt, nhãn tham chiếu và điều kiện
   suy luận. Nếu test cần chuẩn hóa nhãn, tạo bản test-reference v2 độc lập từ
   nguồn, không xem dự đoán, giữ bản v1 và điểm cũ. Không dùng test để chỉnh
   policy/prompt hoặc chọn checkpoint. Báo riêng lỗi format, grounding, role,
   thiếu ý và giới hạn của AI references; giữ evaluator threshold 0.85.
6. Sau khi đạt các kiểm chứng trên, mới dùng bộ adapter/prompt/schema đã chốt
   để sinh facet toàn corpus thành phiên bản mới, kèm nguồn gốc và hàng đợi
   review các ca lỗi. Giữ corpus/facet v1 để đối chiếu.

Đây là lộ trình đã được chấp thuận theo điều kiện; không cần hỏi lại quyết định
thiết kế này ở từng bước. Các bước chuẩn hóa diện rộng và train v2 chưa thực
hiện; lượt Kaggle v1 A/B vẫn là lần suy luận đã push, không thay đổi cấu hình
hay chạy thêm chỉ vì ghi nhận quyết định này.
