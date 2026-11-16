"""Sealed metadata preparation, development selection and held-out dose replay."""

from __future__ import annotations

import argparse
import json
import math
import platform
import time
from collections import Counter
from pathlib import Path

from experiments.ic50_qwen.core import identity
from experiments.ic50_qwen.run import CONTEXT, META, RESERVED, read, sha

from oligo_engine.molecular_design.artifacts import seal, verify, write_new
from oligo_engine.reward.chemistry import parse_helm

from .core import (
    CONFIDENCES,
    MARGINS,
    metrics,
    qualified,
    reference,
    stopped,
    trajectory,
)

DEV = ("F7", "STAT3")
ASSESS = ("DNM2", "PCSK9", "KRAS", "TMPRSS6", "AGT")
METHODS = ("full_grid", "fixed_early", "information_gain", "decision_aware")


def near(a: str, b: str) -> bool:
    """Conservative equal-length <=2 mismatch or one-base-shift sequence link."""
    return len(a) == len(b) and (
        sum(x != y for x, y in zip(a, b, strict=True)) <= 2
        or a[1:] == b[:-1]
        or a[:-1] == b[1:]
    )


def prepare(output: Path) -> None:
    """Outcome-free metadata and protocol seal, with source/context exclusions."""
    import pyarrow.parquet as pq

    if output.exists():
        raise FileExistsError(output)
    root = Path.cwd()
    source = root / "data/aso_atlas_2/release/dose_response.parquet"
    cleaned = root / "data/aso_atlas_2/cleaned/dose_response.parquet"
    expected = read(root / "data/aso_atlas_2/cleaned/audit.json")["endpoints"][
        "dose_response"
    ]
    assert sha(source) == expected["source_sha256"]
    assert sha(cleaned) == expected["cleaned_sha256"]
    risk = read(root / "artifacts/molecular-design-v1/risk-qualification/protocol.json")
    verify(risk)
    risk_ids = set(risk["partitions"]["final"])
    risk_rows = [r for r in risk["records"] if r["id"] in risk_ids]
    forbidden_patents = {r["patent"] for r in risk_rows}
    forbidden_sequences = {r["sequence"] for r in risk_rows}
    assert not (set(DEV + ASSESS) & (RESERVED | {"NLRP3"}))
    f = pq.read_table(source, columns=list(META)).to_pandas()
    f["source_row_id"] = [f"dose_response:{i}" for i in range(len(f))]
    f["target_RNA"] = f.target_RNA.fillna("").str.strip().str.upper()
    f = f[f.target_RNA.isin(DEV + ASSESS)].copy()
    f = f.dropna(subset=[c for c in CONTEXT if c != "cells_per_well"])
    f = f[f.cell_line_species.str.casefold() == "human"]
    f = f[~f["USPTO ID"].isin(forbidden_patents)]
    parsed = {}
    for helm in f["HELM Annotation"].dropna().unique():
        try:
            c = parse_helm(helm.replace("[m5C]", "[5meC]"))
            seq = c.natural_rna.replace("U", "T")
            if len(seq) <= 64 and not any(near(seq, x) for x in forbidden_sequences):
                parsed[helm] = (c.identity, seq)
        except (ValueError, TypeError):
            continue
    f = f[f["HELM Annotation"].isin(parsed)].copy()
    f["compound"] = f["HELM Annotation"].map(lambda h: parsed[h][0])
    campaigns, dev_sequences, dev_patents = [], [], set()
    for target in DEV + ASSESS:
        options = []
        for ctx, group in f[f.target_RNA == target].groupby(
            list(CONTEXT), dropna=False
        ):
            if target in ASSESS and ctx[0] in dev_patents:
                continue
            panels = []
            for compound, rows in group.groupby("compound"):
                ds = sorted(float(x) for x in rows.dosage_nm)
                if not (4 <= len(ds) <= 10 and len(set(ds)) == len(ds)):
                    continue
                if any(not math.isfinite(x) or x <= 0 for x in ds):
                    continue
                seq = parsed[rows.iloc[0]["HELM Annotation"]][1]
                if target in ASSESS and any(near(seq, x) for x in dev_sequences):
                    continue
                panels.append(
                    {
                        "compound": compound,
                        "sequence": seq,
                        "doses": ds,
                        "row_ids": rows.sort_values("dosage_nm").source_row_id.tolist(),
                    }
                )
            grids = Counter(tuple(p["doses"]) for p in panels)
            for grid, n in grids.items():
                if n < 12:
                    continue
                context = {
                    k: None
                    if isinstance(v, float) and math.isnan(v)
                    else v.item()
                    if hasattr(v, "item")
                    else v
                    for k, v in zip(CONTEXT, ctx, strict=True)
                }
                options.append((n, identity(context), context, grid, panels))
        if not options:
            raise ValueError(f"No cohort for {target}")
        n, _, context, grid, panels = sorted(options, key=lambda x: (-x[0], x[1]))[0]
        panels = sorted(
            (p for p in panels if tuple(p["doses"]) == grid),
            key=lambda p: identity({"salt": "adaptive-dose-v1", "id": p["compound"]}),
        )[:48]
        for p in panels:
            p["id"] = identity({"context": context, "compound": p["compound"]})
        role = "development" if target in DEV else "assessment"
        if role == "development":
            dev_sequences.extend(p["sequence"] for p in panels)
            dev_patents.add(context["USPTO ID"])
        campaigns.append(
            {
                "target": target,
                "role": role,
                "context": context,
                "doses": list(grid),
                "eligible": n,
                "panels": panels,
            }
        )
    config = {"campaigns": campaigns}
    write_new(output / "config.json", config)
    sources = [
        *Path(__file__).parent.glob("*.py"),
        Path("experiments/ic50_qwen/core.py"),
        Path("experiments/ic50_qwen/run.py"),
        Path("src/oligo_engine/reward/chemistry.py"),
    ]
    protocol = seal(
        {
            "schema": "adaptive-dose-response-v1",
            "purpose": "retrospective_diagnostic",
            "threshold_nm": 500,
            "max_fpr": 0.05,
            "max_fnr": 0.05,
            "max_unknown_assertion_rate": 0.05,
            "minimum_resolved_coverage": 0.95,
            "coverage_noninferiority_margin": 0.02,
            "development_targets": DEV,
            "assessment_targets": ASSESS,
            "split": (
                "target/patent disjoint, near-sequence excluded vs development; "
                "not globally fresh"
            ),
            "source": str(source),
            "source_sha256": sha(source),
            "cleaned": str(cleaned),
            "cleaned_sha256": sha(cleaned),
            "config_sha256": sha(output / "config.json"),
            "sources": {str(p): sha(p) for p in sources},
            "risk_final_seal": risk["seal"],
            "risk_final_exclusion": "patent and exact/near sequence, all304 preserved",
            "excluded_reserved_targets": sorted(RESERVED | {"NLRP3"}),
            "panel_selection": (
                "largest complete human assay/table/grid per target; "
                "unique4-10doses; hashcap48; no outcomeQC filtering"
            ),
            "reference": (
                "PAVA maxadjust15pp, values[-20,120], absolute50 "
                "logdosecrossing/bounds/unresolved; strict0pp sensitivity"
            ),
            "methods": METHODS,
            "fixed_margins_pp": MARGINS,
            "bayes_confidences": CONFIDENCES,
            "fixed_baseline": (
                "thresholdnearest ordering; monotonicwitness + paid "
                "nearestbracket loginterpolation; fullpaidgrid fallback"
            ),
            "bayes_grid": {
                "bottom": [-10, 0, 10],
                "top": [30, 60, 80, 100, 120],
                "hill": [0.5, 1, 2, 4],
                "log10_midpoint": [-1, 5, 25],
                "sigma_pp": 10,
                "prior": "uniform1500hypotheses; no empiricalBayes fit",
            },
            "quadrature": (
                "prospectiveGaussian response bins "
                "edges[-inf,-30,-20,...,130,inf]; exactcdf masses; "
                "actualcontinuouslikelihoodupdate"
            ),
            "selection": (
                "devminimummeanmeasurements among empirical5%FPR/FNR "
                "and5%unknownassertions and95%coverage; tiespreferstricter; "
                "fallbackfullonly; no assessmenttuning"
            ),
            "assessment_gate": (
                "same errors/unknown constraint andcoverage>=max(.95,fixed-.02); "
                "missingclassunqualified; no populationguarantee"
            ),
            "budget_curves": (
                "truncate frozen selectedpolicy prefixes at1..maximumgrid; no retuning"
            ),
            "minimum_paid_doses": 1,
            "all_panels_replayed_before_reference_qc": True,
            "no_full_reference_in_policy": True,
            "limitations": (
                "historicalexposure, extraction/controls/replicates unverified; "
                "groupcorrelation; replaycost notwetlabcost; Gate1open"
            ),
            "environment": {"python": platform.python_version()},
        }
    )
    write_new(output / "protocol.json", protocol)
    print(
        json.dumps(
            [
                {k: c[k] for k in ("target", "role", "context", "doses", "eligible")}
                | {"selected": len(c["panels"])}
                for c in campaigns
            ],
            indent=2,
        )
    )


