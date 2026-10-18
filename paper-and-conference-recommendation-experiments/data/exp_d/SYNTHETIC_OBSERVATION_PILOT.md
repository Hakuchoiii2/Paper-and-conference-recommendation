# D: pilot quan sát tổng hợp, giữ bài mốc và candidates thật

## Mục đích và phạm vi

Pilot kiểm tra: **khi có bằng chứng tổng hợp được kiểm soát, estimator hiện có có suy đúng focus/direction và thay đổi ranking candidates thật không?** Đây không phải kiểm chứng người dùng thật, không phải mở rộng corpus thật và không phải phương pháp đề xuất đã thắng baseline.

Thực hiện theo báo cáo lịch sử [exposure/interaction](docs/old/bao_cao_exposure_interaction_D.md): thử nhóm nhỏ trước, giữ nguồn thật, phản ứng có điều kiện theo intent và nhiễu; tách observation/candidates; không đưa hidden intent cho scorer; chạy mọi đối chứng trên cùng dữ liệu, kiểm tra seed/nhiễu và báo riêng focus. Kết luận mới nhất xem [evidence_report.md](docs/evidence_report.md).

| Thành phần | Xử lý trong pilot |
|---|---|
| Corpus/A/C và dataset D đã xuất | Chỉ đọc; validate A/C/D theo pipeline hiện hành trước khi chạy; kiểm tra hashes trước/sau |
| Sessions, anchors, candidates, nhãn và query | Chọn nguyên 30 phiên từ D cũ, không sửa nội dung/candidates/relevance/cutoff |
| Chọn phiên | Một phiên mỗi tổ hợp 5 focus × 2 hướng × 3 query modes, seed chọn cố định; ưu tiên anchor chưa dùng, không chọn theo metrics |
| Bài quan sát | Bản mô tả facet giả định với ID riêng `DOBS_...`, gắn `synthetic=true`; chỉ dành cho observation |
| Facet observation | Các facet ngoài focus sao chép từ anchor; focus cùng phía lấy từ anchor, khác phía lấy concept từ bài thật khác, không overlap focus anchor |
| Text observation | Template ghi rõ hypothetical/synthetic, không bịa kết quả nghiên cứu hay giả citation. Không dùng LLM/network |
| Annotation observation | Cấu trúc được dựng có kiểm soát, **không gọi là silver độc lập của A** |
| Matching | Giữ matching chính xác ngoài focus; thêm nguồn observation riêng thay vì nới validator |
| Phản ứng | Giữ utility .7/.05 theo intent + Gaussian noise, ánh xạ bằng thresholds nguồn. Không chọn hành động ngẫu nhiên độc lập với intent |
| Ranking | Giữ TF-IDF gốc từ bài thật, profile C và chính sách -1. Không để thêm observation làm thay IDF candidate |
| Các nhánh so sánh | 4 baseline công khai + oracle trong hai điều kiện: không observation và có observation tổng hợp |
| Ground truth | Chỉ simulator/evaluator được đọc; provenance có true focus/same-focus nằm riêng trong `ground_truth/` |
| Provenance | Overlay có manifest riêng; không sửa hashes/handoff A/C để giả rằng synthetic thuộc nguồn real |

Các cặp có ID riêng và các phản ứng lấy nhiễu riêng, nhưng nhiều mô tả facet có thể trùng. **Không diễn giải bốn cặp tổng hợp thành bốn bài thật độc lập hoặc bằng chứng nội dung độc lập.** Cặp được thiết kế khác ở focus là điều kiện simulator, chưa chứng minh tính thực tế của hành vi.

## Chạy trong CMD

Từ gốc project thực nghiệm:

```cmd
cd /d E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments
python -B data/exp_d/run_synthetic_observation_pilot.py
```

Mặc định đọc nguồn đã validate tại `data/exp_d/workspace`, chạy 30 phiên, 4 cặp/phiên, seeds 42/43/44 và noise 0.2/0.5. Output riêng ở `data/exp_d/evaluation/synthetic_observation_pilot_v1`. Nếu đã tồn tại, chọn tên mới; công cụ không ghi đè:

```cmd
python -B data/exp_d/run_synthetic_observation_pilot.py --source-root data/exp_d/workspace --output data/exp_d/evaluation/synthetic_observation_pilot_v2
```

Chạy một cấu hình trước để kiểm tra nhanh:

