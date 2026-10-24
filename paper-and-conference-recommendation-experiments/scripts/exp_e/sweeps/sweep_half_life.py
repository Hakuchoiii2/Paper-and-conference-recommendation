"""Sweep half-life parameter for Exp E under results/exp_e/sweeps/sensitivity_half_life."""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

EXP_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = EXP_ROOT / "results" / "exp_e" / "sweeps" / "sensitivity_half_life"

HALF_LIVES = [3.0, 7.0, 14.0, 21.0, 30.0, 45.0, 60.0, 90.0, 180.0]


def run_sweep(config_path: str = None):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_summary = []

    print(f"Starting half-life parameter sweep across {len(HALF_LIVES)} values: {HALF_LIVES}")
    print(f"Working Directory: {EXP_ROOT}")
    print(f"Outputs will be saved under: {RESULTS_DIR}\n")

    for hl in HALF_LIVES:
        hl_tag = f"hl_{int(hl) if hl.is_integer() else hl}"
        output_rel = f"results/exp_e/sweeps/sensitivity_half_life/{hl_tag}"
        cmd = [
            sys.executable,
            "scripts/exp_e/run_exp_e.py",
            "--ks", "5", "10",
            "--half-life-days", str(hl),
            "--preset", "canonical",
            "--output", output_rel,
            "--overwrite",
        ]
        if config_path:
            cmd.extend(["--config", config_path])
        print(f"--> Running half_life = {hl} days ({hl_tag})...")
        proc = subprocess.run(cmd, cwd=EXP_ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"Error running half_life {hl}:\n{proc.stderr}")
            continue

        csv_path = EXP_ROOT / output_rel / "summary.csv"
        if not csv_path.exists():
            print(f"Warning: {csv_path} not found!")
            continue

        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["model"] == "decay":
                    results_summary.append({
                        "half_life_days": hl,
                        "group": row["group"],
                        "ndcg@10": float(row["ndcg@10"]),
                        "ndcg@5": float(row["ndcg@5"]),
                        "mrr@10": float(row["mrr@10"]),
                        "importance_mae": float(row["importance_mae"]) if row["importance_mae"] else None,
                        "precision@10": float(row["precision@10"]),
                        "recall@10": float(row["recall@10"]),
                    })
        print(f"    Completed {hl_tag} successfully.")

    summary_csv = RESULTS_DIR / "sweep_metrics.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "half_life_days",
            "group",
            "ndcg@10",
            "ndcg@5",
            "mrr@10",
            "importance_mae",
            "precision@10",
            "recall@10",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results_summary)
    print(f"\nSaved consolidated metrics to {summary_csv}")

    generate_markdown_report(results_summary)


def generate_markdown_report(rows):
    report_path = RESULTS_DIR / "sweep_report.md"

    pivoted = {}
    for r in rows:
        hl = r["half_life_days"]
        grp = r["group"]
        if grp not in pivoted:
            pivoted[grp] = {}
        pivoted[grp][hl] = r

    lines = [
        "# Khảo sát độ nhạy tham số Half-Life (Experiment E)",
        "",
        "Đánh giá ảnh hưởng của chu kỳ bán rã (half-life tính theo ngày) lên mô hình `decay__exp`.",
        "Khung thời gian thực nghiệm gồm 4 kỳ (kỳ 1–4, mỗi kỳ 30 ngày).",
        "",
        "Ghi chú: (↑) giá trị càng cao càng tốt; (↓) giá trị càng thấp càng tốt.",
        "",
        "## 1. Kết quả tổng hợp theo Half-Life (Mô hình Decay)",
        "",
        "| Half-Life (ngày) | Overall nDCG@10 (↑) | Overall MAE (↓) | Drift nDCG@10 (↑) | Drift MAE (↓) | Stable nDCG@10 (↑) | Stable MAE (↓) |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for hl in HALF_LIVES:
        ov = pivoted.get("overall", {}).get(hl, {})
        dr = pivoted.get("drift", {}).get(hl, {})
        st = pivoted.get("stable", {}).get(hl, {})
        lines.append(
            f"| **{int(hl) if hl.is_integer() else hl}** | "
            f"{ov.get('ndcg@10', 0):.4f} | {ov.get('importance_mae', 0):.4f} | "
            f"{dr.get('ndcg@10', 0):.4f} | {dr.get('importance_mae', 0):.4f} | "
            f"{st.get('ndcg@10', 0):.4f} | {st.get('importance_mae', 0):.4f} |"
        )

    lines.extend([
        "",
        "## 2. Chi tiết theo kỳ chuyển dịch (Period 2, 3, 4)",
        "",
        "### Nhóm Drift (Sở thích thay đổi)",
        "| Half-Life | Kỳ 2 (bắt đầu drift) (↑) | Kỳ 3 (chuyển tiếp) (↑) | Kỳ 4 (drift hoàn toàn) (↑) |",
        "|:---:|:---:|:---:|:---:|",
    ])
    for hl in HALF_LIVES:
        p2 = pivoted.get("drift_period_2", {}).get(hl, {}).get("ndcg@10", 0)
        p3 = pivoted.get("drift_period_3", {}).get(hl, {}).get("ndcg@10", 0)
        p4 = pivoted.get("drift_period_4", {}).get(hl, {}).get("ndcg@10", 0)
        lines.append(f"| **{int(hl) if hl.is_integer() else hl}** | {p2:.4f} | {p3:.4f} | {p4:.4f} |")

    lines.extend([
        "",
        "### Nhóm Stable (Sở thích cố định)",
        "| Half-Life | Kỳ 2 (↑) | Kỳ 3 (↑) | Kỳ 4 (↑) |",
        "|:---:|:---:|:---:|:---:|",
    ])
    for hl in HALF_LIVES:
        p2 = pivoted.get("stable_period_2", {}).get(hl, {}).get("ndcg@10", 0)
        p3 = pivoted.get("stable_period_3", {}).get(hl, {}).get("ndcg@10", 0)
        p4 = pivoted.get("stable_period_4", {}).get(hl, {}).get("ndcg@10", 0)
        lines.append(f"| **{int(hl) if hl.is_integer() else hl}** | {p2:.4f} | {p3:.4f} | {p4:.4f} |")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved Markdown report to {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Optional dataset config path")
    args = parser.parse_args()
    run_sweep(config_path=args.config)
