"""Plot ignored run artifacts from saved measured replay histories."""

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _write(fig, output: Path) -> None:
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def figures(root: Path) -> None:
    report = json.loads((root / "report.json").read_text())
    if "methods" in report["summary"]:
        comparison_figure(root, report)
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    for method, row in report["summary"].items():
        values = row["mean_hit_curve"]
        ax.plot(
            range(1, len(values) + 1),
            values,
            label=method,
            linewidth=2.5 if method == "ppo" else 1.2,
        )
    ax.set(
        xlabel="Assays used (including seed assays)",
        ylabel="New measured hits",
        title=f"Atlas discovery · {report['version'].upper()} · equal target weights",
    )
    ax.legend(ncols=2, frameon=False, fontsize=8)
    _write(fig, root / "discovery.png")
    if report["version"] != "v2":
        return
    records = json.loads((root / "episodes.json").read_text())["episodes"]
    ppo = [r for r in records if r["method"] == "ppo"]
    checkpoints = [str(n) for n in report["config"]["checkpoints"]]
    fig, (learning, coverage) = plt.subplots(1, 2, figsize=(9, 4))
    for model in ("v1", "v2", "gp"):
        values = [
            np.mean([r["sentinel"][model][c]["rmse"] for r in ppo]) for c in checkpoints
        ]
        learning.plot(list(map(int, checkpoints)), values, marker="o", label=model)
        levels = [0.5, 0.8, 0.9]
        result = [
            np.mean(
                [
                    r["sentinel"][model][checkpoints[-1]]["intervals"][str(v)][
                        "coverage"
                    ]
                    for r in ppo
                ]
            )
            for v in levels
        ]
        coverage.plot(levels, result, marker="o", label=model)
    learning.set(
        xlabel="Assays used",
        ylabel="RMSE (percentage points)",
        title="Never-acquired sentinel prediction",
    )
    coverage.plot([0.45, 0.95], [0.45, 0.95], "--", lw=1, color="grey")
    coverage.set(
        xlabel="Nominal interval coverage",
        ylabel="Observed coverage",
        title="Empirical coverage at final budget",
    )
    coverage.legend(frameon=False)
    _write(fig, root / "sentinels.png")


def comparison_figure(root: Path, report: dict) -> None:
    """Render all frozen methods and both target groups with honest scope labels."""
    methods = report["summary"]["methods"]
    width = report["config"]["hidden_layers"][0]
    sizes = report["config"].get("evaluation_pool_sizes")
    pool_title = (
        "; ".join(f"{target}: {size:,}" for target, size in sizes.items())
        if sizes
        else f"{report['config']['candidate_pool_size']:,} candidates per campaign"
    )
    names = {
        "ppo": f"PPO · 3 × {width}",
        "mean": "Updated greedy",
        "source_mean": "Frozen ranking",
        "random": "Random",
    }
    colors = {
        "ppo": "#8055cf",
        "mean": "#137baf",
        "source_mean": "#e59e38",
        "random": "#79838d",
    }
    fig, (curve, bars) = plt.subplots(1, 2, figsize=(11, 4.5))
    for method in ("random", "source_mean", "mean", "ppo"):
        row = methods[method]
        curve.plot(
            range(1, len(row["mean_hit_curve"]) + 1),
            row["mean_hit_curve"],
            color=colors[method],
            label=names[method],
            linewidth=2,
        )
    curve.axvline(report["config"]["initial_assays"], color="#b9bdc1", linestyle=":")
    curve.set(
        xlabel="Assays purchased (10 initial + 40 selected)",
        ylabel="New measured hits (>80% recorded inhibition)",
        title=pool_title,
    )
    curve.legend(frameon=False, fontsize=8)
    targets = sorted(methods["ppo"]["target_mean_hits"])
    x = np.arange(len(targets))
    for i, method in enumerate(("random", "source_mean", "mean", "ppo")):
        bars.bar(
            x + (i - 1.5) * 0.2,
            [methods[method]["target_mean_hits"][t] for t in targets],
            width=0.19,
            color=colors[method],
            label=names[method],
        )
    bars.set(
        xticks=x,
        xticklabels=targets,
        ylabel="Mean new hits at 50 assays",
        title="Per-target result · 5 policy seeds / 5 replay seeds",
    )
    fig.suptitle(
        "Retrospective Atlas diagnostic · two prior-exposed targets", fontsize=12
    )
    _write(fig, root / "comparison.png")
