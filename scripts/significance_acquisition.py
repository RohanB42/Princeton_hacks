"""Paired significance analysis of the four-arm Huesken comparison.

EXPLORATORY: the question "does uncertainty beat random?" arose after the seeds in
the suite had been inspected, so tests on those same seeds cannot be confirmatory.
Unit of analysis is the seed (matched split, initial set, predictor); every test is
paired against random for the same seed. Reported per predictor and per family:
paired t-test, exact Wilcoxon signed-rank, bootstrap 95% CI of the mean paired
difference (10,000 resamples, fixed seed) and Cohen's dz, with Holm correction within
the stated family. P-values describe these seeds on this dataset, not new endpoints.

    python scripts/significance_acquisition.py --suite artifacts/acquisition-huesken \
        --output artifacts/acquisition-huesken-significance.json
"""

import argparse
import json
from pathlib import Path

from analyze_acquisition import ARMS, BUDGETS, curve, load_runs

NOT_REACHED = 1050  # right-censored: beyond the 1,000-label cap
MARGIN = 0.03
CHALLENGERS = ("uncertainty", "diversity", "uncertainty_then_diversity")


def paired_tests(diffs):
    import numpy as np
    from scipy import stats

    d = np.asarray(diffs, dtype=float)
    t = stats.ttest_1samp(d, 0.0)
    try:
        w = stats.wilcoxon(d, method="exact")
        w_p = float(w.pvalue)
    except ValueError:
        w_p = None
    rng = np.random.default_rng(0)
    boots = rng.choice(d, size=(10000, len(d)), replace=True).mean(axis=1)
    sd = d.std(ddof=1)
    return {
        "n": len(d),
        "mean_diff": float(d.mean()),
        "sd_diff": float(sd),
        "cohens_dz": float(d.mean() / sd) if sd > 0 else None,
        "ci95_bootstrap": [
            float(np.quantile(boots, 0.025)),
            float(np.quantile(boots, 0.975)),
        ],
        "t_p": float(t.pvalue),
        "wilcoxon_exact_p": w_p,
        "n_positive": int((d > 0).sum()),
    }


def holm(entries, key):
    """Holm step-down adjustment of ``entries[i][key]`` in place as ``<key>_holm``."""
    pairs = sorted(((e[key], i) for i, e in enumerate(entries) if e[key] is not None))
    running = 0.0
    for rank, (p, i) in enumerate(pairs):
        running = max(running, min(1.0, (len(pairs) - rank) * p))
        entries[i][f"{key}_holm"] = running


def first_reaching(run, target):
    return next(
        (n for n, r in sorted(curve(run).items()) if r is not None and r >= target),
        NOT_REACHED,
    )


def analyze(runs):
    seeds = sorted(set.intersection(*(set(runs[a]) for a in ARMS)))
    ref = {s: runs["random"][s]["full_pool_metrics"]["pearson_r"] for s in seeds}
    area = {a: [runs[a][s]["normalized_pearson_aulc"] for s in seeds] for a in ARMS}
    out = {
        "seeds": seeds,
        "primary_aulc_vs_random": [],
        "budgets": [],
        "labels": [],
        "pairwise": [],
    }
    for arm in CHALLENGERS:
        diffs = [a - b for a, b in zip(area[arm], area["random"], strict=True)]
        out["primary_aulc_vs_random"].append({"arm": arm, **paired_tests(diffs)})
    for budget in BUDGETS:
        for arm in CHALLENGERS:
            diffs = [
                curve(runs[arm][s])[budget] - curve(runs["random"][s])[budget]
                for s in seeds
            ]
            out["budgets"].append({"arm": arm, "budget": budget, **paired_tests(diffs)})
    for arm in CHALLENGERS:
        labels = {
            a: [first_reaching(runs[a][s], ref[s] - MARGIN) for s in seeds]
            for a in (arm, "random")
        }
        diffs = [r - c for r, c in zip(labels["random"], labels[arm], strict=True)]
        both = [
            d
            for d, r, c in zip(diffs, labels["random"], labels[arm], strict=True)
            if r < NOT_REACHED and c < NOT_REACHED
        ]
        out["labels"].append(
            {
                "arm": arm,
                "metric": "labels saved vs random to reach own reference - 0.03",
                "censoring": f"not reached coded {NOT_REACHED}",
                "seeds_not_reached": {
                    a: sum(v == NOT_REACHED for v in labels[a]) for a in labels
                },
                **paired_tests(diffs),
                "sensitivity_only_seeds_reached_by_both": paired_tests(both)
                if len(both) > 2
                else None,
            }
        )
    for a, b in (
        ("uncertainty", "diversity"),
        ("uncertainty", "uncertainty_then_diversity"),
    ):
        diffs = [x - y for x, y in zip(area[a], area[b], strict=True)]
        out["pairwise"].append({"contrast": f"{a} minus {b}", **paired_tests(diffs)})
    for family in ("primary_aulc_vs_random", "budgets", "labels", "pairwise"):
        for key in ("t_p", "wilcoxon_exact_p"):
            holm(out[family], key)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous reports")
    report = {}
    for predictor in ("gp", "rf"):
        runs, failed = load_runs(args.suite, predictor)
        if failed:
            raise ValueError(f"Failed runs present: {failed}")
        report[predictor] = analyze(runs)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for predictor, r in report.items():
        print(f"== {predictor} primary: AULC minus random (paired, Holm over 3)")
        for e in r["primary_aulc_vs_random"]:
            print(
                f"  {e['arm']:28s} diff {e['mean_diff']:+.4f} ci [{e['ci95_bootstrap'][0]:+.4f},{e['ci95_bootstrap'][1]:+.4f}] "
                f"dz {e['cohens_dz']:.2f} t_p {e['t_p']:.4f} (holm {e['t_p_holm']:.4f}) "
                f"wilcoxon_p {e['wilcoxon_exact_p']:.4f} (holm {e['wilcoxon_exact_p_holm']:.4f}) +{e['n_positive']}/10"
            )


if __name__ == "__main__":
    main()
