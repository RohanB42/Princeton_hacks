"""Evaluate baseline predictors and diagnose their uncertainty on Huesken (siRNA1).

Every number is labelled with its split (official OligoGym ``nucleobase`` split,
8 k-mer clusters, test_size 0.2). Models: one-hot RF and one-hot GP (this repo's
Predictor contract) plus the upstream in-grid anchor (KMersCounts k=1-3 + standard
LinearModel). Reports, per seed: Pearson/RMSE/MAE/runtime, uncertainty spread over
test candidates, rank agreement between uncertainty and absolute error, interval
coverage, and a nearest-training-siRNA identity leakage check.

    PYTHONPATH=src python scripts/evaluate_predictors.py \
        --seeds 100 130 --output artifacts/predictor-eval.json
"""

import argparse
import json
import re
import statistics as st
import time
from pathlib import Path

from _huesken import load, split

PUBLISHED = {"linear_kmers": 0.6158645398542795, "rf_onehot": 0.5910367239114824}
IDENTITY_BINS = (0.0, 0.6, 0.75, 0.9, 1.0001)


def strand_codes(observations, indices):
    """RNA1 base codes (T treated as U) for positional-identity comparison."""
    import numpy as np

    table = {"A": 0, "C": 1, "G": 2, "U": 3, "T": 3}
    rows = []
    for i in indices:
        block = observations[i].sequence.split("|RNA2")[0]
        rows.append([table[b] for b in re.findall(r"[rd]\((\w)\)", block)])
    return np.asarray(rows)


def max_identity(test_codes, train_codes, max_shift=5):
    """Best ungapped RNA1 identity to any training siRNA over small register shifts."""
    import numpy as np

    length = test_codes.shape[1]
    best = np.zeros(len(test_codes))
    for shift in range(-max_shift, max_shift + 1):
        if shift >= 0:
            a, b = test_codes[:, shift:], train_codes[:, : length - shift]
        else:
            a, b = test_codes[:, : length + shift], train_codes[:, -shift:]
        same = (a[:, None, :] == b[None, :, :]).mean(axis=2)
        best = np.maximum(best, same.max(axis=1))
    return best


def spread(values):
    import numpy as np

    v = np.asarray(values, dtype=float)
    q = np.quantile(v, [0.05, 0.5, 0.95])
    return {
        "min": float(v.min()),
        "p05": float(q[0]),
        "median": float(q[1]),
        "p95": float(q[2]),
        "max": float(v.max()),
        "cv": float(v.std() / v.mean()) if v.mean() > 0 else None,
        "n_unique_6dp": int(len(set(np.round(v, 6)))),
    }


def metrics(truth, pred):
    import numpy as np
    from scipy.stats import pearsonr

    truth, pred = np.asarray(truth), np.asarray(pred)
    return {
        "pearson_r": float(pearsonr(truth, pred)[0]),
        "rmse": float(np.sqrt(np.mean((truth - pred) ** 2))),
        "mae": float(np.mean(np.abs(truth - pred))),
    }


