"""Locked development comparison of corrected PPO and history-aware controls."""

import argparse
import csv
import hashlib
import json
import statistics
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from oligo_engine.molecular_design.artifacts import (
    QueryJournal,
    run_artifact,
    seal,
    verify,
    write_new,
)
from oligo_engine.molecular_design.cli import load_study


def prepare(config: Path, output: Path, existing: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    value, campaigns, registry = load_study(config)
    if any(c.partition == "final" or c.requests != 8 for c in campaigns):
        raise ValueError("This development protocol requires eight-request campaigns")
    write_new(output / "config.json", value)
    policies = {}
    for seed in range(700, 705):
        path = (
            existing / f"batch-64/seed-{seed}"
            if seed <= 702
            else output / f"policy-{seed}"
        )
        entry = {"path": str(path), "reused": seed <= 702}
        if entry["reused"]:
            training = json.loads((path / "training.json").read_text())
            verify(training)
            entry["training_seal"] = training["seal"]
            entry["policy_sha256"] = training["policy_sha256"]
        policies[str(seed)] = entry
    write_new(
        output / "protocol.json",
        seal(
            {
                "scope": "previously used development targets; no final outcomes",
                "seeds": list(range(700, 705)),
                "budgets": [2, 4, 8],
                "primary_budget": 8,
                "primary_outcome": "best eligible archive utility",
                "contrasts": ["ppo minus random", "ppo minus greedy"],
                "secondary": [
                    "request-indexed quality AUC",
                    "screen retention",
                    "actual costs",
                ],
                "methods": ["ppo", "random", "greedy"],
                "baseline_version": "queried-history-v2",
                "policy_decoder": "transactional-v2",
                "inference": "deterministic",
                "policies": policies,
                "registry": registry.key,
                "campaigns": [c.key for c in campaigns],
                "config_sha256": hashlib.sha256(
                    (output / "config.json").read_bytes()
                ).hexdigest(),
                "training": {
                    "total_tokens": 2048,
                    "rollout_tokens": 256,
                    "batch_size": 64,
                    "epochs": 4,
                    "learning_rate": 0.0003,
                    "entropy": 0.01,
                    "validation_interval": 1024,
                    "decoder": "transactional-v2",
                    "site_capacity": max(len(c.target.sequence) for c in campaigns),
                    "archive_capacity": 8,
                },
                "statistics": (
                    "mean and sample SD over five paired seeds, separately per "
                    "target; no cross-target generalization interval"
                ),
                "reuse_note": (
                    "Seeds 700-702 already inspected during repair; this is a "
                    "development extension, not a fresh confirmatory test"
                ),
                "source_sha256": {
                    str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (
                        Path("src/oligo_engine/molecular_design/optimizers.py"),
                        Path("src/oligo_engine/molecular_design/grammar.py"),
                        Path("src/oligo_engine/molecular_design/training.py"),
                    )
                },
            }
        ),
    )


def load(output: Path) -> tuple:
    protocol = json.loads((output / "protocol.json").read_text())
    verify(protocol)
    if (
        hashlib.sha256((output / "config.json").read_bytes()).hexdigest()
        != protocol["config_sha256"]
    ):
        raise ValueError("Locked configuration changed")
    _, campaigns, registry = load_study(output / "config.json")
    if (
        registry.key != protocol["registry"]
        or [c.key for c in campaigns] != protocol["campaigns"]
    ):
        raise ValueError("Scientific identities changed")
    for path, digest in protocol["source_sha256"].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Locked source changed: {path}")
    return protocol, campaigns, registry


def train_seed(output: Path, seed: int) -> None:
    from oligo_engine.molecular_design.training import TrainingConfig, train

    protocol, campaigns, registry = load(output)
    entry = protocol["policies"][str(seed)]
    if entry["reused"]:
        raise ValueError("Existing policies must not be retrained or replaced")
    result = train(
        tuple(c for c in campaigns if c.partition == "training"),
        tuple(c for c in campaigns if c.partition == "validation"),
        registry,
        TrainingConfig(seed=seed, **protocol["training"]),
        Path(entry["path"]),
    )
    print(json.dumps({"seed": seed, "status": result["status"]}))


def evaluate(output: Path) -> None:
    import torch

    from oligo_engine.molecular_design.evaluation import quality_auc
    from oligo_engine.molecular_design.gym_env import MolecularEnv
    from oligo_engine.molecular_design.optimizers import search
    from oligo_engine.molecular_design.scoring import Session
    from oligo_engine.molecular_design.training import load_policy, rollout

    protocol, campaigns, registry = load(output)
    rows, costs = [], []
    torch.set_num_threads(1)
    for seed in protocol["seeds"]:
        entry = protocol["policies"][str(seed)]
        directory = Path(entry["path"])
        training = json.loads((directory / "training.json").read_text())
        verify(training, entry.get("training_seal"))
        for key, value in protocol["training"].items():
            if training["protocol"]["config"][key] != value:
                raise ValueError("Policy training settings differ")
        if training["protocol"]["config"]["seed"] != seed:
            raise ValueError("Policy seed mismatch")
        costs.append(
            {
                "seed": seed,
                "path": str(directory),
                **{
                    k: training[k]
                    for k in (
                        "training_requests",
                        "training_head_calls",
                        "validation_requests",
                        "training_seconds",
                        "selected_tokens",
                    )
                },
                "training_seal": training["seal"],
            }
        )
        loading_env = MolecularEnv(
            campaigns, registry, protocol["training"]["site_capacity"], 8
        )
        model = load_policy(directory, loading_env)
        for budget in protocol["budgets"]:
            tasks = tuple(replace(c, requests=budget) for c in campaigns)
            env = MolecularEnv(
                tasks, registry, protocol["training"]["site_capacity"], 8
            )
            for index, campaign in enumerate(tasks):
                for method in protocol["methods"]:
                    stem = (
                        f"{campaign.target.gene}-{method}-seed-{seed}-budget-{budget}"
                    )
                    journal = QueryJournal(output / "runs" / f"{stem}.jsonl")
                    env.on_receipt = journal
                    start = perf_counter()
                    receipt = (
                        rollout(model, env, index, seed)
                        if method == "ppo"
                        else search(Session(campaign, registry, journal), method, seed)
                    )
                    seconds = perf_counter() - start
                    if any(e["cache_hit"] for e in receipt["trace"]):
                        raise RuntimeError(
                            "Repeated score request in deduplicated comparison"
                        )
                    artifact = run_artifact(campaign, receipt)
                    write_new(output / "runs" / f"{stem}.json", artifact)
                    unique = {e["design_id"]: e for e in receipt["trace"]}
                    rows.append(
                        {
                            "target": campaign.target.gene,
                            "partition": campaign.partition,
                            "seed": seed,
                            "method": method,
                            "budget": budget,
                            "quality": receipt["final_quality"],
                            "auc": quality_auc(receipt, budget),
                            "requests": receipt["requests"],
                            "head_calls": sum(receipt["per_head_calls"].values()),
                            "unique_designs": receipt["unique_designs"],
                            "eligible_designs": sum(
                                e["score"]["eligible"] for e in unique.values()
                            ),
                            "screen_retention": sum(
                                e["score"]["eligible"] for e in unique.values()
                            )
                            / len(unique),
                            "seconds": seconds,
                            "end_reason": receipt["end_reason"],
                            "artifact": str(output / "runs" / f"{stem}.json"),
                            "seal": artifact["seal"],
                        }
                    )
        print(json.dumps({"evaluated_seed": seed}), flush=True)
    write_new(
        output / "results.json",
        seal(
            {
                "protocol_seal": protocol["seal"],
                "records": rows,
                "training_costs": costs,
                "evidence": "computational development diagnostic only",
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
    import numpy as np

    protocol, campaigns, _ = load(output)
    result = json.loads((output / "results.json").read_text())
    verify(result)
    rows = result["records"]
    summaries, contrasts = [], []
    fig, axes = plt.subplots(1, len(campaigns), figsize=(13, 5), sharey=True)
    colors = {"ppo": "#2458a4", "random": "#32936f", "greedy": "#c16a17"}
    for ax, campaign in zip(axes, campaigns, strict=True):
        gene = campaign.target.gene
        for method in protocol["methods"]:
            means, stds = [], []
            for budget in protocol["budgets"]:
                group = [
                    r
                    for r in rows
                    if r["target"] == gene
                    and r["method"] == method
                    and r["budget"] == budget
                ]
                if len(group) != 5 or {r["seed"] for r in group} != set(
                    protocol["seeds"]
                ):
                    raise ValueError("Incomplete study arm")
                values = [r["quality"] for r in group]
                mean, sd = statistics.mean(values), statistics.stdev(values)
                means.append(mean)
                stds.append(sd)
                summaries.append(
                    {
                        "target": gene,
                        "partition": campaign.partition,
                        "method": method,
                        "budget": budget,
                        "mean_quality": mean,
                        "seed_sample_sd": sd,
                        "mean_auc": statistics.mean(r["auc"] for r in group),
                        "mean_requests": statistics.mean(r["requests"] for r in group),
                        "successful_runs": sum(
                            r["eligible_designs"] > 0 for r in group
                        ),
                    }
                )
            ax.plot(
                protocol["budgets"],
                means,
                "o-",
                color=colors[method],
                label=method.upper() if method == "ppo" else method.title(),
            )
            ax.fill_between(
                protocol["budgets"],
                np.maximum(0, np.array(means) - stds),
                np.minimum(1, np.array(means) + stds),
                alpha=0.12,
                color=colors[method],
            )
        for budget in protocol["budgets"]:
            for baseline in ("random", "greedy"):
                differences = []
                for seed in protocol["seeds"]:
                    pair = {
                        r["method"]: r["quality"]
                        for r in rows
                        if r["target"] == gene
                        and r["budget"] == budget
                        and r["seed"] == seed
                    }
                    differences.append(pair["ppo"] - pair[baseline])
                contrasts.append(
                    {
                        "target": gene,
                        "budget": budget,
                        "baseline": baseline,
                        "mean_paired_difference": statistics.mean(differences),
                        "paired_seed_sample_sd": statistics.stdev(differences),
                        "wins": sum(x > 1e-12 for x in differences),
                        "ties": sum(abs(x) <= 1e-12 for x in differences),
                        "losses": sum(x < -1e-12 for x in differences),
                    }
                )
        ax.set_title(f"{gene} · {campaign.partition}")
        ax.set_xlabel("Scoring-request cap (includes start)")
        ax.set_xticks(protocol["budgets"])
        ax.set_ylim(-0.03, 1.03)
        ax.grid(alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Best eligible archive utility (0–1)")
    axes[-1].legend(loc="upper right")
    fig.suptitle(
        "Corrected PPO vs random and greedy · five paired seeds",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.025,
        "Frozen predictors and screens; no repeated queries. Shading: seed SD "
        "clipped to 0–1, not a confidence interval.\nPreviously used development "
        "campaigns; surrogate scores are not biological validation.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.11, 1, 0.93))
    fig.savefig(output / "comparison.png", dpi=180)
    fig.savefig(output / "comparison.pdf")
    plt.close(fig)
    write_new(
        output / "summary.json",
        seal(
            {
                "protocol_seal": protocol["seal"],
                "summaries": summaries,
                "contrasts": contrasts,
                "cross_target_confidence_interval": None,
                "reason": "no independent final target groups",
            }
        ),
    )
    text = [
        "# Corrected PPO versus random and greedy",
        "",
        "Five paired seeds (700–704), three previously used diagnostic targets; "
        "budgets 2, 4 and 8. Primary budget: 8.",
        "PPO uses five independently trained policies, each with 2,048 training "
        "actions and batch size 64. Seeds 700–702 were reused from the repair; "
        "703–704 were trained with identical settings. Both controls avoid "
        "repeated queries and use the same frozen scorer, starting design "
        "and legal candidate space.",
        "",
        "| Target / partition | PPO mean ± seed SD | "
        "Random mean ± seed SD | Greedy mean ± seed SD |",
        "| --- | ---: | ---: | ---: |",
    ]
    for c in campaigns:
        cells = []
        for m in protocol["methods"]:
            s = next(
                s
                for s in summaries
                if s["target"] == c.target.gene
                and s["method"] == m
                and s["budget"] == 8
            )
            cells.append(f"{s['mean_quality']:.4f} ± {s['seed_sample_sd']:.4f}")
        text.append(f"| {c.target.gene} / {c.partition} | " + " | ".join(cells) + " |")
    text += [
        "",
        "Scores are normalized surrogate archive utility, not efficacy percentages. "
        "SD is variation over seeds, not a confidence interval. DGAT2 trained the "
        "policies; CFB selected checkpoints; FGFR4 was previously used in "
        "development. No final outcomes were read, and no cross-target/"
        "generalization claim is supported.",
        "",
        "## Primary paired contrasts",
        "",
        "| Target | PPO minus | Mean difference | Wins / ties / losses |",
        "| --- | --- | ---: | ---: |",
    ]
    for c in contrasts:
        if c["budget"] == 8:
            text.append(
                f"| {c['target']} | {c['baseline']} | "
                f"{c['mean_paired_difference']:+.4f} | "
                f"{c['wins']} / {c['ties']} / {c['losses']} |"
            )
    costs = result["training_costs"]
    text += [
        "",
        "PPO training cost across five policies: "
        f"{sum(c['training_requests'] for c in costs)} scoring requests, "
        f"{sum(c['training_head_calls'] for c in costs)} head calls, plus "
        f"{sum(c['validation_requests'] for c in costs)} checkpoint-validation "
        "requests. Baselines have no policy-training cost. Training costs are "
        "excluded from the common deployment cap but are reported separately.",
        "",
        "The baseline correction is versioned `queried-history-v2`: random uses "
        "a uniform permutation of unqueried designs; greedy reads known neighbor "
        "scores from its archive and spends new requests only on unqueried "
        "designs. Earlier baseline results remain historical, not silently "
        "pooled here.",
        "",
        "![Comparison](comparison.png)",
        "",
        "Raw runs: runs/. Machine-readable summaries: summary.json. All rows and "
        "costs: results.json and results.csv. Frozen protocol: protocol.json.",
    ]
    (output / "report.md").write_text("\n".join(text) + "\n")
    print("\n".join(text[:10]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "train", "evaluate", "report"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--existing", type=Path)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.config, args.output, args.existing)
    elif args.phase == "train":
        train_seed(args.output, args.seed)
    elif args.phase == "evaluate":
        evaluate(args.output)
    else:
        report(args.output)


if __name__ == "__main__":
    main()
