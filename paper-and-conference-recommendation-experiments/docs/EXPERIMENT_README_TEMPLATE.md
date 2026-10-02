# Thực nghiệm <ký hiệu> — <tên tiếng Việt>

Người phụ trách, trạng thái triển khai và phần quy ước cần Khải chốt.

## 1. Mục đích và câu hỏi thực nghiệm

Giải thích câu hỏi cần kiểm chứng, ví dụ sử dụng, quan hệ với A–E khác và giới hạn
dữ liệu thật/mô phỏng. Không mô tả kết quả mô hình chưa chạy.

## 2. Định dạng đầu vào

Ghi đường dẫn rõ ràng, trường bắt buộc, dữ liệu mô hình được phép đọc và liên kết
DATA_CONTRACT.md. Nêu điều kiện đầu vào còn thiếu; dùng chung canonical paper IDs.

## 3. Định dạng đầu ra

Bảng tên tệp và đơn vị bản ghi. Tách observable inputs, nhãn đánh giá, latent
truth và dữ liệu tương lai. Manifest ghi version/kind, seed, hashes và actual counts.

## 4. Định nghĩa trường dữ liệu

Ý nghĩa, kiểu, enum, missing values, khóa duy nhất và foreign keys. Giải thích các
điểm dễ nhầm, nguồn nhãn và mapping chưa duyệt; không tự đổi nhãn native.

## 5. Ví dụ đầu vào và đầu ra

Ví dụ JSON dùng ID trong corpus/bộ mẫu chung. Đánh dấu rõ nhãn minh họa, không coi
ví dụ schema là đáp án đã kiểm chứng. Giữ nguyên tên trường và nội dung bài nguồn.

## 6. Quy tắc tạo dữ liệu và hướng đánh giá

Nguồn, seed, sampling, positives/negatives, sizes, splits, quy tắc ngữ nghĩa và
giới hạn mô phỏng. Chỉ ghi lệnh generator đang chạy được. Nếu chưa triển khai thì
ghi rõ prerequisite và trạng thái; không bịa lệnh. Chỉ số đề xuất cần chốt trước
khi chạy, không trình bày như kết quả hiện có.

## 7. Quy tắc kiểm tra và điều kiện nghiệm thu

Structural/semantic checks, chống leakage, actual counts, review chất lượng và
tiêu chí nghiệm thu riêng. Phân biệt corpus validation hiện có với validator
thực nghiệm chưa xây; không silent-pass khi dữ liệu bắt buộc thiếu.
