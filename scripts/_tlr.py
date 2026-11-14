"""Shared loader for the two Alharbi 2020 TLR immunomodulation endpoints.

Mirrors ``_huesken.py`` and ``_moe_neurotox.py``: repo observations for the pool,
upstream ``Dataset`` for the official ``nucleobase`` split and the labels.

**Upstream key/assay mismatch, resolved 2026-11-14.** The registry
(``all_datasets_info.csv.gz``) has its ``key`` column swapped relative to the assay
descriptions, and the published benchmark aliases follow the key. Resolved from the
data itself and from the source paper, not from the labels:

* ``Alharbi_2020_1`` is the **TLR8 potentiation** assay (its own ``label_desc``:
  HEK293-TLR8, values relative to resiquimod = 1.0). Labels run 0.57-5.44, mean 2.18,
  which only fits a resiquimod = 1.0 normalization. Published alias:
  ``immune_modulation_TLR7`` (median test RMSE 0.889 against a label SD of 1.00).
* ``Alharbi_2020_2`` is the **TLR7 inhibition** assay (HEK293-TLR7, relative to
  resiquimod = 100). Labels run 17.5-126.5, mean 49.8. Published alias:
  ``immune_modulation_TLR8`` (median test RMSE 23.5 against a label SD of 23.08).

Alharbi et al., NAR 2020 (10.1093/nar/gkaa523) report that these ASOs *inhibit* TLR7
and *potentiate* TLR8, which matches the descriptions and the two normalizations.
So the assay descriptions are right and the registry keys are wrong. Report the
assay, never the upstream key, and swap the alias when quoting a published number.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLIT = dict(test_size=0.2, n_clusters=8, kmer=True, kmer_max=3, strand="RNA1")

# name -> (assay actually measured, published benchmark alias, catalog key)
ENDPOINTS = {
    "Alharbi_2020_1": ("TLR8_potentiation", "immune_modulation_TLR7", "TLR7"),
    "Alharbi_2020_2": ("TLR7_inhibition", "immune_modulation_TLR8", "TLR8"),
}


def source(name: str) -> Path:
    return ROOT / f"data/oligogym/{name}_processed"


def load(name: str):
    import numpy as np
    import pandas as pd
    from oligogym.data import Dataset

    from oligo_engine.data.catalog import Catalog

    if name not in ENDPOINTS:
        raise ValueError(f"Unknown TLR endpoint {name!r}; use {list(ENDPOINTS)}")
    path = source(name)
    observations = Catalog().load(name).dataset.observations
    data = Dataset(json.loads(path.with_suffix(".json").read_text()))
    data.build(dataframe=pd.read_csv(f"{path}.csv.gz", compression="gzip"))
    if [o.sequence for o in observations] != list(data.x):
        raise ValueError("Catalog and upstream row order differ")
    return data, observations, np.asarray(data.y, dtype=float).reshape(-1)


def split(data, seed):
    """Official nucleobase split; returns train and test row indices."""
    *_, train_idx, test_idx = data.split(
        "nucleobase", random_state=seed, return_index=True, **SPLIT
    )
    return list(train_idx), list(test_idx)
