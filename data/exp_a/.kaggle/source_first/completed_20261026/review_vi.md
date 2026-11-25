# Kiểm tra V vs Source-first — 26/10/2026

Kaggle: https://www.kaggle.com/code/htnkhi/exp-a-v-vs-source-first-pilot50 — COMPLETE. Đủ 50 bài mỗi nhánh. Không training/fine-tune.

## Kết quả

| Nhánh | Micro-F1 (%) | Macro-F1 (%) | Pipeline fallback | Annotation fallback | Calls mới | Calls tái dùng |
|---|---:|---:|---:|---:|---:|---:|
| R0 | 56.36 | 56.89 | 33/50 | 33/50 | 0 | 0 |
| R2a-V | 56.69 | 56.53 | 18/50 | 18/50 | 74 | 50 |
| Source-first | 50.07 | 51.46 | 43/50 | 22/50 | 146 | 0 |

R0 là baseline lưu sẵn; 0 calls mới không có nghĩa baseline không tốn chi phí. V chỉ tăng 0,33 điểm phần trăm micro-F1 so với R0 và macro-F1 giảm 0,36 điểm. Source-first thấp hơn V 6,63 điểm micro-F1.

| Facet F1 (%) | R0 | V | Source-first |
|---|---:|---:|---:|
| problem | 44.44 | 38.71 | 32.35 |
| task | 54.05 | 54.05 | 40.00 |
| method | 65.38 | 65.64 | 50.20 |
| dataset | 70.59 | 72.73 | 78.79 |
| contribution | 50.00 | 51.54 | 55.94 |

Source-first hơn V ở contribution (+4,40 điểm) và dataset (+6,06), nhưng giảm method (-15,44), task (-14,05), problem (-6,36). Theo micro-F1 từng bài: 13 tốt hơn V, 31 kém hơn, 6 bằng.

## Các vấn đề cần xử lý trước khi chạy lớn

1. **Inventory thường bị bác do thiếu trường bắt buộc.** 41/50 bài vẫn không có inventory hợp lệ sau tối đa hai lần. Trong đó 36 bài thiếu `context_ids`, 1 bài có extra keys, 3 bài không parse được một JSON object duy nhất, 1 bài chạm token cap. Ví dụ P000268 bỏ `context_ids` trong cả hai lần. Validator yêu cầu đúng bộ keys; lần retry chỉ báo `unit 0: wrong keys`, không nêu field thiếu và không cung cấp output cũ. Khi cả hai lần lỗi, inventory bị xóa và chỉ còn một call annotation. Cần thông báo chính xác keys thiếu/thừa và schema rõ ràng (bao gồm `context_ids: []` khi không có liên kết), thử trên các raw lỗi thực trước khi chạy lại. Không tự thêm liên kết hoặc coi inventory chưa hợp lệ là hợp lệ.

2. **Nhãn method vẫn bị gộp và vai trò vẫn có thể sai.** P000268: V tách unigram/bigram/LDA; Source-first gộp `unigram, bigram and LDA content models`, scorer không match được các nhãn riêng và method TP từ 3 xuống 0. P002471: Source-first đưa kết quả so sánh `no more effective ... than text explanation` vào problem dù nguồn không nói đây là hạn chế có trước nghiên cứu. Cần kiểm tra quy tắc tách ý và phân biệt kết quả nghiên cứu với problem bằng ví dụ có người xác nhận.

3. **Quan hệ caveat qua nhiều câu chưa được giải quyết.** Ở P002471, cả hai vẫn tách finding tích cực và câu giới hạn. Source-first match được câu giới hạn với reference tổng hợp, nhưng điều đó không chứng minh schema đã biểu diễn đủ quan hệ. Evidence cuối vẫn chỉ cho phép một sentence ID.

## Chi phí

| Chi phí mới | V | Source-first |
|---|---:|---:|
| Input tokens | 361,183 | 184,806 |
| Output tokens | 20,700 | 48,151 |
| Thời gian generation (phút) | 39.58 | 61.84 |

V tái dùng 50 call draft; Source-first chạy mới toàn bộ. Các số này là chi phí tăng thêm, không phải so sánh tổng compute ngang nhau. Wall time hai nhánh chạy song song: 64,85 phút. Source-first có 44 bài retry inventory, 9 inventory cuối hợp lệ với tổng 48 units; pipeline fallback 43 và annotation fallback 22 là hai chỉ số khác nhau.

## Bằng chứng kiểm tra

- 779 kiểm tra đạt: checksum/signature của 150 records, cohort, frozen settings/code/source, baseline file hashes, draft V tái dùng nguyên văn, call caps, số fallback, chi phí và phép tính TP/FP/FN/F1.
- Replay 94 lượt inventory với validator đóng băng: lỗi khớp bản ghi cloud.
- Audit máy đọc được: [completion_audit.json](completion_audit.json).
- Điểm gốc: [experiment_summary.json](exp_a_v_source_first/results/experiment_summary.json).

## Kết luận

Giữ V làm control cho bước tiếp theo; bản Source-first hiện tại chưa đủ ổn để chạy lớn. Trước hết sửa độ tuân thủ schema và kiểm tra ngữ nghĩa trên tập lỗi nhỏ, sau đó mới đánh giá lại. Chưa kết luận ý tưởng source-first không hiệu quả chỉ từ lần triển khai này.

Giới hạn: pilot50 là development cohort dùng lại, reference do AI tạo và chưa human review. Đã kiểm số học từ các quyết định match lưu sẵn; chưa chạy lại embedding tại local. Fallback thấp không đồng nghĩa ngữ nghĩa tốt.
