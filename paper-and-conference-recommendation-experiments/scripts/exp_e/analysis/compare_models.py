"""Compare all baselines and new temporal ideas across Overall, Drift, and Stable cohorts."""
import argparse
import csv
from pathlib import Path

EXP_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SUMMARY_CSV = EXP_ROOT / "results" / "exp_e" / "ideas" / "all_ideas_benchmark" / "summary.csv"
DEFAULT_OUTPUT_MD = EXP_ROOT / "results" / "exp_e" / "comparison_summary.md"


def format_val(val_str: str) -> str:
    if not val_str:
        return "N/A"
    return f"{float(val_str):.4f}"


def generate_comparison(summary_csv: Path, output_md: Path):
    if not summary_csv.exists():
        raise FileNotFoundError(f"Summary CSV not found at {summary_csv}. Run the 'all' preset first.")

    pivoted = {}
    models_seen = []
    with summary_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            m = row["model"]
            g = row["group"]
            if m not in models_seen:
                models_seen.append(m)
            pivoted.setdefault(g, {})[m] = row

    lines = [
        "# Bảng Tổng Hợp So Sánh Mô Hình (Experiment E — Unified Benchmark)",
        "",
        f"Nguồn dữ liệu: `{summary_csv.relative_to(EXP_ROOT).as_posix()}`",
        "",
        "## 1. Hiệu năng Tổng thể & Theo Nhóm (Overall / Drift / Stable)",
        "",
        "| Mô hình (`<family>__<method>__<param>`) | Overall nDCG@10 (↑) | Overall MAE (↓) | Drift nDCG@10 (↑) | Drift MAE (↓) | Stable nDCG@10 (↑) | Stable MAE (↓) |",
        "|---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for m in models_seen:
        ov = pivoted.get("overall", {}).get(m, {})
        dr = pivoted.get("drift", {}).get(m, {})
        st = pivoted.get("stable", {}).get(m, {})
        lines.append(
            f"| `{m}` | "
            f"{format_val(ov.get('ndcg@10', ''))} | {format_val(ov.get('importance_mae', ''))} | "
            f"{format_val(dr.get('ndcg@10', ''))} | {format_val(dr.get('importance_mae', ''))} | "
            f"{format_val(st.get('ndcg@10', ''))} | {format_val(st.get('importance_mae', ''))} |"
        )

    lines.extend([
        "",
        "## 2. Diễn biến Nhóm Drift qua 3 Kỳ Đánh giá (Period 2 → 3 → 4)",
        "",
        "| Mô hình | Kỳ 2 nDCG@10 (↑) | Kỳ 3 nDCG@10 (↑) | Kỳ 4 nDCG@10 (↑) | Kỳ 4 MAE (↓) |",
        "|---|:---:|:---:|:---:|:---:|",
    ])

    for m in models_seen:
        p2 = pivoted.get("drift_period_2", {}).get(m, {})
        p3 = pivoted.get("drift_period_3", {}).get(m, {})
        p4 = pivoted.get("drift_period_4", {}).get(m, {})
        lines.append(
            f"| `{m}` | "
            f"{format_val(p2.get('ndcg@10', ''))} | "
            f"{format_val(p3.get('ndcg@10', ''))} | "
            f"{format_val(p4.get('ndcg@10', ''))} | "
            f"{format_val(p4.get('importance_mae', ''))} |"
        )

    lines.extend([
        "",
        "## 3. Diễn biến Nhóm Stable qua 3 Kỳ Đánh giá (Period 2 → 3 → 4)",
        "",
        "| Mô hình | Kỳ 2 nDCG@10 (↑) | Kỳ 3 nDCG@10 (↑) | Kỳ 4 nDCG@10 (↑) | Kỳ 4 MAE (↓) |",
        "|---|:---:|:---:|:---:|:---:|",
    ])

    for m in models_seen:
        p2 = pivoted.get("stable_period_2", {}).get(m, {})
        p3 = pivoted.get("stable_period_3", {}).get(m, {})
        p4 = pivoted.get("stable_period_4", {}).get(m, {})
        lines.append(
            f"| `{m}` | "
            f"{format_val(p2.get('ndcg@10', ''))} | "
            f"{format_val(p3.get('ndcg@10', ''))} | "
            f"{format_val(p4.get('ndcg@10', ''))} | "
            f"{format_val(p4.get('importance_mae', ''))} |"
        )

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Comparison report written to {output_md}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()
    generate_comparison(args.summary_csv, args.output_md)
