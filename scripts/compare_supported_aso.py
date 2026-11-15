"""Costed local optimizer comparison using the verified real efficacy bundle."""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from oligo_engine.design.aso_space import ASODesignSpace, TargetContext
from oligo_engine.reward.portable import CHEMISTRY, PortableEfficacy
from oligo_engine.reward.scoring import ScoringSession
from oligo_engine.rl.environment import ASOEnv
from oligo_engine.rl.evaluate import PolicyPartitions, paired_summary
from oligo_engine.rl.local_costs import LocalScoringSession
from oligo_engine.rl.ppo import load_policy, rollout, train
from oligo_engine.rl.search import search


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument(
        "--transcripts", type=Path, default=Path("artifacts/transcripts")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Preserve completed comparison")
    cfg = json.loads(Path("configs/rl/supported_aso_comparison_v1.json").read_text())
    readiness = json.loads((args.bundle_dir / "assessment.json").read_text())[
        "provisional_readiness_gate"
    ]
    if not readiness:
        parser.error("Measured diagnostic gate did not pass; do not scale RL")
    args.output.mkdir(parents=True)
    manifest = json.loads((args.bundle_dir / "bundle-manifest.json").read_text())
    predictor = PortableEfficacy(
        args.bundle_dir / "efficacy.json", manifest["artifact_sha256"]
    )
    scorer = predictor.scorer()
    spaces = {}
    for role in ("training", "validation", "final"):
        gene = cfg[f"{role}_gene"]
        raw = json.loads((args.transcripts / f"homo_sapiens.{gene}.json").read_text())
        target = TargetContext(
            gene,
            raw["transcript_id"],
            raw["sequence"],
            raw["species"],
            raw["source"]
            + "; sha256="
            + hashlib.sha256(raw["sequence"].encode()).hexdigest(),
        )
        spaces[role] = ASODesignSpace(
            target,
            (len(target.sequence) - 20) // 2,
            cfg["radius"],
            cfg["horizon"],
            CHEMISTRY,
        )
    PolicyPartitions(
        (cfg["training_gene"],), (cfg["validation_gene"],), (cfg["final_gene"],)
    )
    (args.output / "frozen-config.json").write_text(
        json.dumps(
            cfg
            | {
                "spaces": {k: asdict(v) for k, v in spaces.items()},
                "scorer_identity": scorer.identity,
                "bundle_sha256": manifest["artifact_sha256"],
            },
            indent=2,
        )
        + "\n"
    )

    def session(space, budget=10, local=True, requests=100):
        arguments = (scorer, space.target, predictor.assay, budget, requests)
        return (
            LocalScoringSession(space, *arguments)
            if local
            else ScoringSession(*arguments)
        )

    # Real inputs must agree across portable inference, scorer and environment.
    probe = ASOEnv(spaces["training"], session(spaces["training"]))
    obs, info = probe.reset(seed=0)
    assert probe.observation_space.contains(obs)
    candidate = spaces["training"].candidate(spaces["training"].start)
    assert info["score"]["endpoints"][0]["raw"] == predictor.predict_helm(
        candidate.helm, predictor.assay
    )
    assert info["score"]["endpoints"][1]["status"] == "unavailable"

    validation_rows = []
    policies = {}
    manifests = {}
    for seed in cfg["seeds"]:
        training = ASOEnv(
            spaces["training"], session(spaces["training"], 100, False, 100000)
        )
        validation = ASOEnv(
            spaces["validation"], session(spaces["validation"], 100, False, 10000)
        )
        directory = args.output / f"policy-{seed}-initial"
        model, receipt = train(
            training, validation, directory, steps=cfg["initial_steps"], seed=seed
        )
        policies[(seed, "initial")] = directory
        manifests[f"{seed}-initial"] = receipt
        for method in cfg["controls"] + ["ppo"]:
            s = session(spaces["validation"], cfg["expansion_validation_budget"])
            result = (
                rollout(model, ASOEnv(spaces["validation"], s), seed)
                if method == "ppo"
                else search(spaces["validation"], s, method, seed)
            )
            validation_rows.append(
                {"seed": seed, "method": method, "best_reward": result["best_reward"]}
            )
        print(f"initial real-scorer policy seed {seed} complete", flush=True)
    means = {
        method: float(
            np.mean(
                [r["best_reward"] for r in validation_rows if r["method"] == method]
            )
        )
        for method in cfg["controls"] + ["ppo"]
    }
    expand = (
        means["ppo"]
        > max(means[m] for m in cfg["controls"] if m != "unchanged") + 1e-12
    )
    (args.output / "expansion-decision.json").write_text(
        json.dumps(
            {
                "validation_mean_utility": means,
                "expand": bool(expand),
                "final_comparisons_read": False,
                "reason": "preset validation-only superiority gate",
            },
            indent=2,
        )
        + "\n"
    )
    if expand:
        for seed in cfg["seeds"]:
            training = ASOEnv(
                spaces["training"], session(spaces["training"], 100, False, 100000)
            )
            validation = ASOEnv(
                spaces["validation"], session(spaces["validation"], 100, False, 10000)
            )
            directory = args.output / f"policy-{seed}-expanded"
            _, receipt = train(
                training, validation, directory, steps=cfg["expanded_steps"], seed=seed
            )
            policies[(seed, "expanded")] = directory
            manifests[f"{seed}-expanded"] = receipt
    final = spaces["final"]
    reference = search(final, session(final, 100, False, 1000), "exhaustive")
    results = []
    comparisons = []
    for seed in cfg["seeds"]:
        for budget in cfg["unique_budgets"]:
            arms = []
            for method in cfg["controls"]:
                arms.append(search(final, session(final, budget), method, seed))
            for stage in ("initial", "expanded") if expand else ("initial",):
                env = ASOEnv(final, session(final, budget))
                model = load_policy(policies[(seed, stage)], env)
                result = rollout(model, env, seed)
                second = rollout(model, ASOEnv(final, session(final, budget)), seed)
                assert (
                    result["actions"] == second["actions"]
                    and result["archive"] == second["archive"]
                )
                result["method"] = f"ppo_{stage}"
                arms.append(result)
            for arm in arms:
                assert arm["moves"] <= cfg["horizon"]
                assert arm["unique_scores"] <= budget
                arm["seed"], arm["budget"] = seed, budget
            results.extend(arms)
            comparisons.append(paired_summary(arms, reference))
    output = {
        "status": "real_surrogate_local_search_diagnostic",
        "config": cfg,
        "expanded": bool(expand),
        "validation_rows": validation_rows,
        "training_manifests": manifests,
        "reference": reference,
        "runs": results,
        "paired_summaries": comparisons,
        "scorer_identity": scorer.identity,
        "measured_outcomes_used_as_rewards": False,
        "safety_validated": False,
        "reload_identical": True,
        "same_local_access": True,
        "limits": (
            "One window per role, known-model target genes, frozen efficacy only; "
            "not a biological design superiority result."
        ),
    }
    (args.output / "comparison.json").write_text(
        json.dumps(output, indent=2, allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {"expanded": bool(expand), "validation_means": means, "runs": len(results)}
        )
    )


if __name__ == "__main__":
    main()
