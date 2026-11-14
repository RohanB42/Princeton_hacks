"""Shared loader for predictor scripts: repo observations + upstream split/labels.

Requires the pinned upstream OligoGym environment. Labels come from the upstream
Dataset (identical row order to the vendored file, asserted below) and never enter
Observation records.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/oligogym/Ichihara_2007_1_processed"
SPLIT = dict(test_size=0.2, n_clusters=8, kmer=True, kmer_max=3, strand="RNA1")


def load():
    import numpy as np
    import pandas as pd
    from oligogym.data import Dataset

    from oligo_engine.data.catalog import Catalog

    observations = Catalog().load("Huesken").dataset.observations
    data = Dataset(json.loads(SOURCE.with_suffix(".json").read_text()))
    data.build(dataframe=pd.read_csv(f"{SOURCE}.csv.gz", compression="gzip"))
    if [o.sequence for o in observations] != list(data.x):
        raise ValueError("Catalog and upstream row order differ")
    return data, observations, np.asarray(data.y, dtype=float).reshape(-1)


def split(data, seed):
    """Official nucleobase split; returns train and test row indices."""
    *_, train_idx, test_idx = data.split(
        "nucleobase", random_state=seed, return_index=True, **SPLIT
    )
    return list(train_idx), list(test_idx)