def uncertainty_report(sd, error, features_train, features_test):
    import numpy as np
    from scipy.stats import spearmanr
    from sklearn.metrics import pairwise_distances

    sd, error = np.asarray(sd), np.abs(np.asarray(error))
    nearest = pairwise_distances(features_test, features_train).min(axis=1)
    return {
        "spread": spread(sd),
        "spearman_sd_vs_abs_error": float(spearmanr(sd, error)[0]),
        "spearman_sd_vs_nearest_train_distance": float(spearmanr(sd, nearest)[0]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs=2, default=[100, 130])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-rf", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous results")

    import numpy as np
    from oligogym.features import KMersCounts
    from oligogym.models import LinearModel

    from oligo_engine.models.baseline import OneHotGaussianProcess, OneHotRandomForest

    data, observations, y = load()
    runs = []
    for seed in range(*args.seeds):
        train, test = split(data, seed)
        obs_train = tuple(observations[i] for i in train)
        obs_test = tuple(observations[i] for i in test)
        y_train, y_test = y[train], y[test]
        run = {"seed": seed, "split": "nucleobase", "n_train": len(train)}
        run["n_test"] = len(test)

        gp = OneHotGaussianProcess(seed)
        started = time.perf_counter()
        gp.fit(obs_train, tuple(y_train))
        parts = gp.predict_components(obs_test)
        elapsed = time.perf_counter() - started
        features_train = gp.featurizer.transform(obs_train)
        features_test = gp.featurizer.transform(obs_test)
        error = parts["mean"] - y_test
        run["gp_onehot"] = {
            **metrics(y_test, parts["mean"]),
            "runtime_s": elapsed,
            "fitted_kernel": gp.fitted_kernel,
            "noise_sd": parts["noise_sd"],
            "latent_sd": uncertainty_report(
                parts["latent_sd"], error, features_train, features_test
            ),
            "total_sd_spread": spread(parts["total_sd"]),
            "coverage_1sd_total": float(np.mean(np.abs(error) <= parts["total_sd"])),
            "coverage_196sd_total": float(
                np.mean(np.abs(error) <= 1.96 * parts["total_sd"])
            ),
        }
        run["_gp_pred"] = parts["mean"].tolist()

        if not args.skip_rf:
            rf = OneHotRandomForest(seed)
            started = time.perf_counter()
            rf.fit(obs_train, tuple(y_train))
            preds = rf.predict(obs_test)
            elapsed = time.perf_counter() - started
            means = np.array([p.mean for p in preds])
            run["rf_onehot"] = {
                **metrics(y_test, means),
                "runtime_s": elapsed,
                "tree_sd": uncertainty_report(
                    [p.uncertainty for p in preds],
                    means - y_test,
                    features_train,
                    features_test,
                ),
            }

        started = time.perf_counter()
        featurizer = KMersCounts(k=[1, 2, 3], modification_abundance=True)
        a = featurizer.fit_transform([o.sequence for o in obs_train])
        b = featurizer.transform([o.sequence for o in obs_test])
        linear = LinearModel(type="standard")
        try:
            linear.fit(a, y_train)
        except np.linalg.LinAlgError as error:
            # Upstream's unregularized least squares is rank-deficient on this
            # representation; record the failure, never drop or impute the seed.
            run["linear_kmers"] = {"error": f"LinAlgError: {error}"}
        else:
            lin_pred = np.asarray(linear.predict(b)).reshape(-1)
            run["linear_kmers"] = {
                **metrics(y_test, lin_pred),
                "runtime_s": time.perf_counter() - started,
            }

        identity = max_identity(
            strand_codes(observations, test), strand_codes(observations, train)
        )
        run["max_identity_to_train"] = spread(identity)
        run["_identity"] = identity.tolist()
        run["_truth"] = y_test.tolist()
        runs.append(run)
        print(
            seed,
            {
                k: round(run[k]["pearson_r"], 3)
                for k in run
                if isinstance(run[k], dict) and "pearson_r" in run[k]
            },
            "latent_sd range",
            round(run["gp_onehot"]["latent_sd"]["spread"]["min"], 2),
            round(run["gp_onehot"]["latent_sd"]["spread"]["max"], 2),
            flush=True,
        )

    summary = {}
    for name in ("gp_onehot", "rf_onehot", "linear_kmers"):
        ok = [r[name] for r in runs if name in r and "error" not in r[name]]
        failed = [r["seed"] for r in runs if name in r and "error" in r[name]]
        values = [m["pearson_r"] for m in ok]
        if not values:
            continue
        mean, sd = st.mean(values), (st.stdev(values) if len(values) > 1 else None)
        entry = {
            "split": "nucleobase",
            "seeds": len(values),
            "failed_seeds": failed,
            "mean_pearson_r": mean,
            "sample_sd": sd,
            "mean_rmse": st.mean(m["rmse"] for m in ok),
            "mean_runtime_s": st.mean(m["runtime_s"] for m in ok),
        }
        if name in PUBLISHED and sd is not None:
            ref = PUBLISHED[name]
            entry.update(
                published_mean=ref,
                gap=mean - ref,
                published_within_mean_pm_sd=bool(mean - sd <= ref <= mean + sd),
            )
        summary[name] = entry
    pooled_identity = np.concatenate([r["_identity"] for r in runs])
    pooled_truth = np.concatenate([r["_truth"] for r in runs])
    pooled_pred = np.concatenate([r["_gp_pred"] for r in runs])
    bins = []
    for low, high in zip(IDENTITY_BINS[:-1], IDENTITY_BINS[1:], strict=True):
        mask = (pooled_identity >= low) & (pooled_identity < high)
        bins.append(
            {
                "identity_range": [low, min(high, 1.0)],
                "n_test_rows": int(mask.sum()),
                "gp_pearson_r": float(
                    np.corrcoef(pooled_truth[mask], pooled_pred[mask])[0, 1]
                )
                if mask.sum() > 2
                else None,
            }
        )
    for run in runs:
        for key in ("_gp_pred", "_identity", "_truth"):
            run.pop(key)
    result = {"summary": summary, "identity_bins_gp": bins, "runs": runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"summary": summary, "identity_bins_gp": bins}, indent=2))


if __name__ == "__main__":
    main()
