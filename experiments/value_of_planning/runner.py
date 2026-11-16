"""Sealed model-based planning grid and fresh PPO comparison; no measured data."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import time
from functools import cache
from itertools import product
from pathlib import Path

from model import BeliefProblem, joint_prior, mean_entropy, panel_probabilities

from oligo_engine.molecular_design.artifacts import seal, verify, write_new

GRID = {
    "uncertainty": (0.1, 0.5, 1.0),
    "confirm_cost": (2, 3, 4),
    "budget": (4, 6, 8),
    "prevalence": (0.25, 0.5, 0.75),
    "coupling": (0.0, 0.75),
}


def cells() -> list[dict]:
    return [dict(zip(GRID, values, strict=True)) for values in product(*GRID.values())]


def problem(cell: dict) -> BeliefProblem:
    return BeliefProblem(
        joint_prior(
            panel_probabilities(cell["prevalence"], cell["uncertainty"]),
            cell["coupling"],
        ),
        cell["confirm_cost"],
        cell["budget"],
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(output: Path) -> None:
    write_new(
        output / "protocol.json",
        seal(
            {
                "schema": "model-based-value-of-planning-v1",
                "purpose": (
                    "ASO-inspired synthetic belief-MDP sensitivity; no measured "
                    "ASO result"
                ),
                "panel_size": 4,
                "grid": GRID,
                "screen_accuracy": 0.9,
                "screen_cost": 1,
                "primary_display": {"budget": 6, "prevalence": 0.5, "coupling": 0.75},
                "confirmation": (
                    "perfect binary endpoint label; may be purchased without screen"
                ),
                "objective": (
                    "expected distinct positive definitive confirmations by budget"
                ),
                "belief": (
                    "exact joint posterior over16binaryworlds, all policies same "
                    "observations"
                ),
                "uncertainty": "q_i=(1-u)*z_i+u*p; panelmean p fixed; entropy reported",
                "coupling": (
                    "within-pair mixture of independent and shared-uniform draws;"
                    " marginals fixed"
                ),
                "baselines": ["greedy", "bayesian_rollout", "random", "optimal_dp"],
                "clairvoyant": (
                    "separate unattainable hidden-world upper bound, not Bayes optimal"
                ),
                "ppo": {
                    "seeds": [2700, 2701, 2702],
                    "timesteps": 32768,
                    "n_steps": 256,
                    "batch_size": 64,
                    "n_epochs": 2,
                    "learning_rate": 0.0003,
                    "gamma": 1.0,
                    "gae_lambda": 1.0,
                    "ent_coef": 0.01,
                    "hidden": [64, 64],
                    "torch_threads": 1,
                    "selection": (
                        "fixed last checkpoint; no performance-based selection"
                    ),
                    "training_tasks": "uniform sampled declared162cells",
                    "evaluation": (
                        "exact expected return of deterministic argmax deployment on "
                        "same taskgrid; no held-out transfer claim"
                    ),
                },
                "training_runtime_gate": (
                    "profile1024steps without outcome selection; launch3fixedfits"
                    " only if forecast below180seconds"
                ),
                "display_slice": (
                    "allprevalences/budgets, separatecouplingpanels; no outcome-"
                    "based selection"
                ),
                "inputs": {
                    str(p): digest(p)
                    for p in sorted(Path(__file__).parent.glob("*.py"))
                },
                "measured_outcomes_accessed": 0,
            }
        ),
    )


def locked(output: Path) -> dict:
    protocol = json.loads((output / "protocol.json").read_text())
    verify(protocol)
    for p, expected in protocol["inputs"].items():
        if digest(Path(p)) != expected:
            raise ValueError("Frozen implementation changed")
    return protocol


def grid(output: Path) -> None:
    protocol = locked(output)
    rows, start = [], time.monotonic()
    for i, cell in enumerate(cells()):
        p = problem(cell)
        t = time.monotonic()
        optimal = p.optimal_value(p.initial)
        greedy = p.greedy_value(p.initial)
        rollout = p.rollout_value(p.initial)
        random = p.random_value(p.initial)
        clairvoyant = p.clairvoyant_bound()
        if not (
            optimal + 1e-10 >= rollout >= greedy - 1e-10
            and clairvoyant + 1e-10 >= optimal
        ):
            raise ValueError("Planning value ordering invariant failed")
        rows.append(
            {
                "cell": i,
                **cell,
                "mean_entropy_bits": mean_entropy(
                    panel_probabilities(cell["prevalence"], cell["uncertainty"])
                ),
                "optimal": optimal,
                "greedy": greedy,
                "bayesian_rollout": rollout,
                "random": random,
                "clairvoyant": clairvoyant,
                "planning_gain": optimal - greedy,
                "remaining_gain_after_rollout": optimal - rollout,
                "dp_states": p.optimal_value.cache_info().currsize,
                "seconds": time.monotonic() - t,
            }
        )
        del p
        gc.collect()
    write_new(
        output / "grid.json",
        seal(
            {
                "protocol_seal": protocol["seal"],
                "rows": rows,
                "seconds": time.monotonic() - start,
            }
        ),
    )
    with (output / "grid.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(
        json.dumps(
            {
                "cells": len(rows),
                "seconds": time.monotonic() - start,
                "max_gain": max(r["planning_gain"] for r in rows),
            }
        ),
        flush=True,
    )


def train(output: Path) -> None:
    import numpy as np
    import torch
    from environment import PlanningEnv
    from sb3_contrib import MaskablePPO

    protocol = locked(output)
    torch.set_num_threads(1)
    cfg = protocol["ppo"]

    def model(seed: int):
        return MaskablePPO(
            "MlpPolicy",
            PlanningEnv(cells()),
            seed=seed,
            n_steps=cfg["n_steps"],
            batch_size=cfg["batch_size"],
            n_epochs=cfg["n_epochs"],
            learning_rate=cfg["learning_rate"],
            gamma=1,
            gae_lambda=1,
            ent_coef=cfg["ent_coef"],
            policy_kwargs={"net_arch": dict(pi=cfg["hidden"], vf=cfg["hidden"])},
            device="cpu",
            verbose=0,
        )

    t = time.monotonic()
    pilot = model(2699)
    pilot.learn(1024)
    elapsed = time.monotonic() - t
    forecast = elapsed * cfg["timesteps"] / 1024 * len(cfg["seeds"])
    write_new(
        output / "runtime-profile.json",
        seal(
            {
                "seconds": elapsed,
                "forecast_seconds": forecast,
                "training_decisions": 1024,
                "seed": 2699,
                "excluded_from_comparison": True,
                "performance_not_used_for_gate": True,
            }
        ),
    )
    del pilot
    gc.collect()
    if forecast > 180:
        write_new(
            output / "ppo.json",
            seal(
                {
                    "protocol_seal": protocol["seal"],
                    "status": "not_launched_runtime_gate",
                    "forecast_seconds": forecast,
                }
            ),
        )
        return
    rows, costs = [], []
    for seed in cfg["seeds"]:
        t = time.monotonic()
        policy = model(seed)
        policy.learn(cfg["timesteps"])
        training_seconds = time.monotonic() - t
        path = output / f"ppo-{seed}.zip"
        policy.save(path)
        train_env = policy.get_env().envs[0].unwrapped
        costs.append(
            {
                "seed": seed,
                "seconds": training_seconds,
                "decisions": cfg["timesteps"],
                "model_sha256": digest(path),
                "simulated_assay_cost": train_env.total_cost,
                "simulated_confirmations": train_env.total_confirmations,
                "simulated_screens": train_env.total_screens,
            }
        )
        policy.policy.set_training_mode(False)
        for i, cell in enumerate(cells()):
            p = problem(cell)

            @cache
            def value(state):
                choices = p.actions(state)
                if not choices:
                    return 0.0
                mask = np.zeros(9, bool)
                mask[list(choices)] = True
                mask[8] = True
                action, _ = policy.predict(
                    np.asarray(p.observation(state), np.float32),
                    action_masks=mask,
                    deterministic=True,
                )
                return (
                    0.0 if int(action) == 8 else p.expected(state, int(action), value)
                )

            rows.append({"cell": i, "seed": seed, "expected_yield": value(p.initial)})
            value.cache_clear()
        policy = None
        gc.collect()
        print(
            json.dumps({"seed": seed, "training_seconds": training_seconds}), flush=True
        )
    write_new(
        output / "ppo.json",
        seal(
            {
                "protocol_seal": protocol["seal"],
                "status": "complete",
                "costs": costs,
                "rows": rows,
            }
        ),
    )


def plot(output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    locked(output)
    data = json.loads((output / "grid.json").read_text())
    verify(data)
    for coupling in GRID["coupling"]:
        for metric, title in [
            ("planning_gain", "Exact optimum minus greedy"),
            ("remaining_gain_after_rollout", "Exact optimum minus Bayesian rollout"),
        ]:
            fig, axes = plt.subplots(3, 3, figsize=(12, 10), constrained_layout=True)
            vmax = max(0.001, max(r[metric] for r in data["rows"]))
            for ri, budget in enumerate(GRID["budget"]):
                for ci, prevalence in enumerate(GRID["prevalence"]):
                    ax = axes[ri, ci]
                    matrix = np.array(
                        [
                            [
                                next(
                                    r[metric]
                                    for r in data["rows"]
                                    if r["coupling"] == coupling
                                    and r["budget"] == budget
                                    and r["prevalence"] == prevalence
                                    and r["uncertainty"] == u
                                    and r["confirm_cost"] == cost
                                )
                                for cost in GRID["confirm_cost"]
                            ]
                            for u in GRID["uncertainty"]
                        ]
                    )
                    im = ax.imshow(
                        matrix, vmin=0, vmax=vmax, cmap="viridis", origin="lower"
                    )
                    ax.set_xticks(range(3), GRID["confirm_cost"])
                    ax.set_yticks(range(3), GRID["uncertainty"])
                    ax.set_title(f"Budget {budget}; prevalence {prevalence}")
                    ax.set_xlabel("Confirmation / screen cost")
                    ax.set_ylabel("Marginal uncertainty strength u")
                    for y in range(3):
                        for x in range(3):
                            ax.text(
                                x,
                                y,
                                f"{matrix[y, x]:.3f}",
                                ha="center",
                                va="center",
                                color="white"
                                if matrix[y, x] < vmax * 0.65
                                else "black",
                            )
            fig.colorbar(im, ax=axes, label="Expected additional confirmed hits")
            fig.suptitle(
                f"{title} | coupling mixture {coupling}\n"
                "MODEL-BASED: four candidates, screen accuracy 0.9; "
                "no measured ASO outcomes"
            )
            stem = f"{metric}-coupling-{coupling}"
            fig.savefig(output / f"{stem}.png", dpi=160)
            fig.savefig(output / f"{stem}.pdf")
            plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "grid", "train", "plot"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    {"prepare": prepare, "grid": grid, "train": train, "plot": plot}[args.phase](
        args.output
    )


if __name__ == "__main__":
    main()
