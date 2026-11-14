"""Summarize and plot the frozen four-arm Huesken comparison.

Reads ``<suite>/<predictor>/<arm>/run-seed-N.json`` written by
run_acquisition_comparison.py. Reports per-arm Pearson at fixed budgets, paired
normalized-AULC differences against random, label-efficiency counts, and writes
summary.json, summary.csv (table view) and one learning-curve PNG per predictor.
Dispersion is sample SD, not a confidence interval. Undefined Pearson values are
never replaced; failed or missing runs are listed.

    python scripts/analyze_acquisition.py --suite artifacts/acquisition-huesken \
        --output artifacts/acquisition-huesken-report
"""

import argparse
import csv
import json
import statistics as st
from pathlib import Path

ARMS = ("random", "uncertainty", "diversity", "uncertainty_then_diversity")
LABELS = {
    "random": "Random",
    "uncertainty": "Uncertainty",
    "diversity": "Diversity",
    "uncertainty_then_diversity": "Uncertainty + diversity",
}
# Slots 1-3 of the validated categorical palette; random is the recessive baseline.
COLORS = {
    "random": "#6b6a66",
    "uncertainty": "#2a78d6",
    "diversity": "#eb6834",
    "uncertainty_then_diversity": "#1baf7a",
}
BUDGETS = (100, 200, 300, 500, 750, 1000)
EFFICIENCY_MARGIN = 0.03


def mean_sd(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0, "mean": None, "sd": None}
    return {
        "n": len(values),
        "mean": st.mean(values),
        "sd": st.stdev(values) if len(values) > 1 else None,
    }


def load_runs(suite: Path, predictor: str):
    runs = {arm: {} for arm in ARMS}
    failed = []
    for arm in ARMS:
        folder = suite / predictor / arm
        for path in sorted(folder.glob("run-seed-*.json")):
            run = json.loads(path.read_text())
            runs[arm][run["config"]["seed"]] = run
        failed += [str(p.relative_to(suite)) for p in folder.glob("*.FAILED.txt")]
    return runs, failed


def curve(run):
    return {c["labels_used"]: c["metrics"]["pearson_r"] for c in run["checkpoints"]}


def summarize(runs):
    seeds = sorted(set.intersection(*(set(runs[a]) for a in ARMS)))
    out = {"seeds": seeds, "arms": {}}
    reference = {s: runs["random"][s]["full_pool_metrics"]["pearson_r"] for s in seeds}
    out["full_pool_reference_r"] = mean_sd(list(reference.values()))
    random_area = {s: runs["random"][s]["normalized_pearson_aulc"] for s in seeds}
    for arm in ARMS:
        area = {s: runs[arm][s]["normalized_pearson_aulc"] for s in seeds}
        diffs = {
            s: None
            if area[s] is None or random_area[s] is None
            else area[s] - random_area[s]
            for s in seeds
        }
        efficiency = []
        for s in seeds:
            hit = next(
                (
                    n
                    for n, r in sorted(curve(runs[arm][s]).items())
                    if r is not None and r >= reference[s] - EFFICIENCY_MARGIN
                ),
                None,
            )
            efficiency.append(hit)
        reached = [h for h in efficiency if h is not None]
        out["arms"][arm] = {
            "pearson_at_budget": {
                str(b): mean_sd([curve(runs[arm][s]).get(b) for s in seeds])
                for b in BUDGETS
            },
            "normalized_aulc": mean_sd(list(area.values())),
            "aulc_minus_random": {
                **mean_sd(list(diffs.values())),
                "seeds_better_than_random": sum(
                    d is not None and d > 0 for d in diffs.values()
                ),
                "per_seed": diffs,
            },
            "reached_reference_minus_0.03": {
                "seeds_reached": len(reached),
                "of": len(seeds),
                "median_labels_when_reached": st.median(reached) if reached else None,
            },
            "reached_absolute_0.60": {
                "seeds_reached": sum(
                    runs[arm][s]["labels_to_threshold"] is not None for s in seeds
                ),
                "of": len(seeds),
            },
        }
    return out


