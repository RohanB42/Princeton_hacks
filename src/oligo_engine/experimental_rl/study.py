"""Five-seed, three-layer PPO comparisons with sealed final evaluation."""

import hashlib
import json
from collections import Counter
from pathlib import Path
from time import perf_counter

import numpy as np

from oligo_engine.evaluation.runner import environment_identity
from oligo_engine.experimental_rl.cohort import Atlas, prepare
from oligo_engine.experimental_rl.environment import OBSERVATION, Expert
from oligo_engine.experimental_rl.run import (
    episode_env,
    prior_and_campaigns,
    rollout,
    sentinel_score,
    train_ppo,
    write_json,
)
from oligo_engine.experimental_rl.runtime import verify_runtime
from oligo_engine.provenance import identity


def validate_config(config: dict) -> None:
    """Reject incompatible comparisons before data fitting or outcome access."""
    if (
        config["hidden_layers"] not in ([32, 32, 32], [64, 64, 64])
        or type(config["candidate_pool_size"]) is not int
        or config["ppo_steps"] < 1024
        or config["ppo_steps"] % 1024
        or len(set(config["policy_seeds"])) != len(config["policy_seeds"])
        or len(config["policy_seeds"]) < 5
        or len(set(config["evaluation_seeds"])) != len(config["evaluation_seeds"])
        or len(config["evaluation_seeds"]) < 5
        or config["methods"] != ["random", "mean", "source_mean", "ppo"]
        or not 0
        < config["initial_assays"]
        < config["total_assays"]
        <= config["candidate_pool_size"]
    ):
        raise ValueError(
            "Invalid frozen candidate-pool, three-layer study configuration"
        )


def paired_summary(records: list[dict], policy_seeds: list[int]) -> dict:
    """Equal target weights; repeated policy fits never multiply baseline weight."""
    if not records or not policy_seeds or len(set(policy_seeds)) != len(policy_seeds):
        raise ValueError("Nonempty records and unique policy seeds required")
    campaigns = sorted({r["campaign"] for r in records})
    methods = sorted({r["method"] for r in records})
    if set(methods) != {"ppo", "random", "mean", "source_mean"}:
        raise ValueError("Required comparison methods missing")
    keys = [(r["campaign"], r["method"], r["seed"], r["policy_seed"]) for r in records]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate policy/replay episode")
    for campaign in campaigns:
        group = [r for r in records if r["campaign"] == campaign]
        reference = {
            (
                r["seed"],
                tuple(e["id"] for e in r["ledger"] if e["expert"] == "seed"),
                r["assays"],
                r["candidate_pool_identity"],
            )
            for r in group
            if r["method"] == "random"
        }
        for method in methods:
            expected = policy_seeds if method == "ppo" else [None]
            actual = {r["policy_seed"] for r in group if r["method"] == method}
            if actual != set(expected):
                raise ValueError("Missing or additional training-seed replicate")
            for seed in expected:
                pair = {
                    (
                        r["seed"],
                        tuple(e["id"] for e in r["ledger"] if e["expert"] == "seed"),
                        r["assays"],
                        r["candidate_pool_identity"],
                    )
                    for r in group
                    if r["method"] == method and r["policy_seed"] == seed
                }
                if not reference or pair != reference:
                    raise ValueError("Unpaired initial measurements, pools or budgets")
    means = {
        method: {
            campaign: float(
                np.mean(
                    [
                        r["hit_count"]
                        for r in records
                        if r["method"] == method and r["campaign"] == campaign
                    ]
                )
            )
            for campaign in campaigns
        }
        for method in methods
    }
    bootstrap = np.random.default_rng(327).integers(
        0, len(campaigns), (5000, len(campaigns))
    )
    summary = {}
    for method in methods:
        differences = np.array([means["ppo"][c] - means[method][c] for c in campaigns])
        group = [r for r in records if r["method"] == method]
        summary[method] = {
            "mean_hits": float(np.mean(list(means[method].values()))),
            "target_mean_hits": means[method],
            "ppo_minus_method": float(differences.mean()),
            "descriptive_target_bootstrap_95": np.quantile(
                differences[bootstrap].mean(axis=1), [0.025, 0.975]
            ).tolist(),
            "mean_hit_curve": np.mean(
                [
                    np.mean(
                        [r["hit_curve"] for r in group if r["campaign"] == c], axis=0
                    )
                    for c in campaigns
                ],
                axis=0,
            ).tolist(),
            "hit_aulc": float(
                np.mean(
                    [
                        np.mean([r["hit_aulc"] for r in group if r["campaign"] == c])
                        for c in campaigns
                    ]
                )
            ),
        }
    seed_means = {
        str(seed): float(
            np.mean(
                [
                    np.mean(
                        [
                            r["hit_count"]
                            for r in records
                            if r["method"] == "ppo"
                            and r["policy_seed"] == seed
                            and r["campaign"] == c
                        ]
                    )
                    for c in campaigns
                ]
            )
        )
        for seed in policy_seeds
    }
    return {
        "methods": summary,
        "independent_target_groups": len(campaigns),
        "ppo_training_seed_mean_hits": seed_means,
        "ppo_training_seed_sample_sd": float(np.std(list(seed_means.values()), ddof=1))
        if len(seed_means) > 1
        else None,
        "interval_caveat": "Descriptive target bootstrap; two prior-exposed targets",
    }


def source_identity() -> dict[str, str]:
    """Hash executed source including uncommitted development files."""
    root = Path(__file__).resolve().parents[3]
    paths = sorted((root / "src/oligo_engine/experimental_rl").glob("*.py")) + [
        root / "src/oligo_engine/data/oracle.py",
        root / "src/oligo_engine/reward/chemistry.py",
        root / "src/oligo_engine/provenance.py",
    ]
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
    }


