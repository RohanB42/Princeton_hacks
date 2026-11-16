"""Frozen, development-only recorded dose-panel pilot with real local Qwen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import string
import time
from collections import Counter
from pathlib import Path

from oligo_engine.molecular_design.artifacts import seal, verify, write_new
from oligo_engine.reward.chemistry import parse_helm

from .core import curve_record, features, identity, replay, success

TARGETS = ("F7", "STAT3", "NLRP3")
RESERVED = {"PTBP1", "KCNQ2", "DMPK", "PLN", "SMAD7", "PSD3", "DUX4"}
META = (
    "USPTO ID",
    "Table Number",
    "Compound ID",
    "HELM Annotation",
    "cell_line",
    "dosage_nm",
    "target_RNA",
    "cell_line_species",
    "transfection_method",
    "treatment_period_hrs",
    "cells_per_well",
)
CONTEXT = (
    "USPTO ID",
    "Table Number",
    "target_RNA",
    "cell_line",
    "cell_line_species",
    "transfection_method",
    "treatment_period_hrs",
    "cells_per_well",
)
SYSTEM = (
    "You select historical antisense oligonucleotide dose panels under a fixed "
    "budget. Maximize discoveries meeting apparent absolute IC50 <= threshold. "
    "Only purchased panels are known. Sequence and chemical descriptors are "
    "available; do not assume unmeasured effects. exact_only counts only "
    "in-range interpolated successes; bound_aware also counts upper bounds "
    "at or below threshold. Unknown curves are not established failures. "
    "Choose the next unpurchased panel. Reply with its single-letter ID only."
)


def sha(path: Path) -> str:
    """Stream a content hash without decoding outcomes."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read(path: Path) -> dict:
    """Read one protocol or provenance artifact."""
    return json.loads(path.read_text())


