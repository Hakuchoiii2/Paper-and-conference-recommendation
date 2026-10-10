# Dữ liệu thực nghiệm

Đây là chỉ mục chuẩn bị đầu vào. README trong từng exp giải thích generator; README tương ứng trong `scripts/` giải thích scorer và đánh giá.

## Các phần dữ liệu

| Phần | Vai trò | Đọc tiếp |
|---|---|---|
| `raw/` | Bản tải nguồn, giấy phép, checksum | [Nguồn gốc](raw/README.md) |
| `processed/` | Corpus canonical: ID, title, abstract, metadata | [Corpus và rebuild](processed/README.md) |
| A | Qwen trích năm facet, metadata/evidence, gộp, chọn gold | [Generator A](exp_a/README.md) |
| B | Bài mốc × ứng viên, nhãn graded, split theo bài mốc | [Generator B](exp_b/README.md) |
| C | Users, latent profile, lịch sử/search/exposure, holdout | [Generator C](exp_c/README.md) |
| D | Phiên có hướng tương tự/khác biệt và tín hiệu quan sát | [Generator D](exp_d/README.md) |
| E | Chuỗi thời gian stable/drift và rolling holdout | [Generator E](exp_e/README.md) |

## Phụ thuộc khi giao cho các thành viên

1. Hoàn thành và gộp A thành silver + metadata + manifest toàn corpus.
2. B/C có thể tạo dữ liệu độc lập sau A. Generator loại bài fallback/còn validation errors khỏi pool khuyến nghị.
3. Tạo bộ C hoàn chỉnh một lần, rồi bàn giao cùng manifest và các tệp liên quan.
4. D dùng users và lịch sử/search/exposure C. E dùng danh sách users C rồi sinh chuỗi riêng.
5. Thành viên D/E chạy baseline riêng ngay khi có dữ liệu; không phải đợi kết quả scorer C.

Gold A là bước kiểm tra chất lượng extraction riêng. B–E hiện dùng ground truth mô phỏng, không cần thêm bộ nhãn relevance do người kiểm duyệt để chạy baseline.

## Quy mô cấu hình chính

| Exp | Mục tiêu generator | Lưu ý |
|---|---|---|
| A | 4.210 bài, 5 phần × 842; chọn 400 bài review | Form pending chưa phải gold |
| B | 300 bài mốc × 100 ứng viên | 30.000 cặp, không phải 30.000 bài |
| C | 300 users × 50 events | 30 lịch sử + 20 holdout/user |
| D | 300 users × 5 sessions × 20 ứng viên | Có thể thiếu quota nếu pool không đủ |
| E | 300 users × 4 kỳ × 15 events | 3 lần đánh giá rolling/user |

Đây là **quota trong cấu hình**, không phải xác nhận dataset đã được sinh đủ. Kiểm tra số lượng thực tế và trạng thái trong manifest/report. Generator không chèn ID hoặc nhãn giả để bù thiếu.

## Đọc tiếp

- [Cách chạy script thực nghiệm](../scripts/README.md) và [lệnh chuẩn bị/chạy nhanh](../docs/RUN_EXPERIMENTS.md).
- [Hợp đồng dữ liệu](../DATA_CONTRACT.md), [protocol A–E](../docs/EXPERIMENT_PROTOCOL.md).
- [Quản lý corpus, freeze và bàn giao](../docs/PROJECT_OPERATIONS.md).
- Pilot nhỏ: [A](exp_a/samples/README.md), [B](exp_b/samples/README.md), [C](exp_c/samples/README.md), [D](exp_d/samples/README.md), [E](exp_e/samples/README.md).

Bài báo là dữ liệu thật; facet A là silver chưa review; profile/intent/hành vi/nhãn B–E là dữ liệu mô phỏng. Cần giữ rõ ba mức này khi viết báo cáo.
