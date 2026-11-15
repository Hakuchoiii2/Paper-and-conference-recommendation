# Pilot A — Kiểm tra extraction và resume

[Generator A](../README.md) · [Đánh giá A](../../../scripts/exp_a/README.md)

## 1. Pilot tại phần đang chạy

Từ gốc repository:

```powershell
python data/exp_a/build_exp_a.py --dry-run
python data/exp_a/build_exp_a.py --limit 2
python data/exp_a/build_exp_a.py --validate-only --allow-partial
```

Dry-run kiểm tra paper_range/output_dir hiện hành. Limit 2 chọn tối đa hai **bài mới còn thiếu trong khoảng**, không có nghĩa luôn chạy lại hai bài đầu.

Pilot này ghi vào output_dir của part đang chọn; kết quả tiếp tục được dùng khi chạy full part. Nó không tự ghi vào samples chỉ vì được gọi là pilot. Nếu phần đã xong, không có bài mới để chạy.

## 2. Pilot tách riêng khi thử policy/model khác

Tạo config mới từ data/exp_a/config.json; giữ corpus gốc, đặt khoảng nhỏ và output_dir riêng dưới data/exp_a/samples/. Chỉ định --config tới tệp đó rồi dry-run trước.

Đổi prompt/model/policy không trộn vào checkpoint của part đã có annotation. Không tạo paper/facet mock vào corpus chính. Pilot nhỏ cũng chưa tạo human gold.

## 3. Đọc output

Kiểm tra silver, evidence/source trong metadata, attempt_scores/validation_errors, fallback flags và missing_ids. Điểm 0–100 là rule score, chưa phải accuracy.

Manifest partial là bình thường khi chỉ chọn vài bài; B–E vẫn cần bộ A complete toàn corpus. Giữ pilot khác phiên bản riêng để audit, không gộp vào full silver.