def prepare(root: Path, output: Path, runtime: Path, model: Path) -> None:
    """Metadata-only largest complete panel grids on fixed development genes."""
    import pyarrow.parquet as pq

    if output.exists():
        raise FileExistsError(output)
    path = root / "data/aso_atlas_2/release/dose_response.parquet"
    cleaned = root / "data/aso_atlas_2/cleaned/dose_response.parquet"
    audit = read(root / "data/aso_atlas_2/cleaned/audit.json")
    expected = audit["endpoints"]["dose_response"]
    if (
        sha(path) != expected["source_sha256"]
        or sha(cleaned) != expected["cleaned_sha256"]
    ):
        raise ValueError("Pinned dose-response source/cleaned bytes changed")
    risk_path = root / "artifacts/molecular-design-v1/risk-qualification/protocol.json"
    risk = read(risk_path)
    verify(risk)
    final_ids = set(risk["partitions"]["final"])
    final_rows = [r for r in risk["records"] if r["id"] in final_ids]
    forbidden_patents = {r["patent"] for r in final_rows}
    forbidden_sequences = {r["sequence"] for r in final_rows}
    frame = pq.read_table(path, columns=list(META)).to_pandas()
    frame["source_row_id"] = [f"dose_response:{i}" for i in range(len(frame))]
    frame["target_RNA"] = frame.target_RNA.fillna("").str.strip().str.upper()
    frame = frame[frame.target_RNA.isin(TARGETS)].copy()
    frame = frame.dropna(subset=[c for c in CONTEXT if c != "cells_per_well"])
    frame = frame[frame.cell_line_species.str.casefold() == "human"]
    frame = frame[~frame["USPTO ID"].isin(forbidden_patents)]
    parsed, rejected = {}, 0
    for helm in frame["HELM Annotation"].dropna().unique():
        try:
            chem = parse_helm(helm.replace("[m5C]", "[5meC]"))
            seq = chem.natural_rna.replace("U", "T")
            if seq in forbidden_sequences or len(seq) > 64:
                continue
            parsed[helm] = (chem, seq)
        except (ValueError, TypeError):
            rejected += 1
    frame = frame[frame["HELM Annotation"].isin(parsed)].copy()
    frame["compound"] = frame["HELM Annotation"].map(lambda h: parsed[h][0].identity)
    campaigns, choices = [], []
    for target in TARGETS:
        if target in RESERVED:
            raise ValueError("Reserved target cannot enter this pilot")
        options = []
        for context, group in frame[frame.target_RNA == target].groupby(
            list(CONTEXT), dropna=False
        ):
            grids = {}
            panels = []
            for compound, rows in group.groupby("compound"):
                doses = sorted(float(x) for x in rows.dosage_nm)
                if (
                    len(doses) < 4
                    or len(set(doses)) != len(doses)
                    or any(not math.isfinite(x) or x <= 0 for x in doses)
                ):
                    continue
                grid = tuple(doses)
                grids[grid] = grids.get(grid, 0) + 1
                chem, seq = parsed[rows.iloc[0]["HELM Annotation"]]
                panels.append(
                    {
                        "compound_id": compound,
                        "grid": grid,
                        "row_ids": rows.sort_values("dosage_nm").source_row_id.tolist(),
                        "features": features(
                            seq,
                            {
                                "sugar_counts": dict(Counter(chem.sugars)),
                                "link_counts": dict(Counter(chem.links)),
                                "terminal": chem.terminal,
                            },
                        ),
                    }
                )
            for grid, n in grids.items():
                if n >= 8:
                    ctx = {
                        k: None
                        if isinstance(v, float) and math.isnan(v)
                        else v.item()
                        if hasattr(v, "item")
                        else v
                        for k, v in zip(CONTEXT, context, strict=True)
                    }
                    options.append((n, identity(ctx), ctx, grid, panels))
        if not options:
            raise ValueError(f"No metadata-compatible >=8-panel group for {target}")
        n, _, context, grid, panels = sorted(options, key=lambda o: (-o[0], o[1]))[0]
        selected = sorted(
            (p for p in panels if p["grid"] == grid),
            key=lambda p: identity(
                {"salt": "ic50-qwen-v1", "compound": p["compound_id"]}
            ),
        )[:24]
        for index, panel in enumerate(selected):
            panel["id"] = string.ascii_uppercase[index]
        campaign = {
            "target": target,
            "context": context,
            "dose_grid_nm": grid,
            "candidates": selected,
            "metadata_eligible_pool": n,
            "role": "retrospective_development_recorded_panel_purchase",
        }
        campaign["id"] = identity(campaign)
        campaigns.append(campaign)
        choices.append(
            {
                "target": target,
                "context": context,
                "panels": len(selected),
                "grid": grid,
            }
        )
    config = {"campaigns": campaigns}
    write_new(output / "config.json", config)
    protocol = seal(
        {
            "schema": "ic50-qwen-from-scratch-v1",
            "scope": (
                "prespecified retrospective development diagnostic, not "
                "independent confirmation"
            ),
            "source": str(path),
            "source_sha256": sha(path),
            "cleaned": str(cleaned),
            "cleaned_sha256": sha(cleaned),
            "runtime_receipt": str(runtime),
            "runtime_receipt_sha256": sha(runtime),
            "environment_sha256": sha(runtime.parent / "environment.json"),
            "model_path": str(model),
            "model_files": {
                p.name: sha(p) for p in sorted(model.iterdir()) if p.is_file()
            },
            "sources": {
                str(p): sha(p)
                for p in [
                    *sorted(Path(__file__).parent.glob("*.py")),
                    root / "src/oligo_engine/reward/chemistry.py",
                    root / "src/oligo_engine/molecular_design/artifacts.py",
                ]
            },
            "config_sha256": sha(output / "config.json"),
            "risk_final_protocol_seal": risk["seal"],
            "risk_final_ids_preserved": len(final_ids),
            "risk_final_exclusion": (
                "all matching patent IDs and exact natural sequences"
            ),
            "reserved_target_exclusion": sorted(RESERVED),
            "history": (
                "F7/STAT3/NLRP3 already used in historical development and "
                "experimental-selection training; no new independent target "
                "claim"
            ),
            "metadata_selection": (
                "largest fixed-table/context exact complete unique-dose-grid "
                "cohort per prespecified gene; hash cap24; all QC failures "
                "retained after outcome access"
            ),
            "targets": list(TARGETS),
            "seeds": [1900, 1901, 1902],
            "methods": ["random", "greedy", "bayesian_group_thompson", "qwen"],
            "rules": ["exact_only", "bound_aware"],
            "budget": 8,
            "initial_panels": 2,
            "cost": (
                "one complete historical dose panel; grid constant within "
                "campaign; all starts charged; dose-readout cost also reported"
            ),
            "primary_threshold_nm": 100.0,
            "threshold_basis": (
                "prespecified operational screening cutoff, not a validated "
                "clinical or assay acceptance threshold"
            ),
            "secondary_thresholds_nm": [10.0, 1000.0],
            "endpoint": (
                "apparent absolute 50% inhibition crossing of reported "
                "normalized responses"
            ),
            "curve_rule": (
                "increasing isotonic PAVA; reject nonfinite or "
                "outside[-20,120]pp; max absolute PAVA adjustment15pp; in-grid "
                "log-dose linear crossing; outside-grid retain bounds; no "
                "biological plateau failure inferred"
            ),
            "curve_sensitivity": (
                "repeat adjudication with zero tolerated PAVA adjustment; no "
                "policy rerun or threshold tuning"
            ),
            "limitations": (
                "raw controls, viability, replicate uncertainty and patent "
                "extraction not independently verified; operational QC is not "
                "biological assay validation"
            ),
            "counterfactual": (
                "exact_only is constructed, not recovered historical V3; only "
                "threshold-qualified upper bounds change success credit; other "
                "unknowns remain unknown"
            ),
            "qwen_system": SYSTEM,
            "qwen_decoding": (
                "greedy constrained one-token legal letter, tokenizer one-token"
                " check; seeded letter reassignment; no repair or heuristic "
                "fallback"
            ),
            "qwen_normal_calls": 108,
            "qwen_failure": (
                "invalid action or inference error aborts arm and records "
                "failure; no fabricated replacement"
            ),
            "primary_analysis": (
                "paired new credited discoveries at8panels; separately both "
                "adjudications on fixed traces and common bound-aware rescoring"
                " of adaptive traces"
            ),
            "statistics": (
                "descriptive three campaign groups and three seeds; no "
                "confirmatory significance claims"
            ),
            "metadata_only_before_seal": True,
        }
    )
    write_new(output / "protocol.json", protocol)
    print(json.dumps(choices, indent=2))


