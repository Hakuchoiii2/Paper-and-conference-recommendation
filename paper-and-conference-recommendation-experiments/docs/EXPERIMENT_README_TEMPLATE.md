# Mẫu README theo từng tầng

[Tổng quan dự án](../README.md) · [Protocol hiện hành](EXPERIMENT_PROTOCOL.md)

## 1. Quy tắc phân tầng

| Vị trí | Nên có | Chi tiết đặt ở đâu? |
|---|---|---|
| README gốc | Mục tiêu, cấu trúc chính, chỉ mục A–E, phụ thuộc | Link tới data/scripts/docs |
| data/README | Chỉ mục nguồn/corpus/generator và thứ tự bàn giao | data/exp_<x>/README |
| scripts/README | Chỉ mục runner và tài liệu chung | scripts/exp_<x>/README |
| data/exp_<x>/README | Nguyên liệu → generator → dataset/ground truth | samples/README cho pilot |
| scripts/exp_<x>/README | Observable inputs → scorer → evaluator → điểm | BASELINE_GUIDE cho hợp đồng chung |

Mỗi README phải có đường quay lại chỉ mục và link sang bước tiếp theo. Càng sâu, ví dụ/công thức/lệnh cụ thể hơn. Không lặp toàn bộ hướng dẫn ở các trang chỉ mục.

## 2. Khung README generator

```text
# Dữ liệu <exp> — <tên>
Link: chỉ mục dữ liệu, runner, protocol

1. Câu hỏi và dataset generator cần tạo
2. Nguyên liệu đã có / prerequisites, config, đường dẫn
3. Từng bước sampling/simulation, seed và phiên bản rule
4. Đáp án sinh từ đâu, ví dụ tính nhãn
5. Observable vs ground_truth; split/cutoff
6. Bảng output: tên tệp, đơn vị record, quota/actual counts
7. Lệnh dry-run, generate, validate đang có
8. Shortfall/failure, provenance, bàn giao và link pilot
```

Ghi rõ bài thật, facet silver, labels/behaviors mock hoặc human gold. Generator sinh query/profile/intent/events là output, không tự mô tả như dữ liệu đã có sẵn.

A trích silver từ corpus thật, selector tạo form pending. B–E generator đã có theo contract 2.0. B/C dùng A; D dùng C users/logs; E dùng C users rồi sinh stream riêng.

Ví dụ chỉ minh họa, không giả danh benchmark đã chạy. Không tự thay ID/title/abstract để khớp labels hoặc chèn facet để đủ quota.

## 3. Khung README runner

```text
# Exp <exp> — <tên>
Link: chỉ mục scripts, generator, giao diện chung

1. Câu hỏi nghiên cứu, baseline/model hiện có
2. Scorer được nhìn những tệp/trường nào; truth bị giấu
3. Representation/profile/direction/time weighting hoạt động từng bước
4. Công thức score và ví dụ số dẫn tới thứ tự ranking
5. Các model/ablation so phần nào với phần nào
6. Evaluator lấy ground truth ở đâu, metric nói gì
7. Code chạy theo thứ tự nào, CLI hiện có, output
8. Cách đọc kết quả và giới hạn
9. Thành viên bổ sung phương pháp/model ở đâu; có cần train không
```

Phân biệt score prediction với relevance label. Không ghi encoder/reranker “đã có” khi mới là đề xuất. Nêu rõ mô hình nào có importance/direction, model nào MAE N/A và oracle đặc quyền.

B split theo anchor; C/D/E chỉ dùng prefix trước cutoff. Tên history/train không tự có nghĩa neural training. D/E không cần scorer C hoàn thành.

## 4. Khung README pilot

Ghi cách tạo config pilot từ config chính, **tên trường và giá trị cần giảm**, output/truth riêng, prerequisites, lệnh cụ thể và phần output phải kiểm tra.

D/E pilot trỏ users_path tới C pilot complete, giữ manifest và các logs được tham chiếu. A limit mặc định tiếp tục part hiện hành; muốn pilot độc lập phải chọn output/config riêng.

## 5. Tránh tài liệu lệch code

Trước khi đổi README, đối chiếu generator/scorer/evaluator, config và protocol. Sau khi tách, sửa links/anchors từ nơi khác trỏ tới mục đã chuyển.

Kiểm tra local links, JSON/Python snippets và tên CLI. Không dùng trạng thái/quota trong config để khẳng định dataset/model đã chạy thành công. Đo thực tế có ngày ghi nhận để trong VALIDATION_STATUS hoặc báo cáo kết quả.
