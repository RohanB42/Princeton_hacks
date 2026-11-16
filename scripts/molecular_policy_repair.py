"""Freeze and run shared-candidate PPO repair and matched optimizer diagnostics."""

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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    config, old, registry = load_study(source)
    groups = {
        "training": ["DGAT2", "SOD1", "B2M", "HPRT1", "PCSK9", "VEGFA"],
        "validation": ["CFB", "F7"],
        "development": ["FGFR4", "F9", "F12", "TTR"],
    }
    campaigns, transcript_hashes = [], {}
    for partition, genes in groups.items():
        for gene in genes:
            path = Path(f"artifacts/transcripts/homo_sapiens.{gene}.json")
            raw = json.loads(path.read_text())
            transcript_hashes[str(path)] = sha(path)
            seq = raw["sequence"].upper().replace("U", "T")
            # Metadata-only fixed fractions, never optimized against predictions.
            for fraction in (0.2, 0.5, 0.8) if partition != "development" else (0.5,):
                start = int(len(seq) * fraction)
                target = Target(
                    gene,
                    raw["transcript_id"],
                    seq,
                    raw["species"],
                    raw["source"],
                    ((start, min(start + 48, len(seq))),),
                )
                c = replace(
                    old[0],
                    name=f"{gene}-region-{fraction}-repair-v3",
                    target=target,
                    partition=partition,
                    starts=((start, old[0].profile.patterns[0].name, "none"),),
                )
                if preflight(c, registry)["status"] == "blocked":
                    raise ValueError(f"Metadata coverage blocked: {c.name}")
                campaigns.append(c)
    audit = audit_partitions(tuple(campaigns))
    # Exact compound overlap must not cross optimizer partitions, either.
    membership = {}
    for c in campaigns:
        for d in c.designs():
            if d.compound_id in membership and membership[d.compound_id] != c.partition:
                raise ValueError("Compound crosses optimizer partitions")
            membership[d.compound_id] = c.partition
    capacity = max(sum(1 for _ in c.designs()) for c in campaigns)
    base = {
        "rollout_tokens": 256,
        "batch_size": 64,
        "epochs": 4,
        "learning_rate": 0.0003,
        "entropy": 0.01,
        "decoder": "transactional-v2",
        "site_capacity": max(len(c.target.sequence) for c in campaigns),
        "archive_capacity": 32,
        "policy": "candidate-v3",
        "candidate_capacity": capacity,
    }
    arms = {
        "architecture": {
            **base,
            "total_tokens": 2048,
            "validation_interval": 1024,
            "collapse_forced": False,
        },
        "full": {
            **base,
            "total_tokens": 16384,
            "validation_interval": 4096,
            "collapse_forced": True,
            "pretrain_requests": 32,
            "pretrain_epochs": 20,
        },
    }
    config["campaigns"] = [asdict(c) for c in campaigns]
    config["qualification"] = (
        "Frozen-surrogate extrapolation diagnostic; no biological or final evidence"
    )
    write_new(output / "config.json", config)
    write_new(
        output / "protocol.json",
        seal(
            {
                "schema": "candidate-policy-repair-v3",
                "seeds": list(range(800, 805)),
                "budgets": [8, 32],
                "primary_budget": 8,
                "primary_outcome": "final eligible archive utility",
                "groups": groups,
                "partition_audit": audit,
                "arms": arms,
                "evaluation_campaigns": [
                    c.key
                    for c in campaigns
                    if "region-0.5-" in c.name
                    and c.target.gene in {"DGAT2", "CFB", "FGFR4", "F9", "F12", "TTR"}
                ],
                "methods": ["full", "architecture", "warm_start", "random", "greedy"],
                "primary_targets": groups["development"],
                "previously_inspected_targets": ["DGAT2", "CFB", "FGFR4"],
                "policy_only_unseen_targets": ["F9", "F12", "TTR"],
                "predictor_exposure": (
                    "Not qualified as held-out from supervised heads; "
                    "surrogate-only evaluation"
                ),
                "training_schedule": (
                    "fixed, no outcome-driven extension; "
                    "six training genes and three windows each"
                ),
                "architecture_arm": (
                    "DGAT2 midpoint only; original CFB midpoint checkpoint selection; "
                    "no warm start or forced collapse"
                ),
                "full_arm": (
                    "18 training campaigns; six validation campaigns across CFB/F7; "
                    "warm-start surrogate queries separately costed"
                ),
                "statistics": (
                    "per-target five-seed mean and sample SD; "
                    "no confirmatory significance or biological claim"
                ),
                "secondary_budget": (
                    "32 requests tests extrapolation beyond eight-request training"
                ),
                "config_sha256": sha(output / "config.json"),
                "registry": registry.key,
                "transcripts": transcript_hashes,
                "sources": {
                    str(p): sha(p)
                    for p in sorted(
                        Path("src/oligo_engine/molecular_design").glob("*.py")
                    )
                },
            }
        ),
    )


