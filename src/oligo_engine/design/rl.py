"""Bounded masked-PPO engineering runs for restricted RNA1 sequence proposals."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import time
from pathlib import Path
from random import Random
from statistics import fmean

from oligo_engine.design.huesken_bundle import HueskenRidgeBundle
from oligo_engine.design.scoring import FrozenRidgeScorer, ToyGScorer
from oligo_engine.design.search import search


def atomic_json(path: Path, value: dict | list) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def starting_manifest(bundle: HueskenRidgeBundle) -> dict:
    unique = list(dict.fromkeys(bundle.training_sequences))
    if len(unique) < 96:
        raise ValueError("Fewer than 96 unique training-only start sequences")
    Random(2026).shuffle(unique)
    return {
        "method": "shuffle_frozen_training_sequences_seed_2026",
        "train": unique[:64],
        "validation": unique[64:80],
        "final": unique[80:96],
        "bundle_identity": bundle.identity(),
    }


def rollout(model, environment, start: str) -> dict:
    observation, _ = environment.reset(options={"start": start})
    actions = []
    while True:
        action, _ = model.predict(
            observation,
            action_masks=environment.action_masks(),
            deterministic=True,
        )
        code = int(action)
        actions.append(code)
        observation, reward, terminated, truncated, info = environment.step(code)
        if terminated or truncated:
            if info.get("invalid_action"):
                raise ValueError("PPO emitted an invalid masked action")
            return {
                "start": start,
                "sequence": info["sequence"],
                "actions": actions,
                "reward": float(reward),
                "score": info["score"],
                "terminated": terminated,
                "truncated": truncated,
            }


def evaluate(model, starts: tuple[str, ...], scorer, edit_budget: int) -> dict:
    from oligo_engine.design.environment import BaseEditEnv

    environment = BaseEditEnv(starts, scorer, edit_budget=edit_budget)
    episodes = [rollout(model, environment, start) for start in starts]
    return {
        "mean_reward": fmean(item["reward"] for item in episodes),
        "mean_raw_prediction": fmean(
            item["score"]["raw_prediction"] for item in episodes
        ),
        "unique_candidates": len({item["sequence"] for item in episodes}),
        "score_requests": scorer.requests,
        "unique_scores": scorer.unique_evaluations,
        "episodes": episodes,
    }


def score_trace(scorer) -> list[dict]:
    best = float("-inf")
    trace = []
    for count, record in enumerate(scorer.cache.values(), start=1):
        best = max(best, record.reward)
        trace.append({"unique_scores": count, "best_reward": best})
    return trace


def save_candidate_archive(scorer, output: Path, synthetic: bool) -> None:
    with (output / "candidates.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "rna1_sequence",
                "predicted_inhibition_raw",
                "reward",
                "domain_distance",
                "domain_penalty",
                "uncertainty_available",
                "unvalidated_hypothesis",
            ]
        )
        for result in sorted(
            scorer.cache.values(), key=lambda item: item.reward, reverse=True
        ):
            writer.writerow(
                [
                    result.sequence,
                    result.raw_prediction,
                    result.reward,
                    result.nearest_training_distance,
                    result.domain_penalty,
                    False,
                    not synthetic,
                ]
            )


def plot_search_comparison(trace: list[dict], comparisons: dict, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    for label, points, color in (
        ("MaskablePPO", trace, "#7B5AA6"),
        ("Random search", comparisons["random"]["trace"], "#2574A9"),
        ("Evolutionary search", comparisons["evolutionary"]["trace"], "#D67D22"),
    ):
        ax.plot(
            [item["unique_scores"] for item in points],
            [item["best_reward"] for item in points],
            label=label,
            color=color,
            linewidth=2,
        )
    ax.set_xlabel("Unique frozen-scorer evaluations")
    ax.set_ylabel("Best predictor-based reward seen")
    ax.set_title("Restricted Huesken surrogate search")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.text(
        0.5,
        0.01,
        "One engineering seed; predicted reward is not measured inhibition.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(output / "search_comparison.png", dpi=180)
    fig.savefig(output / "search_comparison.svg")
    plt.close(fig)


def run_training(
    output: Path,
    seed: int,
    mode: str,
    bundle_path: Path | None,
    updates: int,
    n_steps: int,
    shaping: bool = False,
) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be empty")
    if updates < 1 or n_steps < 64 or n_steps % 64:
        raise ValueError("Require positive updates and n_steps divisible by 64")
    started = time.monotonic()
    os.environ.setdefault("MPLCONFIGDIR", str(output / "matplotlib-cache"))
    os.environ.setdefault("XDG_CACHE_HOME", str(output / "xdg-cache"))
    from sb3_contrib import MaskablePPO

    from oligo_engine.design.environment import BaseEditEnv

    output.mkdir(parents=True, exist_ok=True)
    atomic_json(
        output / "status.json", {"status": "running", "mode": mode, "seed": seed}
    )
    bundle = None
    if mode == "toy":
        train_starts = ("AAAA",)
        validation_starts = ("AAAA",)
        final_starts = ("AAAA",)
        edit_budget = 4

        def scorer_factory():
            return ToyGScorer(4)

        bundle_identity = None
    elif mode == "huesken":
        if bundle_path is None:
            raise ValueError("Huesken mode requires a frozen predictor bundle")
        bundle = HueskenRidgeBundle.load(bundle_path)
        manifest = starting_manifest(bundle)
        train_starts = tuple(manifest["train"])
        validation_starts = tuple(manifest["validation"])
        final_starts = tuple(manifest["final"])
        edit_budget = 8

        def scorer_factory():
            return FrozenRidgeScorer(bundle)

        bundle_identity = bundle.identity()
        atomic_json(output / "starts.json", manifest)
    else:
        raise ValueError("Supported modes are toy and restricted Huesken")
    scorer = scorer_factory()
    environment = BaseEditEnv(train_starts, scorer, edit_budget=edit_budget)
    if shaping:
        from oligo_engine.design.environment import PotentialShaping

        environment = PotentialShaping(environment)
    atomic_json(
        output / "action_vocabulary.json",
        {
            "version": "base_substitution_v1",
            "actions": list(enumerate(environment.unwrapped.action_vocabulary)),
            "observation": "4_base_onehot_per_position_plus_fraction_edits_remaining",
            "edit_budget": edit_budget,
            "stop_action": 0,
        },
    )
    model = MaskablePPO(
        "MlpPolicy",
        environment,
        learning_rate=3e-4,
        n_steps=n_steps,
        batch_size=64,
        n_epochs=5,
        gamma=1.0,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        target_kl=0.02,
        policy_kwargs={"net_arch": [64, 64]},
        device="cpu",
        seed=seed,
        verbose=0,
    )
    import torch

    initial_weights = {
        key: value.detach().clone() for key, value in model.policy.state_dict().items()
    }
    untrained = evaluate(
        model, validation_starts, scorer_factory(), edit_budget=edit_budget
    )
    best_validation = float("-inf")
    history = []
    for update in range(1, updates + 1):
        model.learn(total_timesteps=n_steps, reset_num_timesteps=False)
        checkpoint = output / f"checkpoint-update-{update}.zip"
        model.save(checkpoint)
        validation = evaluate(
            model, validation_starts, scorer_factory(), edit_budget=edit_budget
        )
        record = {
            "update": update,
            "timesteps": model.num_timesteps,
            "training_score_requests": scorer.requests,
            "training_unique_scores": scorer.unique_evaluations,
            "validation_mean_reward": validation["mean_reward"],
            "validation_unique_candidates": validation["unique_candidates"],
            "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        }
        history.append(record)
        if validation["mean_reward"] > best_validation:
            best_validation = validation["mean_reward"]
            model.save(output / "best.zip")
        model.save(output / "last.zip")
        atomic_json(output / "training_history.json", history)
    changed = any(
        not torch.equal(initial_weights[key], value)
        for key, value in model.policy.state_dict().items()
    )
    if not changed:
        raise ValueError("PPO did not update policy parameters")
    best_model = MaskablePPO.load(output / "best.zip", env=environment, device="cpu")
    final = evaluate(
        best_model, final_starts, scorer_factory(), edit_budget=edit_budget
    )
    reloaded = MaskablePPO.load(output / "last.zip", env=environment, device="cpu")
    original_probe = rollout(
        model, BaseEditEnv(train_starts, scorer_factory(), edit_budget), train_starts[0]
    )
    reload_probe = rollout(
        reloaded,
        BaseEditEnv(train_starts, scorer_factory(), edit_budget),
        train_starts[0],
    )
    if original_probe != reload_probe:
        raise ValueError("Checkpoint reload changed masked deterministic inference")
    training_trace = score_trace(scorer)
    if mode == "huesken":
        budget = scorer.unique_evaluations
        comparisons = {}
        for method in ("random", "evolutionary"):
            comparisons[method] = search(
                method,
                scorer_factory(),
                train_starts,
                unique_budget=budget,
                seed=seed,
                edit_budget=edit_budget,
            )
    else:
        comparisons = {}
    save_candidate_archive(scorer, output, synthetic=mode == "toy")
    if comparisons:
        plot_search_comparison(training_trace, comparisons, output)
    report = {
        "status": "complete",
        "mode": mode,
        "seed": seed,
        "bundle_identity": bundle_identity,
        "bundle_path": str(bundle_path) if bundle_path else None,
        "scorer_identity": scorer.identity,
        "environment": {
            "edit_budget": edit_budget,
            "action_count": int(environment.action_space.n),
            "reward_timing": "terminal_only_gamma_1",
            "training_starts": len(train_starts),
            "validation_starts": len(validation_starts),
            "final_starts": len(final_starts),
        },
        "algorithm": {
            "name": "MaskablePPO",
            "potential_shaping": shaping,
            "learning_rate": 3e-4,
            "n_steps": n_steps,
            "updates": updates,
            "batch_size": 64,
            "n_epochs": 5,
            "gamma": 1.0,
            "policy_net_arch": [64, 64],
        },
        "policy_parameters_changed": changed,
        "untrained_validation": untrained,
        "best_validation_mean_reward": best_validation,
        "final_heldout_start_evaluation": final,
        "checkpoint_reload_equal": original_probe == reload_probe,
        "training_score_requests": scorer.requests,
        "training_unique_scores": scorer.unique_evaluations,
        "training_trace": training_trace,
        "comparators": comparisons,
        "history": history,
        "candidate_provenance": "synthetic_engineering_only"
        if mode == "toy"
        else "unvalidated_Huesken_Ridge_surrogate_prediction",
        "runtime_seconds": time.monotonic() - started,
        "software": {
            name: importlib.metadata.version(name)
            for name in (
                "gymnasium",
                "stable-baselines3",
                "sb3-contrib",
                "torch",
                "numpy",
            )
        }
        | {"python": platform.python_version()},
        "measured_efficacy_claim": False,
    }
    atomic_json(output / "report.json", report)
    atomic_json(
        output / "status.json", {"status": "complete", "mode": mode, "seed": seed}
    )
    return report


def audit(bundle_path: Path, output: Path | None) -> dict:
    bundle = HueskenRidgeBundle.load(bundle_path)
    report = {
        "status": "eligible_restricted_siRNA_sequence_proposal_only",
        "bundle_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest(),
        "bundle_identity": bundle.identity(),
        "source_sha256": bundle.source_sha256,
        "source_revision": bundle.source_revision,
        "endpoint": bundle.label_description,
        "modality": "unmodified_siRNA_sequence_proposal",
        "feature": "RNA1_19_base_onehot_57_columns",
        "target_context_supported": False,
        "chemistry_edits_supported": False,
        "uncertainty": "unavailable",
        "allowed_actions": "RNA1_base_substitution_or_STOP",
        "blocked_modes": [
            "target_aware_siRNA_design",
            "PS_2prime_MOE_ASO_potency_and_safety",
            "chemical_modification_editing",
        ],
    }
    if output:
        if output.exists():
            raise FileExistsError(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(output, report)
    return report


def infer_checkpoint(
    checkpoint: Path,
    bundle_path: Path,
    output: Path,
    split: str,
    count: int | None,
) -> dict:
    """Use the saved masked policy on a fixed, training-label-free start manifest."""
    if output.exists():
        raise FileExistsError(output)
    if split not in {"train", "validation", "final"}:
        raise ValueError("Unknown start split")
    if count is not None and count < 1:
        raise ValueError("Count must be positive")
    from sb3_contrib import MaskablePPO

    from oligo_engine.design.environment import BaseEditEnv

    run_dir = checkpoint.parent
    report = json.loads((run_dir / "report.json").read_text())
    manifest = json.loads((run_dir / "starts.json").read_text())
    bundle = HueskenRidgeBundle.load(bundle_path)
    scorer = FrozenRidgeScorer(bundle)
    if (
        report["status"] != "complete"
        or report["mode"] != "huesken"
        or report["bundle_identity"] != bundle.identity()
        or report["scorer_identity"] != scorer.identity
        or manifest["bundle_identity"] != bundle.identity()
    ):
        raise ValueError("Checkpoint, manifest, and frozen scorer identities differ")
    if checkpoint.name not in {
        "best.zip",
        "last.zip",
    } and not checkpoint.name.startswith("checkpoint-update-"):
        raise ValueError("Checkpoint must be a saved policy from the run directory")
    starts = tuple(manifest[split])
    environment = BaseEditEnv(starts, scorer, report["environment"]["edit_budget"])
    model = MaskablePPO.load(checkpoint, env=environment, device="cpu")
    episodes = [rollout(model, environment, start) for start in starts]
    unique = list({episode["sequence"]: episode for episode in episodes}.values())
    unique.sort(key=lambda episode: episode["reward"], reverse=True)
    selected = unique if count is None else unique[:count]
    result = {
        "status": "complete",
        "mode": "unvalidated_Huesken_Ridge_sequence_proposal",
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "bundle_identity": bundle.identity(),
        "scorer_identity": scorer.identity,
        "split": split,
        "start_count": len(starts),
        "mean_reward": fmean(episode["reward"] for episode in episodes),
        "unique_candidates": len(unique),
        "requested_count": count,
        "returned_count": len(selected),
        "shortfall": max(0, count - len(selected)) if count is not None else 0,
        "score_requests": scorer.requests,
        "unique_scores": scorer.unique_evaluations,
        "candidates": selected,
        "measured_efficacy_claim": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--bundle", type=Path, required=True)
    audit_parser.add_argument("--output", type=Path)
    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument("--output", type=Path, required=True)
    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--bundle", type=Path, required=True)
    train_parser.add_argument("--output", type=Path, required=True)
    train_parser.add_argument("--seed", type=int, default=11)
    train_parser.add_argument("--updates", type=int, default=2)
    train_parser.add_argument("--n-steps", type=int, default=128)
    for name in ("evaluate", "generate"):
        inference = subparsers.add_parser(name)
        inference.add_argument("--checkpoint", type=Path, required=True)
        inference.add_argument("--bundle", type=Path, required=True)
        inference.add_argument("--output", type=Path, required=True)
        inference.add_argument(
            "--split", choices=("train", "validation", "final"), default="final"
        )
        if name == "generate":
            inference.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    if args.command == "audit":
        result = audit(args.bundle, args.output)
        print(json.dumps(result, indent=2))
    elif args.command in {"evaluate", "generate"}:
        result = infer_checkpoint(
            args.checkpoint,
            args.bundle,
            args.output,
            args.split,
            args.count if args.command == "generate" else None,
        )
        print(
            f"{args.command}: {result['returned_count']} unique proposals from "
            f"{result['start_count']} starts; "
            f"mean surrogate reward={result['mean_reward']:.3f}"
        )
    else:
        result = run_training(
            args.output,
            11 if args.command == "smoke" else args.seed,
            "toy" if args.command == "smoke" else "huesken",
            None if args.command == "smoke" else args.bundle,
            4 if args.command == "smoke" else args.updates,
            128 if args.command == "smoke" else args.n_steps,
        )
        print(
            f"{result['mode']}: {result['training_unique_scores']} unique scores; "
            f"validation={result['best_validation_mean_reward']:.3f}; "
            f"final={result['final_heldout_start_evaluation']['mean_reward']:.3f}"
        )


if __name__ == "__main__":
    main()
