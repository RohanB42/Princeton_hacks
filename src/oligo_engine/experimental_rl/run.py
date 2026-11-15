"""Matched Atlas policy training, locked replay, and paired reporting."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import gymnasium as gym
import numpy as np
import torch
from sb3_contrib import MaskablePPO

from oligo_engine.experimental_rl.belief import (
    FrozenBelief,
    encode,
    source_model,
    uncertainty_metrics,
)
from oligo_engine.experimental_rl.cohort import Atlas, prepare
from oligo_engine.experimental_rl.environment import (
    Campaign,
    ExperimentalSelectionEnv,
    Expert,
    make_belief,
)
from oligo_engine.provenance import identity


def write_json(path: Path, value: dict) -> None:
    part = path.with_suffix(".tmp")
    part.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    part.replace(path)


def prior_and_campaigns(atlas: Atlas, config: dict) -> tuple:
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


def episode_env(
    atlas: Atlas, campaign: Campaign, config: dict, version: str
) -> ExperimentalSelectionEnv:
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

    def reset(self, *, seed: int | None = None, options: dict | None = None) -> tuple:
        super().reset(seed=seed)
        self._episode += 1
        self._active = self._environments[self._episode % len(self._environments)]
        return self._active.reset(
            seed=int(self.np_random.integers(0, 2**31)), options=options
        )

    def step(self, action: int) -> tuple:
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


def train_ppo(
    train_envs: list[ExperimentalSelectionEnv],
    dev_envs: list[ExperimentalSelectionEnv],
    output: Path,
    config: dict,
) -> tuple[MaskablePPO, dict]:
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
        policy_kwargs={"net_arch": config["hidden_layers"]},
    )
    checkpoint = output / "policy.zip"
    best, history, before_save_probe = None, [], None
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
            before_save_probe = rollout(
                dev_envs[0], "ppo", config["evaluation_seeds"][0], model
            )["ledger"]
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
    if probe1["ledger"] != probe2["ledger"] or probe1["ledger"] != before_save_probe:
        raise ValueError("Policy reload changed the deterministic ledger")
    write_json(output / "reload_probe.json", {"ledger": probe1["ledger"]})
    return loaded, {
        "hidden_layers": config["hidden_layers"],
        "policy_parameters": sum(p.numel() for p in loaded.policy.parameters()),
        "selected_steps": next(
            row["steps"] for row in history if row["development_mean_hits"] == best
        ),
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
