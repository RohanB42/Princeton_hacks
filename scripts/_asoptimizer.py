"""Loader for ASOptimizer (``Hwang_2024_1``): ASO knockdown efficacy.

32,602 gapmer ASOs over 18 targets, percentage inhibition of target mRNA relative to
untreated controls, collected from patents and publications. Published benchmark
alias ``asoptimizer_cleaned``.

Two views, for two different jobs:

* ``load()`` - the whole dataset, for reproducing the published anchor. Its chemistry
  is heterogeneous (2'-MOE, cEt, LNA, 2'-OMe, amino sugars; PS, PO and methoxypropyl
  linkages), so the featurizer alphabets are widened **locally here** rather than in
  ``features/upstream.py``, where growing a shared constant would silently change the
  feature width of every other endpoint's fitted model.
* ``load_matched()`` - only rows whose chemistry matches the design surface's
  ``ps_moe_gapmer`` space: 2'-MOE wings over a DNA core, PS or PO backbone,
  unmodified bases, at most 20 monomers. 5,586 rows over 5 targets. This is the
  subset the deployment efficacy model is fitted on, because a model applied outside
  its chemistry is the error this project already corrected once.

Caveats that travel with every number from here:
  * The matched subset has **5 targets**, dominated by DGAT2 (2,536 rows). No target
    split is possible or claimed.
  * 2,638 of 5,586 matched rows repeat a sequence seen in another row (different
    assay, dose or source). The nucleobase split groups by k-mer cluster, so
    identical sequences land on the same side; the run asserts this rather than
    trusting it.
  * Lengths present are 16, 17, 18 and 20. A 19-mer is encodable (shorter sequences
    pad), but 19 itself is absent from training.
  * Patent-sourced, so expect selection effects.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/oligogym/Hwang_2024_1_processed"
SPLIT = dict(test_size=0.2, n_clusters=8, kmer=True, kmer_max=3, strand="RNA1")

# Local, dataset-specific alphabets. Deliberately not added to the shared constants.
FULL_SUGARS = ("d", "r", "m", "moe", "cEt", "lna", "amino")
FULL_PHOSPHATES = ("p", "sp", "mop", "EMPTY")
FULL_BASES = ("A", "C", "G", "T", "U", "m5C")
FULL_MAX_LENGTH = 25

MATCHED_SUGARS = ("d", "moe")
MATCHED_PHOSPHATES = ("p", "sp", "EMPTY")
MATCHED_BASES = ("A", "C", "G", "T", "U")
MATCHED_MAX_LENGTH = 20


def _dataset():
    import pandas as pd
    from oligogym.data import Dataset

    data = Dataset(json.loads(SOURCE.with_suffix(".json").read_text()))
    data.build(dataframe=pd.read_csv(f"{SOURCE}.csv.gz", compression="gzip"))
    return data


def load():
    """Whole dataset, in source order, with labels from the upstream Dataset."""
    import numpy as np

    from oligo_engine.data.catalog import Catalog

    observations = Catalog().load("Hwang_2024_1").dataset.observations
    data = _dataset()
    if [o.sequence for o in observations] != list(data.x):
        raise ValueError("Catalog and upstream row order differ")
    return data, observations, np.asarray(data.y, dtype=float).reshape(-1)


def matched_indices(observations) -> list[int]:
    """Rows inside the ps_moe_gapmer design space of the surface."""
    from oligogym.features import _extract_monomers

    keep = []
    for index, row in enumerate(observations):
        monomers = _extract_monomers(row.sequence)
        if (
            set(monomers["sugar"]) <= set(MATCHED_SUGARS)
            and set(monomers["phosphate"]) <= set(MATCHED_PHOSPHATES)
            and set(monomers["base"]) <= set(MATCHED_BASES)
            and len(monomers["base"]) <= MATCHED_MAX_LENGTH
        ):
            keep.append(index)
    return keep


def split(data, seed):
    """Official nucleobase split over whichever Dataset is passed."""
    *_, train_idx, test_idx = data.split(
        "nucleobase", random_state=seed, return_index=True, **SPLIT
    )
    return list(train_idx), list(test_idx)


def subset_dataset(indices):
    """A Dataset containing only ``indices``, so splits are computed on the subset."""
    import pandas as pd
    from oligogym.data import Dataset

    frame = pd.read_csv(f"{SOURCE}.csv.gz", compression="gzip").iloc[indices]
    data = Dataset(json.loads(SOURCE.with_suffix(".json").read_text()))
    data.build(dataframe=frame.reset_index(drop=True))
    return data
