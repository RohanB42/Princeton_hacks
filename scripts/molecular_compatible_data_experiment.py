"""Recover compatible-data exposure and near-family feasibility without outcomes.

This is a metadata preflight, not a new reward model. Cross-source ASO metadata
are conservatively quarantined as potentially assessed in existing studies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from oligo_engine.molecular_design.artifacts import seal, verify, write_new
from oligo_engine.molecular_design.contracts import campaign_from_dict
from oligo_engine.molecular_design.metadata_audit import CONTEXTS
from oligo_engine.reward.chemistry import parse_helm

ENDPOINTS = ("in_vitro_inhibition", "neurotoxicity")
GIT_MANIFEST = (
    "model_checkpoints/experimental-selection-ppo-3x32-v1/partition_manifest.json"
)


def digest(path: Path) -> str:
    """Hash bytes without decoding measured outcomes."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path: Path) -> Any:
    """Read provenance documents only, never unfiltered observation tables."""
    return json.loads(path.read_text())


def metadata_columns(endpoint: str) -> list[str]:
    """Positive column allowlist excludes every measured endpoint."""
    if endpoint not in ENDPOINTS:
        raise ValueError("Unsupported metadata endpoint")
    return ["HELM Annotation", "USPTO ID", "target_RNA", *CONTEXTS[endpoint]]


def normalize(value: Any) -> str:
    """Normalize display of metadata, without resolving biological aliases."""
    if value is None:
        return "<missing>"
    if isinstance(value, float):
        import math

        return format(value, ".12g") if math.isfinite(value) else "<missing>"
    return str(value).strip()


def protected_role(role: str) -> bool:
    """Never treat a selection, assessment or reserved membership as new fit data."""
    return any(
        word in role
        for word in (
            "selection",
            "validation",
            "assessment",
            "reserved",
            "development",
            "calibration",
            "final",
            "sentinel",
            "test",
        )
    )


