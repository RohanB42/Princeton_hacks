"""Outcome-blind evaluation inventory, distinct from eligibility for new fitting."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from oligo_engine.molecular_design.artifacts import seal, verify, write_new
from oligo_engine.molecular_design.contracts import campaign_from_dict
from oligo_engine.molecular_design.metadata_audit import CONTEXTS
from oligo_engine.reward.chemistry import parse_helm


def read(path: Path) -> Any:
    """Read existing configuration/provenance, never raw outcome tables."""
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    """Hash bytes without decoding endpoint values."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def normalize(value: Any) -> str:
    """Canonicalize numeric formatting only; do not invent assay aliases."""
    if value is None:
        return "<missing>"
    try:
        number = float(value)
        return format(number, ".12g") if number == number else "<missing>"
    except (ValueError, TypeError):
        return str(value).strip()


def columns(endpoint: str) -> list[str]:
    """A positive metadata projection prevents outcome access."""
    if endpoint not in {"in_vitro_inhibition", "neurotoxicity"}:
        raise ValueError("Only the two declared evaluation endpoints are supported")
    return ["HELM Annotation", "USPTO ID", "target_RNA", *CONTEXTS[endpoint]]


def evaluation_role(
    sid: str,
    fit: set[str],
    selection: set[str],
    calibration: set[str],
    reserved: set[str],
    known_membership: set[str],
) -> str:
    """Fitting disqualifies evaluation; reserved evaluation is not training."""
    if sid in fit:
        return "head_fit"
    if sid in selection:
        return "head_selection"
    if sid in calibration:
        return "head_calibration"
    if sid in reserved:
        return "original_reserved_evaluation_keep_sealed"
    if sid in known_membership:
        return "other_study_membership_exposure_audit_required"
    return "unassigned_metadata_candidate"