def plot(runs, summary, predictor, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    seeds = summary["seeds"]
    ink, muted, grid = "#0b0b0b", "#52514e", "#e5e4e0"
    fig, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(8.6, 7.4),
        dpi=160,
        facecolor="#fcfcfb",
        sharex=True,
        gridspec_kw={"height_ratios": [3, 2], "hspace": 0.12},
    )
    counts = sorted(curve(runs["random"][seeds[0]]))
    for arm in ARMS:
        mean = [st.mean(curve(runs[arm][s])[n] for s in seeds) for n in counts]
        top.plot(counts, mean, color=COLORS[arm], linewidth=2, label=LABELS[arm])
        if arm == "random":
            continue
        diffs = [
            [curve(runs[arm][s])[n] - curve(runs["random"][s])[n] for s in seeds]
            for n in counts
        ]
        centre = [st.mean(d) for d in diffs]
        spread = [st.stdev(d) if len(d) > 1 else 0.0 for d in diffs]
        bottom.fill_between(
            counts,
            [c - e for c, e in zip(centre, spread, strict=True)],
            [c + e for c, e in zip(centre, spread, strict=True)],
            color=COLORS[arm],
            alpha=0.10,
            linewidth=0,
        )
        bottom.plot(counts, centre, color=COLORS[arm], linewidth=2)
    ref = summary["full_pool_reference_r"]["mean"]
    top.axhline(ref, color=muted, linewidth=1, linestyle=(0, (2, 3)))
    top.text(
        55, ref + 0.006, f"All-data reference r = {ref:.3f}", color=muted, fontsize=9
    )
    bottom.axhline(0, color=muted, linewidth=1)
    top.set_title(
        f"Huesken siRNA efficacy, {predictor.upper()} predictor, nucleobase split: "
        f"{len(seeds)} matched seeds",
        color=ink,
        fontsize=11,
        loc="left",
    )
    top.set_ylabel("Held-out Pearson r (mean)", color=muted, fontsize=10)
    bottom.set_ylabel(
        "r minus random, same seed\n(mean ± sample SD)", color=muted, fontsize=10
    )
    bottom.set_xlabel("Labels revealed", color=muted, fontsize=10)
    top.set_xlim(40, 1020)
    top.set_ylim(0.26, 0.65)
    for ax in (top, bottom):
        ax.set_facecolor("#fcfcfb")
        ax.grid(axis="y", color=grid, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(grid)
        ax.tick_params(colors=muted, labelsize=9)
    top.legend(frameon=False, fontsize=9, loc="lower right", labelcolor=ink)
    fig.savefig(destination, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output exists; preserve previous reports")
    args.output.mkdir(parents=True, exist_ok=True)
    report, rows = {}, []
    for predictor in ("gp", "rf"):
        runs, failed = load_runs(args.suite, predictor)
        summary = summarize(runs)
        summary["failed_runs"] = failed
        summary["runs_found"] = {arm: len(runs[arm]) for arm in ARMS}
        report[predictor] = summary
        plot(runs, summary, predictor, args.output / f"learning-curves-{predictor}.png")
        for arm in ARMS:
            a = summary["arms"][arm]
            rows.append(
                [
                    predictor,
                    arm,
                    len(summary["seeds"]),
                    *(f"{a['pearson_at_budget'][str(b)]['mean']:.3f}" for b in BUDGETS),
                    f"{a['normalized_aulc']['mean']:.4f}",
                    f"{a['aulc_minus_random']['mean']:+.4f}",
                    a["aulc_minus_random"]["seeds_better_than_random"],
                    a["reached_reference_minus_0.03"]["seeds_reached"],
                    a["reached_absolute_0.60"]["seeds_reached"],
                ]
            )
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    with (args.output / "summary.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["predictor", "arm", "seeds"]
            + [f"r@{b}" for b in BUDGETS]
            + [
                "aulc",
                "aulc_minus_random",
                "seeds_better_than_random",
                "seeds_reached_ref_minus_0.03",
                "seeds_reached_0.60",
            ]
        )
        writer.writerows(rows)
    print(json.dumps({p: report[p]["runs_found"] for p in report}))


if __name__ == "__main__":
    main()
