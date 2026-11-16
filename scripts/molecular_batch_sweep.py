"""Fixed development-only PPO minibatch sweep and honest loss/quality plots."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from oligo_engine.molecular_design.artifacts import (
    QueryJournal,
    run_artifact,
    seal,
    verify,
    write_new,
)
from oligo_engine.molecular_design.cli import load_study


def prepare(config: Path, output: Path, batch_size: int | None = None) -> None:
    if output.exists():
        raise FileExistsError(output)
    value, campaigns, registry = load_study(config)
    if any(c.partition == "final" for c in campaigns):
        raise ValueError("Batch-size tuning cannot use final campaigns")
    write_new(output / "config.json", value)
    write_new(
        output / "protocol.json",
        seal(
            {
                "scope": "development-only multi-endpoint diagnostic",
                "config_sha256": hashlib.sha256(
                    (output / "config.json").read_bytes()
                ).hexdigest(),
                "registry": registry.key,
                "campaigns": [c.key for c in campaigns],
                "batch_sizes": [batch_size] if batch_size else [32, 64, 128],
                "seeds": [700, 701, 702],
                "total_tokens": 2048,
                "rollout_tokens": 256,
                "epochs": 4,
                "learning_rate": 0.0003,
                "entropy": 0.01,
                "validation_interval": 1024,
                "decoder": "transactional-v2",
                "primary_error": (
                    "SB3 mean critic MSE over final rollout update minibatches/epochs"
                ),
                "performance": (
                    "selected checkpoint final archive quality; "
                    "same starts and 8-request cap"
                ),
                "comparison": "random and greedy, both fixed; no final outcomes",
                "caveat": (
                    "On-policy targets differ across runs; critic loss is not "
                    "molecular prediction error. Fixed samples/epochs imply "
                    "different optimizer-step counts."
                ),
            }
        ),
    )


def run(output: Path, batch_size: int, seed: int | None = None) -> None:
    from oligo_engine.molecular_design.gym_env import MolecularEnv
    from oligo_engine.molecular_design.training import (
        TrainingConfig,
        load_policy,
        rollout,
        train,
    )

    protocol = json.loads((output / "protocol.json").read_text())
    verify(protocol)
    if (
        hashlib.sha256((output / "config.json").read_bytes()).hexdigest()
        != protocol["config_sha256"]
    ):
        raise ValueError("Sweep configuration changed")
    _, campaigns, registry = load_study(output / "config.json")
    if (
        batch_size not in protocol["batch_sizes"]
        or registry.key != protocol["registry"]
    ):
        raise ValueError("Unregistered sweep arm")
    if seed is not None and seed not in protocol["seeds"]:
        raise ValueError("Unregistered training seed")
    for seed in [seed] if seed is not None else protocol["seeds"]:
        directory = output / f"batch-{batch_size}" / f"seed-{seed}"
        config = TrainingConfig(
            seed=seed,
            batch_size=batch_size,
            decoder=protocol.get("decoder", "legacy-v1"),
            **{
                k: protocol[k]
                for k in (
                    "total_tokens",
                    "rollout_tokens",
                    "epochs",
                    "learning_rate",
                    "entropy",
                    "validation_interval",
                )
            },
            site_capacity=max(len(c.target.sequence) for c in campaigns),
            archive_capacity=max(c.requests for c in campaigns),
        )
        result = train(
            tuple(c for c in campaigns if c.partition == "training"),
            tuple(c for c in campaigns if c.partition == "validation"),
            registry,
            config,
            directory,
        )
        env = MolecularEnv(
            campaigns,
            registry,
            config.site_capacity,
            config.archive_capacity,
            decoder=config.decoder,
        )
        model = load_policy(directory, env)
        evaluations = []
        for i, campaign in enumerate(campaigns):
            env.on_receipt = QueryJournal(directory / f"eval-{i}.jsonl")
            receipt = rollout(model, env, i, seed)
            write_new(directory / f"eval-{i}.json", run_artifact(campaign, receipt))
            evaluations.append(
                {
                    "gene": campaign.target.gene,
                    "partition": campaign.partition,
                    "quality": receipt["final_quality"],
                    "requests": receipt["requests"],
                    "initial_quality": receipt["initial_quality"],
                }
            )
        write_new(
            directory / "sweep-arm.json",
            seal(
                {
                    "config": asdict(config),
                    "evaluations": evaluations,
                    "last_update": result["optimization_history"][-1],
                    "training_requests": result["training_requests"],
                    "training_head_calls": result["training_head_calls"],
                    "selected_tokens": result["selected_tokens"],
                }
            ),
        )
        print(
            json.dumps({"batch": batch_size, "seed": seed, "complete": True}),
            flush=True,
        )


def plot(output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from oligo_engine.molecular_design.optimizers import search
    from oligo_engine.molecular_design.scoring import Session

    protocol = json.loads((output / "protocol.json").read_text())
    verify(protocol)
    digest = hashlib.sha256((output / "config.json").read_bytes()).hexdigest()
    if digest != protocol["config_sha256"]:
        raise ValueError("Sweep configuration changed before plotting")
    _, campaigns, registry = load_study(output / "config.json")
    if registry.key != protocol["registry"]:
        raise ValueError("Sweep scorer changed before plotting")
    rows, losses, qualities = [], [], []
    for batch in protocol["batch_sizes"]:
        batch_losses, batch_qualities = [], []
        for seed in protocol["seeds"]:
            arm = json.loads(
                (output / f"batch-{batch}/seed-{seed}/sweep-arm.json").read_text()
            )
            verify(arm)
            if arm["config"]["batch_size"] != batch or arm["config"]["seed"] != seed:
                raise ValueError("Arm identity mismatch")
            loss = arm["last_update"]["metrics"]["value_loss"]
            validation = [
                e["quality"]
                for e in arm["evaluations"]
                if e["partition"] == "validation"
            ]
            quality = float(np.mean(validation))
            batch_losses.append(loss)
            batch_qualities.append(quality)
            for evaluation in arm["evaluations"]:
                rows.append(
                    {
                        "batch_size": batch,
                        "seed": seed,
                        "method": "ppo",
                        "critic_mse": loss,
                        "training_requests": arm["training_requests"],
                        "optimizer_steps": protocol["total_tokens"]
                        * protocol["epochs"]
                        // batch,
                        **evaluation,
                    }
                )
        losses.append(batch_losses)
        qualities.append(batch_qualities)
    baselines = {}
    for method in ("random", "greedy"):
        validation = []
        for campaign in campaigns:
            for seed in protocol["seeds"]:
                path = output / "controls" / f"{campaign.target.gene}-{method}-{seed}"
                receipt = search(
                    Session(
                        campaign, registry, QueryJournal(path.with_suffix(".jsonl"))
                    ),
                    method,
                    seed,
                )
                write_new(path.with_suffix(".json"), run_artifact(campaign, receipt))
                if campaign.partition == "validation":
                    validation.append(receipt["final_quality"])
                rows.append(
                    {
                        "batch_size": None,
                        "seed": seed,
                        "method": method,
                        "critic_mse": None,
                        "training_requests": 0,
                        "optimizer_steps": 0,
                        "gene": campaign.target.gene,
                        "partition": campaign.partition,
                        "quality": receipt["final_quality"],
                        "requests": receipt["requests"],
                        "initial_quality": receipt["initial_quality"],
                    }
                )
        baselines[method] = validation
    with (output / "results.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    batches = np.array(protocol["batch_sizes"])
    losses, qualities = np.asarray(losses), np.asarray(qualities)
    plt.rcParams.update(
        {"font.size": 11, "axes.spines.top": False, "axes.spines.right": False}
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
    for i, (axis, values) in enumerate(zip(axes, (losses, qualities), strict=True)):
        for j, seed in enumerate(protocol["seeds"]):
            axis.plot(
                batches,
                values[:, j],
                "o--",
                alpha=0.4,
                linewidth=1,
                label=f"Seed {seed}",
            )
        axis.plot(
            batches,
            values.mean(axis=1),
            "o-",
            color="#183b56",
            linewidth=2.5,
            label="PPO mean, 3 seeds",
        )
        axis.set_xticks(batches)
        axis.set_xlabel("PPO minibatch size (action transitions)")
        axis.grid(alpha=0.18)
        axis.set_title(
            "Training error at 2,048 actions"
            if i == 0
            else "Validation search performance"
        )
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Critic MSE, final update (log scale)")
    axes[0].legend(fontsize=8)
    axes[1].set_ylabel("Mean best eligible archive utility (0–1)")
    for method, color in (("random", "#b26000"), ("greedy", "#17805c")):
        vals = baselines[method]
        axes[1].axhline(
            np.mean(vals),
            color=color,
            linestyle=":" if method == "random" else "--",
            linewidth=2.5,
            label=f"{method.title()} mean ({np.mean(vals):.3f})",
        )
    axes[1].set_ylim(
        -0.025,
        max(
            0.15,
            float(qualities.max()) + 0.05,
            max(map(np.mean, baselines.values())) + 0.05,
        ),
    )
    axes[1].legend(fontsize=8)
    fig.suptitle(
        "PPO minibatch sweep · real multi-endpoint development diagnostic",
        fontsize=14,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.035,
        "Same 2,048 actions, 256-action rollouts and 4 epochs; "
        "optimizer steps vary with batch size.\n"
        "Critic loss is not molecule accuracy. Validation: CFB only, "
        "8 scoring requests including starts.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.105, 1, 0.94))
    fig.savefig(output / "batch-size-curve.png", dpi=180)
    fig.savefig(output / "batch-size-curve.pdf")
    plt.close(fig)
    result = {
        "protocol_seal": protocol["seal"],
        "rows": rows,
        "mean_critic_mse": dict(zip(map(str, batches), losses.mean(axis=1).tolist())),
        "mean_validation_quality": dict(
            zip(map(str, batches), qualities.mean(axis=1).tolist())
        ),
        "baseline_validation_means": {
            k: float(np.mean(v)) for k, v in baselines.items()
        },
        "evidence": "development diagnostic; no final outcomes",
    }
    immediate_stops = no_new_queries = 0
    end_reasons, action_counts = Counter(), Counter()
    for batch in protocol["batch_sizes"]:
        for seed in protocol["seeds"]:
            for i in range(len(campaigns)):
                artifact = json.loads(
                    (output / f"batch-{batch}/seed-{seed}/eval-{i}.json").read_text()
                )
                verify(artifact)
                actions = artifact["run"]["actions"]
                end_reasons[artifact["run"]["end_reason"]] += 1
                action_counts.update(a["token"]["kind"] for a in actions)
                no_new_queries += artifact["run"]["requests"] == len(
                    campaigns[i].starts
                )
                immediate_stops += bool(
                    actions and actions[0]["token"]["kind"] == "STOP"
                )
    result["immediate_stop_rollouts"] = immediate_stops
    result["no_new_query_rollouts"] = no_new_queries
    result["end_reasons"] = dict(end_reasons)
    result["policy_action_counts"] = dict(action_counts)
    result["total_policy_rollouts"] = (
        len(campaigns) * len(protocol["batch_sizes"]) * len(protocol["seeds"])
    )
    write_new(output / "summary.json", seal(result))
    report = [
        "# PPO minibatch-size diagnostic",
        "",
        "Real frozen multi-endpoint diagnostic, not a qualified biological study.",
        "Three matched policy seeds (700–702); 2,048 actions per run, "
        "256-action rollouts, four epochs, learning rate 0.0003.",
        "Last-update critic MSE is averaged across minibatches/epochs, then seeds. "
        "On-policy return targets differ; this is not molecule prediction error.",
        "The loss is from the last checkpoint; search uses the separately "
        "validation-selected checkpoint. Final labels were not accessed.",
        "",
        "| Batch | Mean critic MSE | Optimizer steps |",
        "| --- | ---: | ---: |",
    ]
    for batch, mean in zip(batches, losses.mean(axis=1), strict=True):
        report.append(f"| {batch} | {mean:.8g} | {2048 * 4 // batch} |")
    report += [
        "",
        "## Matched search performance",
        "",
        "Mean best eligible archive utility (0–1); identical starting design and "
        "eight-request cap. DGAT2 is the training target, CFB the validation "
        "target, FGFR4 a previously used development target. None is final evidence.",
        "",
        "| Method | DGAT2 | CFB | FGFR4 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for method, batch in [("ppo", b) for b in batches] + [
        ("random", None),
        ("greedy", None),
    ]:
        label = f"PPO batch {batch}" if method == "ppo" else method.title()
        values = [
            np.mean(
                [
                    r["quality"]
                    for r in rows
                    if r["method"] == method
                    and r["batch_size"] == batch
                    and r["gene"] == gene
                ]
            )
            for gene in ("DGAT2", "CFB", "FGFR4")
        ]
        report.append(f"| {label} | " + " | ".join(f"{v:.6f}" for v in values) + " |")
    report += [
        "",
        f"Immediate STOP: {immediate_stops}/{result['total_policy_rollouts']} "
        "frozen-policy evaluations.",
        f"No scoring request beyond the initial archive: {no_new_queries}/"
        f"{result['total_policy_rollouts']}. End reasons: {dict(end_reasons)}. "
        f"Action counts: {dict(action_counts)}.",
        "Fixed training actions/epochs do not equalize optimizer steps or predictor "
        "requests. Costs are recorded per arm. Three seeds on one validation "
        "target do not establish an optimal batch size or cross-target superiority.",
        "",
        "![Batch-size curve](batch-size-curve.png)",
        "",
        "Raw values: results.csv. Frozen plan: protocol.json. "
        "All per-update optimization metrics and policy evaluations are retained.",
    ]
    (output / "report.md").write_text("\n".join(report) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "plot"))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.config, args.output, args.batch_size)
    elif args.phase == "run":
        run(args.output, args.batch_size, args.seed)
    else:
        plot(args.output)


if __name__ == "__main__":
    main()
