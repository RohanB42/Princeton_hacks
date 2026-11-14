"""Leave-one-target-out transfer: does an endpoint reward survive an unseen gene?

Every endpoint model here is fitted on a handful of targets (efficacy 5, neurotox
13, TLR 4). The design surface is asked about whatever gene a user types, and an RL
policy would optimise against these models for exactly such a gene. The question
this script answers is therefore the one that decides whether a reward model is
usable: **held out an entire target, does the prediction still rank its ASOs?**

This is an exploratory readiness check, run after the endpoint studies were frozen.
It is not a benchmark comparison and it has no published counterpart: the published
benchmark never ran a target split on any of these datasets.

    PYTHONPATH=src python scripts/reward_transfer_check.py \
        --output ../_oligoal_work/out/reward-transfer.json
"""

import argparse
import collections
import json
from pathlib import Path

MIN_TEST_ROWS = 30


def endpoints():
    """Each endpoint's rows, labels and featurizer, matching its deployment model."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _asoptimizer import (
        MATCHED_BASES,
        MATCHED_MAX_LENGTH,
        MATCHED_PHOSPHATES,
        MATCHED_SUGARS,
        matched_indices,
    )
    from _asoptimizer import load as aso_load
    from _moe_neurotox import load as moe_load

    from oligo_engine.features.upstream import (
        MODIFIED_BASE_ALPHABET,
        MOE_NEUROTOX_MAX_SEQUENCE_LENGTH,
        PHOSPHATE_ALPHABET,
        SUGAR_ALPHABET,
        OneHotBaseFeaturizer,
    )

    _, observations, labels = moe_load()
    yield (
        "neurotox_moe",
        "within-distribution nucleobase reference 0.597",
        list(observations),
        labels,
        OneHotBaseFeaturizer(
            MOE_NEUROTOX_MAX_SEQUENCE_LENGTH,
            component_alphabets={
                "base": MODIFIED_BASE_ALPHABET,
                "sugar": SUGAR_ALPHABET,
                "phosphate": PHOSPHATE_ALPHABET,
            },
        ),
    )

    _, observations, labels = aso_load()
    keep = matched_indices(observations)
    yield (
        "efficacy_aso",
        "within-distribution nucleobase reference 0.317",
        [observations[i] for i in keep],
        labels[keep],
        OneHotBaseFeaturizer(
            MATCHED_MAX_LENGTH,
            component_alphabets={
                "base": MATCHED_BASES,
                "sugar": MATCHED_SUGARS,
                "phosphate": MATCHED_PHOSPHATES,
            },
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous results")

    import numpy as np
    from scipy.stats import pearsonr, spearmanr

    from oligo_engine.models.baseline import OneHotGaussianProcess

    results = {}
    for key, reference, observations, labels, featurizer in endpoints():
        targets = np.array([o.target_id for o in observations])
        counts = collections.Counter(targets)
        folds = []
        for target in sorted(counts, key=lambda t: -counts[t]):
            test = np.where(targets == target)[0]
            train = np.where(targets != target)[0]
            if len(test) < MIN_TEST_ROWS:
                folds.append(
                    {"target": target, "n_test": int(len(test)), "skipped": True}
                )
                continue
            model = OneHotGaussianProcess(0, featurizer=featurizer)
            model.fit(tuple(observations[i] for i in train), tuple(labels[train]))
            predicted = np.array(
                [p.mean for p in model.predict(tuple(observations[i] for i in test))]
            )
            folds.append(
                {
                    "target": target,
                    "n_test": int(len(test)),
                    "n_train": int(len(train)),
                    "pearson_r": float(pearsonr(labels[test], predicted)[0]),
                    "spearman_rho": float(spearmanr(labels[test], predicted).statistic),
                }
            )
            print(f"{key:14s} {target:12s} r {folds[-1]['pearson_r']:+.3f}", flush=True)
        scored = [f for f in folds if "pearson_r" in f]
        results[key] = {
            "within_distribution_reference": reference,
            "held_out_targets": len(scored),
            "mean_pearson_r": float(np.mean([f["pearson_r"] for f in scored])),
            "mean_spearman_rho": float(np.mean([f["spearman_rho"] for f in scored])),
            "negative_folds": sum(1 for f in scored if f["pearson_r"] < 0),
            "folds": folds,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({k: v["mean_pearson_r"] for k, v in results.items()}, indent=2))


if __name__ == "__main__":
    main()
