"""Evaluate one-hot GP/RF predictors on the MOE acute-neurotox ASO endpoint.

Every number is on the official OligoGym ``nucleobase`` split (8 k-mer clusters,
test_size 0.2) of ``MOE_Neurotox_1``. Protocol is frozen in
``docs/neurotox-moe-predictor.md`` before any seed in the reported range is run.

Four arms, two featurizations x two models:

* ``base``: one-hot nucleobase only, alphabet (A, C, G, T, U, m5C), 19 positions.
* ``chem``: base + sugar + phosphate, which spells out the gapmer wing/core layout
  and the PS/PO backbone. Upstream's best configurations on this dataset use the
  same three components, so this is the comparable featurization.

The GP kernel is **not** re-selected here: it is the RBF(4) + White kernel frozen on
Huesken in ``docs/predictor-first-pass.md``. Reusing it avoids a second selection
step on this dataset; the cost is that no kernel is tuned for this endpoint.

Pearson is reported for comparability with the published leaderboard, Spearman
because the label is an eight-level ordinal FOB score and the dataset metadata
recommends it.

    cd scripts && PYTHONPATH=../src python evaluate_neurotox_moe.py \
        --seeds 200 230 --output ../../_oligoal_work/out/neurotox-moe-eval.json
"""

import argparse
import json
import statistics as st
import time
from pathlib import Path

from _moe_neurotox import load, split
from evaluate_predictors import uncertainty_report

# Published nucleobase means for this dataset, from the upstream benchmark CSV
# (45,950 runs, five unseeded folds each). The RF entries are the exact
# max_depth=20 / n_estimators=100 configurations this script runs.
PUBLISHED = {
    "rf_onehot_base": 0.47495694726883586,
    "rf_onehot_chem": 0.5394446486358492,
}
# Best published configuration on this dataset and split, for context only: a
# Transformer over base+sugar+phosphate. Five folds, SD 0.0558.
PUBLISHED_BEST = {
    "model": "Transformer",
    "featurizer": "OneHotEncoder+chem",
    "mean": 0.7025396179890501,
}


def metrics(truth, pred):
    import numpy as np
    from scipy.stats import pearsonr, spearmanr

    truth, pred = np.asarray(truth), np.asarray(pred)
    return {
        "pearson_r": float(pearsonr(truth, pred)[0]),
        "spearman_rho": float(spearmanr(truth, pred)[0]),
        "rmse": float(np.sqrt(np.mean((truth - pred) ** 2))),
        "mae": float(np.mean(np.abs(truth - pred))),
    }


def featurizers():
    from oligo_engine.features.upstream import (
        MODIFIED_BASE_ALPHABET,
        MOE_NEUROTOX_MAX_SEQUENCE_LENGTH,
        PHOSPHATE_ALPHABET,
        SUGAR_ALPHABET,
        OneHotBaseFeaturizer,
    )

    length = MOE_NEUROTOX_MAX_SEQUENCE_LENGTH
    return {
        "base": OneHotBaseFeaturizer(length, MODIFIED_BASE_ALPHABET),
        "chem": OneHotBaseFeaturizer(
            length,
            component_alphabets={
                "base": MODIFIED_BASE_ALPHABET,
                "sugar": SUGAR_ALPHABET,
                "phosphate": PHOSPHATE_ALPHABET,
            },
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs=2, default=[200, 230])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous results")

    import numpy as np

    from oligo_engine.models.baseline import OneHotGaussianProcess, OneHotRandomForest

    data, observations, y = load()
    features = featurizers()
    runs = []
    for seed in range(*args.seeds):
        train, test = split(data, seed)
        obs_train = tuple(observations[i] for i in train)
        obs_test = tuple(observations[i] for i in test)
        y_train, y_test = y[train], y[test]
        run = {
            "seed": seed,
            "split": "nucleobase",
            "n_train": len(train),
            "n_test": len(test),
        }

        for tag, featurizer in features.items():
            x_train = featurizer.transform(obs_train)
            x_test = featurizer.transform(obs_test)

            gp = OneHotGaussianProcess(seed, featurizer=featurizer)
            started = time.perf_counter()
            gp.fit(obs_train, tuple(y_train))
            parts = gp.predict_components(obs_test)
            elapsed = time.perf_counter() - started
            error = parts["mean"] - y_test
            run[f"gp_onehot_{tag}"] = {
                **metrics(y_test, parts["mean"]),
                "runtime_s": elapsed,
                "n_features": featurizer.n_features,
                "fitted_kernel": gp.fitted_kernel,
                "noise_sd": parts["noise_sd"],
                "latent_sd": uncertainty_report(
                    parts["latent_sd"], error, x_train, x_test
                ),
                "coverage_1sd_total": float(
                    np.mean(np.abs(error) <= parts["total_sd"])
                ),
                "coverage_196sd_total": float(
                    np.mean(np.abs(error) <= 1.96 * parts["total_sd"])
                ),
            }

            rf = OneHotRandomForest(seed, featurizer=featurizer)
            started = time.perf_counter()
            rf.fit(obs_train, tuple(y_train))
            preds = rf.predict(obs_test)
            elapsed = time.perf_counter() - started
            means = np.array([p.mean for p in preds])
            run[f"rf_onehot_{tag}"] = {
                **metrics(y_test, means),
                "runtime_s": elapsed,
                "n_features": featurizer.n_features,
                "tree_sd": uncertainty_report(
                    [p.uncertainty for p in preds], means - y_test, x_train, x_test
                ),
            }

        runs.append(run)
        print(
            seed,
            {
                k: round(run[k]["pearson_r"], 3)
                for k in run
                if isinstance(run[k], dict) and "pearson_r" in run[k]
            },
            flush=True,
        )

    summary = {}
    for name in sorted(k for k in runs[0] if k.startswith(("gp_", "rf_"))):
        values = [r[name]["pearson_r"] for r in runs]
        rho = [r[name]["spearman_rho"] for r in runs]
        mean, sd = st.mean(values), (st.stdev(values) if len(values) > 1 else None)
        entry = {
            "split": "nucleobase",
            "seeds": len(values),
            "mean_pearson_r": mean,
            "sample_sd": sd,
            "mean_spearman_rho": st.mean(rho),
            "mean_rmse": st.mean(r[name]["rmse"] for r in runs),
            "mean_runtime_s": st.mean(r[name]["runtime_s"] for r in runs),
            "n_features": runs[0][name]["n_features"],
        }
        if name in PUBLISHED and sd is not None:
            ref = PUBLISHED[name]
            entry.update(
                published_mean=ref,
                gap=mean - ref,
                published_within_mean_pm_sd=bool(mean - sd <= ref <= mean + sd),
            )
        summary[name] = entry

    result = {
        "dataset": "MOE_Neurotox_1",
        "endpoint": "rounded 3h FOB score in mice, 8 ordinal categories, regression",
        "published_best_on_split": PUBLISHED_BEST,
        "summary": summary,
        "runs": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
