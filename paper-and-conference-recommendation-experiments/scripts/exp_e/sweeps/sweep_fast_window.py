"""Sweep fast window parameter n (days) for Monolith-inspired Fast-Slow Facet-Gated model."""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

EXP_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = EXP_ROOT / "results" / "exp_e" / "sweeps" / "sensitivity_fast_window"

SWEEP_MODELS = [
    ("7 ngày", "hybrid__fast_slow_gated__w7"),
    ("14 ngày", "hybrid__fast_slow_gated__w14"),
    ("21 ngày", "hybrid__fast_slow_gated__w21"),
    ("30 ngày", "hybrid__fast_slow_gated__w30"),
    ("45 ngày", "hybrid__fast_slow_gated__w45"),
    ("60 ngày", "hybrid__fast_slow_gated__w60"),
]


def run_sweep(config_path: str = None):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_rel = "results/exp_e/sweeps/sensitivity_fast_window/run_window"
    model_keys = [m for _, m in SWEEP_MODELS]

    cmd = [
        sys.executable,
        "scripts/exp_e/run_exp_e.py",
        "--ks", "5", "10",
        "--models", *model_keys,
        "--output", output_rel,
        "--overwrite",
    ]
    if config_path:
        cmd.extend(["--config", config_path])
    print(f"Running Fast-Slow Facet-Gated window sweep across {len(SWEEP_MODELS)} configurations...")
    proc = subprocess.run(cmd, cwd=EXP_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Error running fast-window sweep:\n{proc.stderr}")

    csv_path = EXP_ROOT / output_rel / "summary.csv"
    rows = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["model"] in model_keys:
                rows.append({
                    "model": row["model"],
                    "group": row["group"],
                    "ndcg@10": float(row["ndcg@10"]),
                    "ndcg@5": float(row["ndcg@5"]),
                    "mrr@10": float(row["mrr@10"]),
                    "importance_mae": float(row["importance_mae"]) if row["importance_mae"] else 0.0,
                    "precision@10": float(row["precision@10"]),
                    "recall@10": float(row["recall@10"]),
                })

    summary_csv = RESULTS_DIR / "sweep_metrics.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        fields = ["model", "group", "ndcg@10", "ndcg@5", "mrr@10", "importance_mae", "precision@10", "recall@10"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    pivoted = {}
    for r in rows:
        pivoted.setdefault(r["group"], {})[r["model"]] = r

    lines = [
        "# Khảo sát độ nhạy cửa sổ Fast State n (ngày) — Fast-Slow Facet-Gated (Exp E)",
        "",
        "Đánh giá ảnh hưởng của độ dài cửa sổ trượt $n$ ngày đối với mô hình Fast-Slow Facet-Gated lấy cảm hứng từ ByteDance Monolith:",
        "",
        "| Độ dài Cửa sổ n | Mã Mô hình | Overall nDCG@10 (↑) | Overall MAE (↓) | Drift nDCG@10 (↑) | Drift MAE (↓) | Stable nDCG@10 (↑) | Stable MAE (↓) |",
        "|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for label, key in SWEEP_MODELS:
        ov = pivoted.get("overall", {}).get(key, {})
        dr = pivoted.get("drift", {}).get(key, {})
        st = pivoted.get("stable", {}).get(key, {})
        lines.append(
            f"| **{label}** | `{key}` | "
            f"{ov.get('ndcg@10', 0.0):.4f} | {ov.get('importance_mae', 0.0):.4f} | "
            f"{dr.get('ndcg@10', 0.0):.4f} | {dr.get('importance_mae', 0.0):.4f} | "
            f"{st.get('ndcg@10', 0.0):.4f} | {st.get('importance_mae', 0.0):.4f} |"
        )

    report_md = RESULTS_DIR / "sweep_report.md"
    report_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Sweep complete! Report generated at: {report_md}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Optional dataset config path (e.g. configs/exp_e_12m.json)")
    args = parser.parse_args()
    run_sweep(config_path=args.config)
