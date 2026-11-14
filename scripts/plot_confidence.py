"""Confidence-interval figures for a matched-seed acquisition suite.

Intervals are two-sided 95% Student-t intervals for the MEAN across seeds (not the
seed-to-seed spread). They are pointwise and uncorrected: use the Holm-adjusted
p-values in significance_acquisition.py for multiplicity. Two figures:

* learning-curves-ci: mean Pearson r per arm with 95% CI, and the paired difference
  from random (same seed) with 95% CI.
* effects-ci: normalized-AULC difference and labels saved versus random, with 95% CI
  and the unadjusted paired t-test p-value.

    python scripts/plot_confidence.py --suite artifacts/acquisition-confirmatory \
        --predictor gp --output artifacts/confirmatory-ci
"""

import argparse
import statistics as st
from pathlib import Path

from analyze_acquisition import ARMS, COLORS, LABELS, curve, load_runs
from significance_acquisition import MARGIN, NOT_REACHED, first_reaching

CHALLENGERS = ("uncertainty", "diversity", "uncertainty_then_diversity")
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e5e4e0", "#fcfcfb"


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


def curves_figure(runs, seeds, predictor, destination, reference):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(8.6, 7.4),
        dpi=160,
        facecolor=SURFACE,
        sharex=True,
        gridspec_kw={"height_ratios": [3, 2], "hspace": 0.12},
    )
    counts = sorted(curve(runs["random"][seeds[0]]))
    for arm in ARMS:
        stats = [mean_ci([curve(runs[arm][s])[n] for s in seeds]) for n in counts]
        top.fill_between(
            counts,
            [x[1] for x in stats],
            [x[2] for x in stats],
            color=COLORS[arm],
            alpha=0.18,
            linewidth=0,
        )
        top.plot(
            counts,
            [x[0] for x in stats],
            color=COLORS[arm],
            linewidth=2,
            label=LABELS[arm],
        )
        if arm == "random":
            continue
        diffs = [
            mean_ci(
                [curve(runs[arm][s])[n] - curve(runs["random"][s])[n] for s in seeds]
            )
            for n in counts[1:]
        ]
        bottom.fill_between(
            counts[1:],
            [x[1] for x in diffs],
            [x[2] for x in diffs],
            color=COLORS[arm],
            alpha=0.15,
            linewidth=0,
        )
        bottom.plot(counts[1:], [x[0] for x in diffs], color=COLORS[arm], linewidth=2)
    top.axhline(reference, color=MUTED, linewidth=1, linestyle=(0, (2, 3)))
    top.text(
        55,
        reference + 0.006,
        f"All-data reference r = {reference:.3f}",
        color=MUTED,
        fontsize=9,
    )
    bottom.axhline(0, color=MUTED, linewidth=1)
    top.set_title(
        f"Huesken siRNA efficacy, {predictor.upper()} predictor, nucleobase split, "
        f"{len(seeds)} seeds: mean with 95% CI",
        color=INK,
        fontsize=11,
        loc="left",
    )
    top.set_ylabel("Held-out Pearson r", color=MUTED, fontsize=10)
    bottom.set_ylabel(
        "r minus random, same seed\n(mean with 95% CI)", color=MUTED, fontsize=10
    )
    bottom.set_xlabel("Labels revealed", color=MUTED, fontsize=10)
    top.set_xlim(40, 1020)
    top.set_ylim(0.20, 0.66)
    style(top)
    style(bottom)
    top.legend(frameon=False, fontsize=9, loc="lower right", labelcolor=INK)
    fig.savefig(destination, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def effects_figure(runs, seeds, predictor, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import stats

    reference = {s: runs["random"][s]["full_pool_metrics"]["pearson_r"] for s in seeds}
    rows = {"aulc": [], "labels": []}
    for arm in CHALLENGERS:
        aulc = [
            runs[arm][s]["normalized_pearson_aulc"]
            - runs["random"][s]["normalized_pearson_aulc"]
            for s in seeds
        ]
        saved = [
            first_reaching(runs["random"][s], reference[s] - MARGIN)
            - first_reaching(runs[arm][s], reference[s] - MARGIN)
            for s in seeds
        ]
        rows["aulc"].append((arm, *mean_ci(aulc), stats.ttest_1samp(aulc, 0).pvalue))
        rows["labels"].append(
            (arm, *mean_ci(saved), stats.ttest_1samp(saved, 0).pvalue)
        )
    fig, axes = plt.subplots(
        1, 2, figsize=(9.6, 3.6), dpi=160, facecolor=SURFACE, sharey=True
    )
    titles = {
        "aulc": "Accuracy: normalized AULC minus random",
        "labels": "Label efficiency: labels saved vs random",
    }
    for ax, key in zip(axes, ("aulc", "labels"), strict=True):
        for i, (arm, mean, low, high, p) in enumerate(rows[key]):
            ax.plot([low, high], [i, i], color=COLORS[arm], linewidth=2.5)
            ax.plot(
                mean,
                i,
                "o",
                color=COLORS[arm],
                markersize=8,
                markeredgecolor=SURFACE,
                markeredgewidth=2,
            )
            fmt = "{:+.4f}" if key == "aulc" else "{:+.0f}"
            shown = "p < 0.001" if p < 0.001 else f"p = {p:.3f}"
            ax.annotate(
                f"{fmt.format(mean)}  ({shown})",
                (high, i),
                xytext=(8, 0),
                textcoords="offset points",
                color=INK,
                fontsize=9,
                va="center",
            )
        ax.axvline(0, color=MUTED, linewidth=1)
        ax.set_yticks(range(len(CHALLENGERS)))
        ax.set_yticklabels([LABELS[a] for a in CHALLENGERS], color=INK, fontsize=9)
        ax.set_ylim(len(CHALLENGERS) - 0.4, -0.6)
        low_all = min(r[2] for r in rows[key])
        high_all = max(r[3] for r in rows[key])
        pad = 0.55 * (high_all - low_all)
        ax.set_xlim(min(low_all, 0) - 0.15 * (high_all - low_all), high_all + pad)
        ax.set_title(titles[key], color=INK, fontsize=10, loc="left")
        ax.set_xlabel(
            "Mean difference with 95% CI (unadjusted p, paired t-test)",
            color=MUTED,
            fontsize=9,
        )
        ax.set_facecolor(SURFACE)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=9, left=False)
    fig.suptitle(
        f"{predictor.upper()} predictor, {len(seeds)} seeds, nucleobase split. "
        f"Not reached coded {NOT_REACHED}.",
        color=MUTED,
        fontsize=9,
        x=0.01,
        ha="left",
    )
    fig.tight_layout()
    fig.savefig(destination, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--predictor", default="gp")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output exists; preserve previous figures")
    args.output.mkdir(parents=True, exist_ok=True)
    runs, failed = load_runs(args.suite, args.predictor)
    if failed:
        raise ValueError(f"Failed runs present: {failed}")
    seeds = sorted(set.intersection(*(set(runs[a]) for a in ARMS)))
    reference = st.mean(
        runs["random"][s]["full_pool_metrics"]["pearson_r"] for s in seeds
    )
    curves_figure(
        runs, seeds, args.predictor, args.output / "learning-curves-ci.png", reference
    )
    rows = effects_figure(runs, seeds, args.predictor, args.output / "effects-ci.png")
    for key, entries in rows.items():
        for arm, mean, low, high, p in entries:
            print(f"{key:7s} {arm:27s} {mean:+.4f} [{low:+.4f}, {high:+.4f}] p={p:.4f}")


if __name__ == "__main__":
    main()
