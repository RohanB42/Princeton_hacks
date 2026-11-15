"""Matched Atlas policy training, locked replay, and paired reporting."""

import hashlib
import json
from dataclasses import replace
from importlib.metadata import version as package_version
from pathlib import Path
from time import perf_counter

import gymnasium as gym
import numpy as np
import torch
from sb3_contrib import MaskablePPO

from oligo_engine.design.aso_space import identity
from oligo_engine.evaluation.runner import environment_identity
from oligo_engine.experimental_rl.belief import (
    FrozenBelief,
    encode,
    source_model,
    uncertainty_metrics,
)
from oligo_engine.experimental_rl.cohort import Atlas, prepare
from oligo_engine.experimental_rl.environment import (
    OBSERVATION,
    Campaign,
    ExperimentalSelectionEnv,
    Expert,
    make_belief,
)
from oligo_engine.rl.ppo import verify_runtime

V1_METHODS = ("random", "mean", "seq_diversity", "chem_diversity", "scheduled", "ppo")
V2_METHODS = V1_METHODS[:-1] + ("latent", "total", "hybrid", "source_mean", "ppo")


def write_json(path: Path, value: dict) -> None:
    part = path.with_suffix(".tmp")
    part.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    part.replace(path)


def prior_and_campaigns(atlas: Atlas, config: dict):
    rows, manifest = prepare(atlas, config)
    fit, cal = (manifest[key] for key in ("source_fit", "source_cal"))
    x, _, _ = encode(rows.loc[fit + cal], config["posterior_dimensions"])
    labels = atlas.labels(fit)
    predictor = source_model(
        x[: len(fit)], np.array([labels[i] for i in fit]), config["ridge_alpha"]
    )
    cal_labels = atlas.labels(cal)
    y = np.array([cal_labels[i] for i in cal])
    cal_predictions = predictor.predict(x[len(fit) :])
    # Includes source transfer/model error; no assumption of true replicate noise.
    noise = float(max(1, np.sqrt(np.mean((y - cal_predictions) ** 2))))
    source = {
        "model": "atlas-chemistry-assay-hashed-ridge",
        "fit_identity": identity(fit),
        "calibration_identity": identity(cal),
        "fit_count": len(fit),
        "calibration_count": len(cal),
        "noise_assumption_std": noise,
        "model_identity": identity(
            [fit, cal, predictor.coef_.tolist(), float(predictor.intercept_), noise]
        ),
        "source_cal_metrics": uncertainty_metrics(
            y, FrozenBelief(cal_predictions, noise).predict()
        ),
    }
    campaigns = []
    for entry in manifest["campaigns"]:
        pool, sentinel = entry["pool"], entry["sentinel"]
        x, mol, seq = encode(rows.loc[pool + sentinel], config["posterior_dimensions"])
        campaigns.append(
            Campaign(
                entry["name"],
                entry["role"],
                entry["context"],
                tuple(pool),
                tuple(sentinel),
                predictor.predict(x),
                mol,
                seq[: len(pool)],
                noise,
                {int(k): tuple(ids) for k, ids in entry["initial"].items()},
            )
        )
    return manifest, source, campaigns, predictor


def episode_env(atlas: Atlas, campaign: Campaign, config: dict, version: str):
    return ExperimentalSelectionEnv(
        campaign,
        atlas.labels(campaign.pool),
        config["total_assays"],
        config["initial_assays"],
        config["hit_threshold"],
        version,
    )


class CyclingCampaigns(gym.Env):
    """Cycle distinct train tasks on reset; validation has its own environments."""

    def __init__(self, environments: list[ExperimentalSelectionEnv]) -> None:
        if len({env.campaign_name for env in environments}) < 2:
            raise ValueError("At least two distinct training campaigns required")
        self._environments, self._episode = environments, -1
        self.observation_space = environments[0].observation_space
        self.action_space = environments[0].action_space

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self._episode += 1
        self._active = self._environments[self._episode % len(self._environments)]
        return self._active.reset(
            seed=int(self.np_random.integers(0, 2**31)), options=options
        )

    def step(self, action: int):
        return self._active.step(action)

    def action_masks(self) -> np.ndarray:
        return self._active.action_masks()


