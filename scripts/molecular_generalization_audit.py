"""Outcome-blind target exposure inventory; never assigns uncertified final groups.

This reads explicitly projected metadata, not endpoint values or model scores.
Existing eligibility flags encode historical endpoint availability; that limited
metadata use is declared in the protocol. No candidate is selected by outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

METADATA_COLUMNS = (
    "source_row_id",
    "USPTO ID",
    "Table Number",
    "target_RNA",
    "exact_helm_sha256",
    "analysis_eligible",
    "cell_line",
    "cell_line_species",
    "transfection_method",
    "dosage_nm",
    "treatment_period_hrs",
)
COHORT_COLUMNS = (
    "source_row_id",
    "target_key",
    "USPTO ID",
    "compound_key",
    "natural_rna",
)


def projected_metadata(path: Path, columns: tuple[str, ...]) -> Any:
    """Reject every column outside the fixed metadata allowlist before I/O."""
    allowed = set(METADATA_COLUMNS) | set(COHORT_COLUMNS)
    if not columns or set(columns) - allowed:
        raise ValueError("Only explicitly allowed metadata columns may be read")
    import pyarrow.parquet as pq

    return pq.read_table(path, columns=list(columns)).to_pandas()


def digest(path: Path) -> str:
    """Hash raw bytes for provenance without decoding outcome columns."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_json(path: Path) -> Any:
    """Read existing provenance/configuration, never measured outcome tables."""
    return json.loads(path.read_text())


