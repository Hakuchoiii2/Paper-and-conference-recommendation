"""Render verified v2 & IEEE artifacts into Markdown, CSV and LaTeX tables."""
import csv
import json
import os
from pathlib import Path

from .experiment_protocol import (
    AGGREGATIONS,
    BACKENDS,
    EXP_A_RAW_METRICS,
    METHODS,
    PROTOCOL,
    WEIGHT_PRESETS,
    digest,
)
from .report_figures import render_sensitivity
from .report_discussion import (
    appendix_macro,
    discussion_sensitivity,
    discussion_table1,
    discussion_table2,
    discussion_table4,
    limitations,
    table4_rationale,
)

MISSING = "Chưa chạy"
LABELS = {"whole_text": "Whole-Text", "flat_5_facet": "Flat 5-Facet", "gated": "Gated 5-Facet"}
IEEE_METHOD_LABELS = {
    "fulltext": "Method 1: Full-text",
    "equal_weight_facet": "Method 2: Equal-weight Facet (0.2 x 5)",
    "weighted_facet_a": "Method 3a: Weighted Facet — Exp B Weighted A (0.4/0.2/0.2/0.1/0.1)",
    "weighted_facet_b": "Method 3b: Weighted Facet — Exp B Weighted B (0.3/0.25/0.25/0.1/0.1)",
    "weighted_facet_cv": "Method 3c: Weighted Facet — Venue CV Best (w_V*)",
}
AGG_LABELS = {
    "sum_knn": "Sum-kNN",
    "temp_softmax": "Temp-Softmax",
    "prior_norm": "Prior-Norm",
    "per_venue_top_m": "Per-Venue Top-m",
}


def config_text(config):
    if not config:
        return MISSING
    parts = []
    if "aggregation" in config:
        parts.append(f"agg={config['aggregation']}")
    if "k" in config:
        parts.append(f"k={config['k']}")
    for key in ("m", "agg_tau", "alpha", "tau", "kappa", "preset", "missing_policy"):
        if key in config:
            parts.append(f"{key}={config[key]}")
    if "weights" in config:
        parts.append("w=" + json.dumps(config["weights"], ensure_ascii=False, sort_keys=True))
    return "; ".join(parts)


def number(metrics, key, cv=False):
    if not metrics or key not in metrics:
        return MISSING
    scale = 100 if ("hit@" in key or "error_rate" in key) else 1
    suffix = "%" if scale == 100 else ""
    value = f"{metrics[key] * scale:.2f}{suffix}" if scale == 100 else f"{metrics[key]:.4f}"
    if cv:
        if key + "_std" not in metrics:
            raise ValueError(f"Missing fold std for {key}")
        std = metrics[key + "_std"] * scale
        value += f" ± {std:.2f}{suffix}" if scale == 100 else f" ± {std:.4f}"
    return value


def table(headers, rows):
    def clean(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
            *["| " + " | ".join(map(clean, row)) + " |" for row in rows],
        ]
    )


def latex_table(headers, rows, caption="", label=""):
    def esc(val):
        s = str(val)
        for ch, rep in [("\\", "\\textbackslash{}"), ("%", "\\%"), ("_", "\\_"), ("&", "\\&"), ("#", "\\#")]:
            s = s.replace(ch, rep)
        return s.replace("±", "$\\pm$").replace("†", "$^{\\dagger}$")

    col_spec = "l" + "r" * (len(headers) - 1)
    lines = [
        "\\begin{table*}[t]",
        "\\centering",
        f"\\caption{{{esc(caption)}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\toprule",
        " & ".join(esc(h) for h in headers) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(esc(c) for c in row) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table*}"]
    return "\n".join(lines) + "\n"


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
            if artifact and (
                not tuning
                or artifact.get("tuning_id") != tuning["tuning_id"]
                or artifact.get("metadata") != tuning["metadata"]
            ):
                raise ValueError(f"Stale/mixed {stage} artifact for {backend}; regenerate it")
        result[backend] = artifacts
    return result


