"""Multi-seed Gate 1 re-test of the frozen Huesken (siRNA1) baseline configs.

Runs the frozen linear and Random Forest configurations from
configs/reproduce-*.toml on many nucleobase-split seeds and compares the local
mean with the published 5-fold mean using a noise-aware test. Mirrors
oligo_engine.reproduce; only the seed list differs. Requires the pinned upstream
OligoGym environment (see docs/upstream-verification.md and
docs/gate1-resolution.md), not the core project environment.

    python scripts/gate1_multiseed.py --output artifacts/gate1-30seed.json
"""

import argparse
import json
import math
import statistics as st
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data/oligogym/Ichihara_2007_1_processed"
SPLIT = dict(test_size=0.2, n_clusters=8, kmer=True, kmer_max=3, strand="RNA1")
REFERENCE = {"linear": 0.6158645398542795, "rf": 0.5910367239114824}
TOLERANCE = 0.03


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=30)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous results")

    import numpy as np
    import pandas as pd
    from oligogym.data import Dataset
    from oligogym.features import KMersCounts, OneHotEncoder
    from oligogym.models import LinearModel, RandomForestModel
    from scipy.stats import pearsonr

    data = Dataset(json.loads(DATA.with_suffix(".json").read_text()))
    data.build(dataframe=pd.read_csv(f"{DATA}.csv.gz", compression="gzip"))
    configs = {
        "linear": (
            lambda: KMersCounts(k=[1, 2, 3], modification_abundance=True),
            lambda seed: LinearModel(type="standard"),
        ),
        "rf": (
            lambda: OneHotEncoder(encode_components=["base"]),
            lambda seed: RandomForestModel(
                n_estimators=100, max_depth=20, random_state=seed, n_jobs=2
            ),
        ),
    }
    results = {}
    for name, (make_features, make_model) in configs.items():
        values = []
        for seed in range(args.seeds):
            np.random.seed(seed)
            x_tr, x_te, y_tr, y_te, _, _ = data.split(
                "nucleobase", random_state=seed, return_index=True, **SPLIT
            )
            features = make_features()
            a, b = features.fit_transform(x_tr), features.transform(x_te)
            if a.ndim == 3:
                a, b = a.reshape(len(x_tr), -1), b.reshape(len(x_te), -1)
            model = make_model(seed)
            model.fit(a, y_tr)
            pred = np.asarray(model.predict(b)).reshape(-1)
            values.append(float(pearsonr(np.asarray(y_te).reshape(-1), pred)[0]))
            print(name, seed, round(values[-1], 4), flush=True)
        mean, sd = st.mean(values), st.stdev(values)
        # Upstream's reference is a mean of 5 unseeded folds, so it has its own error.
        se = math.sqrt(sd**2 / len(values) + sd**2 / 5)
        gap = mean - REFERENCE[name]
        results[name] = {
            "seed_pearson_r": values,
            "local_mean": mean,
            "local_sample_sd": sd,
            "published_mean": REFERENCE[name],
            "gap": gap,
            "combined_se": se,
            "z": gap / se,
            "within_tolerance": abs(gap) <= TOLERANCE,
            "within_2_se": abs(gap / se) <= 2,
        }
        print(f"{name}: mean={mean:.4f} sd={sd:.4f} gap={gap:+.4f} z={gap / se:+.2f}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
