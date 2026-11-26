# Conference Recommendation Dataset

Chỉ dùng CSFCube; bản 5 là bộ đã review mapping để thực nghiệm. Có **1.090 bài matched / 163 hội nghị hoặc joint**; split theo năm raw giữ **30 hội nghị, 602 train + 186 test**. Train ≤ 2015, test 2016–2019; mỗi hội nghị có tổng ≥ 5 bài matched và ít nhất 3 train + 1 test.

Xem [report](Report_dataset.md), [schema](schema_conference.md) và [phương pháp review bản 5](5_mapping_reviewed/METHOD_REVIEW_V5.md). Nhãn đã đối chiếu nguồn kết hợp AI review, chưa phải gold do người chấm độc lập xác nhận.

## Bản chốt và dữ liệu dùng tiếp

**Chốt dùng `5_mapping_reviewed/` cho các giai đoạn tiếp theo.** Các bản 1–4 giữ để đối chiếu lịch sử. Mapping đầy đủ nằm ở `5_mapping_reviewed/output/`; khi chạy thực nghiệm, dùng trực tiếp split đã chia sẵn trong **`5_mapping_reviewed/splits/temporal_2015_2016_2019/`**, không lấy toàn bộ matched để tự chia lại.

| Tệp trong thư mục split | Sử dụng |
|---|---|
| [train.jsonl](5_mapping_reviewed/splits/temporal_2015_2016_2019/train.jsonl) | 602 bài; dùng title/abstract tạo embedding và xây profile hội nghị |
| [test.jsonl](5_mapping_reviewed/splits/temporal_2015_2016_2019/test.jsonl) | 186 bài; dùng title/abstract làm truy vấn, conference_id làm nhãn đúng để đánh giá |
| [label_map.json](5_mapping_reviewed/splits/temporal_2015_2016_2019/label_map.json) | Ánh xạ label_index 0–29 sang ID/tên hội nghị, dùng chung cho train/test |
| [conference_catalog.jsonl](5_mapping_reviewed/splits/temporal_2015_2016_2019/conference_catalog.jsonl) | Danh mục 30 hội nghị được xếp hạng; không dùng catalog 163 hội nghị ở output/ cho split này |

Hai tệp train/test đã có sẵn văn bản và nhãn, không cần nối lại corpus. Không đưa trường nhãn vào văn bản đầu vào; chỉ dùng train xây profile/chọn medoid, giữ test cho đánh giá cuối. Chưa có dev; nếu cần chọn tham số thì tách kiểm định nội bộ từ train. Cấu hình, thống kê từng hội nghị và hash kiểm tra nằm cùng thư mục split.

## Cây thư mục

Cây tổng quan dưới đây chỉ mở tên tệp ở bản 5; các thư mục lưu hồ sơ cũ được thu gọn.

```text
conference_recommendation_dataset/
├── 1_raw_mapping/
├── 2_mapping_enriched/
├── 3_mapping_reviewed/
├── 4_catalog_mapping/
└── 5_mapping_reviewed/
    ├── README.md
    ├── METHOD_REVIEW_V5.md
    ├── venue_mapping.csv
    ├── review_mapping.py
    ├── audit_mapping.py
    ├── preprocess_cube.py
    ├── split_temporal.py
    ├── output/
    │   ├── paper_conference_links.jsonl
    │   ├── conference_catalog.jsonl
    │   ├── conference_papers.jsonl
    │   ├── conference_statistics.csv
    │   ├── comparison.csv
    │   ├── raw_inventory.json
    │   ├── manifest.json
    │   └── report.md
    ├── review/
    │   ├── adjudications.json
    │   ├── alias_review.csv
    │   ├── coverage.json
    │   ├── paper_review.csv
    │   ├── paper_evidence.jsonl
    │   ├── paper_review_overrides.csv
    │   ├── source_cache.jsonl
    │   ├── unresolved_after_review.csv
    │   ├── temporal_split_feasibility.csv
    │   ├── pending_review.csv
    │   ├── paper_sample_review.csv
    │   ├── catalog_manifest.json
    │   ├── venue_directory.jsonl
    │   ├── venue_sources.jsonl
    │   ├── report.md
    │   ├── inherited/
    │   ├── inherited_version4/
    │   └── round1_sample_review/
    └── splits/
        └── temporal_2015_2016_2019/
            ├── train.jsonl
            ├── test.jsonl
            ├── label_map.json
            ├── conference_catalog.jsonl
            ├── conference_split_statistics.csv
            ├── excluded_from_split.csv
            ├── split_config.json
            ├── manifest.json
            └── README.md
```

`output/` giữ mapping toàn bộ corpus; `review/` giữ chứng cứ và quyết định; `splits/` chứa dữ liệu dùng cho mô hình. Chỉ dùng train để xây profile hội nghị, test để đánh giá. `paper_sample_review.csv` và `pending_review.csv` là tệp tương thích; phạm vi review cuối xem `coverage.json` và `paper_review.csv`.
