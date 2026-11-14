"""Offline, one-time GP kernel selection by train-internal grouped validation.

Preregistered grid: oligo_engine.models.baseline.KERNEL_GRID. Uses seed 0's official
nucleobase TRAINING partition only; its test partition is never read. Validation
folds withhold whole k-mer clusters (GroupKFold), mirroring the evaluation split so
near-duplicate shifted siRNAs do not favor tiny length scales. Selection criterion:
mean fold Pearson r (accuracy only; uncertainty quality is judged separately).
The chosen kernel is frozen; hyperparameters still refit inside every fit() on
revealed labels.

    PYTHONPATH=src python scripts/select_gp_kernel.py --output artifacts/gp-kernel.json
"""

import argparse
import json
import statistics as st
from pathlib import Path

from _huesken import load, split


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous results")

    import numpy as np
    from oligogym.features import KMersCounts
    from scipy.stats import pearsonr
    from sklearn.cluster import KMeans
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import normalize

    from oligo_engine.models.baseline import KERNEL_GRID, OneHotGaussianProcess

    data, observations, y = load()
    train, _unused_test = split(data, args.seed)
    del _unused_test
    sequences = [observations[i].sequence for i in train]
    vectors = normalize(
        np.array(KMersCounts(k=[1, 2, 3]).fit_transform(sequences)), norm="l2"
    )
    groups = KMeans(n_clusters=8, random_state=args.seed).fit(vectors).labels_
    folds = list(GroupKFold(n_splits=5).split(vectors, groups=groups))
    rows = []
    for family, length_scale in KERNEL_GRID:
        scores = []
        for fit_pos, val_pos in folds:
            model = OneHotGaussianProcess(args.seed, family, length_scale)
            model.fit(
                tuple(observations[train[i]] for i in fit_pos),
                tuple(float(y[train[i]]) for i in fit_pos),
            )
            pred = model.predict(tuple(observations[train[i]] for i in val_pos))
            truth = [float(y[train[i]]) for i in val_pos]
            scores.append(float(pearsonr(truth, [p.mean for p in pred])[0]))
        rows.append(
            {
                "family": family,
                "initial_length_scale": length_scale,
                "fold_pearson": scores,
                "mean_pearson": st.mean(scores),
                "sd_pearson": st.stdev(scores),
            }
        )
        print(family, length_scale, round(rows[-1]["mean_pearson"], 4), flush=True)
    best = max(rows, key=lambda r: r["mean_pearson"])
    result = {
        "selection_seed": args.seed,
        "partition": "official nucleobase TRAIN only",
        "validation": "GroupKFold(5) over KMeans(8) k-mer clusters",
        "grid": rows,
        "selected": {k: best[k] for k in ("family", "initial_length_scale")},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("selected", result["selected"])


if __name__ == "__main__":
    main()
