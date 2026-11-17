# Bằng chứng nghiên cứu: IE trên mô hình 7–8B

Ngày kiểm nguồn: 2026-10-21. Đọc toàn văn các phần phương pháp, kết quả và ablation; chỉ dùng nguồn tác giả/hội nghị. Không chạy thí nghiệm. Đây là ghi chú nguồn bổ trợ, chưa phải kiểm toán lỗi dự án.

## 1. SciRIFF — sát nhất với văn bản khoa học

[EMNLP 2025, toàn văn](https://aclanthology.org/2025.emnlp-main.310.pdf), §3.2, §4.1–4.2, Table 2–3.

- Backbone được xác minh: Llama 3.1 **8B**, có cả base và Instruct. Đây là **SFT**, không phải chỉ đổi prompt.
- Table 2, Llama 3.1 8B-Instruct: trung bình SciRIFF-Eval **50.5 → 64.1** sau SFT SciRIFF; BioRED **48.8 → 86.0**, SciERC **30.6 → 56.8**. Có nhiệm vụ giảm: MuP **88.3 → 70.5**.
- Table 3: expert template **62.8**, simple **42.2**, synthetic **28.0**. Mỗi biến thể dùng training và evaluation template tương ứng; không được diễn giải thành gain của prompt-only trên model cố định.
- Lưu ý phiên bản: bản arXiv 2024 thường được trích với Llama2 7B; các số 8B ở đây lấy từ bản EMNLP2025.

Suy luận áp dụng: viết rõ quy tắc evidence, trường đầu ra và điều kiện biên trước khi tạo train data; đo riêng từng facet.

## 2. GoLLIE — guideline và ví dụ đại diện

[ICLR 2024, toàn văn HTML](https://arxiv.org/html/2310.03668v5), §3–6, Table 3–5.

- **CodeLlama 7B + QLoRA**; hướng dẫn được biểu diễn bằng dataclass/docstring. Là training có giám sát để học tuân thủ guideline.
- Table 3: zero-shot trung bình **42.3 → 55.3 F1**. Baseline là model **đã được SFT IE** nhưng bỏ guideline/regularization, không phải raw base.
- Table 4: bỏ representative annotation candidates còn **49.9**; bỏ class dropout **54.0**. Shuffling/paraphrase/masking không có đóng góp có ý nghĩa thống kê trong ablation này.
- Table 5, nhãn CrossNER-AI Task: **2.7 → 63.9**. Đây là entity Task của benchmark, không đồng nhất facet task của dự án.
- §6 cũng ghi nhận reference không khớp guideline, nhãn mơ hồ và xung đột độ hạt.

Suy luận áp dụng: thử ít ví dụ đúng/sai gần ranh giới problem/task/method; không bê toàn bộ regularization sang pipeline.

## 3. GuideX — chất lượng và độ hạt của synthetic data

[Toàn văn arXiv2506.00649v1](https://arxiv.org/html/2506.00649v1), §3, §5–6, Table 2.

- Student **Llama3.1 base 8B**, **QLoRA**; teacher tạo nhãn **Llama3.1-Instruct 70B**. Không phải hệ hoàn toàn 8B.
- Tạo dữ liệu qua summary → JSON → guideline → instances; ưu tiên span ngắn nhưng giữ nghĩa; lọc lỗi schema.
- Table 2, trung bình bảy benchmark NER OOD: raw base **30.08**, synthetic-only **37.14**; gold-only **62.77**, synthetic rồi gold **64.15** (**+1.38**, không phải +7 so với gold).
- Synthetic-only làm Movie giảm **40.86 → 31.62**; không bảo đảm mọi miền tăng.
- Lọc code/schema không chứng minh nhãn đúng nghĩa. Kết quả là NER, chưa chứng minh hiệu quả trên contribution nhiều câu.

Suy luận áp dụng: dùng teacher để tạo ví dụ lỗi khó đã kiểm nguồn, rồi chuẩn hóa cùng policy; không tăng synthetic hàng loạt trước khi audit.

## 4. UniversalNER — dạy model trả rỗng

[ICLR2024 toàn văn](https://proceedings.iclr.cc/paper_files/paper/2024/file/34678d08b36076de986df95c5bbba92f-Paper-Conference.pdf), §3.2, §5.4, Table 4.

- UniNER-**7B**, instruction tuning/distillation từ ChatGPT trên LLaMA.
- Negative là entity type **không xuất hiện trong passage**, target **[]**; lấy mẫu theo tần suất type.
- Table 4: không negatives **31.5**, uniform **47.7**, frequency **53.4** F1 trung bình bảy bộ OOD. Tất cả arm đều đã instruction-tuned.
- Đây không phải hard negative phân biệt vai trò của hai span cùng xuất hiện, cũng không phải tự review khi inference.

Suy luận áp dụng: thêm ví dụ facet rỗng thật vào train/dev sau human check. Muốn dạy “method được nhắc nhưng chỉ là background” cần một ablation riêng; bài này không xác nhận trực tiếp.

## Ưu tiên thực nghiệm cho dự án — suy luận, chưa được kiểm chứng

1. **Chốt policy + audit nhãn dev**: cùng câu có thể được tách/gộp khác nhau; ghi riêng lỗi nghĩa, lỗi boundary, lỗi role và lỗi reference. Không đổi reference sau khi thấy output để làm tăng điểm.
2. **Base-only với guideline và ví dụ biên**: cùng weights/decoder/budget, so v1 với sửa một yếu tố mỗi lần. Các paper trên ủng hộ lựa chọn thiết kế; chưa cho bằng chứng số về gain prompt-only của Qwen3-8B.
3. **Kiểm từng item**: source alignment, schema, facet role; repair phải nhận lỗi cụ thể. Đánh giá repair thành công trên item lỗi và tỷ lệ làm hỏng item hợp lệ.
4. **Chuẩn hóa train theo pipeline đã khóa**: nhãn ngắn đủ nghĩa, đủ điều kiện/đối chứng, negative rỗng và ví dụ role khó. Giữ nguyên test; so adapter mới với base dưới cùng protocol.

Không xếp hạng mô hình bằng cách so trực tiếp 55.3/64.1/64.15 giữa các bài: khác dataset, schema, metric và trung bình. Không có bài nào ở đây chứng minh 8B đã giải quyết đầy đủ năm facet của dự án hoặc rằng chỉ thêm epoch sẽ sửa regression v2.