def write_json(path: Path, value: Any) -> None:
    """Persist deterministic JSON with undefined values disallowed."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def classification(roles: list[str], fit: int, selection: int) -> str:
    """Preserve reserved status and fail closed on uncertified independence."""
    if "historical_reserved" in roles:
        return "reserved_pending_cross_study_certification"
    if roles:
        return "development_exposed_or_designated"
    if fit or selection:
        return "predictor_exposed_policy_candidate_unassigned"
    return "candidate_unassigned_pending_independence_audit"


def crossed_precision(
    groups: int, seeds: int, target_sd: float, seed_sd: float, interaction_sd: float
) -> dict[str, float]:
    """Planning approximation for a paired crossed random-effects mean.

    SDs refer to method DIFFERENCES after averaging regions, not individual runs.
    No estimated outcome variance or significance-based stopping is involved.
    """
    if min(groups, seeds) < 2 or min(target_sd, seed_sd, interaction_sd) < 0:
        raise ValueError("Need >=2 groups/seeds and nonnegative SD assumptions")
    se = math.sqrt(
        target_sd**2 / groups
        + seed_sd**2 / seeds
        + interaction_sd**2 / (groups * seeds)
    )
    return {"se": se, "normal_95_half_width": 1.96 * se, "normal_80_mde": 2.802 * se}


def run(root: Path, preparation: Path, output: Path) -> dict[str, Any]:
    """Audit metadata and memberships under a written, hashed access protocol."""
    paths = {
        "inhibition": root / "data/aso_atlas_2/cleaned/in_vitro_inhibition.parquet",
        "cohort": preparation / "cohort.parquet",
        "historical_manifest": preparation / "manifests.json",
        "policy": root / "artifacts/molecular-policy-repair-v3/config.json",
        "efficacy": root / "artifacts/molecular-design-v1/atlas-ridge-reference.json",
        "risk": root / "artifacts/molecular-design-v1/risk-qualification/model.json",
        "risk_protocol": root
        / "artifacts/molecular-design-v1/risk-qualification/protocol.json",
    }
    output.mkdir(parents=True, exist_ok=True)
    protocol = {
        "schema": "molecular-generalization-metadata-v1",
        "scope": "Metadata and existing membership only; no new scores or outcomes",
        "paths": {k: str(v) for k, v in paths.items()},
        "sha256": {k: digest(v) for k, v in paths.items()},
        "projected_columns": {
            "inhibition": METADATA_COLUMNS,
            "cohort": COHORT_COLUMNS,
        },
        "eligibility": "Existing analysis_eligible flag only; includes availability",
        "target_mapping": "strip/uppercase identity only; NOT verified gene aliases",
        "new_development_designations": ["APOC3", "ANGPTL3"],
        "scope_support": "Prior exact chemistry/context audit found zero matches",
        "final_assignment": "None until alias/family/context/head audits complete",
        "prohibited": ["outcome columns", "prediction scoring", "new fitting"],
    }
    protocol_path = output / "protocol.json"
    if protocol_path.exists() and read_json(protocol_path) != json.loads(
        json.dumps(protocol)
    ):
        raise ValueError("Existing audit protocol differs; use a new output version")
    write_json(protocol_path, protocol)
    seal = digest(protocol_path)
    manifest = read_json(paths["historical_manifest"])
    policy = read_json(paths["policy"])
    efficacy = read_json(paths["efficacy"])
    risk = read_json(paths["risk"])
    risk_protocol = read_json(paths["risk_protocol"])
    raw = projected_metadata(paths["inhibition"], METADATA_COLUMNS)
    cohort = projected_metadata(paths["cohort"], COHORT_COLUMNS)
    metadata = raw.loc[raw.analysis_eligible.fillna(False)].copy()
    metadata["target_key"] = metadata.target_RNA.fillna("").str.strip().str.upper()
    roles: dict[str, set[str]] = defaultdict(set)
    for campaign in policy["campaigns"]:
        roles[campaign["target"]["gene"]].add("policy_" + campaign["partition"])
    for campaign in manifest["campaigns"]:
        roles[campaign["target"]].add("historical_" + campaign["role"])
    for target in ["ATXN2", "CFB", "DGAT2", "FGFR4"]:
        roles[target].add("supported_profile_predictor_fit")
    for target in ["ATXN2", "DGAT2", "SERPINA1"]:
        roles[target].add("supported_profile_measured_assessment_inspected")
    for target in protocol["new_development_designations"]:
        roles[target].add("new_policy_development_designation")
    fit_ids, selection_ids = (
        set(efficacy["training_ids"]),
        set(efficacy["validation_ids"]),
    )
    by_id = cohort.set_index("source_row_id")
    missing_ids = (fit_ids | selection_ids) - set(by_id.index)
    if missing_ids:
        raise ValueError(f"Efficacy membership has {len(missing_ids)} unmapped IDs")
    fitted = cohort[cohort.source_row_id.isin(fit_ids)]
    selected = cohort[cohort.source_row_id.isin(selection_ids)]
    fitted_patents = set(fitted["USPTO ID"])
    fitted_bases = set(fitted.natural_rna)
    transcripts = []
    for path in sorted((root / "artifacts/transcripts").glob("*.json")):
        item = read_json(path)
        transcripts.append(
            {
                "gene": item["gene"],
                "transcript_id": item["transcript_id"],
                "length": len(item["sequence"]),
                "sequence_sha256": hashlib.sha256(
                    item["sequence"].encode()
                ).hexdigest(),
                "source": item["source"],
            }
        )
    context = [
        "USPTO ID",
        "Table Number",
        "target_key",
        "cell_line",
        "cell_line_species",
        "transfection_method",
        "dosage_nm",
        "treatment_period_hrs",
    ]
    campaign_sizes = metadata.groupby(context, dropna=False).exact_helm_sha256.nunique()
    broad_100 = campaign_sizes[campaign_sizes >= 100]
    broad_targets = set(broad_100.index.get_level_values("target_key"))
    risk_counts: dict[str, Counter[str]] = defaultdict(Counter)
    risk_partitions = {
        "fit": set(risk["training_ids"]),
        "development": set(risk["validation_ids"]),
        "calibration": set(risk["calibration_ids"]),
        "final_sealed": set(risk_protocol["partitions"]["final"]),
    }
    for record in risk_protocol["records"]:
        target = str(record.get("target") or "").strip().upper()
        for partition, ids in risk_partitions.items():
            if record["id"] in ids:
                risk_counts[target][partition] += 1
    ledger = []
    for target in sorted(set(metadata.target_key) | set(roles)):
        rows = metadata[metadata.target_key.eq(target)]
        strict = cohort[cohort.target_key.eq(target)]
        nfit = int(fitted.target_key.eq(target).sum())
        nselection = int(selected.target_key.eq(target).sum())
        item = {
            "target_identifier": target,
            "gene_alias_certified": False,
            "roles": sorted(roles[target]),
            "broad_analysis_rows": len(rows),
            "strict_cohort_rows": len(strict),
            "patent_identifiers": sorted(rows["USPTO ID"].dropna().unique().tolist()),
            "active_efficacy_fit_rows": nfit,
            "active_efficacy_selection_rows": nselection,
            "strict_rows_sharing_fit_patent": int(
                strict["USPTO ID"].isin(fitted_patents).sum()
            ),
            "strict_rows_sharing_fit_natural_sequence": int(
                strict.natural_rna.isin(fitted_bases).sum()
            ),
            "risk_metadata_partition_counts": dict(risk_counts[target]),
            "has_campaign_100_distinct_helms": target in broad_targets,
            "cached_transcript": next(
                (t for t in transcripts if t["gene"] == target), None
            ),
            "status": classification(sorted(roles[target]), nfit, nselection),
            "final_assignment": None,
            "unresolved": [
                "verified_gene_alias",
                "patent_family",
                "cross_source_near_sequence",
                "full_supervised_exposure",
                "exact_current_profile_context_support",
            ],
        }
        ledger.append(item)
    statuses = Counter(item["status"] for item in ledger)
    summary = {
        "protocol_sha256": seal,
        "analysis_eligible_rows": len(metadata),
        "broad_target_identifiers": int(metadata.target_key.nunique()),
        "normalized_nonempty_identifiers": int(
            metadata.loc[metadata.target_key.ne(""), "target_key"].nunique()
        ),
        "rows_with_missing_target_identifier": int(metadata.target_key.eq("").sum()),
        "raw_target_identifier_spellings": int(metadata.target_RNA.nunique()),
        "case_whitespace_collisions": {
            key: sorted(values.dropna().unique().tolist())
            for key, values in metadata.groupby("target_key").target_RNA
            if values.nunique() > 1
        },
        "broad_patent_identifiers": int(metadata["USPTO ID"].nunique()),
        "campaigns_ge100_distinct_helms": len(broad_100),
        "target_identifiers_with_ge100_campaign": len(broad_targets),
        "status_counts": dict(statuses),
        "qualified_independent_final_groups": 0,
        "historical_source_manifest": {
            "train_pool_rows": len(manifest["source_train_ids"]),
            "validation_pool_rows": len(manifest["source_validation_ids"]),
            "excluded_targets": manifest["excluded_targets"],
            "excluded_patent_identifiers": manifest["excluded_patents"],
            "interpretation": "Available pools, not actual historical fit membership",
        },
        "prior_reserved_campaigns": [
            c for c in manifest["campaigns"] if c["role"] == "reserved"
        ],
        "nonreserved_noninspected_ge100_identifiers": [
            x["target_identifier"]
            for x in ledger
            if x["has_campaign_100_distinct_helms"] and not x["roles"]
        ],
        "nonreserved_noninspected_ge100_no_active_efficacy_exposure": [
            x["target_identifier"]
            for x in ledger
            if x["has_campaign_100_distinct_helms"]
            and not x["roles"]
            and not x["active_efficacy_fit_rows"]
            and not x["active_efficacy_selection_rows"]
        ],
        "same_screen_with_strict_cohort_rows": [
            x["target_identifier"]
            for x in ledger
            if x["has_campaign_100_distinct_helms"]
            and not x["roles"]
            and not x["active_efficacy_fit_rows"]
            and not x["active_efficacy_selection_rows"]
            and x["strict_cohort_rows"] > 0
        ],
        "risk_target_metadata_counts": {
            k: dict(v) for k, v in risk_counts.items() if v
        },
        "cached_transcripts": transcripts,
        "limitations": (
            "Names and patent IDs are not certified independent genes/families. "
            "No final assignment. Historical reserved claims not newly certified."
        ),
    }
    write_json(output / "candidate-manifest.json", ledger)
    write_json(output / "summary.json", summary)
    scenarios = []
    for target_sd in [0.05, 0.1, 0.2]:
        for groups in [5, 10, 20, 40]:
            for seeds in [5, 10]:
                scenarios.append(
                    {
                        "groups": groups,
                        "seeds": seeds,
                        "target_sd": target_sd,
                        "seed_sd": 0.02,
                        "interaction_sd": 0.05,
                        **crossed_precision(groups, seeds, target_sd, 0.02, 0.05),
                    }
                )
    write_json(output / "precision-scenarios.json", scenarios)
    return {
        k: v
        for k, v in summary.items()
        if k
        not in [
            "prior_reserved_campaigns",
            "cached_transcripts",
            "risk_target_metadata_counts",
        ]
    }


def main() -> None:
    """Command-line entry point; the caller supplies the historical owner artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.preparation, args.output), indent=2))


if __name__ == "__main__":
    main()
