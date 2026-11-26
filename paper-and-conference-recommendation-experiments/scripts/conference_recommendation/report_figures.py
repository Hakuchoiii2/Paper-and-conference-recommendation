"""Publication-style sensitivity plots from saved CV artifacts; no inference runs."""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def render_sensitivity(artifacts, target_dir):
    """Return image/vector/data paths. A venv may use its base Python for plotting."""
    available = {backend: {key: bundle["analysis"][key] for key in ("tuning_id", "best_operating_point", "sensitivity")}
                 for backend, bundle in artifacts.items() if bundle.get("analysis")}
    if not available:
        return None
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    source = target_dir / "sensitivity_source.json"
    source.write_text(json.dumps(available, ensure_ascii=False), encoding="utf-8")
    try:
        import matplotlib
    except ImportError:
        base_python = getattr(sys, "_base_executable", sys.executable)
        if Path(base_python).resolve() == Path(sys.executable).resolve():
            raise RuntimeError("Sensitivity figures require matplotlib. Install it in the report Python environment.")
        subprocess.run([base_python, str(Path(__file__).resolve()), str(source), str(target_dir)], check=True)
    else:
        _plot(available, target_dir)
    return {kind: target_dir / ("sensitivity_cv_hit3." + kind) for kind in ("png", "svg", "csv")}


def _plot(available, target_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    colors = {"tfidf": "#176B91", "specter": "#9B4B0F", "bge-small": "#247854"}
    names = {"tfidf": "TF-IDF", "specter": "SPECTER", "bge-small": "BGE-small"}
    labels = {"k": r"Number of neighbors $k$", "tau": r"Problem threshold $\tau$", "kappa": r"Sigmoid slope $\kappa$"}
    parameters = ("k", "tau", "kappa")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "savefig.facecolor": "white"})
    fig, axes = plt.subplots(len(available), 3, figsize=(15, 3.25 * len(available) + 1.2), squeeze=False)
    records = []
    for row, (backend, analysis) in enumerate(available.items()):
        best = analysis["best_operating_point"]
        color = colors.get(backend, "#176B91")
        for col, parameter in enumerate(parameters):
            ax = axes[row, col]
            points = sorted(analysis["sensitivity"][parameter], key=lambda r: r["value"])
            x = np.array([r["value"] for r in points])
            mean = np.array([r["cv"]["hit@3"] * 100 for r in points])
            std = np.array([r["cv"]["hit@3_std"] * 100 for r in points])
            ax.fill_between(x, mean - std, mean + std, color=color, alpha=.13, linewidth=0,
                            label="Mean ± 1 fold SD")
            ax.plot(x, mean, "o-", color=color, linewidth=2, markersize=4, label="CV mean")
            chosen = next(i for i, value in enumerate(x) if np.isclose(value, best[parameter]))
            ax.axvline(x[chosen], color=color, alpha=.45, linestyle="--", linewidth=1)
            ax.scatter(x[chosen], mean[chosen], marker="*", s=160, color="#B81F40",
                       edgecolors="white", linewidths=.7, zorder=5, label="Frozen choice from tuning")
            ax.annotate(f"{parameter}*={best[parameter]:g}\n{mean[chosen]:.2f}%",
                        (x[chosen], mean[chosen]), xytext=(-10 if chosen == len(x)-1 else 8, 14),
                        textcoords="offset points", ha="right" if chosen == len(x)-1 else "left",
                        fontsize=9, color="#8B1530")
            lower, upper = float(min(mean-std)), float(max(mean+std))
            pad = max(.7, (upper-lower)*.13)
            ax.set_ylim(lower-pad, upper+pad*2)
            ax.set_xticks(x)
            ax.tick_params(axis="x", labelsize=9)
            ax.set_xlabel(labels[parameter])
            ax.set_ylabel("Train CV Hit@3 (%)")
            ax.set_title(f"{names.get(backend, backend)} · {parameter}", loc="left", fontweight="bold", fontsize=11)
            ax.grid(axis="y", color="#D5DCE2", linewidth=.6, alpha=.8)
            ax.set_axisbelow(True)
            for point in points:
                records.append({"backend": backend, "parameter": parameter, "value": point["value"],
                                "cv_hit@3_mean": point["cv"]["hit@3"], "cv_hit@3_std": point["cv"]["hit@3_std"],
                                "frozen_choice": int(point["value"] == best[parameter]),
                                "tuning_id": analysis["tuning_id"]})
    handles, labels_legend = axes[0, 0].get_legend_handles_labels()
    fig.suptitle("One-dimensional sensitivity of Gated 5-Facet", x=.055, ha="left", fontsize=17, fontweight="bold", y=.995)
    fig.legend(handles, labels_legend, loc="upper center", bbox_to_anchor=(.53, .96), ncol=3, frameon=False)
    fig.text(.055, .012, "Train CV only · Other parameters and weights frozen per backend · Shading is fold SD, not a confidence interval · Panel-specific y-scales",
             color="#44515D", fontsize=9)
    fig.tight_layout(rect=(.02, .035, 1, .92))
    for suffix in ("png", "svg"):
        fig.savefig(target_dir / f"sensitivity_cv_hit3.{suffix}", dpi=220, bbox_inches="tight")
    plt.close(fig)
    with (target_dir / "sensitivity_cv_hit3.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    _plot(json.loads(args.source.read_text(encoding="utf-8")), args.output_dir)
