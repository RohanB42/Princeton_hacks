"""Bounded MaskablePPO training and fixed-policy evaluation, no outcome access."""

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback

from .artifacts import QueryJournal, seal, verify, write_new
from .contracts import Campaign
from .gym_env import MolecularEnv
from .policy import SearchEncoder
from .preflight import audit_partitions
from .scoring import FrozenRegistry


@dataclass(frozen=True)
class TrainingConfig:
    seed: int
    total_tokens: int
    rollout_tokens: int = 256
    batch_size: int = 64
    epochs: int = 4
    learning_rate: float = 0.0003
    entropy: float = 0.01
    validation_interval: int = 1024
    device: str = "cpu"
    site_capacity: int | None = None
    archive_capacity: int | None = None
    policy: str = "pooled-v2"
    candidate_capacity: int | None = None
    collapse_forced: bool = False
    pretrain_requests: int = 0
    pretrain_epochs: int = 0
    decoder: str = "transactional-v2"

    def __post_init__(self) -> None:
        if self.policy not in {"pooled-v2", "candidate-v3"}:
            raise ValueError("Unknown policy architecture")
        if self.policy == "candidate-v3" and (
            self.candidate_capacity is None or self.decoder != "transactional-v2"
        ):
            raise ValueError(
                "Candidate policy requires capacity and transactional decoder"
            )
        if (
            bool(self.pretrain_requests) != bool(self.pretrain_epochs)
            or min(self.pretrain_requests, self.pretrain_epochs) < 0
        ):
            raise ValueError("Pretraining requires paired nonnegative budget/epochs")
        if self.pretrain_requests and self.policy != "candidate-v3":
            raise ValueError("Warm start requires candidate policy")
        if self.decoder not in {"legacy-v1", "transactional-v2"}:
            raise ValueError("Unknown construction decoder")
        if self.rollout_tokens < 2 or self.batch_size < 2:
            raise ValueError("At least two rollout samples required")
        if (
            self.rollout_tokens % self.batch_size
            or self.total_tokens % self.rollout_tokens
        ):
            raise ValueError("Token budget must contain complete rollout/minibatches")
        if (
            self.total_tokens < self.rollout_tokens
            or self.validation_interval < self.rollout_tokens
        ):
            raise ValueError("Invalid bounded training schedule")
        if self.validation_interval % self.rollout_tokens:
            raise ValueError("Validation must occur at rollout boundaries")