def load(output: Path) -> tuple:
    protocol = json.loads((output / "protocol.json").read_text())
    verify(protocol)
    if sha(output / "config.json") != protocol["config_sha256"]:
        raise ValueError("Frozen configuration changed")
    for path, digest in protocol["sources"].items():
        if sha(Path(path)) != digest:
            raise ValueError(f"Frozen implementation changed: {path}")
    _, campaigns, registry = load_study(output / "config.json")
    if registry.key != protocol["registry"]:
        raise ValueError("Frozen scorer changed")
    return protocol, campaigns, registry


def train_arm(output: Path, seed: int, arm: str) -> None:
    from oligo_engine.molecular_design.training import TrainingConfig, train

    p, campaigns, registry = load(output)
    if seed not in p["seeds"]:
        raise ValueError("Unregistered seed")
    training = tuple(c for c in campaigns if c.partition == "training")
    validation = tuple(c for c in campaigns if c.partition == "validation")
    if arm == "architecture":
        training = tuple(
            c for c in training if c.target.gene == "DGAT2" and "region-0.5-" in c.name
        )
        validation = tuple(
            c for c in validation if c.target.gene == "CFB" and "region-0.5-" in c.name
        )
    result = train(
        training,
        validation,
        registry,
        TrainingConfig(seed=seed, **p["arms"][arm]),
        output / f"{arm}-{seed}",
    )
    print(
        json.dumps(
            {
                "arm": arm,
                "seed": seed,
                "status": result["status"],
                "requests": result["training_requests"],
            }
        ),
        flush=True,
    )