def prepare_study(atlas: Atlas, config: dict, output: Path) -> dict:
    """Persist label-free membership and capacity diagnostics only."""
    validate_config(config)
    _, manifest = prepare(atlas, config)
    with output.open("x") as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
    return manifest


def run_study(atlas: Atlas, config: dict, output: Path) -> dict:
    """Freeze every policy before buying final replay outcomes; defer sentinels."""
    validate_config(config)
    runtime = verify_runtime()
    if output.exists():
        raise FileExistsError(output)
    started = perf_counter()
    executed_sources = source_identity()
    manifest, source, campaigns, predictor = prior_and_campaigns(atlas, config)
    output.mkdir(parents=True)
    np.savez(
        output / "source_parameters.npz",
        intercept=predictor.intercept_,
        coefficients=predictor.coef_,
    )
    source["parameters_sha256"] = hashlib.sha256(
        (output / "source_parameters.npz").read_bytes()
    ).hexdigest()
    write_json(output / "partition_manifest.json", manifest)
    write_json(output / "source_prior.json", source)
    write_json(
        output / "execution.json",
        {
            "source_files": executed_sources,
            "runtime": runtime,
            "code": environment_identity(),
            "config": config,
        },
    )
    tasks = {
        role: [c for c in campaigns if c.role == role]
        for role in ("train", "dev", "test")
    }
    train, dev = (
        [episode_env(atlas, c, config, "v2") for c in tasks[role]]
        for role in ("train", "dev")
    )
    policies, receipts = {}, {}
    for seed in config["policy_seeds"]:
        directory = output / f"policy-{seed}"
        directory.mkdir()
        tick = perf_counter()
        print(json.dumps({"stage": "train", "policy_seed": seed}), flush=True)
        model, receipt = train_ppo(train, dev, directory, config | {"ppo_seed": seed})
        receipt |= {
            "training_seed": seed,
            "wall_seconds": perf_counter() - tick,
            "manifest_identity": manifest["identity"],
            "source_model_identity": source["model_identity"],
            "action_schema": [e.name for e in Expert],
            "observation_schema": OBSERVATION,
            "train_campaigns": [c.name for c in tasks["train"]],
            "dev_campaigns": [c.name for c in tasks["dev"]],
        }
        policies[seed], receipts[str(seed)] = model, receipt
        write_json(directory / "manifest.json", receipt)
        print(
            json.dumps(
                {
                    "stage": "trained",
                    "policy_seed": seed,
                    "wall_seconds": receipt["wall_seconds"],
                    "selected_steps": receipt["selected_steps"],
                }
            ),
            flush=True,
        )
    # All training/checkpoint decisions are fixed before constructing these oracles.
    write_json(
        output / "policy_seal.json",
        {
            "identity": identity(receipts),
            "policies": receipts,
            "source_files": executed_sources,
        },
    )
    records = []
    for campaign in tasks["test"]:
        env = episode_env(atlas, campaign, config, "v2")
        for seed in config["evaluation_seeds"]:
            for method in config["methods"]:
                for policy_seed in (
                    config["policy_seeds"] if method == "ppo" else [None]
                ):
                    record = rollout(env, method, seed, policies.get(policy_seed))
                    record |= {
                        "policy_seed": policy_seed,
                        "candidate_pool_identity": identity(campaign.pool),
                        "candidate_count": len(campaign.pool),
                    }
                    records.append(record)
        print(
            json.dumps({"stage": "evaluation_complete", "target": campaign.name}),
            flush=True,
        )
    write_json(output / "acquisition_seal.json", {"identity": identity(records)})
    # Independent sentinel outcomes are not part of the purchase pool or reward.
    for campaign in tasks["test"]:
        outcomes = atlas.labels(campaign.sentinel)
        for record in records:
            if record["campaign"] == campaign.name:
                record["sentinel"] = sentinel_score(
                    campaign, outcomes, record["ledger"], "v2", config["checkpoints"]
                )
    if executed_sources != source_identity():
        raise RuntimeError("Executed experimental-selection sources changed during run")
    report = {
        "purpose": "retrospective_measured_atlas_diagnostic",
        "version": config.get("study_name")
        or (
            f"{config['candidate_pool_size']}-candidates-three-layer-"
            f"width{config['hidden_layers'][0]}-v2"
        ),
        "config": config,
        "runtime": runtime,
        "source_files": executed_sources,
        "environment_identity": environment_identity(),
        "manifest_identity": manifest["identity"],
        "source": source,
        "policies": receipts,
        "campaigns": [
            {
                "name": c.name,
                "role": c.role,
                "pool": len(c.pool),
                "sentinel": len(c.sentinel),
            }
            for c in campaigns
        ],
        "capacity_exclusions": manifest["counts"]["capacity_exclusions"],
        "episodes": len(records),
        "summary": paired_summary(records, config["policy_seeds"]),
        "expert_counts": dict(
            Counter(
                e["expert"]
                for r in records
                if r["method"] == "ppo"
                for e in r["ledger"]
                if e["expert"] != "seed"
            )
        ),
        "wall_seconds": perf_counter() - started,
        "caveats": [
            "Gate 1 open",
            "Only two prior-exposed final target groups",
            "No new laboratory measurements or clinical safety claim",
            "Dollar mapping unresolved; simulated unit-cost assays only",
            "Aggregate-state expert selection, not an LLM or direct candidate policy",
        ],
    }
    write_json(output / "episodes.json", {"episodes": records})
    write_json(output / "report.json", report)
    return report
