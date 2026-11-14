"""Lossless provenance and label-blind eligibility/campaign construction."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .chemistry import parse_helm

CONTEXT = [
    "USPTO ID",
    "Table Number",
    "target_RNA",
    "cell_line",
    "cell_line_species",
    "transfection_method",
    "treatment_period_hrs",
    "dosage_nm",
]
SOURCE_SHA = "447426f598d3c1763efd0eb31786cc8fdf3daecbcf594c5aa96a95964c367e7f"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stable_id(values: list) -> str:
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, default=str).encode()
    ).hexdigest()[:24]


def prepare(root: Path) -> tuple[pd.DataFrame, dict]:
    path = root / "release/in_vitro_inhibition.parquet"
    if sha(path) != SOURCE_SHA:
        raise ValueError("Atlas release checksum mismatch")
    f = pd.read_parquet(path)
    f["source_row_id"] = [f"in_vitro_inhibition:{i}" for i in range(len(f))]
    audit = {
        "source_sha256": SOURCE_SHA,
        "source_rows": len(f),
        "steps": {},
        "parse_errors": {},
    }
    mask = (
        f["HELM Annotation"].notna()
        & f["USPTO ID"].notna()
        & np.isfinite(f.Inhibition_pct)
    )
    mask &= np.isfinite(f.dosage_nm) & f.dosage_nm.gt(0)
    f = f[mask].copy()
    audit["steps"]["finite_positive_dose"] = len(f)
    mask = f[CONTEXT].notna().all(axis=1)
    for c in ["target_RNA", "cell_line", "cell_line_species", "transfection_method"]:
        mask &= f[c].astype(str).str.strip().ne("")
    f = f[mask].copy()
    audit["steps"]["complete_campaign_metadata"] = len(f)
    parsed = {}
    for h in f["HELM Annotation"].unique():
        try:
            parsed[h] = parse_helm(h)
        except ValueError as e:
            key = str(e)
            audit["parse_errors"][key] = audit["parse_errors"].get(key, 0) + 1
    f = f[f["HELM Annotation"].isin(parsed)].copy()
    # RNase-H-relevant primary chemistry: DNA/MOE/cEt, with at least one DNA base.
    f["chemistry"] = [parsed[h] for h in f["HELM Annotation"]]
    f = f[
        [
            set(c.sugars) <= {"DNA", "MOE", "cEt"} and "DNA" in c.sugars
            for c in f.chemistry
        ]
    ].copy()
    audit["steps"]["supported_gapmer_chemistry"] = len(f)
    f["target_key"] = f.target_RNA.astype(str).str.strip().str.upper()
    f["natural_rna"] = [c.natural_rna for c in f.chemistry]
    f["compound_key"] = [c.identity for c in f.chemistry]
    f["campaign_id"] = [
        stable_id(v) for v in f[CONTEXT].itertuples(index=False, name=None)
    ]
    f["assay_key"] = [stable_id([c, k]) for c, k in zip(f.campaign_id, f.compound_key)]
    counts = f.groupby("assay_key").size()
    f["source_group_rows"] = f.assay_key.map(counts)
    # Select the first immutable source row, not the max outcome or mean of labels.
    f = f.drop_duplicates("assay_key", keep="first").reset_index(drop=True)
    audit["steps"]["one_source_measurement_per_compound_campaign"] = len(f)
    summary = (
        f.groupby(["campaign_id", "target_key", "USPTO ID"], sort=True)
        .agg(compounds=("compound_key", "nunique"), bases=("natural_rna", "nunique"))
        .reset_index()
    )
    audit["campaigns"] = summary.to_dict("records")
    audit["target_mapping"] = "strip/uppercase only; no verified gene alias resolution"
    audit["cohort_targets"] = int(f.target_key.nunique())
    audit["cohort_patents"] = int(f["USPTO ID"].nunique())
    audit["cohort_id"] = stable_id(f.source_row_id.tolist())
    return f, audit
