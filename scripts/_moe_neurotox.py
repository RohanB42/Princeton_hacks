"""Shared loader for the MOE acute-neurotox ASO endpoint (MOE_Neurotox_1).

Mirrors ``_huesken.py``: repo observations for the pool, upstream ``Dataset`` for the
official ``nucleobase`` split and the labels. Labels come from the upstream Dataset
(identical row order to the vendored file, asserted below) and never enter
Observation records. Requires the pinned upstream OligoGym environment.

Endpoint caveats, repeated wherever a number from here is reported:
  * ``y`` is a 3h functional-observational-battery score in mice rounded to eight
    ordinal categories (0 safe .. 7 toxic), modelled as regression. Pearson on an
    eight-level ordinal is reported alongside Spearman, which the dataset metadata
    recommends.
  * Rows were scraped from thirteen patents, so expect selection effects: companies
    patent the sequences that worked.
  * 2,437 rows over 13 targets; chemistry is PS/PO 2'-MOE gapmer, the chemistry the
    design agent is constrained to, which is why this endpoint replaced cytotox LNA.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/oligogym/MOE_Neurotox_1_processed"
SPLIT = dict(test_size=0.2, n_clusters=8, kmer=True, kmer_max=3, strand="RNA1")


def load():
    import numpy as np
    import pandas as pd
    from oligogym.data import Dataset

    from oligo_engine.data.catalog import Catalog

    observations = Catalog().load("MOE_Neurotox_1").dataset.observations
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
