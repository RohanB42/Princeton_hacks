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
