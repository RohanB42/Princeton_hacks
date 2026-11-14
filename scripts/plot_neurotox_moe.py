"""Figure for the MOE acute-neurotox predictor study (docs/neurotox-moe-predictor.md).

Left: per-seed Pearson r for each arm, with the 30-seed mean and a 95% Student-t
interval for that mean, plus the two comparable published five-fold means. Right:
the paired chem-minus-base difference per seed for both model families.

Intervals are for the MEAN across seeds and are pointwise; the seed-to-seed spread
is the scatter itself, which on this dataset is the point worth seeing.

    PYTHONPATH=src python scripts/plot_neurotox_moe.py \
        --results ../_oligoal_work/out/neurotox-moe-eval.json \
        --output docs/figures/neurotox-moe-predictors.png
"""

import argparse
import json
import statistics as st
from pathlib import Path

INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e5e4e0", "#fcfcfb"
ARMS = (
    ("gp_onehot_chem", "GP\nbase+sugar+phosphate", "#1f5fa9"),
    ("gp_onehot_base", "GP\nbase only", "#7aa6d6"),
    ("rf_onehot_chem", "RF\nbase+sugar+phosphate", "#b3561d"),
    ("rf_onehot_base", "RF\nbase only", "#e0a378"),
)
PUBLISHED = {
    "rf_onehot_chem": 0.5394446486358492,
    "rf_onehot_base": 0.47495694726883586,
}


def mean_ci(values):
    from scipy import stats

    n = len(values)
    mean = st.mean(values)
    half = stats.t.ppf(0.975, n - 1) * st.stdev(values) / n**0.5
    return mean, mean - half, mean + half


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    runs = json.loads(args.results.read_text())["runs"]
    values = {arm: np.array([r[arm]["pearson_r"] for r in runs]) for arm, _, _ in ARMS}
    rng = np.random.default_rng(0)  # jitter only, never touches a reported number

    fig, (left, right) = plt.subplots(
        1,
        2,
        figsize=(11.2, 5.6),
        dpi=160,
        facecolor=SURFACE,
        gridspec_kw={"width_ratios": [3, 2], "wspace": 0.22},
    )
    for ax in (left, right):
        style(ax)

    for position, (arm, label, color) in enumerate(ARMS):
        series = values[arm]
        left.scatter(
            position + rng.uniform(-0.13, 0.13, len(series)),
            series,
            s=16,
            color=color,
            alpha=0.45,
            linewidths=0,
            zorder=2,
        )
        mean, low, high = mean_ci(series)
        left.plot(
            [position - 0.3, position + 0.3],
            [mean, mean],
            color=color,
            lw=2.4,
            zorder=3,
        )
        left.plot([position, position], [low, high], color=color, lw=2.4, zorder=3)
        left.annotate(
            f"{mean:.3f}",
            (position, high),
            xytext=(0, 6),
            textcoords="offset points",
            color=INK,
            fontsize=10.5,
            ha="center",
            va="bottom",
            fontweight="demibold",
        )
        if arm in PUBLISHED:
            left.plot(
                [position - 0.3, position + 0.3],
                [PUBLISHED[arm]] * 2,
                color=MUTED,
                lw=1.4,
                ls=(0, (4, 3)),
                zorder=4,
            )
    left.plot(
        [], [], color=MUTED, lw=1.4, ls=(0, (4, 3)), label="published 5-fold mean"
    )
    left.scatter(
        [], [], s=16, color=MUTED, alpha=0.5, linewidths=0, label="one nucleobase seed"
    )
    left.legend(frameon=False, fontsize=9, labelcolor=MUTED, loc="lower left")
    left.set_xticks(range(len(ARMS)))
    left.set_xticklabels([label for _, label, _ in ARMS], fontsize=9, color=MUTED)
    left.set_ylabel("Held-out Pearson r", color=MUTED, fontsize=10)
    left.set_title(
        "MOE acute neurotox (ASO), nucleobase split, 30 seeds",
        color=INK,
        fontsize=11.5,
        fontweight="demibold",
        loc="left",
        pad=12,
    )

    for position, (family, label, color) in enumerate(
        (("gp", "Gaussian process", "#1f5fa9"), ("rf", "Random forest", "#b3561d"))
    ):
        diff = values[f"{family}_onehot_chem"] - values[f"{family}_onehot_base"]
        right.scatter(
            position + rng.uniform(-0.1, 0.1, len(diff)),
            diff,
            s=16,
            color=color,
            alpha=0.45,
            linewidths=0,
            zorder=2,
        )
        mean, low, high = mean_ci(diff)
        right.plot(
            [position - 0.25, position + 0.25],
            [mean, mean],
            color=color,
            lw=2.4,
            zorder=3,
        )
        right.plot([position, position], [low, high], color=color, lw=2.4, zorder=3)
        right.annotate(
            f"{mean:+.3f}\n{int((diff > 0).sum())}/{len(diff)} seeds",
            (position + 0.3, mean),
            color=INK,
            fontsize=9.5,
            va="center",
        )
    right.axhline(0, color=INK, lw=1)
    right.set_xlim(-0.5, 1.9)
    right.set_xticks([0, 1])
    right.set_xticklabels(
        ["Gaussian process", "Random forest"], fontsize=9, color=MUTED
    )
    right.set_ylabel("chem minus base, same seed", color=MUTED, fontsize=10)
    right.set_title(
        "Encoding the gapmer helps",
        color=INK,
        fontsize=11.5,
        fontweight="demibold",
        loc="left",
        pad=12,
    )

    fig.text(
        0.008,
        0.015,
        "Bars: 30-seed mean with 95% t interval for the mean. Points: one official "
        "nucleobase split each. Labels are rounded 3h mouse FOB scores (8 ordinal "
        "categories, patent-scraped). Predictions are not observations.",
        color=MUTED,
        fontsize=8,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, bbox_inches="tight", facecolor=SURFACE)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
