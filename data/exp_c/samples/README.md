# Pilot C — Kiểm tra profile và thời gian

[Generator C](../README.md) · [Runner C](../../../scripts/exp_c/README.md)

## 1. Prerequisites

Cần full silver A hợp lệ. C pilot phải complete để D/E đọc; giữ trọn manifest/config và mọi tệp được tham chiếu.

Pilot vẫn đọc corpus canonical và facet A thật. Giảm quy mô hành vi/cases, không tạo catalog hoặc facet mock khác.

## 2. Tạo config pilot riêng

Copy `configs/exp_c.json` thành `data/exp_c/samples/config.json`, rồi sửa các trường dưới đây; giữ các trường còn lại. Tệp config pilot phải được tạo trước khi chạy lệnh ở mục 3.

| Trường | Giá trị pilot gợi ý | Ý nghĩa |
|---|---|---|
| num_users | 5 | Users chung cho pilot C/D/E |
| events_per_user | 20 | Events/user |
| history_events_per_user | 12 | 12 history, 8 holdout |
| output_dir | data/exp_c/samples/generated | Observable output riêng |
| truth_dir | data/exp_c/samples/ground_truth | Truth riêng |

Paths trong config tính từ gốc repository. Khi input/quy tắc đổi, dùng output phiên bản mới để giữ pilot cũ.

## 3. Sinh và chạy nhỏ

```powershell
python data/exp_c/build_exp_c.py --config data/exp_c/samples/config.json --dry-run
python data/exp_c/build_exp_c.py --config data/exp_c/samples/config.json
python data/exp_c/build_exp_c.py --config data/exp_c/samples/config.json --validate-only
python scripts/exp_c/run_exp_c.py --config data/exp_c/samples/config.json --output results/exp_c/pilot
```

Nếu output kết quả đã có, chọn --output mới hoặc --overwrite. B mặc định test; pilot ít queries có test nhỏ, không dùng điểm này làm kết luận khoa học.

## 4. Kiểm tra gì?

Profile ẩn không nằm trong generated; query < exposure < reaction; logs history trước cutoff; mỗi case có 8 candidates với labels holdout. Số query thực tế phụ thuộc xác suất search.

Manifest phải ghi dataset_kind mock, contract 2.0, actual counts/hashes và trạng thái. Pilot kiểm tra luồng xử lý; chạy full config và giữ protocol để báo cáo thí nghiệm chính.