def load(output: Path) -> tuple[dict, dict]:
    """Validate the frozen code, data identity and configuration before execution."""
    p = read(output / "protocol.json")
    verify(p)
    for name, expected in p["sources"].items():
        if sha(Path(name)) != expected:
            raise ValueError("Frozen experiment code changed")
    if sha(output / "config.json") != p["config_sha256"]:
        raise ValueError("Frozen panel metadata changed")
    return p, read(output / "config.json")


def adjudicate(output: Path) -> None:
    """Only selected development source rows enter the private recorded oracle."""
    import pyarrow.parquet as pq

    p, config = load(output)
    path = Path(p["cleaned"])
    if sha(path) != p["cleaned_sha256"]:
        raise ValueError("Outcome source bytes changed")
    ids = sorted(
        {i for c in config["campaigns"] for d in c["candidates"] for i in d["row_ids"]}
    )
    rows = pq.read_table(
        path,
        columns=["source_row_id", "dosage_nm", "Inhibition_pct"],
        filters=[("source_row_id", "in", ids)],
    ).to_pylist()
    by_id = {r["source_row_id"]: r for r in rows}
    if len(rows) != len(ids) or set(by_id) != set(ids):
        raise ValueError("Selected dose outcome records missing or duplicated")
    oracle, counts = {}, {}
    for campaign in config["campaigns"]:
        oracle[campaign["id"]] = {}
        counts[campaign["target"]] = Counter()
        for c in campaign["candidates"]:
            actual = [by_id[i] for i in c["row_ids"]]
            doses = [float(r["dosage_nm"]) for r in actual]
            if doses != campaign["dose_grid_nm"]:
                raise ValueError("Recorded dose grid changed")
            responses = [r["Inhibition_pct"] for r in actual]
            result = curve_record(doses, responses)
            oracle[campaign["id"]][c["id"]] = result
            counts[campaign["target"]][result["kind"]] += 1
    payload = seal(
        {
            "protocol_seal": p["seal"],
            "outcome_ids_read": ids,
            "oracle": oracle,
            "counts": {k: dict(v) for k, v in counts.items()},
            "raw_curves": {i: by_id[i] for i in ids},
            "strict_monotonicity_oracle": {
                c["id"]: {
                    d["id"]: curve_record(
                        c["dose_grid_nm"],
                        [by_id[i]["Inhibition_pct"] for i in d["row_ids"]],
                        max_adjustment=0,
                    )
                    for d in c["candidates"]
                }
                for c in config["campaigns"]
            },
        }
    )
    write_new(output / "private-oracle.json", payload)
    # Aggregate inspection is deferred until all policies have committed their traces.
    print(
        json.dumps({"selected_outcome_rows": len(ids), "oracle_seal": payload["seal"]})
    )