def helpers(root: Path) -> Any:
    """Reuse the previously tested metadata graph, pinned in this protocol."""
    spec = importlib.util.spec_from_file_location(
        "compatible_graph", root / "scripts/molecular_compatible_data_experiment.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(root: Path, output: Path) -> dict:
    """Inventory own-head independence; do not allocate or unseal evaluation."""
    import pyarrow.parquet as pq

    if output.exists():
        raise FileExistsError("Use a fresh output; no overwriting sealed protocols")
    paths = {
        "config": root / "artifacts/molecular-policy-repair-v3/config.json",
        "efficacy": root / "artifacts/molecular-design-v1/atlas-ridge-reference.json",
        "risk": root / "artifacts/molecular-design-v1/risk-qualification/model.json",
        "risk_protocol": root
        / "artifacts/molecular-design-v1/risk-qualification/protocol.json",
        "ledger": root
        / "artifacts/molecular-compatible-data-experiment-v1"
        / "corrected-role-recovery/exposure-ledger.json",
        "prior_protocol": root
        / "artifacts/molecular-compatible-data-experiment-v1"
        / "corrected-role-recovery/protocol.json",
        "supported": root / "artifacts/supported-aso-v1/partition.json",
        "graph_code": root / "scripts/molecular_compatible_data_experiment.py",
        "driver": Path(__file__).resolve(),
    }
    sources = {
        e: root / f"data/aso_atlas_2/release/{e}.parquet"
        for e in ("in_vitro_inhibition", "neurotoxicity")
    }
    previous = read(paths["prior_protocol"])
    verify(previous)
    if {e: digest(p) for e, p in sources.items()} != previous["source_sha256"]:
        raise ValueError("Pinned release changed")
    cfg, efficacy, risk = (read(paths[k]) for k in ("config", "efficacy", "risk"))
    risk_protocol, ledger = read(paths["risk_protocol"]), read(paths["ledger"])
    verify(risk_protocol)
    if ledger["protocol_seal"] != previous["seal"]:
        raise ValueError("Exposure ledger differs from previous protocol")
    protocol = seal(
        {
            "schema": "molecular-evaluation-data-metadata-v1",
            "purpose": "metadata feasibility; no prediction, fitting or outcome access",
            "input_sha256": {k: digest(p) for k, p in paths.items()},
            "source_sha256": {e: digest(p) for e, p in sources.items()},
            "columns": {e: columns(e) for e in sources},
            "head_independence": "exclude own fit, selection and calibration; "
            "report exact and full-metadata near/patent component links separately",
            "global_exposure": "other-study assessed rows remain retrospective; "
            "no automatic fresh confirmation from own-head exclusion",
            "reserved_risk": "304 original final records remain sealed and assigned",
            "context_transfer": "different contexts are separate candidate strata, "
            "never silently valid for the current profile",
            "new_final_assignments": 0,
            "metadata_selection": "all complete pattern/context combinations",
        }
    )
    write_new(output / "protocol.json", protocol)
    h = helpers(root)
    profile = campaign_from_dict(cfg["campaigns"][0]).profile
    records, failures = [], Counter()
    for endpoint, path in sources.items():
        for index, row in enumerate(
            pq.read_table(path, columns=columns(endpoint)).to_pylist()
        ):
            try:
                chem = parse_helm(row["HELM Annotation"].replace("[m5C]", "[5meC]"))
            except (ValueError, TypeError, AttributeError):
                failures[endpoint] += 1
                continue
            seq = chem.natural_rna.replace("U", "T")
            patterns = [
                p.name
                for p in profile.patterns
                if p.length == len(seq)
                and chem.terminal in p.terminals
                and parse_helm(p.helm(seq, chem.terminal)).identity == chem.identity
            ]
            records.append(
                {
                    "id": f"{endpoint}:{index}",
                    "endpoint": endpoint,
                    "sequences": [seq],
                    "compound": chem.identity,
                    "patent": normalize(row["USPTO ID"]),
                    "target": normalize(row["target_RNA"]).upper(),
                    "context": tuple(normalize(row[k]) for k in CONTEXTS[endpoint]),
                    "patterns": patterns,
                }
            )
    graph = h.Components()
    h.add_exact(graph, records)
    known = set().union(*map(set, ledger["memberships"].values()))
    summaries, candidates = {}, []
    models = {"in_vitro_inhibition": efficacy, "neurotoxicity": risk}
    exact_exclusions = {}
    for endpoint, model in models.items():
        excluded_ids = set(model["training_ids"]) | set(model["validation_ids"])
        excluded_ids |= set(model.get("calibration_ids", []))
        exact_exclusions[endpoint] = h.excluded(graph, records, excluded_ids)
    h.add_near(graph, {seq for row in records for seq in row["sequences"]})
    for endpoint, model in models.items():
        fit, selection = set(model["training_ids"]), set(model["validation_ids"])
        calibration = set(model.get("calibration_ids", []))
        reserved = (
            set(risk_protocol["partitions"]["final"])
            if endpoint == "neurotoxicity"
            else set()
        )
        exclusion = fit | selection | calibration
        near_excluded = h.excluded(graph, records, exclusion)
        context = (
            cfg["bundle"]["context"]
            if endpoint == "in_vitro_inhibition"
            else risk["context"]
        )
        desired = tuple(normalize(context[k]) for k in CONTEXTS[endpoint])
        groups = defaultdict(list)
        for row in records:
            if row["endpoint"] == endpoint and row["patterns"]:
                groups[row["context"]].append(row)
        cells = []
        for ctx, group in sorted(groups.items()):
            complete = "<missing>" not in ctx
            unseen = [r for r in group if r["id"] not in exclusion]
            exact = [r for r in unseen if r["id"] not in exact_exclusions[endpoint]]
            near = [r for r in unseen if r["id"] not in near_excluded]
            cell = {
                "context": dict(zip(CONTEXTS[endpoint], ctx, strict=True)),
                "context_complete": complete,
                "current_context": ctx == desired,
                "rows": len(group),
                "distinct_compounds": len({r["compound"] for r in group}),
                "own_head_roles": dict(
                    Counter(
                        evaluation_role(
                            r["id"], fit, selection, calibration, reserved, known
                        )
                        for r in group
                    )
                ),
                "outside_own_head_rows": len(unseen),
                "outside_exact_sequence_patent_components": len(exact),
                "outside_near_sequence_patent_components": len(near),
                "remaining_components": len(
                    {graph.find("row:" + r["id"]) for r in near}
                ),
                "remaining_targets": sorted({r["target"] for r in near}),
                "historically_assigned_among_remaining": sum(
                    r["id"] in known for r in near
                ),
                "original_reserved_among_remaining": sum(
                    r["id"] in reserved for r in near
                ),
                "new_final_assignment": None,
            }
            cells.append(cell)
            if complete:
                for row in unseen:
                    candidates.append(
                        {
                            "source_row_id": row["id"],
                            "head": endpoint,
                            "context": cell["context"],
                            "current_context": cell["current_context"],
                            "role": evaluation_role(
                                row["id"], fit, selection, calibration, reserved, known
                            ),
                            "exact_component_excluded": row["id"]
                            in exact_exclusions[endpoint],
                            "near_component_excluded": row["id"] in near_excluded,
                            "new_final_assignment": None,
                        }
                    )
        summaries[endpoint] = cells
    result = seal(
        {
            "protocol_seal": protocol["seal"],
            "parser_rejections": dict(failures),
            "heads": summaries,
            "risk_reserved_records": len(risk_protocol["partitions"]["final"]),
            "risk_final_outcomes_read": False,
            "new_measured_outcomes_read": 0,
            "new_final_assignments": 0,
            "limitations": "Full-metadata component sensitivity is stricter than "
            "original risk-context split; aliases/patent families/cross-source "
            "exposure certification still open. Known membership is not identical "
            "to observed-label access. No source-pool membership certifies freshness.",
        }
    )
    write_new(output / "result.json", result)
    write_new(
        output / "evaluation-candidates.json",
        {"protocol_seal": protocol["seal"], "candidates": candidates},
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root, args.output)
    print(
        json.dumps(
            {
                head: [c for c in cells if c["current_context"]]
                for head, cells in result["heads"].items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
