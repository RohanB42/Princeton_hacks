"""Evaluate one-hot GP/RF predictors on both Alharbi 2020 TLR endpoints.

Two 192-row immunomodulation assays over the same 192 ASOs (4 targets x 48): TLR8
potentiation (``Alharbi_2020_1``) and TLR7 inhibition (``Alharbi_2020_2``). See
``_tlr.py`` for the resolved upstream key/assay mismatch; this script reports the
assay actually measured and carries the published alias alongside it.

Every number is on the official OligoGym ``nucleobase`` split (8 k-mer clusters,
test_size 0.2), mean over the requested seeds with sample SD, not a confidence
interval. The two endpoints are separate tasks and are never pooled: they share
sequences, not units, and ``AGENTS.md`` forbids a combined score.

Representation: one-hot nucleobase only, alphabet (A,C,G,T,U), 20 positions. Sugar
and phosphate are **deliberately not encoded** because they are constant across all
192 rows (every ASO is a 5-10-5 2'OMe gapmer on a full phosphorothioate backbone),
so they can only add zero-variance columns. The script asserts that constancy rather
than assuming it. Note that the base alphabet still carries the gapmer layout
implicitly: the 2'OMe wings use U and the DNA core uses T.

No random split is run. These are mutant screens around a few parent sequences, so a
random split puts near-duplicates on both sides; the published random-split numbers
for these datasets should be read with that in mind.

    PYTHONPATH=src python scripts/evaluate_tlr.py \
        --seeds 300 330 --output ../_oligoal_work/out/tlr-eval.json
"""

import argparse
import json
import statistics as st
import time
from pathlib import Path

from _tlr import ENDPOINTS, SPLIT, load, split
from evaluate_neurotox_moe import metrics
from evaluate_predictors import uncertainty_report

MAX_SEQUENCE_LENGTH = 20
# Published nucleobase means, upstream benchmarks/oligogym_benchmarks.csv, for the
# exact anchor configuration this script runs (RF, one-hot base, depth 20, 100
# trees), keyed by dataset name rather than by the mislabelled upstream alias.
PUBLISHED_RF_BASE = {
    "Alharbi_2020_1": (0.6589731299267072, 0.0501),
    "Alharbi_2020_2": (0.5896102197450284, 0.0778),
}
# Best published nucleobase configuration per dataset, for context only; each is the
# best of 372 configurations and so carries selection bias.
PUBLISHED_BEST = {
    "Alharbi_2020_1": (0.727, "RandomForest, one-hot base, depth 10, 1000 trees"),
    "Alharbi_2020_2": (0.6995, "RandomForest, one-hot base+sugar+phosphate, depth 30"),
}


