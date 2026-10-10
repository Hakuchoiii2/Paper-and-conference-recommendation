# Pilot D — Kiểm tra session direction

[Generator D](../README.md) · [Runner D](../../../scripts/exp_d/README.md)

## 1. Prerequisites

Cần full silver A và C pilot complete. Đặt users_path = data/exp_c/samples/generated/users.jsonl; D đọc C history/search/exposure cùng directory và kiểm tra handoff manifest. Không cần C predictions.

Pilot vẫn đọc corpus canonical và facet A thật. Giảm quy mô hành vi/cases, không tạo catalog hoặc facet mock khác.

## 2. Tạo config pilot riêng

Copy `configs/exp_d.json` thành `data/exp_d/samples/config.json`, rồi sửa các trường dưới đây; giữ các trường còn lại. Tệp config pilot phải được tạo trước khi chạy lệnh ở mục 3.

| Trường | Giá trị pilot gợi ý | Ý nghĩa |
|---|---|---|
| sessions_per_user | 2 | Phiên/user |
| candidates_per_case | 10 | Ứng viên/phiên |
| observation_pairs | 4 | Giữ tín hiệu cặp đủ để thử estimator |
| output_dir | data/exp_d/samples/generated | Observable output riêng |
| truth_dir | data/exp_d/samples/ground_truth | Truth riêng |

Paths trong config tính từ gốc repository. Khi input/quy tắc đổi, dùng output phiên bản mới để giữ pilot cũ.

## 3. Sinh và chạy nhỏ

```powershell
python data/exp_d/build_exp_d.py --config data/exp_d/samples/config.json --dry-run
python data/exp_d/build_exp_d.py --config data/exp_d/samples/config.json
python data/exp_d/build_exp_d.py --config data/exp_d/samples/config.json --validate-only
python scripts/exp_d/run_exp_d.py --config data/exp_d/samples/config.json --output results/exp_d/pilot
```

Nếu output kết quả đã có, chọn --output mới hoặc --overwrite. B mặc định test; pilot ít queries có test nhỏ, không dùng điểm này làm kết luận khoa học.

## 4. Kiểm tra gì?

Bài quan sát cặp không nằm trong candidates; focus/directions/weights ở truth; query_mode có clear/ambiguous/none theo sessions sinh được. Ít users/sessions có thể không bao phủ mọi nhóm; partial không đủ cho runner chính.

Manifest phải ghi dataset_kind mock, contract 2.0, actual counts/hashes và trạng thái. Pilot kiểm tra luồng xử lý; chạy full config và giữ protocol để báo cáo thí nghiệm chính.
