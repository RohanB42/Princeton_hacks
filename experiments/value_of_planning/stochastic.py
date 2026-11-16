"""Posthoc exact stochastic deployment evaluation; no training or selection."""

import argparse
import hashlib
import json
import time
from functools import cache
from pathlib import Path

import numpy as np
import torch
from runner import cells, digest, locked, problem
from sb3_contrib import MaskablePPO

from oligo_engine.molecular_design.artifacts import seal, verify, write_new


def distribution(policy, p, state) -> np.ndarray:
    """Action probabilities use the same observable belief and legal mask."""
    mask = np.zeros(9, bool)
    mask[list(p.actions(state))] = True
    mask[8] = True
    obs, _ = policy.policy.obs_to_tensor(np.asarray(p.observation(state), np.float32))
    with torch.no_grad():
        probs = policy.policy.get_distribution(obs, action_masks=mask)
        return probs.distribution.probs[0].cpu().numpy()


def expectation(policy, p) -> tuple[float, int]:
    @cache
    def value(state):
        actions = p.actions(state)
        if not actions:
            return 0.0
        probabilities = distribution(policy, p, state)
        if not np.isclose(probabilities.sum(), 1, atol=1e-6):
            raise ValueError("Action probabilities do not normalize")
        return sum(
            float(probabilities[a]) * p.expected(state, a, value) for a in actions
        )

    result = value(p.initial)
    count = value.cache_info().currsize
    value.cache_clear()
    return result, count


def run(output: Path) -> None:
    torch.set_num_threads(1)
    original = locked(output)
    grid = json.loads((output / "grid.json").read_text())
    verify(grid)
    seeds = original["ppo"]["seeds"]
    protocol = seal(
        {
            "schema": "planning-stochastic-evaluation-v1",
            "status": "posthoc supplementary deployment diagnostic",
            "parent_protocol_seal": original["seal"],
            "grid_seal": grid["seal"],
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "policy_sha256": {str(s): digest(output / f"ppo-{s}.zip") for s in seeds},
            "estimator": "exact policy-probability-weighted Bellman expectation",
            "runtime_gate": "largest-state cell forecast under90seconds for486cells",
            "performance_used_for_selection": False,
        }
    )
    write_new(output / "stochastic-protocol.json", protocol)
    profiled = max(grid["rows"], key=lambda r: r["dp_states"])["cell"]
    policy = MaskablePPO.load(output / f"ppo-{seeds[0]}.zip", device="cpu")
    policy.policy.set_training_mode(False)
    start = time.monotonic()
    _, states = expectation(policy, problem(cells()[profiled]))
    elapsed = time.monotonic() - start
    forecast = elapsed * len(cells()) * len(seeds)
    if forecast > 90:
        write_new(
            output / "stochastic-results.json",
            seal(
                {
                    "protocol_seal": protocol["seal"],
                    "status": "not_launched_runtime_gate",
                    "forecast_seconds": forecast,
                    "profile_states": states,
                }
            ),
        )
        return
    rows = []
    for seed in seeds:
        policy = MaskablePPO.load(output / f"ppo-{seed}.zip", device="cpu")
        policy.policy.set_training_mode(False)
        for i, cell in enumerate(cells()):
            value, count = expectation(policy, problem(cell))
            if value > grid["rows"][i]["optimal"] + 1e-6:
                raise ValueError("Stochastic policy exceeds Bayesian optimum")
            rows.append(
                {"seed": seed, "cell": i, "expected_yield": value, "states": count}
            )
    write_new(
        output / "stochastic-results.json",
        seal(
            {
                "protocol_seal": protocol["seal"],
                "status": "complete",
                "rows": rows,
                "seconds": time.monotonic() - start,
                "forecast_seconds": forecast,
            }
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
