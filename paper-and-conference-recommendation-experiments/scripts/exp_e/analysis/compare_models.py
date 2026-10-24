"""Compare all baselines and new temporal ideas across Overall, Drift, and Stable cohorts."""
import argparse
import csv
from pathlib import Path
from typing import Dict, List

EXP_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SUMMARY_CSV = EXP_ROOT / "results" / "exp_e" / "ideas" / "all_ideas_benchmark" / "summary.csv"
DEFAULT_OUTPUT_MD = EXP_ROOT / "results" / "exp_e" / "comparison_summary.md"

FRIENDLY_NAMES: Dict[str, Dict[str, str]] = {
    "popularity": {
        "full": "**Global Popularity** (Tần suất toàn tập)",
        "short": "**Global Popularity**",
    },
    "static": {
        "full": "**Static Baseline** (Toàn bộ quá khứ, $w_t = 1.0$)",
        "short": "**Static Baseline** (All History)",
    },
    "baseline__static__all": {
        "full": "**Static Baseline** (Toàn bộ quá khứ, $w_t = 1.0$)",
        "short": "**Static Baseline** (All History)",
    },
    "recent": {
        "full": "**Recent Baseline** (Chỉ kỳ gần nhất)",
        "short": "**Recent Baseline** (Prev Period)",
    },
    "baseline__recent__prev_period": {
        "full": "**Recent Baseline** (Chỉ kỳ gần nhất)",
        "short": "**Recent Baseline** (Prev Period)",
    },
    "decay": {
        "full": "**Exponential Decay** ($T_{1/2} = 30$ ngày)",
        "short": "**Exp Decay** ($T_{1/2}=30$d)",
    },
    "decay__exp__hl14": {
        "full": "**Exponential Decay** ($T_{1/2} = 14$ ngày)",
        "short": "**Exp Decay** ($T_{1/2}=14$d)",
    },
    "decay__exp__hl21": {
        "full": "**Exponential Decay** ($T_{1/2} = 21$ ngày)",
        "short": "**Exp Decay** ($T_{1/2}=21$d)",
    },
    "decay__exp__hl30": {
        "full": "**Exponential Decay** ($T_{1/2} = 30$ ngày)",
        "short": "**Exp Decay** ($T_{1/2}=30$d)",
    },
    "decay__exp__hl60": {
        "full": "**Exponential Decay** ($T_{1/2} = 60$ ngày)",
        "short": "**Exp Decay** ($T_{1/2}=60$d)",
    },
    "decay__power_law__beta0.6": {
        "full": "**Power-Law Hyperbolic Decay** ($\\beta = 0.6$)",
        "short": "**Power-Law** ($\\beta=0.6$)",
    },
    "decay__adaptive__divergence": {
        "full": "**Adaptive Decay** (Co giãn $T_{1/2}$ theo Divergence)",
        "short": "**Adaptive Decay** (Divergence)",
    },
    "drift__shift_gate__cos0.55": {
        "full": "**Change-Point Shift Gate** (Phát hiện điểm gãy, $\\tau = 0.55$)",
        "short": "**Shift Gate** ($\\tau=0.55$)",
    },
    "hybrid__dual_state__alpha0.35": {
        "full": "**Dual-State Hybrid** (Ngắn hạn $\\alpha = 0.35$)",
        "short": "**Dual-State** ($\\alpha=0.35$)",
    },
    "hybrid__dual_state__alpha0.50": {
        "full": "**Dual-State Hybrid** (Cân bằng $\\alpha = 0.50$)",
        "short": "**Dual-State** ($\\alpha=0.50$)",
    },
    "hybrid__dual_state__alpha0.65": {
        "full": "**Dual-State Hybrid** (Ngắn hạn $\\alpha = 0.65$)",
        "short": "**Dual-State** ($\\alpha=0.65$)",
    },
    "hybrid__dual_state__alpha0.80": {
        "full": "**Dual-State Hybrid** (Ngắn hạn $\\alpha = 0.80$)",
        "short": "**Dual-State** ($\\alpha=0.80$)",
    },
    "fast_slow_gated": {
        "full": "**Fast-Slow Facet-Gated (Monolith)** ($w = 30$ ngày)",
        "short": "**Fast-Slow Gated** ($w=30$d)",
    },
    "hybrid__fast_slow_gated__w7": {
        "full": "**Fast-Slow Facet-Gated (Monolith)** ($w = 7$ ngày)",
        "short": "**Fast-Slow Gated** ($w=7$d)",
    },
    "hybrid__fast_slow_gated__w14": {
        "full": "**Fast-Slow Facet-Gated (Monolith)** ($w = 14$ ngày)",
        "short": "**Fast-Slow Gated** ($w=14$d)",
    },
    "hybrid__fast_slow_gated__w21": {
        "full": "**Fast-Slow Facet-Gated (Monolith)** ($w = 21$ ngày — Sweet spot)",
        "short": "**Fast-Slow Gated** ($w=21$d)",
    },
    "hybrid__fast_slow_gated__w30": {
        "full": "**Fast-Slow Facet-Gated (Monolith)** ($w = 30$ ngày)",
        "short": "**Fast-Slow Gated** ($w=30$d)",
    },
    "hybrid__fast_slow_gated__w45": {
        "full": "**Fast-Slow Facet-Gated (Monolith)** ($w = 45$ ngày)",
        "short": "**Fast-Slow Gated** ($w=45$d)",
    },
    "hybrid__fast_slow_gated__w60": {
        "full": "**Fast-Slow Facet-Gated (Monolith)** ($w = 60$ ngày)",
        "short": "**Fast-Slow Gated** ($w=60$d)",
    },
}