def _build_ieee_tables(artifacts):
    """Build the 4 IEEE-standard publication tables from verified artifacts."""
    primary_backend = "bert" if artifacts.get("bert", {}).get("test") else next(
        (b for b, a in artifacts.items() if a.get("test")), "bert"
    )
    bundle = artifacts.get(primary_backend, {})
    test_art = bundle.get("test")
    analysis_art = bundle.get("analysis")
    bench_art = bundle.get("benchmark")

    # IEEE Table 1: Main Results (RQ2)
    t1_headers = [
        "Method",
        "Aggregation",
        "Train CV Hit@3",
        "Test Hit@1",
        "Test Hit@3",
        "Test Hit@5",
        "Test MRR",
        "Test Macro-Hit@3 (95% CI)",
        "Tail Hit@3 (6v)",
        "Disc Hit@1",
    ]
    t1_rows = []
    if test_art:
        rnd = test_art.get("random_theoretical", {})
        t1_rows.append(
            [
                "Random Baseline (30 venues)",
                "—",
                "—",
                number(rnd, "hit@1"),
                number(rnd, "hit@3"),
                number(rnd, "hit@5"),
                number(rnd, "mrr"),
                "—",
                "—",
                "—",
            ]
        )
        for row in test_art.get("ieee_rows", []):
            m = row["metrics"]
            sig = row.get("significance_vs_fulltext", {})
            h3_str = number(m, "hit@3")
            if sig.get("mcnemar_hit@3", {}).get("significant_005"):
                h3_str += "†"
            mrr_str = number(m, "mrr")
            if sig.get("permutation_mrr", {}).get("significant_005"):
                mrr_str += "†"
            ci = row.get("bootstrap_ci", {}).get("macro_hit@3", {})
            if ci:
                mh3_str = f"{m['macro_hit@3']*100:.2f}% [{ci['ci_low']*100:.1f}, {ci['ci_high']*100:.1f}]"
            else:
                mh3_str = number(m, "macro_hit@3")
            t1_rows.append(
                [
                    IEEE_METHOD_LABELS.get(row["ieee_method"], row["ieee_method"]),
                    AGG_LABELS.get(row["aggregation"], row["aggregation"]),
                    number(row.get("cv"), "hit@3", True),
                    number(m, "hit@1"),
                    h3_str,
                    number(m, "hit@5"),
                    mrr_str,
                    mh3_str,
                    number(m, "tail_hit@3"),
                    number(m, "discipline_hit@1"),
                ]
            )

    # IEEE Table 2: Leave-One-Out 5-Facet Ablation & Temporal Drift + Exp C3 Zero-Imputation
    t2_headers = [
        "Variant",
        "Train CV (<=2015) Hit@3",
        "Train CV Delta Hit@3 (pp)",
        "Test (2016-2019) Hit@3",
        "Test Delta Hit@3 (pp)",
        "Test MRR",
        "Test Delta MRR",
        "Cross-Disc Error (%)",
    ]
    t2_rows = []
    if analysis_art:
        for row in analysis_art.get("ieee_ablation_temporal_drift", []):
            if "test" not in row:
                t2_rows.append([row.get("label", row["name"]), MISSING, MISSING, MISSING, MISSING, MISSING, MISSING, MISSING])
                continue
            tm = row["test"]["metrics"]
            t2_rows.append(
                [
                    row.get("label", row["name"]),
                    number(row.get("cv"), "hit@3", True),
                    f"{row['delta_cv_hit@3']*100:+.2f}",
                    number(tm, "hit@3"),
                    f"{row['delta_test_hit@3']*100:+.2f}",
                    number(tm, "mrr"),
                    f"{row['delta_test_mrr']:+.4f}",
                    number(tm, "cross_discipline_error_rate"),
                ]
            )

    # IEEE Table 3: Cross-LLM Substitution (5 Raw LLMs) + Spearman / Kendall Correlations
    t3_headers = [
        "Facet Scorer",
        "Raw LLM",
        "Exp A Micro/Macro-F1",
        "Key Facets F1 (P/T/M)",
        "Test Cov (%)",
        "Storage (KB/p)",
        "Hit@1",
        "Hit@3",
        "Hit@5",
        "MRR",
        "Macro-Hit@3",
        "W/T/L vs Qwen-8B",
    ]
    t3_rows = []
    if bench_art:
        for m_key in ("equal_weight_facet", "weighted_facet_a", "weighted_facet_cv"):
            for r in bench_art.get("ieee_benchmark", {}).get(m_key, []):
                ext = r["extractor"]
                ea = EXP_A_RAW_METRICS.get(ext, {})
                ea_str = f"{ea['micro_f1']*100:.2f} / {ea['macro_f1']*100:.2f}" if ea else "—"
                kf_str = (
                    f"{ea['problem_f1']*100:.1f} / {ea['task_f1']*100:.1f} / {ea['method_f1']*100:.1f}"
                    if ea else "—"
                )
                wtl = r.get("vs_qwen8b", {})
                wtl_str = f"{wtl.get('win', 0)}/{wtl.get('tie', 0)}/{wtl.get('loss', 0)}" if wtl else "—"
                m = r["metrics"]
                t3_rows.append(
                    [
                        m_key,
                        ext,
                        ea_str,
                        kf_str,
                        f"{r.get('facet_stats', {}).get('avg_facet_coverage_pct', 0.0):.2f}%",
                        f"{r.get('storage_kb_per_paper', 0.0):.2f}",
                        number(m, "hit@1"),
                        number(m, "hit@3"),
                        number(m, "hit@5"),
                        number(m, "mrr"),
                        number(m, "macro_hit@3"),
                        wtl_str,
                    ]
                )

    # IEEE Table 4: Encoder Robustness Check (Exp C1: specter2 / bge-base)
    t4_headers = [
        "Encoder",
        "Method",
        "Aggregation",
        "Train CV Hit@3",
        "Test Hit@1",
        "Test Hit@3",
        "Test Hit@5",
        "Test MRR",
        "Test Macro-Hit@3",
        "p-val vs Full-text (Hit@3 / MRR)",
    ]
    t4_rows = []
    for enc in ("specter2", "bge-base"):
        enc_test = artifacts.get(enc, {}).get("test")
        if not enc_test:
            continue
        for row in enc_test.get("ieee_rows", []):
            if row["ieee_method"] not in ("fulltext", "equal_weight_facet", "weighted_facet_a", "weighted_facet_cv"):
                continue
            m = row["metrics"]
            sig = row.get("significance_vs_fulltext", {})
            p_str = (
                f"{sig['mcnemar_hit@3']['p_value']:.4f} / {sig['permutation_mrr']['p_value']:.4f}"
                if "mcnemar_hit@3" in sig
                else "—"
            )
            t4_rows.append(
                [
                    enc,
                    IEEE_METHOD_LABELS.get(row["ieee_method"], row["ieee_method"]),
                    AGG_LABELS.get(row["aggregation"], row["aggregation"]),
                    number(row.get("cv"), "hit@3", True),
                    number(m, "hit@1"),
                    number(m, "hit@3"),
                    number(m, "hit@5"),
                    number(m, "mrr"),
                    number(m, "macro_hit@3"),
                    p_str,
                ]
            )

    return {
        "ieee_table1_main_results": (t1_headers, t1_rows, "Main Conference Ranking Results (RQ2)", "tab:ieee_main"),
        "ieee_table2_ablation_temporal_drift": (
            t2_headers,
            t2_rows,
            "Leave-One-Out 5-Facet Ablation, Temporal Drift and Zero-Imputation (Exp C3)",
            "tab:ieee_ablation",
        ),
        "ieee_table3_cross_llm_substitution": (
            t3_headers,
            t3_rows,
            "Cross-LLM Fixed-Index Query-Side Substitution Benchmark (RQ3, RQ4, Exp C4)",
            "tab:ieee_cross_llm",
        ),
        "ieee_table4_encoder_robustness": (
            t4_headers,
            t4_rows,
            "Encoder Robustness Check on Scientific/Contrastive Encoders (Exp C1)",
            "tab:ieee_encoder_robustness",
        ),
    }