def rollout(
    model: MaskablePPO,
    env: MolecularEnv,
    index: int = 0,
    seed: int = 0,
    deterministic: bool = True,
) -> dict:
    """Frozen parameters; adaptation comes only from observed history."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    obs, _ = env.reset(seed=seed, options={"campaign_index": index})
    done = False
    total = 0.0
    while not done:
        action, _ = model.predict(
            obs, deterministic=deterministic, action_masks=env.action_masks()
        )
        obs, reward, terminated, truncated, _ = env.step(action)
        total += reward
        done = terminated or truncated
    receipt = env.receipt()
    if not np.isclose(total, receipt["final_quality"] - receipt["initial_quality"]):
        raise RuntimeError("Episode return/archive objective mismatch")
    return {
        "method": "ppo",
        "seed": seed,
        "deterministic": deterministic,
        "episode_return": total,
        **receipt,
    }


class StudyCallback(BaseCallback):
    def __init__(
        self, validation: MolecularEnv, config: TrainingConfig, output: Path
    ) -> None:
        super().__init__()
        self.validation, self.config, self.output = validation, config, output
        self.training_requests = self.training_head_calls = 0
        self.completed_episodes = 0
        self.history = []
        self.optimization_history = []
        self.best = -float("inf")
        self.last_validation = -1

    def _on_step(self) -> bool:
        for info in self.locals["infos"]:
            if "episode_receipt" in info:
                receipt = info["episode_receipt"]
                self.training_requests += receipt["requests"]
                self.training_head_calls += sum(receipt["per_head_calls"].values())
                self.completed_episodes += 1
        return True

    def validate(self) -> None:
        # Validation must not advance the training RNG streams.
        py, np_state, torch_state = (
            random.getstate(),
            np.random.get_state(),
            torch.get_rng_state(),
        )
        device_states = (
            torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
        )
        try:
            receipts = [
                rollout(self.model, self.validation, i, self.config.seed)
                for i in range(len(self.validation.campaigns))
            ]
        finally:
            random.setstate(py)
            np.random.set_state(np_state)
            torch.set_rng_state(torch_state)
            if device_states is not None:
                torch.cuda.set_rng_state_all(device_states)
        quality = float(np.mean([r["final_quality"] for r in receipts]))
        entry = {
            "tokens": self.num_timesteps,
            "mean_final_quality": quality,
            "requests": sum(r["requests"] for r in receipts),
            "receipts": receipts,
            "new_designs": sum(
                sum(not e["initial"] and not e["cache_hit"] for e in r["trace"])
                for r in receipts
            ),
        }
        if self.config.decoder == "transactional-v2" and any(
            r["requests"] == len(c.starts)
            and len({d.key for d in c.designs()})
            > len({c.construct(*start).key for start in c.starts})
            for r, c in zip(receipts, self.validation.campaigns, strict=True)
        ):
            raise RuntimeError("Transactional policy failed to make a new proposal")
        self.history.append(entry)
        write_new(self.output / f"validation-{self.num_timesteps}.json", seal(entry))
        if quality > self.best:
            self.best = quality
            self.model.save(self.output / "selected-policy")
            self.selected_tokens = self.num_timesteps
        self.last_validation = self.num_timesteps

    def _on_rollout_start(self) -> None:
        # Called after the previous rollout's PPO updates; not before them.
        self.record_optimization()
        if (
            self.num_timesteps
            and self.num_timesteps % self.config.validation_interval == 0
        ):
            self.validate()

    def _on_training_end(self) -> None:
        self.record_optimization()
        if self.last_validation != self.num_timesteps:
            self.validate()

    def record_optimization(self) -> None:
        """Persist SB3 diagnostics after each update, including the final one."""
        if not self.num_timesteps or (
            self.optimization_history
            and self.optimization_history[-1]["tokens"] == self.num_timesteps
        ):
            return
        metrics = {
            key.removeprefix("train/"): float(value) if np.isfinite(value) else None
            for key, value in self.model.logger.name_to_value.items()
            if key.startswith("train/") and isinstance(value, (int, float, np.number))
        }
        if "value_loss" not in metrics:
            raise RuntimeError("PPO update did not expose critic-loss diagnostics")
        entry = {"tokens": self.num_timesteps, "metrics": metrics}
        self.optimization_history.append(entry)
        write_new(self.output / f"optimization-{self.num_timesteps}.json", seal(entry))


def train(
    training: tuple[Campaign, ...],
    validation: tuple[Campaign, ...],
    registry: FrozenRegistry,
    config: TrainingConfig,
    output: Path,
) -> dict:
    if not training or not validation:
        raise ValueError("Separate nonempty training and validation campaigns required")
    if any(c.partition != "training" for c in training) or any(
        c.partition != "validation" for c in validation
    ):
        raise ValueError("Policy partition mismatch")
    audit_partitions(training + validation)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    site_capacity = config.site_capacity or max(
        len(c.target.sequence) for c in training + validation
    )
    archive_capacity = config.archive_capacity or max(
        c.requests for c in training + validation
    )
    train_env = MolecularEnv(
        training,
        registry,
        site_capacity,
        archive_capacity,
        QueryJournal(output / "training-queries.jsonl"),
        config.decoder,
        config.candidate_capacity,
        config.collapse_forced,
    )
    validation_env = MolecularEnv(
        validation,
        registry,
        site_capacity,
        archive_capacity,
        QueryJournal(output / "validation-queries.jsonl"),
        config.decoder,
        config.candidate_capacity,
        config.collapse_forced,
    )
    lock = {
        "config": asdict(config),
        "training": [c.key for c in training],
        "validation": [c.key for c in validation],
        "registry": registry.key,
        "schema_id": train_env.schema_id,
        "site_capacity": site_capacity,
        "archive_capacity": archive_capacity,
        "selection": "maximum validation mean final archive quality; earliest tie",
        "gamma": 1.0,
        "gae_lambda": 1.0,
    }
    write_new(output / "protocol.json", seal(lock))
    torch.set_num_threads(1)
    policy_class = "MultiInputPolicy"
    extra_policy_kwargs = {}
    if config.policy == "candidate-v3":
        from .candidate_policy import CandidatePolicy
        from .grammar import Grammar

        policy_class = CandidatePolicy
        extra_policy_kwargs["action_tokens"] = [
            asdict(t)
            for t in Grammar(training[0], site_capacity, archive_capacity).tokens
        ]
    model = MaskablePPO(
        policy_class,
        train_env,
        gamma=1.0,
        gae_lambda=1.0,
        seed=config.seed,
        n_steps=config.rollout_tokens,
        batch_size=config.batch_size,
        n_epochs=config.epochs,
        learning_rate=config.learning_rate,
        ent_coef=config.entropy,
        device=config.device,
        policy_kwargs={
            "features_extractor_class": SearchEncoder,
            "net_arch": {"pi": [64], "vf": [64]},
            **extra_policy_kwargs,
        },
    )
    callback = StudyCallback(validation_env, config, output)
    started = perf_counter()
    try:
        pretraining = None
        if config.pretrain_requests:
            from .pretraining import pretrain_candidates

            pretraining = pretrain_candidates(
                model.policy,
                training,
                registry,
                output,
                config.seed,
                config.pretrain_requests,
                config.pretrain_epochs,
            )
            # Preserve the initialized policy as a matched no-PPO ablation.
            model.save(output / "warm-start-policy")
        model.learn(total_timesteps=config.total_tokens, callback=callback)
    except Exception as exc:
        write_new(
            output / "failure.json",
            seal(
                {
                    "status": "execution_failed",
                    "error": str(exc),
                    "protocol": lock,
                    "partial_run": train_env.core.receipt()
                    if train_env.core is not None
                    else None,
                    "query_journals": [
                        "training-queries.jsonl",
                        "validation-queries.jsonl",
                    ],
                }
            ),
        )
        raise
    model.save(output / "last-policy")
    from .resume import save_resume

    save_resume(model, train_env, output / "resume")
    selected = output / "selected-policy.zip"
    # Current partial episode is real expenditure too (including reset starts).
    partial = train_env.core.session.receipt()
    result = {
        "status": "complete_policy_development",
        "protocol": lock,
        "training_seconds": perf_counter() - started,
        "pretraining_requests": pretraining["requests"] if pretraining else 0,
        "pretraining_head_calls": pretraining["head_calls"] if pretraining else 0,
        "pretraining_seal": pretraining["seal"] if pretraining else None,
        "warm_start_sha256": hashlib.sha256(
            (output / "warm-start-policy.zip").read_bytes()
        ).hexdigest()
        if pretraining
        else None,
        "training_requests": callback.training_requests + partial["requests"],
        "training_head_calls": callback.training_head_calls
        + sum(partial["per_head_calls"].values()),
        "completed_episodes": callback.completed_episodes,
        "validation_requests": sum(v["requests"] for v in callback.history),
        "validation_history": callback.history,
        "optimization_history": callback.optimization_history,
        "selected_tokens": callback.selected_tokens,
        "policy_sha256": hashlib.sha256(selected.read_bytes()).hexdigest(),
        "reload_kind": (
            "selected inference; last policy has complete rollout-boundary resume"
        ),
    }
    write_new(output / "training.json", seal(result))
    return result


def load_policy(directory: Path, env: MolecularEnv) -> MaskablePPO:
    receipt = json.loads((directory / "training.json").read_text())
    verify(receipt)
    if receipt["protocol"]["schema_id"] != env.schema_id:
        raise ValueError("Policy observation/action/scorer schema mismatch")
    path = directory / "selected-policy.zip"
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt["policy_sha256"]:
        raise ValueError("Policy checkpoint hash mismatch")
    return MaskablePPO.load(path, env=env, device="cpu")
