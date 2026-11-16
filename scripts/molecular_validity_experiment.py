"""Outcome-free profile feasibility and exposure audit; never qualifies a model.

Uses explicit Parquet metadata projections, preserves source-row positions, and
records all candidate contexts rather than selecting a context using predictions.
"""

import argparse
import hashlib
import json
import math
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from oligo_engine.molecular_design.artifacts import seal, write_new
from oligo_engine.molecular_design.cli import load_study
from oligo_engine.molecular_design.metadata_audit import CONTEXTS
from oligo_engine.provenance import identity
from oligo_engine.reward.chemistry import ASOChemistry, parse_helm

ENDPOINTS = ("in_vitro_inhibition", "neurotoxicity")
BASE_COLUMNS = ("HELM Annotation", "USPTO ID", "target_RNA", "model_eligible")


def digest(path: Path) -> str:
    """Hash immutable bytes without decoding any outcome columns."""
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def projection(endpoint: str, columns: list[str] | None = None) -> list[str]:
    """Reject all columns outside the positive metadata allowlist."""
    if endpoint not in ENDPOINTS:
        raise ValueError("Endpoint outside this sealed metadata experiment")
    allowed = [*BASE_COLUMNS, *CONTEXTS[endpoint]]
    requested = allowed if columns is None else columns
    if not requested or set(requested) - set(allowed):
        raise ValueError("Only explicitly allowed metadata columns may be read")
    return requested


def normalized(value: Any) -> str:
    """Normalize numeric formatting, without guessing biological aliases."""
    if value is None or isinstance(value, float) and not math.isfinite(value):
        return "<missing>"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value).strip()
    return format(number, ".12g") if math.isfinite(number) else "<missing>"


def context_key(values: dict[str, Any], endpoint: str) -> tuple[str, ...]:
    return tuple(normalized(values[field]) for field in CONTEXTS[endpoint])


def uniform_family(chem: ASOChemistry) -> dict[str, Any] | None:
    """Identify only fully observable uniform-C gapmer families.

    Molecules with no cytosine cannot distinguish methylated/unmodified templates.
    Mixed C/5meC patterns and uracil templates remain outside this bounded search.
    A family describes compatibility, not evidence for every possible sequence.
    """
    bases = set(chem.bases)
    if "U" in bases or not (bases & {"C", "5meC"}):
        return None
    if {"C", "5meC"} <= bases:
        return None
    try:
        first = chem.sugars.index("DNA")
        last = len(chem.sugars) - 1 - chem.sugars[::-1].index("DNA")
    except ValueError:
        return None
    if first == 0 or last == len(chem.sugars) - 1:
        return None
    if chem.sugars[first : last + 1] != ("DNA",) * (last - first + 1):
        return None
    if set(chem.sugars) - {"DNA", "MOE", "OMe", "cEt"}:
        return None
    return {
        "length": len(chem.bases),
        "sugars": chem.sugars,
        "links": chem.links[:-1],
        "terminal": chem.terminal,
        "methyl_c": "5meC" in bases,
        "wing5": first,
        "wing3": len(chem.sugars) - last - 1,
    }


