"""Plot saved measured-ranking and surrogate-search diagnostics without refitting."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    measured = json.loads((args.study / "assessment.json").read_text())
    comparison = json.loads((args.comparison / "comparison.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), layout="constrained")
    rows = measured["rows"]
    x = np.arange(len(rows))
    axes[0].bar(
        x - 0.17,
        [r["random_expected_mean"] for r in rows],
        0.34,
        label="Random expected mean",
        color="#aab5c3",
    )
    bars = axes[0].bar(
        x + 0.17,
        [r["selected_mean"] for r in rows],
        0.34,
        label="Model's preselected top 20",
        color="#167d8d",
    )
    axes[0].bar_label(
        bars, labels=[f"+{r['lift_percentage_points']:.2f} pp" for r in rows], padding=4
    )
    axes[0].set_xticks(x, [f"{r['target']} (n={r['n']})" for r in rows])
    axes[0].set_ylim(0, 100)
    axes[0].set_ylabel("Measured inhibition (%)")
    axes[0].set_title(
        "Held-out recorded assays\nDevelopment ranking; fixed 20-mer chemistry"
    )
    axes[0].legend(loc="upper left", frameon=False, fontsize=9)
    methods = ["unchanged", "random", "greedy", "genetic", "ppo_initial"]
    means, deviations = [], []
    for method in methods:
        values = [
            r["best_reward"]
            for r in comparison["runs"]
            if r["method"] == method and r["budget"] == 6
        ]
        means.append(np.mean(values))
        deviations.append(np.std(values, ddof=1))
    axes[1].bar(
        np.arange(len(methods)),
        means,
        yerr=deviations,
        capsize=4,
        color=["#aab5c3", "#167d8d", "#77a699", "#a4c0b2", "#dc8158"],
    )
    axes[1].axhline(
        comparison["reference"]["best_reward"],
        linestyle="--",
        color="#333333",
        linewidth=1,
        label="17-score enumeration reference",
    )
    axes[1].set_xticks(
        np.arange(len(methods)), ["Start", "Random", "Greedy", "Genetic", "PPO"]
    )
    axes[1].set_ylim(0, 1.02)
    axes[1].set_ylabel("Best visited surrogate utility (0–1)")
    axes[1].set_title(
        "FGFR4: one final transcript window\n6-score cap, 8 moves; mean ± seed SD (n=3)"
    )
    axes[1].legend(loc="upper left", frameon=False, fontsize=8)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis="y", alpha=0.16)
    fig.supxlabel(
        "Recorded-assay ranking ≠ validation of generated ASOs. "
        "Safety unknown; PPO expansion gate failed.",
        fontsize=10,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
