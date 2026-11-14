"""Figure for the TLR immunomodulation endpoints.

See docs/tlr-immunomodulation-predictors.md.

One panel per assay: per-seed held-out Pearson r for the GP and RF arms, with the
30-seed mean, a 95% Student-t interval for that mean, and the published five-fold
mean for the matching anchor configuration. Panels are titled by the assay actually
measured, with the mislabelled upstream alias named underneath.

    PYTHONPATH=src python scripts/plot_tlr.py \
        --results ../_oligoal_work/out/tlr-eval.json \
        --output docs/figures/tlr-immunomodulation-predictors.png
"""

import argparse
import json
import statistics as st
from pathlib import Path

INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e5e4e0", "#fcfcfb"
ARMS = (
    ("gp_onehot_base", "Gaussian\nprocess", "#1f5fa9"),
    ("rf_onehot_base", "Random\nforest", "#b3561d"),
)
TITLES = {
    "Alharbi_2020_1": "TLR8 potentiation",
    "Alharbi_2020_2": "TLR7 inhibition",
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

    endpoints = json.loads(args.results.read_text())["endpoints"]
    rng = np.random.default_rng(0)  # jitter only; never touches a reported number
    fig, axes = plt.subplots(
        1,
        len(endpoints),
        figsize=(9.6, 5.2),
        dpi=160,
        facecolor=SURFACE,
        sharey=True,
        gridspec_kw={"wspace": 0.08},
    )
    for ax, (name, endpoint) in zip(axes, endpoints.items(), strict=True):
        style(ax)
        for position, (arm, label, color) in enumerate(ARMS):
            series = np.array([r[arm]["pearson_r"] for r in endpoint["runs"]])
            ax.scatter(
                position + rng.uniform(-0.12, 0.12, len(series)),
                series,
                s=17,
                color=color,
                alpha=0.45,
                linewidths=0,
                zorder=2,
            )
            mean, low, high = mean_ci(series)
            ax.plot(
                [position - 0.28, position + 0.28],
                [mean, mean],
                color=color,
                lw=2.4,
                zorder=3,
            )
            ax.plot([position, position], [low, high], color=color, lw=2.4, zorder=3)
            ax.annotate(
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
            published = endpoint["summary"][arm].get("published_mean")
            if published is not None:
                ax.plot(
                    [position - 0.4, position + 0.4],
                    [published] * 2,
                    color=MUTED,
                    lw=1.4,
                    ls=(0, (4, 3)),
                    zorder=4,
                )
                ax.annotate(
                    f"published {published:.3f}",
                    (position + 0.3, published),
                    color=MUTED,
                    fontsize=8.5,
                    va="center",
                )
        ax.set_xticks(range(len(ARMS)))
        ax.set_xticklabels([label for _, label, _ in ARMS], fontsize=9.5, color=MUTED)
        ax.set_xlim(-0.6, len(ARMS) - 0.1)
        ax.set_title(
            TITLES[name],
            color=INK,
            fontsize=12,
            fontweight="demibold",
            loc="left",
            pad=24,
        )
        ax.annotate(
            f"{name}, published as '{endpoint['published_alias']}'",
            xy=(0, 1),
            xycoords="axes fraction",
            xytext=(0, 8),
            textcoords="offset points",
            color=MUTED,
            fontsize=8.5,
            va="bottom",
        )
    axes[0].set_ylabel("Held-out Pearson r", color=MUTED, fontsize=10)
    fig.text(
        0.008,
        0.015,
        "192 ASOs per assay, official nucleobase split, 30 seeds, about 42 "
        "held-out rows each. Bars: mean with 95% t interval for the mean; "
        "points: one split each. Upstream's registry key is swapped relative to "
        "the assay description; panels name the assay measured.",
        color=MUTED,
        fontsize=8,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, bbox_inches="tight", facecolor=SURFACE)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
