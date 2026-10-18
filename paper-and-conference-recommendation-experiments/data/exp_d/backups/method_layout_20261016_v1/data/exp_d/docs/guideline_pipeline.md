# Tái lập pipeline D từ đầu: workspace mới, code hiện tại, baseline và xuất kết quả

Cập nhật: 2026-10-16. Các lệnh dùng **CMD trong IDE**, không dùng PowerShell. Gốc project thực nghiệm là:

```text
E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments
```

**Đã kiểm chứng end-to-end:** lượt `pipeline_check_20261016` tạo workspace mới từ code hiện tại, sinh/validate D, chạy đủ baseline 1.500 phiên và xuất kết quả; nhánh synthetic chạy đủ 6 cấu hình và xuất riêng. Kết thúc `PIPELINE COMPLETE`; nguồn đã snapshot không đổi. Bản xuất ở `data/exp_d/results/pipeline_check_20261016/` và `data/exp_d/results/pipeline_check_20261016_synthetic/`.

## 1. Hiểu đúng workspace và code mới

Workspace cũ là snapshot, không tự nhận thay đổi từ file gốc. Tuy nhiên **không cần xóa workspace cũ để làm lại**. Pipeline mới tạo một workspace có tên riêng cho mỗi lượt; giữ lượt cũ để đối chiếu, tránh mất kết quả.

Workspace được dùng vì provenance kiểm tra bytes: corpus và `scripts/build_corpus.py` ở checkout có thể bị CRLF thay cho LF. Công cụ chuẩn bị chỉ chuẩn hóa hai bản sao nếu khớp hash đã ghi, không sửa nguồn chung hoặc sửa hash để vượt kiểm tra.

Ngoài LF còn có vấn đề khác: generator D hiện tại đã đổi so với dataset cũ. Vì thế **copy code mới rồi chạy baseline trên manifest D cũ là sai quy trình**. Phải sinh lại D để manifest mới ghi nhận đúng code/data, validate rồi mới scoring.

| Bước | File thực thi | Chạy ở đâu? |
|---|---|---|
| Tạo snapshot từ code hiện tại | `data/exp_d/prepare_workspace.py --mode current` | Gốc project hiện tại |
| Sinh D theo generator mới | `data/exp_d/build_exp_d.py` | Bên trong workspace mới |
| Validate/dry-run/scoring | Generator và `scripts/exp_d/run_exp_d.py` | Bên trong workspace mới |
| Xuất kết quả | `data/exp_d/export_results.py` | Gốc project hiện tại |
| Pilot synthetic nếu chọn | `data/exp_d/run_synthetic_observation_pilot.py --source-root ...` | Gốc project hiện tại, chỉ đọc workspace mới |

`build_exp_d.py` vẫn chỉ tạo observation từ bài thật khi có cặp hợp lệ. Pipeline canonical có thể tiếp tục có 0 exposures/interactions. **Observation tổng hợp chỉ xuất hiện ở nhánh pilot riêng**, không được trộn vào corpus thật/A silver.

## 2. Cách khuyến nghị: một lệnh tự chạy toàn bộ

Chuyển về gốc project:

```cmd
cd /d E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments
```

Chạy baseline trên dataset D sinh từ code hiện tại, sau đó tự xuất kết quả về D:

```cmd
python -B data/exp_d/run_baseline_pipeline.py --name baseline_20261016_v1
```

Nếu muốn chạy **cả baseline canonical và pilot synthetic** theo thiết kế đã chọn, dùng lệnh này thay lệnh trên:

```cmd
python -B data/exp_d/run_baseline_pipeline.py --name baseline_20261016_v1 --with-synthetic
```

Chọn một trong hai lệnh, không chạy cả hai cùng tên. Nếu tên đã tồn tại, đổi thành `baseline_20261016_v2`. Có thể bỏ `--name` để công cụ tự đặt tên theo giờ Việt Nam.

Script tự làm tuần tự và dừng ngay khi một bước lỗi:

1. Tạo `data/exp_d/workspace_baseline_20261016_v1/` với code D hiện tại và A/C/corpus hợp lệ.
2. Sinh lại D **trong workspace mới**, tạo manifest/provenance tương ứng. Chỉ ghi đè bản D vừa sao chép trong workspace mới, không đụng workspace cũ hoặc dataset nguồn.
3. Validate D và dry-run runner.
4. Chạy bốn baseline công khai + oracle, chấm @5/10.
5. Kiểm tra hash output rồi tự copy bộ kết quả về `data/exp_d/results/baseline_20261016_v1/`.
6. Nếu có `--with-synthetic`, chạy 30 phiên pilot trên dataset mới với 3 seed × 2 noise; sau đó tự copy toàn bộ bundle sang `data/exp_d/results/baseline_20261016_v1_synthetic/`.
7. Kiểm tra input/code nguồn đã snapshot không bị thay đổi và ghi `pipeline_receipt.json`. Kết thúc bằng `PIPELINE COMPLETE`.

**Không cần chạy riêng `prepare_workspace.py`, generator hoặc exporter nếu đã dùng lệnh pipeline.** Không cần chạy scorer C, extraction A, tải model hoặc tải dataset.

## 3. Kết quả cuối cùng ở đâu?

```text
data/exp_d/
├── build_exp_d.py                       Generator gốc hiện tại
├── prepare_workspace.py                 Chuẩn bị snapshot
├── run_baseline_pipeline.py             Điều phối toàn bộ lượt chạy
├── export_results.py                    Kiểm tra hash và copy kết quả
├── run_synthetic_observation_pilot.py    Pilot riêng nếu chọn
├── workspace/                          Snapshot cũ, giữ nguyên
├── workspace_baseline_20261016_v1/      Snapshot/lượt mới
│   ├── data/exp_d/generated/            Dataset D mới và manifest
│   ├── data/exp_d/ground_truth/         Đáp án tương ứng
│   └── results/exp_d/baseline_20261016_v1/  Kết quả chạy gốc
├── evaluation/baseline_20261016_v1_synthetic/  Pilot gốc nếu chọn
└── results/                            Kết quả được tự xuất để xem/bàn giao
    ├── baseline_20261016_v1/
    │   ├── report.md                   Mở trước: bảng metrics
    │   ├── summary.csv                 Bảng cho Excel
    │   ├── report.json                 Metrics dạng JSON
    │   ├── predictions.jsonl           Prediction từng case/model
    │   ├── details.jsonl               Đánh giá từng case/model
    │   ├── manifest.json               Giữ nguyên bytes từ lượt chạy
    │   ├── export_receipt.json         Nguồn copy và các hash đã kiểm tra
    │   └── pipeline_receipt.json       Vị trí snapshot và kết quả hai nhánh
    └── baseline_20261016_v1_synthetic/  Nếu chạy --with-synthetic
        ├── manifest.json
        ├── export_receipt.json
        ├── focus_sensitivity.json
        ├── generated/
        ├── ground_truth/
        └── seed_42_noise_0.2/results/report.md  Và các seed/noise khác
```

Từ gốc project, mở thư mục kết quả:

```cmd
start "" "data\exp_d\results\baseline_20261016_v1"
```

Đọc baseline: `report.md` cho direction/ranking/compliance, `manifest.json` cho tham số/hashes, `export_receipt.json` cho xuất kết quả. Bộ canonical đủ quota có 1.500 phiên × 5 phương pháp = 7.500 predictions.

Đọc pilot: `focus_sensitivity.json` và từng `seed_*/results/focus_metrics.json` để xem focus riêng; `report.md` để xem ranking. Các con số trong báo cáo pilot ngày 15/10 dùng dataset cũ làm nguồn; lượt pipeline mới sinh D mới nên có thể có kết quả và độ phủ anchor khác. Không lấy điểm giữa hai dataset để quy thành cải thiện phương pháp.

Export là **copy**, không di chuyển/xóa. Manifest gốc giữ nguyên: input paths/hashes vẫn mô tả workspace đã chạy. `export_receipt.json` ghi nơi copy, không giả rằng scoring diễn ra ở thư mục kết quả mới.

## 4. Nếu muốn chạy từng bước thủ công từ khi chưa có workspace

Ví dụ dùng tên riêng `workspace_manual_v1`; chọn tên chưa tồn tại.

### Bước A — tạo workspace, đứng ở gốc project

```cmd
cd /d E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments
python -B data/exp_d/prepare_workspace.py --name workspace_manual_v1 --mode current
```

Lúc này snapshot mới có code D mới nhưng còn bản dataset D cũ vừa copy. **Chưa chạy scoring hoặc coi manifest D cũ là hợp lệ với code mới.**

### Bước B — sinh lại và validate D, đứng trong workspace mới

