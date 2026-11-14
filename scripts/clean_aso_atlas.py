"""Lossless, audited preparation of the pinned ASO Atlas 2.0 release."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE = Path("data/aso_atlas_2/release")
DEST = Path("data/aso_atlas_2/cleaned")
ENDPOINTS = ("in_vitro_inhibition", "dose_response", "hepatotoxicity", "neurotoxicity")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def clean() -> dict:
    DEST.mkdir(parents=True, exist_ok=True)
    expected = json.loads((SOURCE / "upstream_manifest.json").read_text())
    audit = {
        "source_repository": "https://github.com/barneyhill/aso-atlas-2",
        "source_code_revision": "bb90c946013f183379da04678340e193088e5f99",
        "release_tag": "neurips-rebuttal",
        "license": "CC BY 4.0",
        "rules_version": 1,
        "endpoints": {},
        "folds": {},
    }
    all_molecules = {}
    for name in ENDPOINTS:
        path = SOURCE / f"{name}.parquet"
        frame = pd.read_parquet(path)
        original_columns = list(frame.columns)
        assert len(frame) == expected["configs"][name]["rows"]
        assert (
            int(frame["model_eligible"].sum())
            == (expected["configs"][name]["model_eligible_rows"])
        )
        helm = frame["HELM Annotation"].astype("string").str.strip()
        has_helm = helm.notna() & helm.ne("")
        mismatch = frame["model_eligible"].astype(bool) != has_helm
        if mismatch.any():
            raise ValueError(f"{name}: upstream eligibility differs from nonempty HELM")
        # Preserve every source column and row, including nulls, outliers and repeats.
        frame.insert(0, "source_row_id", [f"{name}:{i}" for i in range(len(frame))])
        frame["exact_helm_sha256"] = [
            hashlib.sha256(str(x).encode()).hexdigest() if pd.notna(x) else None
            for x in frame["HELM Annotation"]
        ]
        frame["has_resolved_helm"] = has_helm.astype(bool)
        frame["has_uncertain_chemistry_marker"] = helm.str.contains(
            "?", regex=False, na=False
        ).astype(bool)
        frame["has_helm_frame"] = helm.str.startswith("RNA1{", na=False).astype(
            bool
        ) & helm.str.endswith("$$$$", na=False).astype(bool)
        frame["has_patent_id"] = frame["USPTO ID"].notna() & frame["USPTO ID"].astype(
            "string"
        ).str.strip().ne("")
        frame["has_target_name"] = frame["target_RNA"].notna() & frame[
            "target_RNA"
        ].astype("string").str.strip().ne("")
        if name in ("in_vitro_inhibition", "dose_response"):
            y = pd.to_numeric(frame["Inhibition_pct"], errors="coerce")
            dose = pd.to_numeric(frame["dosage_nm"], errors="coerce")
            frame["finite_endpoint"] = np.isfinite(y)
            frame["valid_dose"] = np.isfinite(dose) & dose.ge(0)
            frame["out_of_0_100_inhibition"] = np.isfinite(y) & ((y < 0) | (y > 100))
            frame["has_cell_line"] = frame["cell_line"].notna() & frame[
                "cell_line"
            ].astype("string").str.strip().ne("")
            frame["analysis_eligible"] = (
                frame["has_resolved_helm"]
                & frame["has_patent_id"]
                & frame["finite_endpoint"]
                & frame["valid_dose"]
            )
        elif name == "neurotoxicity":
            frame["finite_endpoint"] = frame["FOB_score"].map(
                lambda value: isinstance(value, (list, np.ndarray))
                and any(np.isfinite(float(item)) for item in value if item is not None)
            )
            frame["valid_dose"] = np.isfinite(
                pd.to_numeric(frame["dosage_ug"], errors="coerce")
            ) & pd.to_numeric(frame["dosage_ug"], errors="coerce").ge(0)
            frame["analysis_eligible"] = (
                frame["has_resolved_helm"]
                & frame["has_patent_id"]
                & frame["finite_endpoint"]
            )
        else:
            biomarkers = ["ALT", "AST", "ALB", "BUN", "CREA", "TBIL", "PC_ratio"]
            frame["finite_endpoint"] = frame[biomarkers].apply(
                lambda row: any(
                    isinstance(v, (list, np.ndarray))
                    and any(np.isfinite(float(n)) for n in v if n is not None)
                    for v in row
                ),
                axis=1,
            )
            frame["valid_dose"] = np.isfinite(
                pd.to_numeric(frame["dosage_mg_per_kg"], errors="coerce")
            ) & pd.to_numeric(frame["dosage_mg_per_kg"], errors="coerce").ge(0)
            frame["analysis_eligible"] = (
                frame["has_resolved_helm"]
                & frame["has_patent_id"]
                & frame["finite_endpoint"]
            )
        output = DEST / f"{name}.parquet"
        frame.to_parquet(output, index=False)
        replay = pd.read_parquet(output)
        if len(replay) != len(frame) or not replay["source_row_id"].is_unique:
            raise ValueError(f"{name}: failed lossless row audit")
        for column in original_columns:
            if not frame[column].equals(replay[column]):
                raise ValueError(f"{name}: source column changed: {column}")
        for key in frame.loc[frame["has_resolved_helm"], "exact_helm_sha256"]:
            all_molecules.setdefault(key, set()).add(name)
        audit["endpoints"][name] = {
            "source_file": path.name,
            "source_sha256": sha(path),
            "cleaned_sha256": sha(output),
            "rows_source": len(frame),
            "rows_cleaned": len(replay),
            "upstream_model_eligible": int(frame["model_eligible"].sum()),
            "analysis_eligible": int(frame["analysis_eligible"].sum()),
            "unresolved_helm": int((~frame["has_resolved_helm"]).sum()),
            "uncertain_chemistry_marker": int(
                frame["has_uncertain_chemistry_marker"].sum()
            ),
            "resolved_without_expected_helm_frame": int(
                (frame["has_resolved_helm"] & ~frame["has_helm_frame"]).sum()
            ),
            "missing_patent": int((~frame["has_patent_id"]).sum()),
            "missing_target_name": int((~frame["has_target_name"]).sum()),
            "missing_or_nonfinite_endpoint": int((~frame["finite_endpoint"]).sum()),
            "invalid_or_missing_dose": int((~frame["valid_dose"]).sum()),
            "unique_exact_helm": int(frame["exact_helm_sha256"].nunique()),
            "exact_repeated_helm_rows": int(
                frame["exact_helm_sha256"].duplicated(keep=False).sum()
            ),
        }
        if "out_of_0_100_inhibition" in frame:
            audit["endpoints"][name]["out_of_0_100_inhibition_preserved"] = int(
                frame["out_of_0_100_inhibition"].sum()
            )
        if "has_cell_line" in frame:
            audit["endpoints"][name]["missing_cell_line"] = int(
                (~frame["has_cell_line"]).sum()
            )
    for path in sorted((SOURCE / "folds").glob("*.csv.gz")):
        fold = pd.read_csv(path)
        audit["folds"][path.name] = {
            "rows": len(fold),
            "sha256": sha(path),
            "fold_values": sorted(fold["fold"].dropna().astype(int).unique().tolist()),
        }
    audit["unique_exact_helm_all_endpoints"] = len(all_molecules)
    audit["exact_helm_in_multiple_endpoints"] = sum(
        len(v) > 1 for v in all_molecules.values()
    )
    (DEST / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    print(json.dumps(clean()["endpoints"], indent=2))
