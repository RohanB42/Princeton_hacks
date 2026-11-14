"""Evaluate ASO knockdown efficacy predictors on ASOptimizer (``Hwang_2024_1``).

Two arms of the same study, because they answer different questions:

* ``--scope matched`` (default): the 5,586 rows whose chemistry matches the design
  surface's ps_moe_gapmer space. GP and RF, one-hot base+sugar+phosphate at 20
  positions. This is the model the surface uses, and it has **no published anchor**,
  because the published runs used the whole heterogeneous dataset.
* ``--scope full``: the whole 32,602-row dataset with widened local alphabets, RF
  only (a GP on 26k training rows is not tractable), to reproduce the published
  anchor of 0.4094 for the same configuration.

Every number is on the official OligoGym ``nucleobase`` split (8 k-mer clusters,
test_size 0.2), mean over the requested seeds with sample SD. No target split is run
or claimed: the matched subset has five targets.

    PYTHONPATH=src python scripts/evaluate_aso_efficacy.py --scope matched \
        --seeds 400 430 --output ../_oligoal_work/out/aso-efficacy-matched.json
"""

import argparse
import json
import statistics as st
import time
from pathlib import Path

from _asoptimizer import (
    FULL_BASES,
    FULL_MAX_LENGTH,
    FULL_PHOSPHATES,
    FULL_SUGARS,
    MATCHED_BASES,
    MATCHED_MAX_LENGTH,
    MATCHED_PHOSPHATES,
    MATCHED_SUGARS,
    load,
    matched_indices,
    split,
    subset_dataset,
)
from evaluate_neurotox_moe import metrics
from evaluate_predictors import uncertainty_report

# Published nucleobase mean for RF, one-hot base+sugar+phosphate, depth 20, 100
# trees, on the whole dataset (five unseeded folds).
PUBLISHED_FULL_RF = (0.4093881682092161, 0.0656)
PUBLISHED_BEST_FULL = (0.4792, "CNN, one-hot base+sugar+phosphate")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("matched", "full"), default="matched")
    parser.add_argument("--seeds", type=int, nargs=2, default=[400, 430])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous results")

    import numpy as np

    from oligo_engine.features.upstream import OneHotBaseFeaturizer
    from oligo_engine.models.baseline import OneHotGaussianProcess, OneHotRandomForest

    data, observations, y = load()
    if args.scope == "matched":
        indices = matched_indices(observations)
        data = subset_dataset(indices)
        observations = [observations[i] for i in indices]
        y = y[indices]
        alphabets = {
            "base": MATCHED_BASES,
            "sugar": MATCHED_SUGARS,
            "phosphate": MATCHED_PHOSPHATES,
        }
        max_length = MATCHED_MAX_LENGTH
        arms = ("gp_chem", "rf_chem")
    else:
        alphabets = {
            "base": FULL_BASES,
            "sugar": FULL_SUGARS,
            "phosphate": FULL_PHOSPHATES,
        }
        max_length = FULL_MAX_LENGTH
        arms = ("rf_chem",)

    sequences = [o.sequence for o in observations]
    runs = []
    for seed in range(*args.seeds):
        train, test = split(data, seed)
        obs_train = tuple(observations[i] for i in train)
        obs_test = tuple(observations[i] for i in test)
        y_train, y_test = y[train], y[test]
        shared = {sequences[i] for i in train} & {sequences[i] for i in test}
        run = {
            "seed": seed,
            "n_train": len(train),
            "n_test": len(test),
            # Half the rows repeat a sequence; a split that separated them would
            # leak. Recorded per seed rather than assumed.
            "sequences_on_both_sides": len(shared),
        }
        if shared:
            raise ValueError(f"seed {seed}: {len(shared)} sequences leak across split")

        featurizer = OneHotBaseFeaturizer(max_length, component_alphabets=alphabets)
        features_train = featurizer.transform(obs_train)
        features_test = featurizer.transform(obs_test)

        for arm in arms:
            factory = (
                OneHotGaussianProcess if arm.startswith("gp") else (OneHotRandomForest)
            )
            model = factory(seed, featurizer=featurizer)
            started = time.perf_counter()
            model.fit(obs_train, tuple(y_train))
            if arm.startswith("gp"):
                parts = model.predict_components(obs_test)
                means, spread = parts["mean"], parts["latent_sd"]
                extra = {"fitted_kernel": model.fitted_kernel}
            else:
                predictions = model.predict(obs_test)
                means = np.array([p.mean for p in predictions])
                spread = np.array([p.uncertainty for p in predictions])
                extra = {}
            run[arm] = {
                **metrics(y_test, means),
                **extra,
                "runtime_s": time.perf_counter() - started,
                "n_features": featurizer.n_features,
                "uncertainty": uncertainty_report(
                    spread, means - y_test, features_train, features_test
                ),
            }
        runs.append(run)
        print(
            seed,
            {a: round(run[a]["pearson_r"], 3) for a in arms},
            flush=True,
        )

    summary = {}
    for arm in arms:
        values = [r[arm]["pearson_r"] for r in runs]
        mean, sd = st.mean(values), st.stdev(values)
        entry = {
            "scope": args.scope,
            "seeds": len(values),
            "mean_pearson_r": mean,
            "sample_sd": sd,
            "mean_spearman_rho": st.mean(r[arm]["spearman_rho"] for r in runs),
            "mean_rmse": st.mean(r[arm]["rmse"] for r in runs),
            "mean_runtime_s": st.mean(r[arm]["runtime_s"] for r in runs),
        }
        if args.scope == "full" and arm == "rf_chem":
            reference, fold_sd = PUBLISHED_FULL_RF
            combined_se = float(np.sqrt(sd**2 / len(values) + fold_sd**2 / 5))
            entry.update(
                published_mean=reference,
                published_fold_sd=fold_sd,
                gap=mean - reference,
                combined_se=combined_se,
                gap_in_combined_se=(mean - reference) / combined_se,
            )
        summary[arm] = entry

    result = {
        "dataset": "Hwang_2024_1",
        "benchmark_alias": "asoptimizer_cleaned",
        "endpoint": "percentage inhibition of target mRNA vs untreated control",
        "scope": args.scope,
        "rows": len(observations),
        "label_mean": float(np.mean(y)),
        "label_sd": float(np.std(y)),
        "published_best_full_dataset": PUBLISHED_BEST_FULL,
        "summary": summary,
        "runs": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
