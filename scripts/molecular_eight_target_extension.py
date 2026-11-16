"""Two additional development targets under frozen v3 policies and query budgets."""

import argparse
import csv
import hashlib
import json
import statistics
from dataclasses import asdict, replace
from pathlib import Path

from oligo_engine.molecular_design.artifacts import (
    QueryJournal,
    run_artifact,
    seal,
    verify,
    write_new,
)
from oligo_engine.molecular_design.cli import load_study
from oligo_engine.molecular_design.contracts import Target
from oligo_engine.molecular_design.preflight import audit_partitions, preflight


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(parent: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    protocol = json.loads((parent / "protocol.json").read_text())
    verify(protocol)
    if digest(parent / "config.json") != protocol["config_sha256"]:
        raise ValueError("Parent configuration differs from frozen protocol")
    config, original, registry = load_study(parent / "config.json")
    cfg = protocol["arms"]["full"]
    exposed = {
        d.compound_id
        for c in original
        if c.partition in {"training", "validation"}
        for d in c.designs()
    }
    campaigns, hashes = [], {}
    reserved = {"PTBP1", "KCNQ2", "DMPK", "PLN", "SMAD7", "PSD3", "DUX4"}
    for gene in ("APOC3", "ANGPTL3"):
        if gene in reserved or gene in {c.target.gene for c in original}:
            raise ValueError("Target is reserved or already in policy campaign set")
        path = Path(f"artifacts/transcripts/homo_sapiens.{gene}.json")
        raw = json.loads(path.read_text())
        hashes[str(path)] = digest(path)
        sequence = raw["sequence"].upper().replace("U", "T")
        if len(sequence) > cfg["site_capacity"]:
            raise ValueError("Full transcript exceeds frozen schema; never truncate")
        start = len(sequence) // 2
        target = Target(
            gene,
            raw["transcript_id"],
            sequence,
            raw["species"],
            raw["source"],
            ((start, start + 48),),
        )
        c = replace(
            original[0],
            name=f"{gene}-eight-target-development-extension",
            target=target,
            partition="development",
            requests=8,
            tokens=160,
            starts=((start, original[0].profile.patterns[0].name, "none"),),
        )
        designs = tuple(c.designs())
        if len(designs) != 89 or any(d.compound_id in exposed for d in designs):
            raise ValueError("Unexpected catalog size or policy fit/selection overlap")
        if preflight(c, registry)["status"] == "blocked":
            raise ValueError("Diagnostic metadata preflight blocked")
        campaigns.append(c)
    audit_partitions(original + tuple(campaigns))
    config["campaigns"] = [asdict(c) for c in campaigns]
    write_new(output / "config.json", config)
    policies = {}
    for seed in protocol["seeds"]:
        for arm in ("full", "architecture"):
            directory = parent / f"{arm}-{seed}"
            receipt = json.loads((directory / "training.json").read_text())
            verify(receipt)
            policies[f"{arm}-{seed}"] = {
                "path": str(directory),
                "training_seal": receipt["seal"],
                "policy_sha256": receipt["policy_sha256"],
                "warm_start_sha256": receipt["warm_start_sha256"],
            }
    write_new(
        output / "protocol.json",
        seal(
            {
                "schema": "eight-target-development-extension-v1",
                "parent": str(parent),
                "parent_protocol_seal": protocol["seal"],
                "registry": registry.key,
                "seeds": protocol["seeds"],
                "budget": 8,
                "arms": protocol["arms"],
                "methods": [
                    "full",
                    "architecture",
                    "warm_start",
                    "prior",
                    "random",
                    "greedy",
                ],
                "targets": [c.target.gene for c in campaigns],
                "campaigns": [c.key for c in campaigns],
                "target_selection": (
                    "APOC3 and ANGPTL3 chosen before scoring; public human ASO target"
                    " examples, schema-compatible, outside historical reserved seven"
                ),
                "scope": (
                    "additional surrogate-development evaluations; not independent "
                    "biological confirmation"
                ),
                "exposure": {
                    "APOC3": {
                        "active_efficacy_fit_rows": 0,
                        "active_efficacy_selection_rows": 0,
                        "strict_atlas_rows": 1,
                    },
                    "ANGPTL3": {
                        "active_efficacy_fit_rows": 45,
                        "active_efficacy_selection_rows": 3,
                        "strict_atlas_rows": 4426,
                    },
                },
                "exposure_limits": (
                    "No exact current-profile applicability or independent risk-head "
                    "exclusion established; both become inspected development targets"
                ),
                "policies": policies,
                "transcripts": hashes,
                "config_sha256": digest(output / "config.json"),
                "runner_sha256": digest(Path(__file__)),
                "sources": {
                    str(p): digest(p)
                    for p in sorted(
                        Path("src/oligo_engine/molecular_design").glob("*.py")
                    )
                },
            }
        ),
    )


def load(output: Path) -> tuple:
    p = json.loads((output / "protocol.json").read_text())
    verify(p)
    if digest(output / "config.json") != p["config_sha256"]:
        raise ValueError("Frozen configuration changed")
    if digest(Path(__file__)) != p["runner_sha256"]:
        raise ValueError("Frozen extension runner changed")
    for path, sha in p["sources"].items():
        if digest(Path(path)) != sha:
            raise ValueError("Frozen implementation changed")
    _, campaigns, registry = load_study(output / "config.json")
    if registry.key != p["registry"] or [c.key for c in campaigns] != p["campaigns"]:
        raise ValueError("Scientific identities changed")
    return p, campaigns, registry


def evaluate(output: Path) -> None:
    import numpy as np
    import torch
    from sb3_contrib import MaskablePPO

    from oligo_engine.molecular_design.candidate_encoding import encode_candidate
    from oligo_engine.molecular_design.gym_env import MolecularEnv
    from oligo_engine.molecular_design.optimizers import search
    from oligo_engine.molecular_design.scoring import Session
    from oligo_engine.molecular_design.training import load_policy, rollout

    p, campaigns, registry = load(output)
    torch.set_num_threads(1)
    rows = []
    for seed in p["seeds"]:
        models = {}
        for arm in ("full", "architecture"):
            entry = p["policies"][f"{arm}-{seed}"]
            directory, cfg = Path(entry["path"]), p["arms"][arm]
            receipt = json.loads((directory / "training.json").read_text())
            verify(receipt, entry["training_seal"])
            env = MolecularEnv(
                campaigns,
                registry,
                cfg["site_capacity"],
                cfg["archive_capacity"],
                candidate_capacity=cfg["candidate_capacity"],
                collapse_forced=cfg["collapse_forced"],
            )
            models[arm] = load_policy(directory, env)
            if arm == "full":
                warm = directory / "warm-start-policy.zip"
                if digest(warm) != entry["warm_start_sha256"]:
                    raise ValueError("Pretrained policy hash mismatch")
                models["warm_start"] = MaskablePPO.load(warm, env=env, device="cpu")
                models["warm_start"].policy.set_training_mode(False)
        for c in campaigns:
            for method in p["methods"]:
                stem = f"{c.target.gene}-{method}-{seed}"
                journal = QueryJournal(output / "runs" / f"{stem}.jsonl")
                if method in models:
                    cfg = p["arms"][
                        "architecture" if method == "architecture" else "full"
                    ]
                    env = MolecularEnv(
                        (c,),
                        registry,
                        cfg["site_capacity"],
                        cfg["archive_capacity"],
                        journal,
                        candidate_capacity=cfg["candidate_capacity"],
                        collapse_forced=cfg["collapse_forced"],
                    )
                    result = rollout(models[method], env, seed=seed)
                elif method == "prior":
                    designs = tuple(c.designs())
                    patterns = {p.name: p for p in c.profile.patterns}
                    features = np.stack(
                        [
                            encode_candidate(
                                d,
                                patterns[d.pattern],
                                max(p.length for p in c.profile.patterns),
                            )
                            for d in designs
                        ]
                    )
                    with torch.no_grad():
                        estimates = torch.sigmoid(
                            models["warm_start"].policy.molecular_predictions(
                                torch.as_tensor(features)
                            )
                        )
                        utility = (estimates[:, 0] * estimates[:, 1]).numpy()
                    order = sorted(
                        range(len(designs)),
                        key=lambda i: (-float(utility[i]), designs[i].key),
                    )
                    session = Session(c, registry, journal)
                    for i in order:
                        if not session.remaining:
                            break
                        if designs[i].key not in session.archive:
                            session.query(designs[i])
                    result = {
                        "method": "pretrained_prior_ranking",
                        "seed": seed,
                        "end_reason": "request_budget"
                        if not session.remaining
                        else "space_enumerated",
                        **session.receipt(),
                    }
                else:
                    result = search(Session(c, registry, journal), method, seed)
                if any(e["cache_hit"] for e in result["trace"]):
                    raise ValueError("Unexpected duplicate query")
                artifact = run_artifact(c, result)
                path = output / "runs" / f"{stem}.json"
                write_new(path, artifact)
                rows.append(
                    {
                        "target": c.target.gene,
                        "method": method,
                        "seed": seed,
                        "budget": p["budget"],
                        "quality": result["final_quality"],
                        "initial_quality": result["initial_quality"],
                        "requests": result["requests"],
                        "head_calls": sum(result["per_head_calls"].values()),
                        "eligible": sum(
                            e["score"]["eligible"] for e in result["trace"]
                        ),
                        "end_reason": result["end_reason"],
                        "artifact": str(path),
                        "seal": artifact["seal"],
                    }
                )
        print(json.dumps({"evaluated_seed": seed}), flush=True)
    write_new(output / "results.json", seal({"protocol_seal": p["seal"], "rows": rows}))


def report(output: Path) -> None:
    p, _, _ = load(output)
    parent = Path(p["parent"])
    base = json.loads((parent / "results.json").read_text())
    prior = json.loads((parent / "prior-control-results.json").read_text())
    extension = json.loads((output / "results.json").read_text())
    for result in (base, prior, extension):
        verify(result)
    if extension["protocol_seal"] != p["seal"]:
        raise ValueError("Extension results belong to a different protocol")
    rows = [x for x in base["rows"] if x["budget"] == 8]
    rows += [{**x, "method": "prior"} for x in prior["rows"] if x["budget"] == 8]
    rows += extension["rows"]
    summaries = []
    roles = {
        "DGAT2": "training",
        "CFB": "validation",
        "FGFR4": "previous development",
        "F9": "development",
        "F12": "development",
        "TTR": "development",
        "APOC3": "new development",
        "ANGPTL3": "new development; predictor-seen",
    }
    text = [
        "# Eight-target development comparison",
        "",
        (
            "Eight targets, eight scoring requests per run including the "
            "start, five policy seeds. Mean surrogate utility; no biological "
            "or confirmatory significance claim. Original six targets are "
            "preserved; APOC3/ANGPTL3 are a separately frozen extension."
        ),
        "",
        (
            "| Target / role | Revised PPO | Pretrained staged | Pretrained "
            "ranking | Random | Greedy |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    methods = ["full", "warm_start", "prior", "random", "greedy"]
    for target, role in roles.items():
        cells = []
        for method in methods + ["architecture"]:
            group = [x for x in rows if x["target"] == target and x["method"] == method]
            if len(group) != 5 or {x["seed"] for x in group} != set(p["seeds"]):
                raise ValueError("Incomplete target/method cell")
            mean = statistics.mean(x["quality"] for x in group)
            sd = statistics.stdev(x["quality"] for x in group)
            summaries.append(
                {
                    "target": target,
                    "role": role,
                    "method": method,
                    "mean": mean,
                    "sd": sd,
                    "mean_requests": statistics.mean(x["requests"] for x in group),
                }
            )
            if method in methods:
                cells.append(f"{mean:.4f} ± {sd:.4f}")
        text.append(f"| {target} / {role} | " + " | ".join(cells) + " |")
    text += [
        "",
        (
            "Sample SD measures seed variability, not cross-target "
            "confidence. ANGPTL3 appears in the active efficacy head's "
            "fitting and selection data. APOC3 has sparse measured metadata "
            "support; neither new target qualifies the current efficacy "
            "chemistry/context or independent risk support."
        ),
        "",
        (
            "All policy weights, reward definitions and screens remain "
            "frozen. New evaluation costs and ending reasons are in "
            "results.json. These two targets now join the development "
            "exposure ledger and must not be reused as fresh confirmation "
            "groups."
        ),
    ]
    write_new(
        output / "eight-target-summary.json",
        seal(
            {
                "protocol_seal": p["seal"],
                "summaries": summaries,
                "original_protocol_seal": p["parent_protocol_seal"],
            }
        ),
    )
    with (output / "eight-target-summary.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    (output / "report.md").write_text("\n".join(text) + "\n")
    print("\n".join(text))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "evaluate", "report"))
    parser.add_argument(
        "--parent", type=Path, default=Path("artifacts/molecular-policy-repair-v3")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.parent, args.output)
    elif args.phase == "evaluate":
        evaluate(args.output)
    else:
        report(args.output)


if __name__ == "__main__":
    main()