class Qwen:
    """Real pinned local model; legal action masking is applied to model logits."""

    def __init__(self, protocol: dict) -> None:
        import mlx.core as mx
        from mlx_lm import generate
        from mlx_lm import load as load_model

        self.mx, self.generate = mx, generate
        path = Path(protocol["model_path"])
        for name, expected in protocol["model_files"].items():
            if sha(path / name) != expected:
                raise ValueError("Frozen Qwen model bytes changed")
        if sha(Path(protocol["runtime_receipt"])) != protocol["runtime_receipt_sha256"]:
            raise ValueError("Runtime receipt changed")
        self.model, self.tokenizer = load_model(str(path))
        self.tokens = {}
        for letter in string.ascii_uppercase[:24]:
            values = self.tokenizer.encode(letter, add_special_tokens=False)
            if len(values) != 1:
                raise ValueError("Action letters must each tokenize as one token")
            self.tokens[letter] = values[0]
        if len(set(self.tokens.values())) != 24:
            raise ValueError("Action letters must have distinct token IDs")
        self.system = protocol["qwen_system"]
        self.calls = 0

    def callback(self, campaign: dict, seed: int, log: Path):
        """Random display labels are fixed per seed and shared between objectives."""
        names = sorted(d["id"] for d in campaign["candidates"])
        permuted = random.Random(seed + 92173).sample(names, len(names))
        forward = dict(zip(names, permuted, strict=True))
        reverse = {v: k for k, v in forward.items()}

        def act(obs: dict) -> tuple[str, dict]:
            view = json.loads(json.dumps(obs))
            for section in ("candidates", "history"):
                for row in view[section]:
                    row["id"] = forward[row["id"]]
            view["candidates"].sort(key=lambda r: r["id"])
            allowed = [r["id"] for r in view["candidates"]]
            messages = [
                {"role": "system", "content": self.system},
                {"role": "user", "content": json.dumps(view, separators=(",", ":"))},
            ]
            prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            token_ids = self.mx.array([self.tokens[x] for x in allowed])

            def sampler(logprobs):
                return token_ids[self.mx.argmax(logprobs[..., token_ids], axis=-1)]

            started = time.monotonic()
            call_path = log / f"step-{len(obs['history']) + 1}"
            write_new(
                call_path / "request.json",
                seal(
                    {
                        "messages": messages,
                        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                        "allowed_ids": allowed,
                        "display_mapping": forward,
                        "max_tokens": 1,
                        "constrained_decoding": True,
                    }
                ),
            )
            self.calls += 1
            response = self.generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=1,
                sampler=sampler,
                verbose=False,
            )
            write_new(
                call_path / "response.json",
                seal(
                    {
                        "response": response,
                        "seconds": time.monotonic() - started,
                    }
                ),
            )
            if response not in allowed:
                raise ValueError(
                    "Constrained Qwen response failed exact legal-ID check"
                )
            return reverse[response], {
                "model_call": self.calls,
                "messages": messages,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "input_tokens": len(self.tokenizer.encode(prompt)),
                "response": response,
                "physical_action": reverse[response],
                "display_mapping": forward,
                "constrained_decoding": True,
                "generated_tokens": 1,
                "seconds": time.monotonic() - started,
            }

        return act