class Components:
    """Deterministic connected components with no outcome-dependent decisions."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, node: str) -> str:
        self.parent.setdefault(node, node)
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def add_exact(graph: Components, records: list[dict]) -> None:
    """Link exact sequences and patent IDs; missing patents never link rows."""
    for row in records:
        rid = "row:" + row["id"]
        graph.find(rid)
        for sequence in row["sequences"]:
            graph.union(rid, "seq:" + sequence)
        if row["patent"] != "<missing>":
            graph.union(rid, "patent:" + row["patent"])


def add_near(graph: Components, sequences: set[str]) -> None:
    """Exact Hamming <=2 and one-base shifts, streamed by length/position pair.

    At most one mask dictionary is kept; no all-pairs distance matrix. These
    declared local families are not an exhaustive biological homology definition.
    """
    groups: dict[int, list[str]] = defaultdict(list)
    for seq in sorted(sequences):
        groups[len(seq)].append(seq)
    for length, values in sorted(groups.items()):
        for i, j in combinations(range(length), 2):
            seen: dict[str, str] = {}
            for seq in values:
                key = seq[:i] + seq[i + 1 : j] + seq[j + 1 :]
                if key in seen:
                    graph.union("seq:" + seq, "seq:" + seen[key])
                else:
                    seen[key] = seq
        # Prefix/suffix matches represent a one-base shift only at equal length.
        seen_shift: dict[str, str] = {}
        for seq in values:
            for key in (seq[1:], seq[:-1]):
                if key in seen_shift:
                    graph.union("seq:" + seq, "seq:" + seen_shift[key])
                else:
                    seen_shift[key] = seq


def excluded(graph: Components, records: list[dict], ids: set[str]) -> set[str]:
    """Expand protected memberships through the full metadata graph."""
    roots = {graph.find("row:" + sid) for sid in ids}
    return {r["id"] for r in records if graph.find("row:" + r["id"]) in roots}


def get_ids(value: Any) -> set[str]:
    """Collect source-qualified IDs from an already identified membership field."""
    if isinstance(value, list):
        return set().union(*(get_ids(v) for v in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(get_ids(v) for v in value.values())) if value else set()
    if isinstance(value, str) and value.startswith("in_vitro_inhibition:"):
        return {value}
    return set()


def recover(value: Any, path: str = "") -> dict[str, set[str]]:
    """Recover explicit provenance fields; ignore numeric outcomes and metrics."""
    found = {}
    if isinstance(value, dict):
        for key, child in value.items():
            label = f"{path}/{key}"
            if key in {"ids", "source_ids", "initial_ids", "acquired_ids"}:
                if ids := get_ids(child):
                    found[label + "_fit"] = ids
            elif key in {"validation_ids", "calibration_ids", "test_ids"}:
                if ids := get_ids(child):
                    found[label + "_" + key.replace("_ids", "")] = ids
            elif key not in {"metrics", "scores", "history", "predictions", "y"}:
                found.update(recover(child, label))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            if isinstance(child, (dict, list)):
                found.update(recover(child, f"{path}/{i}"))
    return found


def receipt_memberships(paths: list[Path]) -> tuple[dict, dict]:
    """Keep path provenance separate from semantic exposure-role classification."""
    ledger, provenance = {}, {}
    for index, path in enumerate(paths):
        for field, ids in recover(read(path)).items():
            key = f"recovered_{index}{field}"
            ledger[key] = ids
            provenance[key] = {"path": str(path), "field": field}
    return ledger, provenance


def run(root: Path, historical: Path, output: Path) -> dict:
    """Execute an exposure-aware metadata feasibility experiment; never fit."""
    import pandas as pd
    import pyarrow.parquet as pq

    started = time.monotonic()
    if output.exists():
        raise FileExistsError("Use a new output directory; protocols are immutable")
    prior_dir = root / "artifacts/molecular-validity-experiment-v1"
    prior = read(prior_dir / "protocol.json")
    verify(prior)
    prior_ledger = read(prior_dir / "exposure-ledger.json")
    if prior_ledger["protocol_seal"] != prior["seal"]:
        raise ValueError("Prior exposure ledger differs from audited protocol")
    config_path = root / "artifacts/molecular-policy-repair-v3/config.json"
    supported_path = root / "artifacts/supported-aso-v1/partition.json"
    config, supported = read(config_path), read(supported_path)
    profile = campaign_from_dict(config["campaigns"][0]).profile
    git_revision = subprocess.check_output(
        ["git", "rev-parse", "origin/main"], cwd=root, text=True
    ).strip()
    git_bytes = subprocess.check_output(
        ["git", "show", f"{git_revision}:{GIT_MANIFEST}"], cwd=root
    )
    published = json.loads(git_bytes)
    model_roots = [
        historical / "scaling-v1",
        Path("/private/tmp/oligoal-atlas-rnafm-20261114/artifacts/atlas-rnafm"),
    ]
    receipts = sorted(model_roots[0].glob("*/receipt.json"))
    receipts += [
        model_roots[1] / name
        for name in (
            "classical-development-v1/report.json",
            "fm-development-v1/suite.json",
            "fm-profile-v1/report.json",
            "acquisition-development-v1/report.json",
        )
    ]
    sources = {e: root / f"data/aso_atlas_2/release/{e}.parquet" for e in ENDPOINTS}
    source_hashes = {e: digest(p) for e, p in sources.items()}
    if source_hashes != prior["source_sha256"]:
        raise ValueError("Source release differs from previous pinned audit")
    if (
        source_hashes[ENDPOINTS[0]]
        != published["atlas"]["hashes"]["release/in_vitro_inhibition.parquet"]
    ):
        raise ValueError("Published source membership refers to another release")
    oligogym = root / "data/oligogym"
    og_manifest = read(oligogym / "manifest.json")
    og_sources = []
    for path in sorted(oligogym.glob("*_processed.json")):
        if read(path)["modality"] == "ASO":
            og_sources.append(path.with_suffix(".csv.gz"))
    for path in og_sources:
        if digest(path) != og_manifest["files"][path.name]["sha256"]:
            raise ValueError("OligoGym release bytes differ")
    inputs = [
        Path(__file__),
        config_path,
        supported_path,
        prior_dir / "protocol.json",
        prior_dir / "exposure-ledger.json",
        oligogym / "manifest.json",
        *receipts,
    ]
    protocol = seal(
        {
            "schema": "compatible-data-exposure-feasibility-v1",
            "scope": "metadata only; no measured outcomes, predictions or fitting",
            "parent_protocol_seal": prior["seal"],
            "input_sha256": {str(p): digest(p) for p in inputs},
            "source_sha256": source_hashes,
            "published_manifest": {
                "revision": git_revision,
                "path": GIT_MANIFEST,
                "sha256": hashlib.sha256(git_bytes).hexdigest(),
                "identity": published["identity"],
            },
            "metadata_columns": {e: metadata_columns(e) for e in ENDPOINTS},
            "oligogym_columns": ["x", "fasta", "targets"],
            "oligogym_sha256": {str(p): digest(p) for p in og_sources},
            "cross_source_rule": "Conservatively quarantine every ASO counterpart; "
            "prior full-data diagnostics prevent claiming these are untouched",
            "sequence_rule": "Exact plus Hamming <=2 and exact one-base shift, "
            "equal lengths; transitive patent components across all parsed rows",
            "target_rule": "No invented alias/patent-family normalization",
            "fit_gate": "No new fitting if preserved roles or independent "
            "same-context assessment cannot be certified",
            "fallback": "Audit prior supported-profile fit and assessment roles; "
            "do not silently reassign selection/calibration labels into fitting",
        }
    )
    write_new(output / "protocol.json", protocol)
    write_new(output / "published-partition-manifest.json", published)
    ledger = {k: set(v) for k, v in prior_ledger["memberships"].items()}
    ledger["published_source_fit"] = set(published["source_fit"])
    ledger["published_source_calibration"] = set(published["source_cal"])
    for c in published["campaigns"]:
        role = {"train": "training", "dev": "development", "test": "final"}[c["role"]]
        for part in ("pool", "sentinel"):
            ledger[f"published_{role}_{c['name']}_{part}"] = set(c[part])
    recovered, recovered_provenance = receipt_memberships(receipts)
    ledger.update(recovered)
    recovered_count = len(recovered)
    protected = set().union(*(v for k, v in ledger.items() if protected_role(k)))
    protected_old = set().union(
        *(set(v) for k, v in prior_ledger["memberships"].items() if protected_role(k))
    )
    print(
        json.dumps(
            {"receipts_recovered": len(receipts), "protected_ids": len(protected)}
        ),
        flush=True,
    )
    records, parse_failures = [], Counter()
    for endpoint, path in sources.items():
        for i, row in enumerate(
            pq.read_table(path, columns=metadata_columns(endpoint)).to_pylist()
        ):
            try:
                chem = parse_helm(row["HELM Annotation"].replace("[m5C]", "[5meC]"))
            except (ValueError, TypeError, AttributeError):
                parse_failures[endpoint] += 1
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
                    "id": f"{endpoint}:{i}",
                    "endpoint": endpoint,
                    "compound": chem.identity,
                    "sequences": [seq],
                    "patent": normalize(row["USPTO ID"]),
                    "target": normalize(row["target_RNA"]).upper(),
                    "context": tuple(normalize(row[k]) for k in CONTEXTS[endpoint]),
                    "patterns": patterns,
                }
            )
    graph = Components()
    add_exact(graph, records)
    old_excluded = excluded(graph, records, protected_old)
    new_excluded = excluded(graph, records, protected)
    og_records, og_summary = [], []
    for path in og_sources:
        frame = pd.read_csv(path, usecols=["x", "fasta", "targets"])
        failures = discrepancies = 0
        for i, row in enumerate(frame.to_dict("records")):
            seqs = set()
            fasta = str(row["fasta"]).upper().replace("U", "T")
            if fasta and set(fasta) <= set("ACGT"):
                seqs.add(fasta)
            try:
                helm = row["x"].removesuffix("V2.0").replace("[m5C]", "[5meC]")
                chem = parse_helm(helm)
                seq = chem.natural_rna.replace("U", "T")
                discrepancies += bool(seqs and seq not in seqs)
                seqs.add(seq)
            except (ValueError, TypeError, AttributeError):
                failures += 1
            # Conflicting FASTA/HELM sequences are both quarantine evidence;
            # they are never merged into an asserted exact molecular identity.
            og_records.append(
                {
                    "id": f"oligogym:{path.name}:{i}",
                    "sequences": sorted(seqs),
                    "patent": "<missing>",
                }
            )
        og_summary.append(
            {
                "dataset": path.name,
                "rows": len(frame),
                "helm_parser_failures": failures,
                "fasta_helm_discrepancies": discrepancies,
            }
        )
    add_exact(graph, og_records)
    cross_source_ids = {r["id"] for r in og_records}
    all_protected = protected | cross_source_ids
    cross_excluded = excluded(graph, records, all_protected)
    print(
        json.dumps(
            {
                "atlas_parsed": len(records),
                "oligogym_rows": len(og_records),
                "exact_cross_protected": len(cross_excluded),
            }
        ),
        flush=True,
    )
    add_near(graph, {s for r in records + og_records for s in r["sequences"]})
    near_excluded = excluded(graph, records, all_protected)
    groups = defaultdict(list)
    for row in records:
        if row["endpoint"] == ENDPOINTS[0]:
            for pattern in row["patterns"]:
                groups[(pattern, row["context"])].append(row)
    summaries = []
    for (pattern, context), group in sorted(groups.items()):
        survivors = [r for r in group if r["id"] not in near_excluded]
        summaries.append(
            {
                "pattern": pattern,
                "context": dict(zip(CONTEXTS[ENDPOINTS[0]], context)),
                "raw_rows": len(group),
                "published_calibration_rows": sum(
                    r["id"] in ledger["published_source_calibration"] for r in group
                ),
                "previous_exact_available": sum(
                    r["id"] not in old_excluded for r in group
                ),
                "recovered_exact_available": sum(
                    r["id"] not in new_excluded for r in group
                ),
                "cross_source_exact_available": sum(
                    r["id"] not in cross_excluded for r in group
                ),
                "near_family_available": len(survivors),
                "remaining_components": len(
                    {graph.find("row:" + r["id"]) for r in survivors}
                ),
                "remaining_patents": sorted({r["patent"] for r in survivors}),
                "remaining_targets": sorted({r["target"] for r in survivors}),
                "surviving_ids": [r["id"] for r in survivors],
            }
        )
    fallback = {}
    for part in ("train", "test"):
        ids = {r["source_row_id"] for r in supported[part]}
        fallback[part] = {
            "rows": len(ids),
            "explicit_protected_ids": len(ids & protected),
            "published_calibration_overlap": len(ids & set(published["source_cal"])),
            "published_fit_overlap": len(ids & set(published["source_fit"])),
            "outside_recovered_exact_components": len(ids - new_excluded),
            "outside_cross_source_near_components": len(ids - near_excluded),
        }
    result = seal(
        {
            "protocol_seal": protocol["seal"],
            "metadata_only": True,
            "models_fitted": 0,
            "outcomes_read": False,
            "receipt_documents": len(receipts),
            "recovered_membership_fields": recovered_count,
            "previous_protected_ids": len(protected_old),
            "protected_ids": len(protected),
            "new_protected_ids": len(protected - protected_old),
            "parsed_atlas_rows": len(records),
            "parser_rejections": dict(parse_failures),
            "protected_ids_without_parsed_metadata": len(
                protected - {r["id"] for r in records}
            ),
            "membership_ids_without_parsed_metadata": len(
                set().union(*ledger.values()) - {r["id"] for r in records}
            ),
            "protected_exact_rows_previous": len(old_excluded),
            "protected_exact_rows_recovered": len(new_excluded),
            "protected_exact_rows_cross_source": len(cross_excluded),
            "protected_near_rows_cross_source": len(near_excluded),
            "oligogym": og_summary,
            "active_pattern_contexts": summaries,
            "supported_profile_fallback": fallback,
            "risk_final_preserved": len(ledger["risk_final"]),
            "status": "metadata_preflight_complete_no_fitting",
            "qualification": "No independent cohort certified; alias/patent-family "
            "and original experimental-selection manifest recovery remain incomplete",
            "elapsed_seconds": time.monotonic() - started,
        }
    )
    write_new(
        output / "exposure-ledger.json",
        {
            "protocol_seal": protocol["seal"],
            "memberships": {k: sorted(v) for k, v in ledger.items()},
            "recovered_provenance": recovered_provenance,
        },
    )
    write_new(output / "result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--historical",
        type=Path,
        default=Path(
            "/private/tmp/oligoal-atlas-lora-scaling-20261114/artifacts/atlas-rnafm"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    r = run(args.root, args.historical, args.output)
    print(
        json.dumps(
            {
                k: r[k]
                for k in (
                    "status",
                    "protected_ids",
                    "protected_near_rows_cross_source",
                    "elapsed_seconds",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