def rollout(env: ExperimentalSelectionEnv, method: str, seed: int, model=None) -> dict:
    started = perf_counter()
    obs, _ = env.reset(seed=seed)
    while True:
        if method == "ppo":
            action, _ = model.predict(
                obs, action_masks=env.action_masks(), deterministic=True
            )
            action = int(action)
        elif method == "scheduled":
            action = (
                Expert.CHEM_DIVERSITY
                if len(env.ledger) < env.budget / 3
                else Expert.MEAN
            )
        else:
            action = Expert[method.upper()]
        obs, _, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break
    ledger = [dict(entry) for entry in env.ledger]
    hits = np.cumsum([r["reward"] for r in ledger])
    first = next((i for i, row in enumerate(ledger, 1) if row["reward"]), None)
    if len({r["id"] for r in ledger}) != len(ledger) or len(ledger) != env.budget:
        raise ValueError("Unmatched or repeated assay purchases")
    for i, row in enumerate(ledger):
        row["fit_set_hash"] = (
            identity([r["id"] for r in ledger[:i]])
            if (row["fit_labels_before"] > 0)
            else None
        )
    return {
        "campaign": env.campaign_name,
        "assay_context": env.assay_context,
        "method": method,
        "seed": seed,
        "ledger": ledger,
        "hit_curve": hits.tolist(),
        "hit_count": int(hits[-1]),
        "seeds_with_hits": sum(row["hit"] for row in ledger[: env.seed_count]),
        "hit_aulc": float(np.mean(hits)),
        "first_new_hit_at_total_assays": first,
        "first_hit_censored": first is None,
        "best_measured": max(row["observed"] for row in ledger),
        "assays": len(ledger),
        "terminal_reason": info["terminal_reason"],
        "prediction_passes": len(ledger) + 1 if env.version != "v1" else 1,
        "wall_seconds": perf_counter() - started,
    }


def train_ppo(train_envs, dev_envs, output: Path, config: dict):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    train_env = CyclingCampaigns(train_envs)
    model = MaskablePPO(
        "MlpPolicy",
        train_env,
        device="cpu",
        gamma=1,
        n_steps=256,
        batch_size=64,
        n_epochs=5,
        learning_rate=3e-4,
        seed=config["ppo_seed"],
        verbose=0,
        policy_kwargs={"net_arch": [32, 32]},
    )
    checkpoint = output / "policy.zip"
    best, history = None, []
    for step in range(1024, config["ppo_steps"] + 1, 1024):
        model.learn(total_timesteps=1024, reset_num_timesteps=False)
        results = [
            rollout(env, "ppo", seed, model)
            for env in dev_envs
            for seed in config["evaluation_seeds"][:3]
        ]
        score = float(np.mean([r["hit_count"] for r in results]))
        history.append({"steps": step, "development_mean_hits": score})
        if best is None or score > best:
            best = score
            model.save(checkpoint)
    if not history:
        raise ValueError("PPO budget must contain at least one 1,024-step block")
    loaded = MaskablePPO.load(checkpoint, device="cpu")
    probe1 = rollout(dev_envs[0], "ppo", config["evaluation_seeds"][0], loaded)
    probe2 = rollout(
        dev_envs[0],
        "ppo",
        config["evaluation_seeds"][0],
        MaskablePPO.load(checkpoint, device="cpu"),
    )
    if probe1["ledger"] != probe2["ledger"]:
        raise ValueError("Policy reload changed the deterministic ledger")
    return loaded, {
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "training_decisions": config["ppo_steps"],
        "validation_episodes": len(history) * len(dev_envs) * 3,
        "history": history,
        "reload_ledger_equal": True,
    }


def sentinel_score(
    campaign: Campaign,
    outcomes: dict,
    ledger: list[dict],
    version: str,
    checkpoints: list[int],
) -> dict:
    # Called after optimizer rollouts finish, on disjoint sentinel outcomes.
    if set(outcomes) != set(campaign.sentinel):
        raise ValueError("Sentinel capability must match its declared evaluation IDs")
    index = {i: k for k, i in enumerate(campaign.pool)}
    y = np.array([outcomes[i] for i in campaign.sentinel])
    result = {}
    constant = {}
    for kind in ("v1", "v2", "gp") if version == "v2" else ("v1",):
        belief = make_belief(kind, campaign.prior, campaign.features, campaign.noise)
        points = {}
        for i, row in enumerate(ledger, 1):
            belief.update(index[row["id"]], row["observed"])
            if i in checkpoints:
                prediction = belief.predict()
                prediction = replace(
                    prediction,
                    mean=prediction.mean[len(index) :],
                    latent_std=(
                        None
                        if prediction.latent_std is None
                        else prediction.latent_std[len(index) :]
                    ),
                    predictive_std=prediction.predictive_std[len(index) :],
                )
                points[str(i)] = uncertainty_metrics(
                    y,
                    prediction,
                )
                if kind == "v2":
                    # Same adaptive mean isolates the constant-scale comparison.
                    constant[str(i)] = uncertainty_metrics(
                        y,
                        replace(
                            prediction, predictive_std=np.full(len(y), campaign.noise)
                        ),
                    )
        result[kind] = points
    if constant:
        result["constant_scale"] = constant
    return result


