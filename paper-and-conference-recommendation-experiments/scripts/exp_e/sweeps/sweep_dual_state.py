"""Sweep alpha parameter for Dual-State Hybrid model under results/exp_e/sweeps/sensitivity_dual_state."""
import csv
import subprocess
import sys
from pathlib import Path

EXP_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = EXP_ROOT / "results" / "exp_e" / "sweeps" / "sensitivity_dual_state"

SWEEP_MODELS = [
    ("0.00 (Static)", "baseline__static__all"),
    ("0.35", "hybrid__dual_state__alpha0.35"),
    ("0.50", "hybrid__dual_state__alpha0.50"),
    ("0.65", "hybrid__dual_state__alpha0.65"),
    ("0.80", "hybrid__dual_state__alpha0.80"),
    ("1.00 (Recent)", "baseline__recent__prev_period"),
]


def run_sweep():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_rel = "results/exp_e/sweeps/sensitivity_dual_state/run_alpha"
    model_keys = [m for _, m in SWEEP_MODELS]

    cmd = [
        sys.executable,
        "scripts/exp_e/run_exp_e.py",
        "--ks", "5", "10",
        "--models", *model_keys,
        "--output", output_rel,
        "--overwrite",
    ]
    print(f"Running Dual-State Hybrid alpha sweep across {len(SWEEP_MODELS)} configurations...")
    proc = subprocess.run(cmd, cwd=EXP_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Error running dual-state sweep:\n{proc.stderr}")

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
        "# Khảo sát độ nhạy trọng số Alpha — Dual-State Hybrid (Experiment E)",
        "",
        "Đánh giá sự kết hợp tuyến tính giữa hồ sơ ngắn hạn ($\\alpha$) và hồ sơ dài hạn ($1 - \\alpha$):",
        "$$\\mathcal{P}_{\\text{hybrid}}(u) = \\alpha \\cdot \\mathcal{P}_{\\text{short}}(u) + (1 - \\alpha) \\cdot \\mathcal{P}_{\\text{long}}(u)$$",
        "",
        "| Hệ số Alpha | Mã Mô hình | Overall nDCG@10 (↑) | Overall MAE (↓) | Drift nDCG@10 (↑) | Drift MAE (↓) | Stable nDCG@10 (↑) | Stable MAE (↓) |",
        "|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for label, key in SWEEP_MODELS:
        ov = pivoted.get("overall", {}).get(key, {})
        dr = pivoted.get("drift", {}).get(key, {})
        st = pivoted.get("stable", {}).get(key, {})
        lines.append(
            f"| **{label}** | `{key}` | "
            f"{ov.get('ndcg@10', 0):.4f} | {ov.get('importance_mae', 0):.4f} | "
            f"{dr.get('ndcg@10', 0):.4f} | {dr.get('importance_mae', 0):.4f} | "
            f"{st.get('ndcg@10', 0):.4f} | {st.get('importance_mae', 0):.4f} |"
        )

    report_path = RESULTS_DIR / "sweep_report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved Dual-State sweep report to {report_path}")


if __name__ == "__main__":
    run_sweep()