def evaluate(output: Path) -> None:
    """Execute all frozen arms; no prompt/model selection using outcome aggregates."""
    p, config = load(output)
    private = read(output / "private-oracle.json")
    verify(private)
    if private["protocol_seal"] != p["seal"]:
        raise ValueError("Recorded oracle belongs to another protocol")
    qwen = Qwen(p)
    results = []
    for c in config["campaigns"]:
        for seed in p["seeds"]:
            for method in p["methods"]:
                for rule in p["rules"]:
                    stem = f"{c['target']}-{method}-{rule}-{seed}"
                    path = output / "runs" / f"{stem}.json"
                    if path.exists():
                        existing = read(path)
                        verify(existing)
                        if existing["protocol_seal"] != p["seal"]:
                            raise ValueError("Existing arm belongs to another protocol")
                        results.append(existing)
                        continue
                    try:
                        run = replay(
                            c,
                            private["oracle"][c["id"]],
                            method,
                            rule,
                            seed,
                            p["budget"],
                            p["primary_threshold_nm"],
                            qwen.callback(c, seed, output / "calls" / stem)
                            if method == "qwen"
                            else None,
                        )
                    except Exception as exc:
                        write_new(
                            output / "failures" / f"{stem}.json",
                            seal(
                                {
                                    "protocol_seal": p["seal"],
                                    "arm": stem,
                                    "error": f"{type(exc).__name__}: {exc}",
                                    "action": "abort; no heuristic fallback",
                                }
                            ),
                        )
                        raise
                    artifact = seal({"protocol_seal": p["seal"], "run": run})
                    write_new(path, artifact)
                    results.append(artifact)
            print(
                json.dumps({"completed_target": c["target"], "seed": seed}), flush=True
            )
    write_new(
        output / "results.json", seal({"protocol_seal": p["seal"], "runs": results})
    )
    print(json.dumps({"runs": len(results), "qwen_calls_this_process": qwen.calls}))


