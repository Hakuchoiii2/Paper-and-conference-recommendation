# Pilot B — Kiểm tra query/pool/labels

[Generator B](../README.md) · [Runner B](../../../scripts/exp_b/README.md)

## 1. Prerequisites

Cần full silver A hợp lệ; không cần C.

Pilot vẫn đọc corpus canonical và facet A thật. Giảm quy mô hành vi/cases, không tạo catalog hoặc facet mock khác.

## 2. Tạo config pilot riêng

Copy `configs/exp_b.json` thành `data/exp_b/samples/config.json`, rồi sửa các trường dưới đây; giữ các trường còn lại. Tệp config pilot phải được tạo trước khi chạy lệnh ở mục 3.

| Trường | Giá trị pilot gợi ý | Ý nghĩa |
|---|---|---|
| num_queries | 10 | Số bài mốc |
| candidates_per_query | 20 | Số ứng viên/query |
| output_dir | data/exp_b/samples/generated | Observable output riêng |
| truth_dir | data/exp_b/samples/ground_truth | Truth riêng |

Paths trong config tính từ gốc repository. Khi input/quy tắc đổi, dùng output phiên bản mới để giữ pilot cũ.

## 3. Sinh và chạy nhỏ

```powershell
python data/exp_b/build_exp_b.py --config data/exp_b/samples/config.json --dry-run
python data/exp_b/build_exp_b.py --config data/exp_b/samples/config.json
python data/exp_b/build_exp_b.py --config data/exp_b/samples/config.json --validate-only
python scripts/exp_b/run_exp_b.py --config data/exp_b/samples/config.json --output results/exp_b/pilot
```

Nếu output kết quả đã có, chọn --output mới hoặc --overwrite. B mặc định test; pilot ít queries có test nhỏ, không dùng điểm này làm kết luận khoa học.

## 4. Kiểm tra gì?

Query không chứa anchor, candidates không trùng, mọi cặp có relevance/provenance, split không trùng anchor. Thiếu pool vẫn ghi shortfall; không ép đủ quota bằng nhãn giả.

Manifest phải ghi dataset_kind mock, contract 2.0, actual counts/hashes và trạng thái. Pilot kiểm tra luồng xử lý; chạy full config và giữ protocol để báo cáo thí nghiệm chính.