def load(output: Path) -> tuple[dict, dict]:
    """Fail if frozen code/config/data changed after preparation."""
    p = read(output / "protocol.json")
    verify(p)
    for path, expected in p["sources"].items():
        assert sha(Path(path)) == expected, path
    assert sha(output / "config.json") == p["config_sha256"]
    assert sha(Path(p["cleaned"])) == p["cleaned_sha256"]
    return p, read(output / "config.json")


def replay_role(output: Path, role: str) -> None:
    """Read only selected role outcomes, generate paid traces, then adjudicate."""
    import pyarrow.parquet as pq

    protocol, config = load(output)
    selection = None
    if role == "assessment":
        selection = read(output / "selection.json")
        verify(selection)
        assert selection["protocol_seal"] == protocol["seal"]
    campaigns = [c for c in config["campaigns"] if c["role"] == role]
    ids = [i for c in campaigns for p in c["panels"] for i in p["row_ids"]]
    rows = pq.read_table(
        protocol["cleaned"],
        columns=["source_row_id", "dosage_nm", "Inhibition_pct"],
        filters=[("source_row_id", "in", ids)],
    ).to_pylist()
    by_id = {r["source_row_id"]: r for r in rows}
    assert len(rows) == len(ids) == len(by_id)
    results, start = [], time.monotonic()
    for c in campaigns:
        for panel in c["panels"]:
            values = [by_id[i]["Inhibition_pct"] for i in panel["row_ids"]]
            assert [by_id[i]["dosage_nm"] for i in panel["row_ids"]] == c["doses"]
            values = [float(v) if v is not None else float("nan") for v in values]
            traces = {}
            for method in ("fixed_early", "information_gain", "decision_aware"):
                purchased = set()

                def buy(index: int, purchased: set = purchased) -> float:
                    if index in purchased or not 0 <= index < len(values):
                        raise ValueError("Invalid/repeated dose")
                    purchased.add(index)
                    return values[index]

                traces[method] = trajectory(c["doses"], buy, method)
            # Deferred full reference is outside all policy calls.
            results.append(
                {
                    "id": panel["id"],
                    "target": c["target"],
                    "doses": c["doses"],
                    "traces": traces,
                    "reference": reference(c["doses"], values),
                    "strict_reference": reference(c["doses"], values, 0),
                }
            )
    write_new(
        output / f"{role}-traces.json",
        seal(
            {
                "protocol_seal": protocol["seal"],
                "selection_seal": selection["seal"] if selection else None,
                "role": role,
                "outcome_ids": ids,
                "panels": results,
                "seconds": time.monotonic() - start,
            }
        ),
    )
    print(
        json.dumps(
            {
                "role": role,
                "panels": len(results),
                "source_rows": len(ids),
                "seconds": time.monotonic() - start,
            }
        )
    )