```cmd
cd /d E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments\data\exp_d\workspace_manual_v1
python -B data/exp_d/build_exp_d.py
python -B data/exp_d/build_exp_d.py --validate-only
python -B scripts/exp_d/run_exp_d.py --config configs/exp_d.json --output results/exp_d/manual_v1 --ks 5 10 --dry-run
```

Generator nạp/kiểm tra A/C hợp lệ trước khi tạo D. Cần các lệnh exit 0 và dry-run báo đủ cases. Giữ `/` trong `--config configs/exp_d.json`; dùng `configs\exp_d.json` có thể gây `Missing or extra input hashes` do so key đường dẫn trong validator.

### Bước C — chạy baseline, vẫn đứng trong workspace mới

```cmd
python -B scripts/exp_d/run_exp_d.py --config configs/exp_d.json --output results/exp_d/manual_v1 --ks 5 10
```

Chờ `PASS D`. Đầu ra lúc này nằm trong `workspace_manual_v1/results/exp_d/manual_v1`.

### Bước D — xuất về exp_d/results, quay về gốc project

```cmd
cd /d E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments
python -B data/exp_d/export_results.py --source data/exp_d/workspace_manual_v1/results/exp_d/manual_v1 --name manual_v1
```

Kết quả xem/bàn giao ở `data/exp_d/results/manual_v1/`. Nếu lần sau chạy runner trực tiếp, chạy exporter lại với source/name của lượt đó; **runner dùng chung không bị sửa để tự copy**. Tính tự động nằm ở `run_baseline_pipeline.py`.

### Bước E — pilot synthetic tùy chọn, vẫn ở gốc project

```cmd
python -B data/exp_d/run_synthetic_observation_pilot.py --source-root data/exp_d/workspace_manual_v1 --output data/exp_d/evaluation/manual_v1_synthetic
python -B data/exp_d/export_results.py --source data/exp_d/evaluation/manual_v1_synthetic --name manual_v1_synthetic
```

Pilot có validator riêng cho overlay, tái sử dụng checker matching/time hiện hành và baseline chung. Không cần sửa C/corpus hoặc bỏ hash gates.

## 5. Làm sạch không gian thế nào?

- Không bắt buộc xóa workspace cũ. Mỗi lượt có workspace/result tên riêng, nên không lẫn code mới/cũ.
- Chỉ cân nhắc xóa thủ công khi đã kiểm tra kết quả xuất, biết rõ snapshot nào không cần tái lập nữa. Quy trình này không tự xóa bất kỳ workspace hoặc output nào.
- Snapshot, evaluation và kết quả xuất là artifact cục bộ, được Git ignore; không đưa hàng nghìn file snapshot lên Git. Source mới cần theo dõi là các script pipeline/export và tests.
- `prepare_workspace.py --mode baseline` dành cho tái lập dataset cũ: nếu D generator hiện tại khác hash, công cụ chỉ dùng bản từ Git HEAD khi bytes khớp chính xác hash cũ. Đây không phải chế độ áp dụng code mới. Với nhu cầu hiện tại, dùng `--mode current` và sinh lại D.

## 6. Khi gặp lỗi

| Lỗi | Xử lý |
|---|---|
| Workspace/output tồn tại | Chọn `--name` mới, không xóa hoặc ghi đè để chạy tiếp |
| Manifest bytes không tái lập được | Đọc đúng file được báo; ngoài generator D ở chế độ current, không tự bỏ kiểm tra hoặc sửa hash |
| Generator hashes changed | Có thể đã chép code vào snapshot sau khi sinh data; tạo lượt mới và sinh lại D |
| Missing or extra input hashes | Kiểm tra `--config` dùng dấu `/` |
| Export checksum mismatch | Không bàn giao bản đó; kiểm tra source result có bị sửa/dở dang không |
| Pipeline fail giữa chừng | Lệnh dừng, giữ artifact để chẩn đoán. Không coi thiếu `PIPELINE COMPLETE` là chạy thành công; dùng tên mới sau khi xử lý nguyên nhân |
| Baseline canonical vẫn 0 exposures | Đúng giới hạn nguồn thật hiện tại; dùng nhánh synthetic riêng nếu cần thử cơ chế behavior |

Tests cho exporter:

```cmd
python -B -m unittest discover -s data/exp_d -p test_export_results.py
```

Tham khảo: [thiết kế pilot synthetic](../SYNTHETIC_OBSERVATION_PILOT.md), [overview](overview.md), [changed.md](old/changed.md).