def paired_summary(records: list[dict]) -> dict:
    methods = sorted({r["method"] for r in records})
    campaigns = sorted({r["campaign"] for r in records})
    by_method = {
        m: {
            target: [r for r in records if r["method"] == m and r["campaign"] == target]
            for target in campaigns
        }
        for m in methods
    }
    for target in campaigns:
        pairs = [
            {
                (
                    r["seed"],
                    tuple(e["id"] for e in r["ledger"] if e["expert"] == "seed"),
                    r["assays"],
                )
                for r in by_method[m][target]
            }
            for m in methods
        ]
        if not pairs[0] or any(pair != pairs[0] for pair in pairs):
            raise ValueError("Unpaired campaign: initial assays or budgets differ")
    rng = np.random.default_rng(327)
    bootstrap = rng.integers(0, len(campaigns), size=(5000, len(campaigns)))
    result = {}
    for m, tasks in by_method.items():
        target_hits = {
            t: float(np.mean([r["hit_count"] for r in v])) for t, v in tasks.items()
        }
        differences = np.array(
            [
                np.mean([r["hit_count"] for r in by_method["ppo"][t]]) - target_hits[t]
                for t in campaigns
            ]
        )
        result[m] = {
            "mean_hits": float(np.mean(list(target_hits.values()))),
            "target_mean_hits": target_hits,
            "mean_hit_curve": np.mean(
                [
                    np.mean([r["hit_curve"] for r in tasks[t]], axis=0)
                    for t in campaigns
                ],
                axis=0,
            ).tolist(),
            "mean_best_measured": float(
                np.mean(
                    [np.mean([r["best_measured"] for r in tasks[t]]) for t in campaigns]
                )
            ),
            "hit_aulc": float(
                np.mean([np.mean([r["hit_aulc"] for r in tasks[t]]) for t in campaigns])
            ),
            "ppo_minus_method": float(differences.mean()),
            "target_bootstrap_95": np.quantile(
                differences[bootstrap].mean(axis=1), [0.025, 0.975]
            ).tolist(),
        }
    return result


def run(
    atlas: Atlas,
    config: dict,
    output: Path,
    version: str,
    v1_report: Path | None = None,
) -> dict:
    if output.exists():
        raise FileExistsError(output)
    runtime = verify_runtime()
    if config["ppo_steps"] < 1024 or config["ppo_steps"] % 1024:
        raise ValueError("PPO budget must be a positive multiple of 1024")
    started = perf_counter()
    if version not in ("v1", "v2"):
        raise ValueError("Unsupported replay version")
    manifest, source, campaigns, predictor = prior_and_campaigns(atlas, config)
    if version == "v2":
        if v1_report is None:
            raise ValueError("V2 requires the completed V1 report")
        previous = json.loads(v1_report.read_text())
        if (
            previous["version"] != "v1"
            or not previous["v1_gate"]["passed"]
            or (
                previous["manifest_identity"] != manifest["identity"]
                or previous["source"]["model_identity"] != source["model_identity"]
            )
        ):
            raise ValueError("V1 gate, partition or source prior mismatch")
    output.mkdir(parents=True)
    parameters = output / "source_parameters.npz"
    np.savez(parameters, intercept=predictor.intercept_, coefficients=predictor.coef_)
    source["parameters_sha256"] = hashlib.sha256(parameters.read_bytes()).hexdigest()
    write_json(output / "partition_manifest.json", manifest)
    write_json(output / "source_prior.json", source)
    tasks = {
        role: [c for c in campaigns if c.role == role]
        for role in ("train", "dev", "test")
    }
    if min(map(len, tasks.values())) < 2:
        raise ValueError("Insufficient distinct task groups")
    train, dev = (
        [episode_env(atlas, c, config, version) for c in tasks[role]]
        for role in ("train", "dev")
    )
    model, policy = train_ppo(train, dev, output, config)
    policy |= {
        "action_schema": [x.name for x in Expert],
        "observation_schema": OBSERVATION,
        "manifest_identity": manifest["identity"],
        "source_model_identity": source["model_identity"],
        "train_campaigns": [c.name for c in tasks["train"]],
        "dev_campaigns": [c.name for c in tasks["dev"]],
        "version": version,
    }
    write_json(output / "policy_manifest.json", policy)
    methods = V1_METHODS if version == "v1" else V2_METHODS
    records = []
    for campaign in tasks["test"]:
        env = episode_env(atlas, campaign, config, version)
        for seed in config["evaluation_seeds"]:
            for method in methods:
                records.append(rollout(env, method, seed, model))
    # External sentinel labels are loaded only after every choice is complete.
    for campaign in tasks["test"]:
        labels = atlas.labels(campaign.sentinel)
        for row in records:
            if row["campaign"] == campaign.name:
                row["sentinel"] = sentinel_score(
                    campaign, labels, row["ledger"], version, config["checkpoints"]
                )
    report = {
        "version": version,
        "purpose": "retrospective_measured_atlas_diagnostic",
        "config": config,
        "runtime": runtime,
        "environment_identity": environment_identity(),
        "atlas_packages": {
            package: package_version(package) for package in ("pandas", "pyarrow")
        },
        "manifest_identity": manifest["identity"],
        "source": source,
        "policy": policy,
        "campaign_counts": {k: len(v) for k, v in tasks.items()},
        "episodes": len(records),
        "summary": paired_summary(records),
        "v1_gate": {
            "passed": version == "v1",
            "basis": [
                "source/campaign isolation",
                "target-disjoint validated PPO",
                "matched held-out replay",
                "identical checkpoint-reload ledger",
            ],
        }
        if version == "v1"
        else None,
        "wall_seconds": perf_counter() - started,
    }
    write_json(output / "episodes.json", {"episodes": records})
    write_json(output / "report.json", report)
    return report
