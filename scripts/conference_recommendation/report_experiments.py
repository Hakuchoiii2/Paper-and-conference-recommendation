"""Render only verified v2 artifacts into the four experiment tables."""
import csv
import json
import os
from pathlib import Path

from .experiment_protocol import BACKENDS, METHODS, PROTOCOL, WEIGHT_PRESETS, digest
from .report_figures import render_sensitivity
from .report_discussion import (
    discussion_table1, discussion_table2, discussion_sensitivity, discussion_table4, limitations, appendix_macro,
    table4_rationale,
)

MISSING = "Chưa chạy"
LABELS = {"whole_text": "Whole-Text", "flat_5_facet": "Flat 5-Facet", "gated": "Gated 5-Facet"}


def config_text(config):
    if not config:
        return MISSING
    parts = [f"k={config['k']}"]
    for key in ("tau", "kappa", "preset"):
        if key in config:
            parts.append(f"{key}={config[key]}")
    if "weights" in config:
        parts.append("w=" + json.dumps(config["weights"], ensure_ascii=False, sort_keys=True))
    return "; ".join(parts)


def number(metrics, key, cv=False):
    if not metrics or key not in metrics:
        return MISSING
    scale = 100 if "hit@" in key else 1
    suffix = "%" if scale == 100 else ""
    value = f"{metrics[key] * scale:.2f}{suffix}" if scale == 100 else f"{metrics[key]:.4f}"
    if cv:
        if key + "_std" not in metrics:
            raise ValueError(f"Missing fold std for {key}")
        std = metrics[key + "_std"] * scale
        value += (f" ± {std:.2f}{suffix}" if scale == 100 else f" ± {std:.4f}")
    return value


def table(headers, rows):
    def clean(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "| " + " | ".join(["---"] * len(headers)) + " |",
                      *["| " + " | ".join(map(clean, row)) + " |" for row in rows]])


def read_artifacts(output):
    result = {}
    for backend in BACKENDS:
        tag = backend.replace("-", "_")
        artifacts = {}
        for stage in ("tuning", "test", "analysis", "benchmark"):
            path = output / f"{stage}_{tag}.json"
            artifacts[stage] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        tuning = artifacts["tuning"]
        if tuning:
            unsigned = {k: v for k, v in tuning.items() if k != "tuning_id"}
            if tuning.get("metadata", {}).get("protocol") != PROTOCOL or digest(unsigned) != tuning.get("tuning_id"):
                raise ValueError(f"Invalid tuning artifact for {backend}")
        for stage in ("test", "analysis", "benchmark"):
            artifact = artifacts[stage]
            if artifact and (not tuning or artifact.get("tuning_id") != tuning["tuning_id"] or artifact.get("metadata") != tuning["metadata"]):
                raise ValueError(f"Stale/mixed {stage} artifact for {backend}; regenerate it")
        result[backend] = artifacts
    return result