def score(
    panels: list[dict],
    method: str,
    setting: float | None,
    cap: int | None = None,
    strict: bool = False,
) -> tuple[dict, list[dict]]:
    """Evaluate costed prefixes only after their decisions are fixed."""
    rows = []
    for p in panels:
        trace = p["traces"]["fixed_early" if method == "full_grid" else method]
        r = stopped(p["doses"], trace, method, setting, cap)
        rows.append(
            {
                **r,
                "id": p["id"],
                "target": p["target"],
                "reference": p["strict_reference" if strict else "reference"]["label"],
            }
        )
    return metrics(rows), rows


def select(output: Path) -> None:
    """Lock settings using development references only, before assessment access."""
    protocol, _ = load(output)
    dev = read(output / "development-traces.json")
    verify(dev)
    selected, all_metrics = {"full_grid": None}, {}
    coverage = 0.95
    for method in METHODS[1:]:
        settings = MARGINS if method == "fixed_early" else CONFIDENCES
        candidates = []
        all_metrics[method] = []
        for index, setting in enumerate(settings):
            m, _ = score(dev["panels"], method, setting)
            valid = qualified(m, coverage)
            all_metrics[method].append({"setting": setting, "qualified": valid, **m})
            if valid:
                candidates.append((m["mean_measurements"], -index, setting, m))
        if candidates:
            _, _, selected[method], chosen = min(candidates, key=lambda r: r[:2])
        else:
            selected[method] = settings[-1]
            chosen, _ = score(dev["panels"], method, selected[method])
        if method == "fixed_early":
            coverage = max(0.95, (chosen["resolved_coverage"] or 0) - 0.02)
    write_new(
        output / "selection.json",
        seal(
            {
                "protocol_seal": protocol["seal"],
                "development_seal": dev["seal"],
                "settings": selected,
                "candidates": all_metrics,
                "no_assessment_access": not (
                    output / "assessment-traces.json"
                ).exists(),
            }
        ),
    )
    print(json.dumps({"selected": selected}))