def report(output: Path) -> None:
    """Describe fixed-trace relabeling separately from adaptive policy changes."""
    p, config = load(output)
    results, private = (
        read(output / "results.json"),
        read(output / "private-oracle.json"),
    )
    verify(results)
    verify(private)
    runs = [r["run"] for r in results["runs"]]
    summaries = []
    for c in config["campaigns"]:
        for method in p["methods"]:
            pair = {
                rule: sorted(
                    [
                        r
                        for r in runs
                        if r["target"] == c["target"]
                        and r["method"] == method
                        and r["rule"] == rule
                    ],
                    key=lambda r: r["seed"],
                )
                for rule in p["rules"]
            }
            if any(len(v) != len(p["seeds"]) for v in pair.values()):
                raise ValueError("Missing prespecified cell")
            old, new = pair["exact_only"], pair["bound_aware"]
            summaries.append(
                {
                    "target": c["target"],
                    "method": method,
                    "exact_only_new_hits": statistics.mean(
                        r["new_credited_hits"] for r in old
                    ),
                    "bound_aware_new_hits": statistics.mean(
                        r["new_credited_hits"] for r in new
                    ),
                    "exact_only_unknown_panels": statistics.mean(
                        r["unknown_panels"] for r in old
                    ),
                    "bound_aware_unknown_panels": statistics.mean(
                        r["unknown_panels"] for r in new
                    ),
                    "exact_only_credited_hits": statistics.mean(
                        r["credited_hits"] for r in old
                    ),
                    "bound_aware_credited_hits": statistics.mean(
                        r["credited_hits"] for r in new
                    ),
                    "fixed_trace_credit_gain": statistics.mean(
                        r["counterfactual_rescore"]["bound_aware"]
                        - r["counterfactual_rescore"]["exact_only"]
                        for r in old
                    ),
                    "adaptive_gain_common_bound_evaluator": statistics.mean(
                        b["counterfactual_rescore"]["bound_aware"]
                        - a["counterfactual_rescore"]["bound_aware"]
                        for a, b in zip(old, new, strict=True)
                    ),
                    "changed_sequences": sum(
                        [h["id"] for h in a["history"]]
                        != [h["id"] for h in b["history"]]
                        for a, b in zip(old, new, strict=True)
                    ),
                }
            )
    strict = private["strict_monotonicity_oracle"]
    strict_results = [
        {
            "target": r["target"],
            "method": r["method"],
            "rule": r["rule"],
            "seed": r["seed"],
            "strict_bound_hits": sum(
                success(strict[r["campaign"]][h["id"]], 100, "bound_aware") is True
                for h in r["history"]
            ),
        }
        for r in runs
    ]
    out = seal(
        {
            "protocol_seal": p["seal"],
            "summaries": summaries,
            "curve_counts": private["counts"],
            "strict_QC_fixed_trace_rescore": strict_results,
        }
    )
    write_new(output / "summary.json", out)
    lines = [
        "# Recorded dose-panel IC50/Qwen pilot",
        "",
        (
            "Means over three seeds; eight charged panels including two "
            "starts. Operational retrospective diagnostic, not biological "
            "validation."
        ),
        "",
        (
            "| Target | Method | Exact-only hits | Bound-aware hits | "
            "Fixed-trace credit gain | Adaptive gain, common evaluator | "
            "Changed traces / 3 |"
        ),
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in summaries:
        lines.append(
            f"| {r['target']} | {r['method']} | "
            f"{r['exact_only_credited_hits']:.3f} | "
            f"{r['bound_aware_credited_hits']:.3f} | "
            f"{r['fixed_trace_credit_gain']:.3f} | "
            f"{r['adaptive_gain_common_bound_evaluator']:.3f} | "
            f"{r['changed_sequences']} |"
        )
    lines += [
        "",
        "Primary outcome excludes the two charged starting panels:",
        "",
        "| Target | Method | Exact-only new hits | Bound-aware new hits |",
        "|---|---|---:|---:|",
    ]
    for r in summaries:
        lines.append(
            f"| {r['target']} | {r['method']} | "
            f"{r['exact_only_new_hits']:.3f} | {r['bound_aware_new_hits']:.3f} |"
        )
    lines += [
        "",
        "Curve category counts: " + json.dumps(private["counts"], sort_keys=True),
        "",
        (
            "Exact-only is a constructed counterfactual, not a recovered V3"
            " implementation. Threshold100nM is operational; raw controls "
            "and extraction remain unverified. No final labels, neural "
            "fitting, PPO or COBALT implementation is claimed."
        ),
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase", choices=("prepare", "adjudicate", "evaluate", "report")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--runtime",
        type=Path,
        default=Path("artifacts/ic50-qwen-runtime-v1/download-receipt.json"),
    )
    parser.add_argument(
        "--model", type=Path, default=Path("artifacts/ic50-qwen-runtime-v1/model")
    )
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(
            args.root.resolve(),
            args.output.resolve(),
            args.runtime.resolve(),
            args.model.resolve(),
        )
    elif args.phase == "adjudicate":
        adjudicate(args.output.resolve())
    elif args.phase == "evaluate":
        evaluate(args.output.resolve())
    else:
        report(args.output.resolve())


if __name__ == "__main__":
    main()