def write_report(output_dir, report_path, overwrite=False):
    output, target = Path(output_dir), Path(report_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} exists; use --overwrite")
    artifacts = read_artifacts(output)
    figures = render_sensitivity(artifacts, target.parent / "figures")
    sections = ["# Báo cáo thực nghiệm khuyến nghị hội nghị — giao thức v2",
                "Trạng thái: số liệu chỉ được điền từ artifact v2 đã kiểm tra nguồn gốc. `Chưa chạy` là ô chưa có kết quả; không dùng lại số cũ.",
                "## Giao thức chung",
                "Chọn cấu hình bằng CV phân tầng trên Train. TF-IDF học từ phần Train của từng fold, riêng cho từng trường; bỏ token ngoài từ vựng. Dense encoder cố định. Thiếu Problem → gate=0.5. Thiếu facet giải pháp → chuẩn hóa lại trọng số quan sát được.",
                "CV ghi mean ± sample std (ddof=1) giữa các fold. Điểm CV của cấu hình thắng cuộc là điểm dùng để lựa chọn, có thể lạc quan; Test là đánh giá sau đóng băng. Macro chỉ lấy các hội nghị có mẫu trong tập đánh giá. Không dùng Test để đổi cấu hình.",
                "Việc sửa pipeline không làm cho tập Test từng được xem trước đây trở thành một holdout mới. Khi viết bài cần mô tả đúng lịch sử sử dụng Test; nếu đã chọn thiết kế theo Test thì cần một holdout mới để xác nhận độc lập."]
    for backend, bundle in artifacts.items():
        tuning = bundle["tuning"]
        if not tuning:
            sections.append(f"- **{backend}:** chưa chạy tuning v2.")
            continue
        meta = tuning["metadata"]
        counts = ", ".join(f"{LABELS[m]}={len(tuning['methods'][m]['cv_all'])}" for m in METHODS)
        sections.append(f"- **{backend}:** Train={meta['n_train']}, Test={meta['n_test']}, ứng viên={len(meta['candidates'])}; "
                        f"{meta['n_splits']} folds, seed={meta['seed']}; số cấu hình: {counts}. "
                        f"Chọn: `{tuning['selection_rule']}`. Tuning ID: `{tuning['tuning_id']}`. "
                        f"Grid: `{json.dumps({k:v for k,v in tuning['search_space'].items() if k in ('k','tau','kappa')})}`.")
        sections.append(f"  Embedding checkpoint: `{meta.get('embedding_model') or 'TF-IDF, vocabulary fit trên reference từng fold'}`. "
                        f"Phiên bản thư viện: `{json.dumps(meta.get('versions', {}), sort_keys=True)}`.")
        if meta.get("rare_train_venues"):
            sections.append(f"  Lớp hiếm (<{meta['n_splits']} mẫu): `{json.dumps(meta['rare_train_venues'], sort_keys=True)}`. "
                            "Phân phối mẫu mỗi lớp giữa các fold lệch tối đa 1; lớp hiếm không thể xuất hiện ở mọi validation fold. "
                            "Mọi phương pháp dùng cùng fold; Macro CV chỉ lấy lớp có mẫu trong validation của fold đó.")
    exports = {}
    rows = []
    for backend, bundle in artifacts.items():
        tuning, test = bundle["tuning"], bundle["test"]
        expected = test.get("random_theoretical") if test else None
        rows.append([backend, "Random (kỳ vọng lý thuyết)", "Uniform shuffle; không tune", "Không áp dụng", "Không áp dụng",
                     *[number(expected, k) for k in ("hit@1", "hit@3", "hit@5", "mrr")]])
        for method in METHODS:
            for variant, label in (("default", "Mặc định"), ("best", "Best tuned")):
                record = tuning["methods"][method][variant] if tuning else None
                test_row = next((r for r in test["rows"] if r["method"] == method and r["variant"] == variant), None) if test else None
                metrics = test_row["metrics"] if test_row else None
                rows.append([backend, LABELS[method] + " — " + label, config_text(record["config"] if record else None),
                             number(record["cv"] if record else None, "hit@3", True), number(record["cv"] if record else None, "mrr", True),
                             *[number(metrics, k) for k in ("hit@1", "hit@3", "hit@5", "mrr")]])
    headers = ["Backend", "Method", "Cấu hình", "Train CV Hit@3", "Train CV MRR", "Test Hit@1", "Test Hit@3", "Test Hit@5", "Test MRR"]
    grid_description = (
        "## Không gian quét siêu tham số\n\n"
        "Grid cụ thể và số cấu hình của từng backend được đọc từ JSON tuning ở trên, "
        "không lấy hằng số từ mẫu báo cáo. Whole-Text tune k; Flat tune k và preset 5 chiều; "
        "Gated tune k, tau, kappa và preset 4 chiều. Tất cả tham số được chọn bằng Train CV. "
        "Danh sách chính xác từng preset/trọng số và mọi cấu hình đã đánh giá có trong CSV/JSON được dẫn ở cuối. "
        "Các dòng mặc định được đánh giá riêng; chúng không làm tăng số cấu hình grid."
    )
    sections += [grid_description, "## Bảng 1 — Best tuned, mặc định và baselines",
                 "> **Cấu hình:** cùng split, fold, catalog và encoder cho mọi phương pháp trong từng backend. Whole-Text tune k; Flat tune k và 10 preset 5 chiều; Gated tune k, tau, kappa và 10 preset 4 chiều. Không yêu cầu các phương pháp có cùng số tổ hợp; phải công bố ngân sách tìm kiếm. Random ghi kỳ vọng lý thuyết, không có CV std thực nghiệm.", table(headers, rows)]
    exports["table1"] = (headers, rows)
    sections += discussion_table1(artifacts)
    sections += ["## Bảng 2 — Preset trọng số và facet ablation",
                 "> **Cấu hình:** cố định k*, tau*, kappa* từ Train CV của từng backend. Mỗi backend có 10 dòng: 6 preset mô tả và 4 leave-one-out từ weights* (giữ tỷ lệ những trọng số còn lại). Delta so với Gated Best ở Bảng 1, đơn vị điểm phần trăm; âm nghĩa là giảm. Các phép đo Test này chỉ là phân tích đã định trước, không được chọn lại cấu hình."]
    for backend, bundle in artifacts.items():
        analysis, tuning, test = bundle["analysis"], bundle["tuning"], bundle["test"]
        rows = []
        names = list(WEIGHT_PRESETS)
        base = next((r["metrics"]["hit@3"] for r in test["rows"] if r["method"] == "gated" and r["variant"] == "best"), None) if test else None
        for i, name in enumerate(names):
            record = analysis["facet_ablation_table2"][i] if analysis else None
            cv = record.get("cv") if record else None
            metrics = record.get("test", {}).get("metrics") if record else None
            delta = f"{100 * (metrics['hit@3'] - base):+.2f}" if metrics and base is not None else MISSING
            weights = record.get("config", {}).get("weights") if record else None
            rows.append([name, json.dumps(weights, sort_keys=True) if weights else MISSING,
                         number(cv, "hit@3", True), number(metrics, "hit@1"), number(metrics, "hit@3"),
                         number(metrics, "hit@5"), number(metrics, "mrr"), delta])
        headers = ["Preset", "Weights thực dùng", "Train CV Hit@3", "Test Hit@1", "Test Hit@3", "Test Hit@5", "Test MRR", "Delta Hit@3 (pp)"]
        best = tuning["methods"]["gated"]["best"]["config"] if tuning else None
        sections += [f"### {backend}", f"Cấu hình cố định: {config_text(best)}.", table(headers, rows)]
        exports[f"table2_{backend}"] = (headers, rows)
        gate = analysis["problem_gate_ablation"] if analysis else None
        sections.append("**Kiểm tra riêng Problem:** tắt gate (gate=1), giữ nguyên weights* và k*. "
                        f"CV Hit@3: {number(gate['cv'] if gate else None, 'hit@3', True)}; "
                        f"Test Hit@3: {number(gate['test']['metrics'] if gate else None, 'hit@3')}. "
                        "Đây là phép kiểm tra thành phần gate, bổ sung cho 4 facet giải pháp; không suy ra tính không thể thay thế của mọi facet trước khi có dữ liệu.")
    sections += discussion_table2(artifacts)
    sections += ["## Bảng 3 — Độ nhạy một chiều trên Train CV",
                 "> **Cấu hình:** giữ weights* và hai siêu tham số còn lại ở cấu hình thắng cuộc, thay đổi một tham số. Chỉ dùng Train CV; không chọn lại từ Test. Luôn thêm điểm tốt nhất vào dải khảo sát nếu nằm ngoài dải mặc định. Điểm tốt nhất của grid chưa chắc là đỉnh toàn cục; không giả định đường cong hình chuông."]
    for backend, bundle in artifacts.items():
        analysis = bundle["analysis"]
        sections.append(f"### {backend}")
        sections.append("Cấu hình cố định: " + config_text(analysis["best_operating_point"] if analysis else None) + ".")
        rows = []
        if analysis:
            for parameter, records in analysis["sensitivity"].items():
                for record in records:
                    rows.append([parameter, record["value"], number(record["cv"], "hit@3", True), number(record["cv"], "mrr", True)])
        else:
            tau = ([.15, .20, .25, .30, .35, .40, .45, .50] if backend == "tfidf"
                   else [.35, .40, .45, .50, .55, .60, .65, .70])
            rows = [[parameter, value, MISSING, MISSING]
                    for parameter, values in {"k": [5, 10, 15, 20, 25, 30], "tau": tau,
                                              "kappa": [2., 5., 10., 15., 20., 30.]}.items()
                    for value in values]
        headers = ["Tham số thay đổi", "Giá trị", "Train CV Hit@3", "Train CV MRR"]
        sections.append(table(headers, rows))
        exports[f"table3_{backend}"] = (headers, rows)
    if figures:
        image_path = Path(os.path.relpath(figures["png"], target.parent)).as_posix()
        svg_path = Path(os.path.relpath(figures["svg"], target.parent)).as_posix()
        data_path = Path(os.path.relpath(figures["csv"], target.parent)).as_posix()
        sections += ["### Hình 3 — Biểu đồ đường bổ sung cho Bảng 3",
                     f"![Độ nhạy Hit@3 theo k, tau và kappa trên Train CV]({image_path})",
                     "**Chú thích:** mỗi hàng là một backend, mỗi cột là một siêu tham số. Đường nối là mean Hit@3 trên Train CV; "
                     "vùng tô là ±1 sample std giữa các fold (ddof=1), **không phải khoảng tin cậy**. "
                     "Ngôi sao đỏ đánh dấu giá trị đã chọn từ tuning; hai tham số còn lại và weights* giữ cố định theo backend. "
                     "Trục tung từng ô có thể khác nhau. Bảng 3 vẫn giữ nguyên để tra số Hit@3 và MRR.",
                     f"Tải [hình vector SVG]({svg_path}) hoặc [CSV dữ liệu vẽ]({data_path})."]
    sections += discussion_sensitivity(artifacts)
    sections += ["## Bảng 4 — Cross-LLM với cấu hình đóng băng",
                 "> **Cấu hình:** giữ nguyên Train Qwen-8B, encoder/vocabulary và cấu hình Gated Best của Bảng 1; chỉ thay facets Test. Mỗi backend có 5 LLM (15 dòng cho 3 backend). Thiếu file hoặc thiếu paper ID gây lỗi, không tự dùng số cũ hay âm thầm bỏ qua LLM."]
    sections += table4_rationale()
    rows = []
    for backend, bundle in artifacts.items():
        benchmark = bundle["benchmark"]
        source = benchmark["rows"] if benchmark else [{"extractor": name} for name in ("Qwen-8B", "Qwen-14B", "Qwen-4B", "Llama-8B", "Gemma-9B")]
        for row in source:
            rows.append([backend, row["extractor"], config_text(row.get("config")),
                         *[number(row.get("metrics"), k) for k in ("hit@1", "hit@3", "hit@5", "mrr", "macro_hit@3", "macro_mrr")]])
    headers = ["Backend", "LLM", "Frozen config", "Hit@1", "Hit@3", "Hit@5", "MRR", "Macro-Hit@3", "Macro-MRR"]
    sections += [table(headers, rows)]
    sections += discussion_table4(artifacts)
    sections += limitations(artifacts)
    sections += appendix_macro(artifacts, table, number)
    if figures:
        sections += ["## Phụ lục B — Code và dữ liệu tạo Hình 3",
                     "Hình được tạo tự động bằng **Python/Matplotlib**, từ trường `sensitivity` trong các file "
                     "`analysis_tfidf.json`, `analysis_specter.json`, `analysis_bge_small.json` đã lưu. "
                     "Mỗi điểm là mean CV Hit@3 của một cấu hình thực nghiệm; vùng tô lấy trực tiếp std giữa các fold. "
                     "Code nối các điểm đo, không tự đặt số liệu, không nội suy đường cong trơn và không chạy lại grid search.",
                     "Code vẽ: `scripts/conference_recommendation/report_figures.py` (hàm `render_sensitivity` và `_plot`). "
                     "Bộ tạo report `report_experiments.py` gọi code này, rồi chèn PNG vào Markdown. "
                     "CSV dữ liệu vẽ và JSON nguồn rút gọn được lưu trong thư mục `figures` cạnh report; mỗi điểm CSV có tuning ID để truy vết.",
                     "Để tạo lại report và hình từ kết quả đã có, chạy tại thư mục `paper-and-conference-recommendation-experiments`:\n\n"
                     "```powershell\n.\\.venv-qwen\\Scripts\\python.exe scripts\\conference_recommendation\\run_experiments.py --stage report --overwrite\n```"]
    sections += ["## Nguồn số liệu", f"Thư mục artifact: `{output.resolve()}`. JSON lưu cấu hình, điểm từng fold, split IDs, phiên bản thư viện, fingerprint dữ liệu, dự đoán từng bài và thống kê theo venue. Các CSV cùng tên bảng nằm trong thư mục `report_tables`. Không lấy số từ report cũ."]
    sections.append("**Toàn bộ grid được lưu thành CSV riêng**, không chép hàng nghìn dòng vào report. "
                    "Mỗi dòng có cấu hình, từng trọng số, CV mean/std, điểm từng fold, thứ hạng và dấu chọn best. "
                    "CSV dùng giá trị thô 0..1 để phân tích; có thể đính kèm như dữ liệu bổ sung/phụ lục điện tử.")
    for backend in BACKENDS:
        tag = backend.replace("-", "_")
        links = []
        for kind in ("all", "folds"):
            source = output / f"grid_search_{kind}_{tag}.csv"
            relative = Path(os.path.relpath(source, target.parent)).as_posix()
            links.append(f"[{source.name}]({relative})" if source.exists() else f"`{source.name}` — chưa chạy")
        sections.append(f"- **{backend}:** " + "; ".join(links))
    exports["table4"] = (headers, rows)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    csv_dir = output / "report_tables"
    csv_dir.mkdir(parents=True, exist_ok=True)
    for name, (headers, rows) in exports.items():
        with (csv_dir / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)
    print(f"Report: {target}", flush=True)
    return target
