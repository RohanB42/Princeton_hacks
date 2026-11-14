"""Fixed-duration shaping ablation and fresh-start matched-request evaluation."""

import json
from pathlib import Path
from random import Random
from statistics import mean, stdev

import numpy as np
from sb3_contrib import MaskablePPO

from oligo_engine.design.environment import BaseEditEnv
from oligo_engine.design.huesken_bundle import HueskenRidgeBundle
from oligo_engine.design.rl import atomic_json, run_training, starting_manifest
from oligo_engine.design.scoring import FrozenRidgeScorer
from oligo_engine.design.search import hamming, mutate, random_candidate


def main() -> None:
    root = Path("artifacts/rl_design/fresh_shaping_v1")
    root.mkdir(parents=True, exist_ok=False)
    bundle_path = Path(
        "artifacts/rl_design/huesken_ridge_bundle_seed0/ridge_bundle.json"
    )
    bundle = HueskenRidgeBundle.load(bundle_path)
    old = starting_manifest(bundle)
    excluded = set(old["train"] + old["validation"] + old["final"])
    fresh = sorted(set(bundle.training_sequences) - excluded)
    Random(8142026).shuffle(fresh)
    starts = fresh[:32]
    atomic_json(
        root / "protocol.json",
        {
            "fresh_starts": starts,
            "excluded_starts": sorted(excluded),
            "seeds": [11, 23, 37, 53, 71],
            "steps": 4096,
            "updates": 32,
            "evaluation_requests_per_start": 16,
            "shaping": "r + Phi(next) - Phi(current), initial and terminal Phi=0",
            "comparison": "equal training steps, NOT equal training oracle cost",
            "selection": "validation only; no tuning after fresh evaluation",
        },
    )
    rows = []
    for seed in [11, 23, 37, 53, 71]:
        shaped_dir = root / f"shaped_seed{seed}"
        report = run_training(
            shaped_dir, seed, "huesken", bundle_path, 32, 128, shaping=True
        )
        paths = {
            "terminal": Path(
                f"artifacts/rl_design/improvement_4096/seed{seed}/best.zip"
            ),
            "shaped": shaped_dir / "best.zip",
        }
        models = {k: MaskablePPO.load(p, device="cpu") for k, p in paths.items()}
        for model in models.values():
            model.set_random_seed(seed + 10000)
        for index, start in enumerate(starts):
            for method in ["terminal", "shaped", "random", "evolutionary", "unchanged"]:
                scorer = FrozenRidgeScorer(bundle)
                rng = Random(seed * 1000 + index)
                env = BaseEditEnv((start,), scorer, 8)
                best = -float("inf")
                incumbent = start
                incumbent_score = -float("inf")
                for trial in range(1 if method == "unchanged" else 16):
                    if method in models:
                        obs, _ = env.reset(seed=seed + trial)
                        while True:
                            action, _ = models[method].predict(
                                obs,
                                action_masks=env.action_masks(),
                                deterministic=False,
                            )
                            obs, value, done, _, info = env.step(int(action))
                            if done:
                                break
                    else:
                        if method == "unchanged" or (
                            method == "evolutionary" and trial == 0
                        ):
                            candidate = start
                        elif method == "random":
                            candidate = random_candidate((start,), rng, 8)
                        else:
                            candidate = mutate(incumbent, rng)
                            if hamming(candidate, start) > 8:
                                candidate = incumbent
                        value = scorer.score(candidate).reward
                        if value > incumbent_score:
                            incumbent, incumbent_score = candidate, value
                    best = max(best, value)
                rows.append(
                    {
                        "seed": seed,
                        "start": start,
                        "method": method,
                        "best_reward": best,
                        "requests": scorer.requests,
                        "unique_scores": scorer.unique_evaluations,
                    }
                )
        atomic_json(root / f"evaluation_seed{seed}.json", rows[-160:])
        print(seed, report["best_validation_mean_reward"], flush=True)
    summary = {}
    for method in ["terminal", "shaped", "random", "evolutionary", "unchanged"]:
        values = [
            mean(
                r["best_reward"]
                for r in rows
                if r["seed"] == seed and r["method"] == method
            )
            for seed in [11, 23, 37, 53, 71]
        ]
        summary[method] = {
            "seed_means": values,
            "mean": mean(values),
            "sd": stdev(values),
        }
    diff = np.array(summary["shaped"]["seed_means"]) - summary["terminal"]["seed_means"]
    half = 2.7764451052 * float(diff.std(ddof=1)) / np.sqrt(5)
    summary["paired_shaped_minus_terminal"] = {
        "mean": float(diff.mean()),
        "ci95": [float(diff.mean() - half), float(diff.mean() + half)],
    }
    atomic_json(root / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