```cmd
python -B data/exp_d/run_synthetic_observation_pilot.py --seeds 42 --noise-levels 0.2 --output data/exp_d/evaluation/synthetic_observation_quick_v1
```

Nguồn workspace được dùng vì đã có A/C/D provenance hợp lệ. Không tự copy generator gốc đã sửa vào snapshot, không sửa manifest để vượt hash. Nếu dùng root khác, root đó phải tự vượt validator nguồn hiện hành. Script pilot tự đọc helper từ root nguồn đã chọn.

## Output và cách đọc

```text
evaluation/synthetic_observation_pilot_v1/
├── manifest.json                       Nguồn/hashes, seed, danh sách case và hashes toàn output
├── generated/
│   ├── sessions.jsonl                  30 phiên thật giữ nguyên
│   └── search_events.jsonl             Query nguồn giữ nguyên
├── ground_truth/
│   ├── session_intents.jsonl
│   └── intent_labels.jsonl             600 nhãn nguồn giữ nguyên
├── focus_sensitivity.json              Focus-only metrics qua các seed/noise
└── seed_42_noise_0.2/                   Các cấu hình khác có cùng cấu trúc
    ├── generated/
    │   ├── observation_papers.jsonl     240 mô tả tổng hợp, không phải corpus real
    │   ├── observation_facets.jsonl
    │   ├── exposures.jsonl             120 cặp, tách candidates
    │   └── interactions_train.jsonl    240 phản ứng trước cutoff
    ├── ground_truth/
    │   └── observation_provenance.jsonl
    └── results/
        ├── predictions.jsonl           30 phiên × 10 model/điều kiện = 300 dòng
        ├── details.jsonl
        ├── report.json
        ├── report.md
        ├── summary.csv
        ├── focus_metrics.json          Đọc focus riêng; không lẫn context được cung cấp
        └── manifest.json
```

So `direction_behavior__no_observations` với `direction_behavior__synthetic_observations` trên cùng 30 phiên. Đọc focus F1/accuracy/coverage trong `focus_metrics.json`, sau đó xem ranking/compliance ở `report.md`. Không dùng riêng coverage context+focus để kết luận behavior đã hoạt động.

Fixed/profile và oracle phải giống giữa hai điều kiện; script kiểm tra ranking fixed/profile không đổi. Script còn đối chiếu đầy đủ control công khai với hàm predict của baseline nguồn. Synthetic xuất hiện chỉ trong đầu vào estimator; không nằm trong candidate pool và không tham gia tính IDF hay profile dài hạn.

## Kiểm tra

```cmd
python -B -m unittest discover -s data/exp_d -p test_synthetic_observation_pilot.py
```

Tests dùng helper từ workspace đã có, không tải gì: kiểm tra deterministic, provenance synthetic, không có hidden fields trong logs, matching sai/nhãn sai/phản ứng sau cutoff bị từ chối và feedback phụ thuộc intent. Chạy pilot còn kiểm tra structural contract bằng `check_d` hiện hành trên tập facet gốc + overlay, so control với baseline nguồn và kiểm tra nguồn không đổi.

`check_d` PASS trên overlay **không có nghĩa** bài tổng hợp vượt loader corpus real hoặc annotation A. Bundle này dùng runner pilot riêng và protocol `d_synthetic_observation_overlay_v1`; runner canonical không tự nhận bundle như dataset D chuẩn.

## Giới hạn và bước tiếp

- 30 phiên là kiểm tra cơ chế; chưa phải tập đánh giá cuối hoặc bằng chứng tổng quát hóa.
- Intent dùng để sinh phản ứng là hợp lệ trong simulator, nhưng dữ liệu dễ theo thiết kế; điểm cao không chứng minh người thật phản ứng tương tự.
- Dùng concept donor thật không biến bài quan sát tổng hợp thành bài thật hoặc bảo đảm nội dung khoa học hợp lý.
- Khi nghiên cứu phương pháp mới, so với baseline trên cùng overlay và cùng noise/seed; không so trực tiếp điểm với baseline 1.500 phiên cũ để tuyên bố cải tiến thuật toán.
- Không tune tham số theo pilot rồi gọi chính pilot là test cuối. Đánh giá tiếp cần tách anchor giữa phần phát triển và đánh giá.
- Có thể cân nhắc LLM hoặc người review sau, nhưng chưa tích hợp. Không cần sửa C hoặc corpus để chạy pilot overlay này.
