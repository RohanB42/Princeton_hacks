"""Checkpoint at a consumed-rollout boundary, with complete environment/RNG state."""

import hashlib
import json
import random
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO

from .artifacts import seal, verify, write_new
from .contracts import Campaign
from .environment import DesignCore
from .gym_env import MolecularEnv
from .scoring import FrozenRegistry, Head, Prediction


def restore_core(
    snapshot: dict,
    campaign: Campaign,
    registry: FrozenRegistry,
    site_capacity: int,
    archive_capacity: int,
) -> DesignCore:
    """Replay saved responses to verify state, without querying actual predictors."""
    if (
        snapshot["campaign_id"] != campaign.key
        or snapshot["registry_id"] != registry.key
    ):
        raise ValueError("Resume scientific identities changed")
    records = {e["design_id"]: e["score"] for e in snapshot["trace"]}

    def replay(name):
        def predict(d, context):
            result = next(r for r in records[d.key]["endpoints"] if r["name"] == name)
            if result["raw"] is None:
                raise ValueError("Resume attempted unrecorded inference")
            return Prediction(
                result["raw"],
                result["uncertainty"],
                tuple(tuple(v) for v in result["diagnostics"]),
            )

        return predict

    replay_registry = FrozenRegistry(
        registry.profile,
        tuple(
            Head(h.manifest, replay(h.manifest.name) if h.predict is not None else None)
            for h in registry.heads
        ),
    )
    core = DesignCore(
        campaign,
        replay_registry,
        site_capacity,
        archive_capacity,
        decoder=snapshot.get("decoder", "legacy-v1"),
    )
    for event in snapshot["actions"]:
        _, reward, _, _ = core.step(event["action"])
        if reward != event["reward"]:
            raise ValueError("Resume action/reward replay disagrees")
    if (
        core.session.quality != snapshot["final_quality"]
        or core.session.requests != snapshot["requests"]
    ):
        raise ValueError("Resume archive/budget replay disagrees")
    core.session.trace = snapshot["trace"]
    core.registry = core.session.registry = registry
    return core


def save_resume(model: MaskablePPO, env: MolecularEnv, path: Path) -> None:
    """Call only after the rollout has been consumed by a PPO update.

    We preserve an empty next rollout, not a partially collected rollout. The
    caller's update boundary is recorded and verified by the integration test.
    """
    if path.exists():
        raise FileExistsError(path)
    path.mkdir(parents=True)
    model.save(path / "model")
    monitor = model.get_env().envs[0]
    state = {
        "python_rng": random.getstate(),
        "numpy_rng": np.random.get_state(),
        "torch_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all()
        if torch.cuda.is_available()
        else None,
        "env_rng": env.np_random.bit_generator.state,
        "core": env.core.receipt(),
        "campaign": env.core.campaign.key,
        "schema_id": env.schema_id,
        "policy_decisions": env.policy_decisions,
        "num_timesteps": model.num_timesteps,
        "n_updates": model._n_updates,
        "monitor": {
            name: getattr(monitor, name)
            for name in (
                "needs_reset",
                "rewards",
                "episode_returns",
                "episode_lengths",
                "episode_times",
                "total_steps",
                "current_reset_info",
            )
        },
    }
    torch.save(state, path / "state.pt")
    write_new(
        path / "resume.json",
        seal(
            {
                "schema": "ppo-resume-v1",
                "boundary": "after_consumed_rollout",
                "schema_id": env.schema_id,
                "model_sha256": hashlib.sha256(
                    (path / "model.zip").read_bytes()
                ).hexdigest(),
                "state_sha256": hashlib.sha256(
                    (path / "state.pt").read_bytes()
                ).hexdigest(),
                "runtime": {"torch": str(torch.__version__), "numpy": np.__version__},
            }
        ),
    )


def load_resume(path: Path, env: MolecularEnv) -> MaskablePPO:
    receipt = json.loads((path / "resume.json").read_text())
    verify(receipt)
    if receipt["schema_id"] != env.schema_id:
        raise ValueError("Resume schema mismatch")
    if receipt["runtime"] != {"torch": str(torch.__version__), "numpy": np.__version__}:
        raise ValueError("Exact continuation requires matching numerical runtime")
    for name in ("model", "state"):
        file = path / ("model.zip" if name == "model" else "state.pt")
        if hashlib.sha256(file.read_bytes()).hexdigest() != receipt[f"{name}_sha256"]:
            raise ValueError("Resume artifact hash mismatch")
    # Local trusted, hash-verified checkpoint; contains NumPy/Python RNG objects.
    state = torch.load(path / "state.pt", map_location="cpu", weights_only=False)
    campaign = next(c for c in env.campaigns if c.key == state["campaign"])
    env.core = restore_core(
        state["core"], campaign, env.registry, env.site_capacity, env.archive_capacity
    )
    env.core.on_receipt = env.core.session.on_receipt = env.on_receipt
    env.policy_decisions = state.get("policy_decisions", 0)
    env.np_random.bit_generator.state = state["env_rng"]
    model = MaskablePPO.load(
        path / "model.zip", env=env, device="cpu", force_reset=False
    )
    monitor = model.get_env().envs[0]
    for name, value in state["monitor"].items():
        setattr(monitor, name, value)
    random.setstate(state["python_rng"])
    np.random.set_state(state["numpy_rng"])
    torch.set_rng_state(state["torch_rng"])
    if state["cuda_rng"] is not None:
        torch.cuda.set_rng_state_all(state["cuda_rng"])
    if (
        model.num_timesteps != state["num_timesteps"]
        or model._n_updates != state["n_updates"]
    ):
        raise ValueError("Resume training counters changed")
    return model
