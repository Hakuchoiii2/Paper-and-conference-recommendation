# Pilot E — Kiểm tra rolling và decay

[Generator E](../README.md) · [Runner E](../../../scripts/exp_e/README.md)

## 1. Prerequisites

Cần full silver A và C pilot complete. Đặt users_path = data/exp_c/samples/generated/users.jsonl; giữ manifest/tệp C được tham chiếu. E chỉ dùng danh tính rồi tạo stream riêng, không lấy C logs làm stream E.

Pilot vẫn đọc corpus canonical và facet A thật. Giảm quy mô hành vi/cases, không tạo catalog hoặc facet mock khác.

## 2. Tạo config pilot riêng

Copy `configs/exp_e.json` thành `data/exp_e/samples/config.json`, rồi sửa các trường dưới đây; giữ các trường còn lại. Tệp config pilot phải được tạo trước khi chạy lệnh ở mục 3.

| Trường | Giá trị pilot gợi ý | Ý nghĩa |
|---|---|---|
| events_per_user_per_period | 6 | Events/user/kỳ |
| output_dir | data/exp_e/samples/generated | Observable output riêng |
| truth_dir | data/exp_e/samples/ground_truth | Truth riêng |

Paths trong config tính từ gốc repository. Khi input/quy tắc đổi, dùng output phiên bản mới để giữ pilot cũ.

## 3. Sinh và chạy nhỏ

```powershell
python data/exp_e/build_exp_e.py --config data/exp_e/samples/config.json --dry-run
python data/exp_e/build_exp_e.py --config data/exp_e/samples/config.json
python data/exp_e/build_exp_e.py --config data/exp_e/samples/config.json --validate-only
python scripts/exp_e/run_exp_e.py --config data/exp_e/samples/config.json --output results/exp_e/pilot
```

Nếu output kết quả đã có, chọn --output mới hoặc --overwrite. B mặc định test; pilot ít queries có test nhỏ, không dùng điểm này làm kết luận khoa học.

## 4. Kiểm tra gì?

Giữ bốn boundaries và drift_coefficients [0,.5,1,1]. Các bản sao kỳ 2/3 trong history/truth phải giống nhau; runner kỳ 2 chỉ nhìn kỳ 1. Với 5 users, stable_fraction .5 cho 2 stable và 3 drift, không phải đúng 50/50.

Manifest phải ghi dataset_kind mock, contract 2.0, actual counts/hashes và trạng thái. Pilot kiểm tra luồng xử lý; chạy full config và giữ protocol để báo cáo thí nghiệm chính.