def write_report(output_dir, report_path, overwrite=False):
    output, target = Path(output_dir), Path(report_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} exists; use --overwrite")
    artifacts = read_artifacts(output)
    figures = render_sensitivity(artifacts, target.parent / "figures")
    sections = [
        "# Báo cáo thực nghiệm khuyến nghị hội nghị — giao thức v2 (Chuẩn IEEE)",
        "Trạng thái: số liệu chỉ được điền từ artifact v2 đã kiểm tra nguồn gốc. `Chưa chạy` là ô chưa có kết quả; không dùng lại số cũ. Tuyệt đối không sử dụng `validated_silver.jsonl`.",
        "## Giao thức chung",
        "Chọn cấu hình bằng 5-Fold Stratified CV trên 602 bài Train (seed=42), khóa cứng bằng SHA-256 `tuning_id` trước khi đánh giá trên 168 bài Test sạch (100% Unseen).",
        "CV ghi mean ± sample std (ddof=1) giữa các fold. Kiểm định ý nghĩa thống kê trên 168 bài Test dùng McNemar Exact Test (Hit@K), Paired Permutation Test (10.000 lần, MRR), Paired Bootstrap 95% CI (Macro-Hit@3/MRR) và hiệu chỉnh Holm-Bonferroni.",
    ]
    for backend, bundle in artifacts.items():
        tuning = bundle["tuning"]
        if not tuning:
            sections.append(f"- **{backend}:** chưa chạy tuning v2.")
            continue
        meta = tuning["metadata"]
        counts = ", ".join(f"{LABELS[m]}={len(tuning['methods'][m]['cv_all'])}" for m in METHODS)
        sections.append(
            f"- **{backend}:** Train={meta['n_train']}, Test={meta['n_test']}, ứng viên={len(meta['candidates'])}; "
            f"{meta['n_splits']} folds, seed={meta['seed']}; số cấu hình: {counts}. "
            f"Chọn: `{tuning['selection_rule']}`. Tuning ID: `{tuning['tuning_id']}`."
        )
        sections.append(
            f"  Embedding checkpoint: `{meta.get('embedding_model') or 'TF-IDF, vocabulary fit trên reference từng fold'}`. "
            f"Phiên bản thư viện: `{json.dumps(meta.get('versions', {}), sort_keys=True)}`."
        )
        if meta.get("rare_train_venues"):
            sections.append(
                f"  Lớp hiếm (<{meta['n_splits']} mẫu): `{json.dumps(meta['rare_train_venues'], sort_keys=True)}`."
            )

    exports = {}
    # Legacy v2 4-table section (kept for full compatibility with existing tooling/tests)
    rows = []
    for backend, bundle in artifacts.items():
        tuning, test = bundle["tuning"], bundle["test"]
        expected = test.get("random_theoretical") if test else None
        rows.append(
            [
                backend,
                "Random (kỳ vọng lý thuyết)",
                "Uniform shuffle; không tune",
                "Không áp dụng",
                "Không áp dụng",
                *[number(expected, k) for k in ("hit@1", "hit@3", "hit@5", "mrr")],
            ]
        )
        for method in METHODS:
            for variant, label in (("default", "Mặc định"), ("best", "Best tuned")):
                record = tuning["methods"][method][variant] if tuning else None
                test_row = (
                    next((r for r in test["rows"] if r["method"] == method and r["variant"] == variant), None)
                    if test
                    else None
                )
                metrics = test_row["metrics"] if test_row else None
                rows.append(
                    [
                        backend,
                        LABELS[method] + " — " + label,
                        config_text(record["config"] if record else None),
                        number(record["cv"] if record else None, "hit@3", True),
                        number(record["cv"] if record else None, "mrr", True),
                        *[number(metrics, k) for k in ("hit@1", "hit@3", "hit@5", "mrr")],
                    ]
                )
    headers = ["Backend", "Method", "Cấu hình", "Train CV Hit@3", "Train CV MRR", "Test Hit@1", "Test Hit@3", "Test Hit@5", "Test MRR"]
    sections += ["## Bảng 1 — Best tuned, mặc định và baselines", table(headers, rows)]
    exports["table1"] = (headers, rows)
    sections += discussion_table1(artifacts)

    sections += ["## Bảng 2 — Preset trọng số và facet ablation"]
    for backend, bundle in artifacts.items():
        analysis, tuning, test = bundle["analysis"], bundle["tuning"], bundle["test"]
        if not analysis and backend not in ("tfidf", "bert"):
            continue
        t2_rows = []
        names = list(WEIGHT_PRESETS)
        base = (
            next((r["metrics"]["hit@3"] for r in test["rows"] if r["method"] == "gated" and r["variant"] == "best"), None)
            if test
            else None
        )
        for i, name in enumerate(names):
            record = analysis["facet_ablation_table2"][i] if analysis else None
            cv = record.get("cv") if record else None
            metrics = record.get("test", {}).get("metrics") if record else None
            delta = f"{100 * (metrics['hit@3'] - base):+.2f}" if metrics and base is not None else MISSING
            weights = record.get("config", {}).get("weights") if record else None
            t2_rows.append(
                [
                    name,
                    json.dumps(weights, sort_keys=True) if weights else MISSING,
                    number(cv, "hit@3", True),
                    number(metrics, "hit@1"),
                    number(metrics, "hit@3"),
                    number(metrics, "hit@5"),
                    number(metrics, "mrr"),
                    delta,
                ]
            )
        t2_headers = ["Preset", "Weights thực dùng", "Train CV Hit@3", "Test Hit@1", "Test Hit@3", "Test Hit@5", "Test MRR", "Delta Hit@3 (pp)"]
        best = tuning["methods"]["gated"]["best"]["config"] if tuning else None
        sections += [f"### {backend}", f"Cấu hình cố định: {config_text(best)}.", table(t2_headers, t2_rows)]
        exports[f"table2_{backend}"] = (t2_headers, t2_rows)
    sections += discussion_table2(artifacts)

    sections += ["## Bảng 3 — Độ nhạy một chiều trên Train CV"]
    for backend, bundle in artifacts.items():
        analysis = bundle["analysis"]
        if not analysis and backend not in ("tfidf", "bert"):
            continue
        sections.append(f"### {backend}")
        t3_rows = []
        if analysis:
            for parameter, records in analysis["sensitivity"].items():
                for record in records:
                    t3_rows.append([parameter, record["value"], number(record["cv"], "hit@3", True), number(record["cv"], "mrr", True)])
        else:
            t3_rows = [["k", 10, MISSING, MISSING]]
        t3_headers = ["Tham số thay đổi", "Giá trị", "Train CV Hit@3", "Train CV MRR"]
        sections.append(table(t3_headers, t3_rows))
        exports[f"table3_{backend}"] = (t3_headers, t3_rows)

    if figures:
        image_path = Path(os.path.relpath(figures["png"], target.parent)).as_posix()
        svg_path = Path(os.path.relpath(figures["svg"], target.parent)).as_posix()
        data_path = Path(os.path.relpath(figures["csv"], target.parent)).as_posix()
        sections += [
            "### Hình 3 — Biểu đồ đường bổ sung cho Bảng 3",
            f"![Độ nhạy Hit@3 theo k, tau và kappa trên Train CV]({image_path})",
            f"Tải [hình vector SVG]({svg_path}) hoặc [CSV dữ liệu vẽ]({data_path}).",
        ]
    sections += discussion_sensitivity(artifacts)

    sections += ["## Bảng 4 — Cross-LLM với cấu hình đóng băng"]
    sections += table4_rationale()
    t4_rows = []
    for backend, bundle in artifacts.items():
        benchmark = bundle["benchmark"]
        if not benchmark and backend not in ("tfidf", "bert"):
            continue
        source = benchmark["rows"] if benchmark else [{"extractor": name} for name in ("Qwen-8B", "Gemma-9B", "Qwen-14B", "Llama-8B", "Qwen-4B")]
        for row in source:
            t4_rows.append(
                [
                    backend,
                    row["extractor"],
                    config_text(row.get("config")),
                    *[number(row.get("metrics"), k) for k in ("hit@1", "hit@3", "hit@5", "mrr", "macro_hit@3", "macro_mrr")],
                ]
            )
    t4_headers = ["Backend", "LLM", "Frozen config", "Hit@1", "Hit@3", "Hit@5", "MRR", "Macro-Hit@3", "Macro-MRR"]
    sections += [table(t4_headers, t4_rows)]
    exports["table4"] = (t4_headers, t4_rows)
    sections += discussion_table4(artifacts)

    # IEEE 4-Table Publication Section (Markdown + CSV + LaTeX)
    ieee_tables = _build_ieee_tables(artifacts)
    sections.append("## Bộ 4 Bảng Kết quả Chuẩn Hội nghị IEEE (Exp B-Aligned)")
    for tbl_key, (hdrs, rws, caption, lbl) in ieee_tables.items():
        sections.append(f"### {caption} (`{tbl_key}`)")
        if rws:
            sections.append(table(hdrs, rws))
        else:
            sections.append(f"*{MISSING}*")
        exports[tbl_key] = (hdrs, rws)

    sections += limitations(artifacts)
    sections += appendix_macro(artifacts, table, number)
    if figures:
        sections += ["## Phụ lục B — Code và dữ liệu tạo Hình 3", "Hình được tạo tự động bằng Python/Matplotlib từ trường `sensitivity`."]

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    csv_dir = output / "report_tables"
    csv_dir.mkdir(parents=True, exist_ok=True)
    for name, (hdrs, rws) in exports.items():
        with (csv_dir / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(hdrs)
            writer.writerows(rws)
    for name, (hdrs, rws, caption, lbl) in ieee_tables.items():
        if rws:
            (csv_dir / f"{name}.tex").write_text(latex_table(hdrs, rws, caption, lbl), encoding="utf-8")
    print(f"Report: {target}", flush=True)
    return target
