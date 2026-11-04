# V-recall pilot50 — kiểm tra kết quả 26/10/2026

Kaggle COMPLETE, version 1, đủ 50 signed records mỗi nhánh. Mục tiêu đã chọn: ưu tiên recall.

| Nhánh | Precision (%) | Recall (%) | F2 (%) | F1 (%) | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| R0 | 58.97 | 53.98 | 54.91 | 56.36 | 217 | 151 | 185 |
| R2a-V | 60.00 | 53.73 | 54.88 | 56.69 | 216 | 144 | 186 |
| V-review1 | 60.66 | 54.48 | 55.61 | 57.40 | 219 | 142 | 183 |
| V-recall | 58.25 | 56.22 | 56.61 | 57.22 | 226 | 162 | 176 |

V-recall so với V: recall +2,49 điểm phần trăm, F2 +1,74 điểm, F1 +0,52 điểm; precision -1,75 điểm. Đây là cải thiện mô tả trên tập dev đã dùng lại, chưa phải bằng chứng tổng quát hóa.

`V-review1` là kết quả sau lượt review đầu, trước coverage, không phải arm dùng thêm model. So với mốc này, coverage thêm đúng 27 nhãn: 7 khớp reference (4 method, 3 task), 20 không khớp. TP +7, FP +20, FN -7; recall +1,74 điểm, F2 +1,00 điểm, nhưng F1 -0,19 điểm. Vì vậy không quy toàn bộ +10 TP so với V cho coverage.

| Recall theo facet (%) | V | V-review1 | V-recall |
|---|---:|---:|---:|
| task | 47.62 | 48.81 | 52.38 |
| method | 59.03 | 59.03 | 61.81 |
| contribution | 52.76 | 54.33 | 54.33 |
| problem | 38.71 | 38.71 | 38.71 |
| dataset | 75.00 | 75.00 | 75.00 |

## Coverage tìm được gì và vẫn sai ở đâu

- P002471: bổ sung method `text explanation of step-by-step execution of the program`, khớp phương pháp đối chứng trong reference.
- P001389: bổ sung `qualitative and quantitative evaluations`, khớp reference; vẫn có một nhãn phương pháp khác không khớp.
- P002877: thêm `comparable BLEU scores for each language pair in WMT15` vào method. Đây là kết quả đánh giá, không phải tên phương pháp — lỗi vai trò có thể quan sát từ nguồn.
- P001963: đưa nhận định `users in the same community tend to be interested in similar set of topics in all time periods` vào task. Đây là nhận định/giả định trong nguồn, không phải một mục tiêu thao tác.
- 20 nhãn không khớp reference không đồng nghĩa 20 nhãn chắc chắn sai; cần xem nguồn và reference vì matcher/reference chưa hoàn hảo.

## Điểm nghẽn

Coverage trả 195 đề xuất: 114 trùng nhãn theo chuẩn hóa chữ nên bị bỏ qua, 27 được nhận, 54 bị bác ở 27 bài. Việc lặp lại 114 nhãn cho thấy model chưa tuân thủ tốt yêu cầu chỉ tìm ý còn thiếu. Trong 54 đề xuất bị bác, 52 lỗi từ/thứ tự nguồn và 2 sai keys; không có lỗi parse toàn bộ coverage. Ví dụ model tạo `end-to-end training` trong khi nguồn viết `train our network in an end-to-end manner`. Một số đề xuất còn diễn giải/infer hoạt động thay vì chọn đoạn nguyên văn. Chưa xác nhận mọi đề xuất bị bác đều đáng giữ.

Annotation fallback: V 18/50, V-review1 24/50, V-recall 23/50. Coverage fallback 27/50; pipeline fallback V-recall là hợp của hai nhóm, 34/50. Bản thử thay một lượt repair bằng coverage nên không kỳ vọng fallback bằng V. Fallback không đo ngữ nghĩa.

## Chi phí và kiểm chứng

V: 74 calls mới +50 inherited, 361,183 input tokens mới, 20,700 output tokens mới; generation 38.59 phút.
V-recall: 100 calls mới +50 inherited, 282,168 input tokens mới, 18,120 output tokens mới; generation 33.01 phút.
Hai worker song song; tổng wall time 41.53 phút. Cùng trần 3x2048 nhưng chi phí thực khác nhau.

2,312 checks đạt: checksum/signature 150 records, nguồn/code/settings/draft đóng băng, seeds/calls/cost, first-review prompt hash và raw output khớp V ở 50/50 bài, replay toàn bộ pipeline 50 bài, accepted/rejected additions, phép tính điểm và delta trước/sau.

[Audit JSON](completion_audit.json) · [Script replay](audit_completion.py) · [Điểm gốc](exp_a_v_recall/results/experiment_summary.json)

Chưa chạy lại embedding tại local; kiểm tra số học dựa trên các quyết định match đã lưu. Reference AI, human review pending; pilot50 là development cohort dùng lại.

## Hướng tiếp theo

Tiếp tục giữ nhánh recall-first để phát triển, đồng thời giữ V gốc làm control. Bản tiếp theo nên sửa hai việc trong cùng lượt coverage: chọn cụm từ nguyên văn từ nguồn thay vì diễn giải; phân biệt mục tiêu/kỹ thuật với giả định hoặc kết quả đánh giá. Không nới validator hoặc threshold để nhận thêm nhãn. Xem thủ công nhóm không khớp và nhóm bị bác trước khi chọn thay đổi prompt; chưa tự động chạy lượt mới.