def report(output: Path) -> None:
    """All operating points and exclusions retained, with no outcome-driven rerun."""
    protocol, _ = load(output)
    selected = read(output / "selection.json")
    verify(selected)
    report = {
        "protocol_seal": protocol["seal"],
        "selection_seal": selected["seal"],
        "roles": {},
    }
    for role in ("development", "assessment"):
        artifact = read(output / f"{role}-traces.json")
        verify(artifact)
        panels = artifact["panels"]
        result = {
            "reference_categories": dict(
                Counter(p["reference"]["kind"] for p in panels)
            ),
            "methods": {},
            "targets": {},
            "budget_curves": {},
            "strict_sensitivity": {},
        }
        for method in METHODS:
            m, rows = score(panels, method, selected["settings"][method])
            result["methods"][method] = m
            result["strict_sensitivity"][method] = score(
                panels, method, selected["settings"][method], strict=True
            )[0]
            result["targets"][method] = {
                t: metrics([r for r in rows if r["target"] == t])
                for t in sorted({p["target"] for p in panels})
            }
            result["budget_curves"][method] = [
                {
                    "cap": k,
                    **score(panels, method, selected["settings"][method], cap=k)[0],
                }
                for k in range(1, max(len(p["doses"]) for p in panels) + 1)
            ]
        base = result["methods"]["fixed_early"]
        coverage = max(0.95, (base["resolved_coverage"] or 0) - 0.02)
        result["primary_comparison"] = {
            method: {
                "measurement_reduction_vs_fixed": 1
                - m["mean_measurements"] / base["mean_measurements"],
                "empirically_qualified": qualified(m, coverage),
                "baseline_qualified": qualified(base, 0.95),
            }
            for method, m in result["methods"].items()
        }
        report["roles"][role] = result
    write_new(output / "report.json", seal(report))
    print(json.dumps(report["roles"]["assessment"]["methods"], indent=2))


def main() -> None:
    """Run each phase once; output files never overwrite sealed evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase", choices=["prepare", "development", "select", "assessment", "report"]
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.phase in {"development", "assessment"}:
        replay_role(args.output, args.phase)
    else:
        {"prepare": prepare, "select": select, "report": report}[args.phase](
            args.output
        )


if __name__ == "__main__":
    main()