def evaluate(output: Path) -> None:
    import torch
    from sb3_contrib import MaskablePPO

    from oligo_engine.molecular_design.evaluation import quality_auc
    from oligo_engine.molecular_design.gym_env import MolecularEnv
    from oligo_engine.molecular_design.optimizers import search
    from oligo_engine.molecular_design.scoring import Session
    from oligo_engine.molecular_design.training import load_policy, rollout

    p, campaigns, registry = load(output)
    torch.set_num_threads(1)
    evaluation = tuple(c for c in campaigns if c.key in p["evaluation_campaigns"])
    rows, costs = [], []
    for seed in p["seeds"]:
        models = {}
        for arm, cfg in p["arms"].items():
            directory = output / f"{arm}-{seed}"
            receipt = json.loads((directory / "training.json").read_text())
            verify(receipt)
            if (
                any(receipt["protocol"]["config"][k] != v for k, v in cfg.items())
                or receipt["protocol"]["config"]["seed"] != seed
            ):
                raise ValueError("Training arm settings changed")
            for partition in ("training", "validation"):
                expected = {
                    c.key
                    for c in campaigns
                    if c.partition == partition
                    and (
                        arm == "full"
                        or (
                            c.target.gene
                            == ("DGAT2" if partition == "training" else "CFB")
                            and "region-0.5-" in c.name
                        )
                    )
                }
                if set(receipt["protocol"][partition]) != expected:
                    raise ValueError("Policy campaign membership changed")
            if arm == "full":
                warm = json.loads((directory / "pretraining.json").read_text())
                verify(warm, receipt["pretraining_seal"])
                if any(
                    x["campaign_id"] not in receipt["protocol"]["training"]
                    for x in warm["identities"]
                ):
                    raise ValueError("Non-training warm-start query")
            costs.append(
                {
                    "arm": arm,
                    "seed": seed,
                    **{
                        k: receipt[k]
                        for k in (
                            "training_requests",
                            "training_head_calls",
                            "pretraining_requests",
                            "pretraining_head_calls",
                            "validation_requests",
                            "selected_tokens",
                            "training_seconds",
                        )
                    },
                }
            )
            env = MolecularEnv(
                evaluation,
                registry,
                cfg["site_capacity"],
                cfg["archive_capacity"],
                candidate_capacity=cfg["candidate_capacity"],
                collapse_forced=cfg["collapse_forced"],
            )
            models[arm] = load_policy(directory, env)
            if arm == "full":
                if (
                    sha(directory / "warm-start-policy.zip")
                    != receipt["warm_start_sha256"]
                ):
                    raise ValueError("Warm-start policy changed")
                models["warm_start"] = MaskablePPO.load(
                    directory / "warm-start-policy.zip", env=env, device="cpu"
                )
        for budget in p["budgets"]:
            for c in evaluation:
                campaign = replace(c, requests=budget, tokens=max(c.tokens, budget * 8))
                for method in p["methods"]:
                    stem = f"{c.target.gene}-{method}-{seed}-b{budget}"
                    journal = QueryJournal(output / "runs" / f"{stem}.jsonl")
                    if method in models:
                        cfg = p["arms"][
                            "architecture" if method == "architecture" else "full"
                        ]
                        env = MolecularEnv(
                            (campaign,),
                            registry,
                            cfg["site_capacity"],
                            cfg["archive_capacity"],
                            journal,
                            candidate_capacity=cfg["candidate_capacity"],
                            collapse_forced=cfg["collapse_forced"],
                        )
                        result = rollout(models[method], env, seed=seed)
                    else:
                        result = search(
                            Session(campaign, registry, journal), method, seed
                        )
                    if any(e["cache_hit"] for e in result["trace"]):
                        raise ValueError("Unexpected repeated query")
                    artifact = run_artifact(campaign, result)
                    path = output / "runs" / f"{stem}.json"
                    write_new(path, artifact)
                    rows.append(
                        {
                            "target": c.target.gene,
                            "partition": c.partition,
                            "seed": seed,
                            "method": method,
                            "budget": budget,
                            "quality": result["final_quality"],
                            "initial_quality": result["initial_quality"],
                            "archive_gain": result["final_quality"]
                            - result["initial_quality"],
                            "new_proposals": sum(
                                not e["initial"] for e in result["trace"]
                            ),
                            "auc": quality_auc(result, budget),
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
    write_new(
        output / "results.json",
        seal(
            {
                "protocol_seal": p["seal"],
                "rows": rows,
                "costs": costs,
                "evaluation_driver_sha256": sha(Path(__file__)),
            }
        ),
    )
    with (output / "results.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def report(output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    p, _, _ = load(output)
    result = json.loads((output / "results.json").read_text())
    verify(result)
    rows = result["rows"]
    targets = list(dict.fromkeys(r["target"] for r in rows))
    summaries = []
    text = [
        "# Shared-candidate policy repair",
        "",
        "Five policy seeds; frozen surrogate diagnostic. Values are utility mean "
        "± seed SD, not measured efficacy or confidence intervals.",
        "",
        "| Target | Full PPO | Architecture only | "
        "Warm start, no PPO | Random | Greedy |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for target in targets:
        cells = []
        for budget in p["budgets"]:
            for method in p["methods"]:
                group = [
                    r
                    for r in rows
                    if (r["target"], r["budget"], r["method"])
                    == (target, budget, method)
                ]
                if len(group) != 5 or {r["seed"] for r in group} != set(p["seeds"]):
                    raise ValueError("Incomplete evaluation arm")
                mean = statistics.mean(r["quality"] for r in group)
                sd = statistics.stdev(r["quality"] for r in group)
                summaries.append(
                    {
                        "target": target,
                        "method": method,
                        "budget": budget,
                        "mean": mean,
                        "sd": sd,
                        "mean_requests": statistics.mean(r["requests"] for r in group),
                        "successes": sum(r["eligible"] > 0 for r in group),
                        "mean_gain": statistics.mean(r["archive_gain"] for r in group),
                    }
                )
                if budget == p["primary_budget"]:
                    cells.append(f"{mean:.4f} ± {sd:.4f}")
        text.append(f"| {target} | " + " | ".join(cells) + " |")
    text += [
        "",
        "Primary cap: eight scoring requests including the start.",
        "",
        "| Target | Full PPO mean queries | Warm-start mean queries |",
        "| --- | ---: | ---: |",
    ]
    for target in targets:
        actual = {
            s["method"]: s["mean_requests"]
            for s in summaries
            if s["target"] == target and s["budget"] == p["primary_budget"]
        }
        text.append(f"| {target} | {actual['full']:.1f} | {actual['warm_start']:.1f} |")
    for arm in ("full", "architecture"):
        costs = [c for c in result["costs"] if c["arm"] == arm]
        text += [
            "",
            f"{arm}: {sum(c['training_requests'] for c in costs)} PPO "
            f"training requests + {sum(c['pretraining_requests'] for c in costs)} "
            f"pretraining requests + {sum(c['validation_requests'] for c in costs)} "
            "checkpoint-validation requests across five policies.",
        ]
    contrasts = []
    for target in targets:
        for budget in p["budgets"]:
            for control in ("architecture", "warm_start", "random", "greedy"):
                diffs = []
                for seed in p["seeds"]:
                    pair = {
                        r["method"]: r["quality"]
                        for r in rows
                        if (r["target"], r["budget"], r["seed"])
                        == (target, budget, seed)
                    }
                    diffs.append(pair["full"] - pair[control])
                contrasts.append(
                    {
                        "target": target,
                        "budget": budget,
                        "control": control,
                        "mean": statistics.mean(diffs),
                        "sd": statistics.stdev(diffs),
                        "wins": sum(d > 1e-12 for d in diffs),
                        "ties": sum(abs(d) <= 1e-12 for d in diffs),
                        "losses": sum(d < -1e-12 for d in diffs),
                    }
                )
    write_new(
        output / "summary.json",
        seal(
            {"protocol_seal": p["seal"], "summaries": summaries, "contrasts": contrasts}
        ),
    )
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True)
    colors = {
        "full": "#2458a4",
        "warm_start": "#8755a8",
        "random": "#32936f",
        "greedy": "#c16a17",
    }
    for ax, target in zip(axes.flat, p["primary_targets"], strict=True):
        for method, color in colors.items():
            entries = [
                s for s in summaries if s["target"] == target and s["method"] == method
            ]
            ax.errorbar(
                [s["budget"] for s in entries],
                [s["mean"] for s in entries],
                yerr=[s["sd"] for s in entries],
                marker="o",
                capsize=3,
                color=color,
                label=method.replace("_", " "),
            )
        ax.set_title(
            target
            + (" · previously inspected" if target == "FGFR4" else " · policy-unseen")
        )
        ax.set_xticks(p["budgets"])
        ax.set_ylim(-0.05, 1.05)
        ax.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=8)
    fig.supxlabel("Scoring-request cap, including starting design")
    fig.supylabel("Best eligible surrogate utility (mean ± seed SD)")
    fig.suptitle("Shared-candidate PPO repair · five seeds · no biological validation")
    fig.tight_layout()
    fig.savefig(output / "comparison.png", dpi=160)
    fig.savefig(output / "comparison.pdf")
    plt.close(fig)
    text += [
        "",
        "The full arm combines shared molecular scoring, forced-transition collapse, "
        "broader training and surrogate warm start. Architecture-only changes the "
        "molecular scorer at the original training scale. Warm start uses the full "
        "arm's pre-PPO weights. This does not isolate every interaction.",
        "",
        "DGAT2 and CFB retain training/selection roles. FGFR4 was inspected before. "
        "F9/F12/TTR were excluded from policy fitting and checkpoint selection, "
        "but are not qualified independent biological evaluation targets. "
        "No final measured labels were read.",
        "",
        "Budgets exclude separately reported policy training/pretraining costs in "
        "results.json. Early stopping retains the archive; actual queries and "
        "ending reasons are reported. No policy tuning uses these evaluation results. "
        "The 32-request cap extrapolates beyond eight-request training episodes.",
        "",
        "![Curves](comparison.png)",
    ]
    (output / "report.md").write_text("\n".join(text) + "\n")
    print("\n".join(text[:20]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "train", "evaluate", "report"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--arm", choices=("architecture", "full"))
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.config, args.output)
    elif args.phase == "train":
        train_arm(args.output, args.seed, args.arm)
    elif args.phase == "evaluate":
        evaluate(args.output)
    else:
        report(args.output)


if __name__ == "__main__":
    main()