def check_chemistry_is_constant(observations) -> dict:
    """Confirm sugar/phosphate carry no information before we drop them."""
    from oligogym.features import _extract_monomers

    patterns, backbones = set(), set()
    for row in observations:
        monomers = _extract_monomers(row.sequence)
        patterns.add(tuple(monomers["sugar"]))
        backbones.add(tuple(monomers["phosphate"]))
    if len(patterns) != 1 or len(backbones) != 1:
        raise ValueError(
            "Sugar/phosphate are not constant on this endpoint; the base-only "
            "representation is no longer justified "
            f"({len(patterns)} sugar patterns, {len(backbones)} backbones)"
        )
    (sugar,), (phosphate,) = patterns, backbones
    return {
        "distinct_sugar_patterns": 1,
        "distinct_backbones": 1,
        "sugar_pattern": "".join({"m": "M", "d": "D"}.get(s, "?") for s in sugar),
        "phosphate_symbols": sorted(set(phosphate)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs=2, default=[300, 330])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous results")

    import numpy as np

    from oligo_engine.features.upstream import BASE_ALPHABET, OneHotBaseFeaturizer
    from oligo_engine.models.baseline import OneHotGaussianProcess, OneHotRandomForest

    result = {"endpoints": {}}
    for name, (assay, alias, upstream_key) in ENDPOINTS.items():
        data, observations, y = load(name)
        chemistry = check_chemistry_is_constant(observations)
        runs = []
        for seed in range(*args.seeds):
            train, test = split(data, seed)
            obs_train = tuple(observations[i] for i in train)
            obs_test = tuple(observations[i] for i in test)
            y_train, y_test = y[train], y[test]
            run = {"seed": seed, "n_train": len(train), "n_test": len(test)}

            featurizer = OneHotBaseFeaturizer(MAX_SEQUENCE_LENGTH, BASE_ALPHABET)
            gp = OneHotGaussianProcess(seed, featurizer=featurizer)
            started = time.perf_counter()
            gp.fit(obs_train, tuple(y_train))
            parts = gp.predict_components(obs_test)
            elapsed = time.perf_counter() - started
            features_train = featurizer.transform(obs_train)
            features_test = featurizer.transform(obs_test)
            error = parts["mean"] - y_test
            run["gp_onehot_base"] = {
                **metrics(y_test, parts["mean"]),
                "runtime_s": elapsed,
                "fitted_kernel": gp.fitted_kernel,
                "noise_sd": parts["noise_sd"],
                "latent_sd": uncertainty_report(
                    parts["latent_sd"], error, features_train, features_test
                ),
                "coverage_1sd_total": float(
                    np.mean(np.abs(error) <= parts["total_sd"])
                ),
                "coverage_196sd_total": float(
                    np.mean(np.abs(error) <= 1.96 * parts["total_sd"])
                ),
            }

            rf = OneHotRandomForest(
                seed, featurizer=OneHotBaseFeaturizer(MAX_SEQUENCE_LENGTH)
            )
            started = time.perf_counter()
            rf.fit(obs_train, tuple(y_train))
            preds = rf.predict(obs_test)
            means = np.array([p.mean for p in preds])
            run["rf_onehot_base"] = {
                **metrics(y_test, means),
                "runtime_s": time.perf_counter() - started,
                "tree_sd": uncertainty_report(
                    [p.uncertainty for p in preds],
                    means - y_test,
                    features_train,
                    features_test,
                ),
            }
            runs.append(run)
            print(
                name,
                seed,
                {
                    k: round(run[k]["pearson_r"], 3)
                    for k in run
                    if isinstance(run[k], dict) and "pearson_r" in run[k]
                },
                flush=True,
            )

        summary = {}
        for arm in ("gp_onehot_base", "rf_onehot_base"):
            values = [r[arm]["pearson_r"] for r in runs]
            mean, sd = st.mean(values), st.stdev(values)
            entry = {
                "seeds": len(values),
                "mean_pearson_r": mean,
                "sample_sd": sd,
                "mean_spearman_rho": st.mean(r[arm]["spearman_rho"] for r in runs),
                "mean_rmse": st.mean(r[arm]["rmse"] for r in runs),
                "undefined_or_negative_seeds": sum(1 for v in values if v <= 0),
            }
            if arm == "rf_onehot_base":
                reference, fold_sd = PUBLISHED_RF_BASE[name]
                combined_se = float(np.sqrt(sd**2 / len(values) + fold_sd**2 / 5))
                entry.update(
                    published_mean=reference,
                    published_fold_sd=fold_sd,
                    gap=mean - reference,
                    combined_se=combined_se,
                    gap_in_combined_se=(mean - reference) / combined_se,
                )
            summary[arm] = entry

        best_r, best_config = PUBLISHED_BEST[name]
        result["endpoints"][name] = {
            "assay_measured": assay,
            "published_alias": alias,
            "upstream_key": upstream_key,
            "key_note": "upstream key and assay description disagree; see _tlr.py",
            "split": "nucleobase",
            "split_parameters": dict(SPLIT),
            "chemistry": chemistry,
            "label_mean": float(np.mean(y)),
            "label_sd": float(np.std(y)),
            "published_best": {"mean_pearson_r": best_r, "configuration": best_config},
            "summary": summary,
            "runs": runs,
        }
        print(json.dumps({name: summary}, indent=2), flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
