"""Metadata-only V3 readiness audit. No dose-response outcomes are read."""

import hashlib
import json

import numpy as np
import pandas as pd

from oligo_engine.experimental_rl.cohort import Atlas
from oligo_engine.reward.chemistry import parse_helm

KEYS = [
    "USPTO ID",
    "gene",
    "compound",
    "cell_line",
    "cell_line_species",
    "transfection_method",
    "treatment_period_hrs",
]
CONTEXT = [
    "USPTO ID",
    "Table Number",
    "target_RNA",
    "HELM Annotation",
    "dosage_nm",
    "cell_line",
    "cell_line_species",
    "transfection_method",
    "treatment_period_hrs",
]


def normalize_context(rows: pd.DataFrame) -> pd.DataFrame:
    rows = rows.copy()
    for key in ("cell_line", "cell_line_species", "transfection_method"):
        rows[key] = rows[key].str.strip().str.casefold()
    return rows


def linkage_audit(atlas: Atlas) -> dict:
    meta = normalize_context(atlas.metadata()[0])
    path = atlas.root / "release/dose_response.parquet"
    audit = json.loads((atlas.root / "cleaned/audit.json").read_text())
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != audit["endpoints"]["dose_response"]["source_sha256"]:
        raise ValueError("Dose-response hash mismatch")
    raw = pd.read_parquet(path, columns=CONTEXT)
    rows = int(len(raw))
    raw = (
        raw.dropna()
        .loc[
            lambda df: (
                df.dosage_nm.gt(0)
                & np.isfinite(df.dosage_nm)
                & df.treatment_period_hrs.gt(0)
                & np.isfinite(df.treatment_period_hrs)
            )
        ]
        .copy()
    )
    by_helm = {}
    for raw_helm in raw["HELM Annotation"].unique():
        try:
            by_helm[raw_helm] = parse_helm(raw_helm).identity
        except ValueError:
            continue
    raw["gene"] = raw.target_RNA.str.strip().str.upper()
    raw["compound"] = raw["HELM Annotation"].map(by_helm)
    raw = normalize_context(raw.dropna(subset=["compound"]))
    raw = raw.loc[
        raw.cell_line.ne("")
        & raw.transfection_method.ne("")
        & raw.cell_line_species.eq("human")
    ]
    curves = raw.groupby([*KEYS, "Table Number"]).dosage_nm.nunique().reset_index()
    curves = curves.loc[curves.dosage_nm.ge(4)].drop(columns="dosage_nm")
    merged = (
        meta[KEYS + ["Table Number"]]
        .drop_duplicates()
        .merge(curves, on=KEYS, suffixes=("_screen", "_curve"))
    )
    matched = merged.loc[merged["Table Number_screen"].ne(merged["Table Number_curve"])]
    counts = matched.groupby(["gene", "USPTO ID"]).compound.nunique()
    qualifying = counts.loc[counts.ge(20)]
    return {
        "dose_response_source_sha256": digest,
        "dose_rows": rows,
        "human_curves_with_four_distinct_positive_doses": len(curves),
        "matched_distinct_compounds": int(matched.compound.nunique()),
        "distinct_matching_target_patent_groups": len(counts),
        "target_patent_groups_with_at_least_20": len(qualifying),
        "groups": [
            {"target": target, "patent": patent, "linked_compounds": int(n)}
            for (target, patent), n in counts.items()
        ],
        "planning_floor": {"distinct_compounds": 200, "groups_with_at_least_20": 5},
        "metadata_only": True,
        "curve_fit_and_independent_assay_verification": "pending",
        "gate_passed": False,
    }
