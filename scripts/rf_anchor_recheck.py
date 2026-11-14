"""Re-check every RF anchor against the configuration upstream actually ran.

`benchmarks/train_model.py` filters model arguments through
``inspect.signature(RandomForestModel).parameters.keys()``, which is
``(task, n_estimators, model_kwargs)``. **max_depth is therefore dropped**, and every
published RF row labelled ``max_depth: 10/20/30`` trained with scikit-learn's default
of unlimited depth. Our endpoint studies passed ``max_depth=20`` straight to the
model, where it does apply, so those anchor comparisons were not like-for-like.

This script re-runs each anchor under both settings on the same seeds, so each study
can be corrected with a measured number rather than an assumption.

    PYTHONPATH=src python scripts/rf_anchor_recheck.py \
        --output ../_oligoal_work/out/rf-anchor-recheck.json
"""

import argparse
import json
import statistics as st
from pathlib import Path

from _asoptimizer import FULL_BASES, FULL_PHOSPHATES, FULL_SUGARS
from evaluate_neurotox_moe import metrics

# dataset -> (loader module, encoding, max length, alphabets, published mean, fold SD,
#             seed range)
ANCHORS = {
    "MOE_Neurotox_1": {
        "study": "docs/neurotox-moe-predictor.md",
        "encoding": "chem",
        "max_length": 19,
        "published": 0.5394446486358492,
        "published_fold_sd": 0.1186,
        "seeds": (200, 230),
    },
    "Alharbi_2020_1": {
        "study": "docs/tlr-immunomodulation-predictors.md",
        "encoding": "base",
        "max_length": 20,
        "published": 0.6589731299267072,
        "published_fold_sd": 0.0501,
        "seeds": (300, 330),
    },
    "Alharbi_2020_2": {
        "study": "docs/tlr-immunomodulation-predictors.md",
        "encoding": "base",
        "max_length": 20,
        "published": 0.5896102197450284,
        "published_fold_sd": 0.0778,
        "seeds": (300, 330),
    },
    "Hwang_2024_1": {
        "study": "docs/aso-efficacy-predictor.md",
        "encoding": "full",
        "max_length": 25,
        "published": 0.4093881682092161,
        "published_fold_sd": 0.0656,
        "seeds": (400, 410),
    },
}


def featurizer_for(spec):
    from oligo_engine.features.upstream import (
        BASE_ALPHABET,
        MODIFIED_BASE_ALPHABET,
        PHOSPHATE_ALPHABET,
        SUGAR_ALPHABET,
        OneHotBaseFeaturizer,
    )

    if spec["encoding"] == "base":
        return OneHotBaseFeaturizer(spec["max_length"], BASE_ALPHABET)
    if spec["encoding"] == "chem":
        return OneHotBaseFeaturizer(
            spec["max_length"],
            component_alphabets={
                "base": MODIFIED_BASE_ALPHABET,
                "sugar": SUGAR_ALPHABET,
                "phosphate": PHOSPHATE_ALPHABET,
            },
        )
    return OneHotBaseFeaturizer(
        spec["max_length"],
        component_alphabets={
            "base": FULL_BASES,
            "sugar": FULL_SUGARS,
            "phosphate": FULL_PHOSPHATES,
        },
    )


def load_for(name):
    if name == "MOE_Neurotox_1":
        from _moe_neurotox import load, split
    elif name.startswith("Alharbi"):
        from _tlr import load as tlr_load
        from _tlr import split

        def load():
            return tlr_load(name)
    else:
        from _asoptimizer import load, split
    return load, split


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous results")

    import numpy as np

    from oligo_engine.models.baseline import OneHotRandomForest

    results = {}
    for name, spec in ANCHORS.items():
        load, split = load_for(name)
        data, observations, y = load()
        per_depth = {}
        for label, depth in (("depth_20_ours", 20), ("unlimited_upstream", None)):
            values = []
            for seed in range(*spec["seeds"]):
                train, test = split(data, seed)
                model = OneHotRandomForest(
                    seed, max_depth=depth, featurizer=featurizer_for(spec)
                )
                model.fit(tuple(observations[i] for i in train), tuple(y[train]))
                predicted = np.array(
                    [
                        p.mean
                        for p in model.predict(tuple(observations[i] for i in test))
                    ]
                )
                values.append(metrics(y[test], predicted)["pearson_r"])
            mean, sd = st.mean(values), st.stdev(values)
            combined_se = float(
                np.sqrt(sd**2 / len(values) + spec["published_fold_sd"] ** 2 / 5)
            )
            per_depth[label] = {
                "effective_max_depth": depth,
                "seeds": len(values),
                "mean_pearson_r": mean,
                "sample_sd": sd,
                "gap": mean - spec["published"],
                "combined_se": combined_se,
                "gap_in_combined_se": (mean - spec["published"]) / combined_se,
            }
            print(
                f"{name:18s} {label:20s} r {mean:.4f} +- {sd:.4f} "
                f"gap {mean - spec['published']:+.4f}",
                flush=True,
            )
        results[name] = {
            "study": spec["study"],
            "published_mean": spec["published"],
            "published_fold_sd": spec["published_fold_sd"],
            "note": (
                "Upstream's benchmark filtered max_depth out of the model arguments, "
                "so the published row ran with unlimited depth whatever its label."
            ),
            "by_depth": per_depth,
            "depth_effect": (
                per_depth["unlimited_upstream"]["mean_pearson_r"]
                - per_depth["depth_20_ours"]["mean_pearson_r"]
            ),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({k: v["depth_effect"] for k, v in results.items()}, indent=2))


if __name__ == "__main__":
    main()
