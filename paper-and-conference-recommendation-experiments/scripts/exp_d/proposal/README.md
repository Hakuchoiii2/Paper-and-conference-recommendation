# D — runner hoàn chỉnh: tám phương pháp và Oracle Intent

Chạy từ `paper-and-conference-recommendation-experiments`:

```powershell
python -B -m unittest discover -s scripts/exp_d/proposal -p "test_*.py" -v
python -B scripts/exp_d/proposal/run_benchmark.py
```

**Chỉ một runner chính.** Runner suy lại cả tám phương pháp từ dataset đã khóa; không cần chạy benchmark cũ, probe hay bước bổ sung metrics trước/sau. Không train, không sinh lại dataset và không đọc predictions cũ.

Mặc định dataset là `data/exp_d/proposal/datasets/observation_v1/`. Output tự tạo tên theo giờ Việt Nam, không ghi đè:

```powershell
python -B scripts/exp_d/proposal/run_benchmark.py --output data/exp_d/proposal/results/my_complete_run
```

## Tổ chức code

| File | Trách nhiệm |
|---|---|
| `run_benchmark.py` | Validate, tính profile/vector chung, chạy tất cả methods, đối chiếu gốc, evaluator/oracle, lưu kết quả |
| `data_io.py` | Chỉ nạp đầu vào công khai; lọc user/session/cutoff |
| `methods.py` | Bốn baseline gốc, QUERY-ONLY, VOTE, BAYES-H; gọi Ordinal-Intent |
| `ordinal_intent.py` | Likelihood ordinal; giữ hòa, marginalize strength cố định |
| `benchmark_config.json`, `ordinal_config.json` | Tham số cố định trước chạy; không sweep theo điểm |
| `common_ranking.py` | R_active chung: unique predicted focus → context/focus; chưa rõ → fallback similar |
| `evaluate.py` | Focus metrics; gọi nguyên evaluator/aggregate gốc; tạo Oracle bằng true directions và true weights |
| `reporting.py` | Tự xuất báo cáo giảng giải có hai sơ đồ, bảng methods/data/scorer/metrics/kết quả |
| `test_*.py` | Parity gốc, rò nhãn/thời gian, matching, likelihood, metrics, Oracle, chạy toàn luồng |

Code và README gốc ngoài proposal được giữ nguyên. `run_ordinal_benchmark.py` chỉ còn là entry point tương thích gọi runner chính; `probe_focus_mask.py` và `focus_masked.py` là công cụ lịch sử, không nằm trong đường chạy chính.

## Các dòng trong bảng

Public: `fixed_similar`, `profile_similar`, `query_only`, `direction_behavior`, `direction_search`, `vote`, `bayes_h`, `ordinal_intent`.

Evaluator thêm riêng **`oracle_intent`**, dùng cả directions và importance ẩn đúng README gốc. Oracle không tham gia chọn phương pháp thắng. Không đồng nhất Oracle này với probe cũ vẫn giữ C weights.

Tám methods cùng R_active và intent_scores gốc. Fixed_similar giữ trọng số đều; bảy methods khác dùng chung C profile. Raw directions giữ riêng với ranking_directions. Không coi fallback ranking là dự đoán hướng thành công.

## Kết quả tự xuất

| Tệp | Nội dung |
|---|---|
| `report.md` | Báo cáo dễ đọc: hai hình, scorer cụ thể, kết quả chính và metrics gốc |
| `predictions.jsonl` | Chỉ tám public methods; raw directions, policy/ranking mới và legacy_ranking phục vụ audit |
| `oracle_predictions.jsonl` | Predictions đặc quyền, tạo sau khi public predictions đã lưu |
| `summary.json/csv`, `groups.csv` | Trung bình theo thiết kế → nhóm công trình anchor; đầy đủ metrics tại focus và metrics context+focus |
| `legacy_summary.json/csv`, `legacy_groups.csv` | Nguyên evaluator/aggregate gốc: case-condition mean, F1 gộp confusion context+focus |
| `details.jsonl`, `metric_definitions.json` | Điểm từng case/condition và định nghĩa/đơn vị tổng hợp |
| `baseline_parity.json` | Cả bốn baseline khớp directions/weights/legacy ranking trên mọi phiên ở mọi condition |
| `paired_comparisons.csv`, `conclusions.json` | Bootstrap theo nhóm anchor; best public, Oracle loại khỏi selection |
| `validation_report.json`, `shared_profiles.json` | Kiểm dữ liệu và profile C khóa chung |
| `config.json`, `protocol.md`, `manifest.json` | Tham số trước chạy, kế hoạch, hashes, trạng thái |

Metrics: accuracy/coverage/joint tại focus, F1 focus; context+focus F1/accuracy/coverage gốc; nDCG/Recall/Precision/MRR@5/10; Compliance@5/10; importance MAE; Grade-2@1 và pair diagnostics.

Một grade 2/phiên → trần Compliance@5=.20, @10=.10. Recall/MRR gốc coi cả grade 1 là positive. Không đọc nDCG thành phần trăm đoán đúng.

Manifest phải có `status=complete`; lỗi ghi FAILED và không được gọi là kết quả hoàn tất. Output mới chỉ được nằm trong `data/exp_d/proposal/results/`.

## Lịch sử và giới hạn

Snapshot code trước khi gom runner: `../backup/20261021_complete_runner/`, có manifest hashes. Các output cũ giữ nguyên; hashes code trong output lịch sử đối chiếu với snapshot tương ứng, không mặc định với code hiện tại đã được phát triển tiếp.

Đây là pilot mô phỏng đã được xem trong các lượt trước, không phải test độc lập hay chứng minh novelty. Data: 19 thiết kế/12 anchors/114 phiên; 15 thiết kế candidates thật, 4 thiết kế có bổ sung một candidate tổng hợp. Observation và phản ứng đều mô phỏng. [Kế hoạch hiện hành](../../../data/exp_d/README_PROPOSAL.md).

Lượt hoàn chỉnh đã chạy: `benchmark_complete_20261021_01`, manifest complete, 6.156 lượt đánh giá gồm Oracle, 31 tests pass. [Báo cáo tự sinh](../../../data/exp_d/proposal/results/benchmark_complete_20261021_01/report.md).