def describe(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe metadata diversity; counts are not independent evidence units."""
    return {
        "rows": len(records),
        "upstream_model_eligible_rows": sum(r["eligible"] for r in records),
        "distinct_compounds": len({r["compound"] for r in records}),
        "distinct_sequences": len({r["sequence"] for r in records}),
        "patent_identifiers": sorted({r["patent"] for r in records}),
        "target_identifiers": sorted({r["target"] for r in records}),
    }


def protected_connections(
    records: list[dict[str, Any]], protected_ids: set[str]
) -> set[str]:
    """Conservatively exclude entire exact-sequence/patent components.

    Includes transitive connections through unselected metadata rows. Near sequence
    families and patent families still require a separate audit before label use.
    """
    parent: dict[str, str] = {}

    def find(item: str) -> str:
        parent.setdefault(item, item)
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != root:
            next_item = parent[item]
            parent[item] = root
            item = next_item
        return root

    for row in records:
        nodes = ["row:" + row["id"]]
        for key in ("sequence", "patent"):
            if row[key] != "<missing>":
                nodes.append(key + ":" + row[key])
        for node in nodes[1:]:
            parent[find(node)] = find(nodes[0])
    forbidden = {find("row:" + i) for i in protected_ids}
    return {r["id"] for r in records if find("row:" + r["id"]) in forbidden}


def run(args: argparse.Namespace) -> dict[str, Any]:
    import pyarrow.parquet as pq

    started = time.monotonic()
    output, root = args.output, args.root
    config, campaigns, _ = load_study(args.config)
    profile = campaigns[0].profile
    risk_path = root / "artifacts/molecular-design-v1/risk-qualification/protocol.json"
    risk = json.loads(risk_path.read_text())
    export_path = root / "artifacts/molecular-design-v1/atlas-ridge-reference.json"
    export = json.loads(export_path.read_text())
    old_manifest_path = args.historical / "preparation-v1/manifests.json"
    old = json.loads(old_manifest_path.read_text())
    supported_path = root / "artifacts/supported-aso-v1/partition.json"
    supported = json.loads(supported_path.read_text())
    audit_path = root / "data/aso_atlas_2/cleaned/audit.json"
    audit = json.loads(audit_path.read_text())
    ledger = {
        "active_efficacy_fit": set(export["training_ids"]),
        "active_efficacy_selection": set(export["validation_ids"]),
        "historical_source_pool": set(old["source_train_ids"]),
        "historical_source_validation": set(old["source_validation_ids"]),
        "supported_profile_fit": {r["source_row_id"] for r in supported["train"]},
        "supported_profile_measured_assessment": {
            r["source_row_id"] for r in supported["test"]
        },
        **{"risk_" + k: set(v) for k, v in risk["partitions"].items()},
    }
    for campaign in old["campaigns"]:
        for part in ("pool_ids", "test_ids"):
            ledger[f"atlas_{campaign['role']}_{campaign['target']}_{part}"] = set(
                campaign[part]
            )
    receipts = {}
    for size in (2869, 4781):
        for seed in (510, 511, 512):
            name = f"source-{size}-{seed}-ridge"
            receipt_path = args.historical / "scaling-v1" / name / "receipt.json"
            receipt = json.loads(receipt_path.read_text())
            ledger[name + "_fit"] = set(receipt["ids"])
            ledger[name + "_selection"] = set(receipt["validation_ids"])
            receipts[str(receipt_path)] = digest(receipt_path)
    source_paths = {
        endpoint: root / f"data/aso_atlas_2/release/{endpoint}.parquet"
        for endpoint in ENDPOINTS
    }
    hashes = {endpoint: digest(path) for endpoint, path in source_paths.items()}
    for endpoint, sha in hashes.items():
        if sha != audit["endpoints"][endpoint]["source_sha256"]:
            raise ValueError("Released source hash mismatch")
    protocol = seal(
        {
            "schema": "molecular-validity-metadata-v1",
            "outcome_access": "forbidden; no outcome reader or scoring phase",
            "source_sha256": hashes,
            "metadata_columns": {e: projection(e) for e in ENDPOINTS},
            "input_sha256": {
                str(p): digest(p)
                for p in (
                    args.config,
                    risk_path,
                    export_path,
                    old_manifest_path,
                    supported_path,
                    audit_path,
                    Path(__file__),
                )
            }
            | receipts,
            "git_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, cwd=root
            ).strip(),
            "code_status": "working-tree script bound by input SHA256",
            "family_rule": "uniform observed C methylation; full sugar/link/terminal",
            "unknown_family": "no-C, mixed-C, U or unsupported gapmer: not inferred",
            "alias": "existing [m5C] to [5meC] parser alias only",
            "selection": "report all shared families and contexts; no score ranking",
            "support_gate": "metadata compatibility only; cannot qualify predictors",
            "protected_roles": "existing selection/calibration/final roles retained",
            "scope": "existing profile across contexts; alternative uniform-C gapmers",
        }
    )
    write_new(output / "protocol.json", protocol)
    write_new(
        output / "exposure-ledger.json",
        {
            "protocol_seal": protocol["seal"],
            "memberships": {k: sorted(v) for k, v in ledger.items()},
            "historical_excluded_targets": old["excluded_targets"],
            "historical_excluded_patents": old["excluded_patents"],
            "policy_inspected_genes": sorted({c.target.gene for c in campaigns}),
            "cross_project_exposure_status": "incomplete; final claim not authorized",
        },
    )
    records: dict[str, list[dict[str, Any]]] = {}
    summaries, families = {}, {}
    efficacy_context = context_key(config["bundle"]["context"], ENDPOINTS[0])
    risk_context = context_key(risk["risk_context"], ENDPOINTS[1])
    for endpoint, path in source_paths.items():
        rows = pq.read_table(path, columns=projection(endpoint)).to_pylist()
        parsed, failures = [], Counter()
        exact_context_rows = exact_context_failures = 0
        for index, row in enumerate(rows):
            context = context_key(row, endpoint)
            fixed = context == (
                efficacy_context if endpoint == ENDPOINTS[0] else risk_context
            )
            exact_context_rows += fixed
            try:
                chem = parse_helm(row["HELM Annotation"].replace("[m5C]", "[5meC]"))
            except (ValueError, TypeError, AttributeError) as error:
                failures[type(error).__name__ + ":" + str(error)] += 1
                exact_context_failures += fixed
                continue
            sequence = chem.natural_rna.replace("U", "T")
            matching = [
                p.name
                for p in profile.patterns
                if p.length == len(sequence)
                and chem.terminal in p.terminals
                and parse_helm(p.helm(sequence, chem.terminal)).identity
                == chem.identity
            ]
            family = uniform_family(chem)
            family_id = identity(family) if family else None
            if family:
                families[family_id] = family
            parsed.append(
                {
                    "id": f"{endpoint}:{index}",
                    "compound": chem.identity,
                    "sequence": sequence,
                    "patent": normalized(row["USPTO ID"]),
                    "target": normalized(row["target_RNA"]).upper(),
                    "context": context,
                    "fixed_context": fixed,
                    "eligible": row["model_eligible"] is True,
                    "active_patterns": matching,
                    "family": family_id,
                    "cytosine_positions": [
                        i for i, b in enumerate(chem.bases) if b in {"C", "5meC"}
                    ],
                }
            )
        records[endpoint] = parsed
        summaries[endpoint] = {
            "source_rows": len(rows),
            "parsed_rows": len(parsed),
            "parser_rejections": sum(failures.values()),
            "rejection_reasons": dict(failures),
            "fixed_context_raw_rows": exact_context_rows,
            "fixed_context_parser_rejections": exact_context_failures,
            "fixed_context_active_patterns": dict(
                Counter(
                    p
                    for r in parsed
                    if r["fixed_context"]
                    for p in r["active_patterns"]
                )
            ),
        }
    efficacy, neuro = records[ENDPOINTS[0]], records[ENDPOINTS[1]]
    memberships = defaultdict(set)
    for role, ids in ledger.items():
        for sample_id in ids:
            memberships[sample_id].add(role)
    protected = set().union(
        *(
            ids
            for role, ids in ledger.items()
            if "selection" in role
            or "validation" in role
            or "assessment" in role
            or "reserved" in role
            or "development" in role
            or "calibration" in role
            or "final" in role
        )
    )
    connected_protected = protected_connections(efficacy + neuro, protected)

    def group_summary(group: list[dict[str, Any]]) -> dict[str, Any]:
        return describe(group) | {
            "membership_counts": dict(
                Counter(role for r in group for role in memberships[r["id"]])
            ),
            "rows_outside_protected_ids": sum(r["id"] not in protected for r in group),
            "rows_outside_protected_exact_sequence_patent_components": sum(
                r["id"] not in connected_protected for r in group
            ),
            "cytosine_position_counts": dict(
                sorted(
                    Counter(i for r in group for i in r["cytosine_positions"]).items()
                )
            ),
        }

    active_groups = defaultdict(list)
    for row in efficacy:
        for pattern in row["active_patterns"]:
            active_groups[(pattern, row["context"])].append(row)
    active = [
        {
            "pattern": p,
            "context": dict(zip(CONTEXTS[ENDPOINTS[0]], ctx)),
            **group_summary(rows),
        }
        for (p, ctx), rows in sorted(active_groups.items())
    ]
    efficacy_groups, neuro_groups = defaultdict(list), defaultdict(list)
    for row in efficacy:
        if row["family"]:
            efficacy_groups[row["family"]].append(row)
    for row in neuro:
        if row["family"] and row["fixed_context"]:
            neuro_groups[row["family"]].append(row)
    common = []
    for family_id in sorted(efficacy_groups.keys() & neuro_groups.keys()):
        contexts = defaultdict(list)
        for row in efficacy_groups[family_id]:
            contexts[row["context"]].append(row)
        common.append(
            {
                "family_id": family_id,
                "pattern": families[family_id],
                "risk_fixed_context": group_summary(neuro_groups[family_id]),
                "efficacy_all_contexts": group_summary(efficacy_groups[family_id]),
                "efficacy_fixed_context": group_summary(
                    [r for r in efficacy_groups[family_id] if r["fixed_context"]]
                ),
                "efficacy_contexts": [
                    {
                        "context": dict(zip(CONTEXTS[ENDPOINTS[0]], ctx)),
                        **group_summary(rows),
                    }
                    for ctx, rows in sorted(contexts.items())
                ],
            }
        )
    risk_final = ledger["risk_final"]
    result = seal(
        {
            "schema": "molecular-validity-metadata-result-v1",
            "protocol_seal": protocol["seal"],
            "outcomes_read": False,
            "models_fitted": 0,
            "models_scored": 0,
            "endpoint_audits": summaries,
            "active_patterns_across_contexts": active,
            "common_uniform_C_gapmer_families": common,
            "risk_final_rows_preserved": len(risk_final),
            "known_protected_ids": len(protected),
            "protected_exact_sequence_patent_connected_rows": len(connected_protected),
            "exposure_complete": False,
            "remaining_exposure_work": [
                "OligoGym/Atlas cross-source compound and near-sequence families",
                "verified gene aliases and patent-family mapping",
                "other research branches' actual fitting and outcome-access receipts",
            ],
            "measured_evaluation_status": "blocked_scope_and_incomplete_exposure_audit",
            "qualification": "metadata feasibility only; no predictor or safety claim",
            "elapsed_seconds": time.monotonic() - started,
        }
    )
    write_new(output / "result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "outcomes_read",
                    "models_fitted",
                    "risk_final_rows_preserved",
                    "measured_evaluation_status",
                    "elapsed_seconds",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