def get_friendly_name(model_key: str, mode: str = "full") -> str:
    """Return an academic, publication-ready friendly name for a model."""
    if model_key in FRIENDLY_NAMES:
        base = FRIENDLY_NAMES[model_key][mode]
    else:
        # Fallback formatting: human-readable title
        clean = model_key.replace("__", " · ").replace("_", " ").title()
        base = f"**{clean}**"

    if mode == "full" and model_key != "popularity":
        return f"{base}<br><sub><code>{model_key}</code></sub>"
    return base


def format_val(val_str: str) -> str:
    if not val_str:
        return "N/A"
    return f"{float(val_str):.4f}"


def generate_comparison(summary_csv: Path, output_md: Path):
    if not summary_csv.exists():
        raise FileNotFoundError(f"Summary CSV not found at {summary_csv}. Run the experiment first.")

    pivoted: Dict[str, Dict[str, Dict[str, str]]] = {}
    models_seen: List[str] = []
    with summary_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            m = row["model"]
            g = row["group"]
            if m not in models_seen:
                models_seen.append(m)
            pivoted.setdefault(g, {})[m] = row

    # Dynamically extract all evaluation periods present in the summary CSV
    drift_period_keys = [g for g in pivoted.keys() if g.startswith("drift_period_")]
    periods = sorted(set(int(g.split("_")[-1]) for g in drift_period_keys))

    lines = [
        "# Bảng Tổng Hợp So Sánh Mô Hình (Experiment E — Unified Benchmark)",
        "",
        f"Nguồn dữ liệu: `{summary_csv.relative_to(EXP_ROOT).as_posix() if summary_csv.is_relative_to(EXP_ROOT) else summary_csv}`",
        "",
        "## 1. Hiệu năng Tổng thể & Theo Nhóm (Overall / Drift / Stable)",
        "",
        "| Phương pháp Khuyến nghị (Model) | Overall nDCG@10 (↑) | Overall MAE (↓) | Drift nDCG@10 (↑) | Drift MAE (↓) | Stable nDCG@10 (↑) | Stable MAE (↓) |",
        "|---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for m in models_seen:
        ov = pivoted.get("overall", {}).get(m, {})
        dr = pivoted.get("drift", {}).get(m, {})
        st = pivoted.get("stable", {}).get(m, {})
        lines.append(
            f"| {get_friendly_name(m, mode='full')} | "
            f"{format_val(ov.get('ndcg@10', ''))} | {format_val(ov.get('importance_mae', ''))} | "
            f"{format_val(dr.get('ndcg@10', ''))} | {format_val(dr.get('importance_mae', ''))} | "
            f"{format_val(st.get('ndcg@10', ''))} | {format_val(st.get('importance_mae', ''))} |"
        )

    if periods:
        last_p = periods[-1]
        period_headers = " | ".join(f"Kỳ {p} nDCG@10 (↑)" for p in periods)
        period_aligns = " | ".join(":---:" for _ in periods)

        # Section 2: Drift Group Progression
        lines.extend([
            "",
            f"## 2. Diễn biến Nhóm Drift qua {len(periods)} Kỳ Đánh giá (Period {periods[0]} → ... → {last_p})",
            "",
            f"| Phương pháp Khuyến nghị | {period_headers} | Kỳ {last_p} MAE (↓) |",
            f"|---|{period_aligns}|:---:|",
        ])
        for m in models_seen:
            p_vals = [
                format_val(pivoted.get(f"drift_period_{p}", {}).get(m, {}).get("ndcg@10", ""))
                for p in periods
            ]
            last_mae = format_val(pivoted.get(f"drift_period_{last_p}", {}).get(m, {}).get("importance_mae", ""))
            lines.append(f"| {get_friendly_name(m, mode='short')} | {' | '.join(p_vals)} | {last_mae} |")

        # Section 3: Stable Group Progression
        lines.extend([
            "",
            f"## 3. Diễn biến Nhóm Stable qua {len(periods)} Kỳ Đánh giá (Period {periods[0]} → ... → {last_p})",
            "",
            f"| Phương pháp Khuyến nghị | {period_headers} | Kỳ {last_p} MAE (↓) |",
            f"|---|{period_aligns}|:---:|",
        ])
        for m in models_seen:
            p_vals = [
                format_val(pivoted.get(f"stable_period_{p}", {}).get(m, {}).get("ndcg@10", ""))
                for p in periods
            ]
            last_mae = format_val(pivoted.get(f"stable_period_{last_p}", {}).get(m, {}).get("importance_mae", ""))
            lines.append(f"| {get_friendly_name(m, mode='short')} | {' | '.join(p_vals)} | {last_mae} |")

        # Section 4: Adaptation Gap (Stable nDCG - Drift nDCG)
        gap_headers = " | ".join(f"Kỳ {p} Gap (↓)" for p in periods)
        lines.extend([
            "",
            f"## 4. Độ lệch Thích ứng Adaptation Gap: Stable nDCG@10 − Drift nDCG@10 (Càng gần 0 càng thích ứng tốt)",
            "",
            f"| Phương pháp Khuyến nghị | {gap_headers} |",
            f"|---|{period_aligns}|",
        ])
        for m in models_seen:
            gap_vals = []
            for p in periods:
                st_val = pivoted.get(f"stable_period_{p}", {}).get(m, {}).get("ndcg@10")
                dr_val = pivoted.get(f"drift_period_{p}", {}).get(m, {}).get("ndcg@10")
                if st_val and dr_val:
                    gap = float(st_val) - float(dr_val)
                    gap_vals.append(f"{gap:+.4f}")
                else:
                    gap_vals.append("N/A")
            lines.append(f"| {get_friendly_name(m, mode='short')} | {' | '.join(gap_vals)} |")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Comparison report written to {output_md}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()
    generate_comparison(args.summary_csv, args.output_md)
