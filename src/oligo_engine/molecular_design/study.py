"""Frozen matched-budget matrix, developmental comparator selection, sealed runs."""

import json
from pathlib import Path

from .artifacts import QueryJournal, run_artifact, seal, verify, write_new
from .contracts import Campaign
from .evaluation import paired_summary, quality_auc
from .gym_env import MolecularEnv
from .optimizers import search
from .preflight import audit_partitions
from .scoring import FrozenRegistry, Session
from .training import TrainingConfig, load_policy, rollout, train


def compare(
    campaigns: tuple[Campaign, ...],
    registry: FrozenRegistry,
    config: dict,
    output: Path,
) -> dict:
    if output.exists():
        raise FileExistsError(output)
    training = tuple(c for c in campaigns if c.partition == "training")
    validation = tuple(c for c in campaigns if c.partition == "validation")
    final = tuple(c for c in campaigns if c.partition == "final")
    if not final:
        raise ValueError("Locked comparison requires explicit final campaigns")
    partitions = audit_partitions(campaigns)
    if registry.profile.purpose != "fixture":
        evidence = config.get("scientific_lock", {})
        verify(evidence)
        required = (
            "independent_evaluator",
            "metadata_audit",
            "risk_validation",
            "chemistry_validation",
            "predictor_exposure_audit",
        )
        if (
            registry.profile.purpose != "full"
            or not partitions["cross_target_claim_ready"]
        ):
            raise ValueError(
                "Real matrix requires full scope and sufficient target groups"
            )
        if evidence.get("registry") != registry.key or any(
            not evidence.get(k) for k in required
        ):
            raise ValueError("Real study evidence lock incomplete or mismatched")
        if evidence.get("campaigns") != [c.key for c in campaigns]:
            raise ValueError("Scientific lock does not cover these campaigns")
        for gate in required:
            reference = evidence[gate]
            if not isinstance(reference, dict) or set(reference) != {"path", "seal"}:
                raise ValueError(f"{gate} requires a sealed evidence artifact")
            report = json.loads(Path(reference["path"]).read_text())
            verify(report, reference["seal"])
            if (
                report.get("gate") != gate
                or report.get("status") != "passed"
                or report.get("registry") != registry.key
                or report.get("campaigns") != [c.key for c in campaigns]
            ):
                raise ValueError(f"{gate} evidence is unqualified or mismatched")
    seeds = config["seeds"]
    if len(set(seeds)) < 5:
        raise ValueError("At least five paired policy/search seeds required")
    output.mkdir(parents=True)
    lock = {
        "campaigns": [c.key for c in campaigns],
        "registry": registry.key,
        "seeds": seeds,
        "methods": config["methods"],
        "training": config["training"],
        "partitions": partitions,
        "primary": "final archive quality",
        "comparator_selection": (
            "highest mean validation quality among active controls; alphabetical ties"
        ),
    }
    write_new(output / "protocol.json", seal(lock))
    development = []
    for method in config["methods"]:
        if method == "initial":
            continue
        qualities = []
        for c in validation:
            for seed in seeds:
                journal = QueryJournal(
                    output / "development" / f"{c.name}-{method}-{seed}.queries.jsonl"
                )
                receipt = search(Session(c, registry, journal), method, seed)
                qualities.append(receipt["final_quality"])
                write_new(
                    output / "development" / f"{c.name}-{method}-{seed}.json",
                    run_artifact(c, receipt),
                )
        development.append((sum(qualities) / len(qualities), method))
    baseline = sorted(development, key=lambda x: (-x[0], x[1]))[0][1]
    write_new(
        output / "comparator-selection.json",
        seal({"selected": baseline, "development": development}),
    )
    records = []
    # Final fixture targets share capacities, never outcomes or selection feedback.
    for seed in seeds:
        training_config = TrainingConfig(
            **(
                {
                    "site_capacity": max(len(c.target.sequence) for c in campaigns),
                    "archive_capacity": max(c.requests for c in campaigns),
                }
                | config["training"]
                | {"seed": seed}
            )
        )
        policy_dir = output / f"policy-{seed}"
        train(training, validation, registry, training_config, policy_dir)
        env = MolecularEnv(
            final,
            registry,
            training_config.site_capacity,
            training_config.archive_capacity,
            decoder=training_config.decoder,
        )
        policy = load_policy(policy_dir, env)
        for i, c in enumerate(final):
            for method in config["methods"] + ["ppo"]:
                journal = QueryJournal(
                    output / "final" / f"{c.name}-{method}-{seed}.queries.jsonl"
                )
                env.on_receipt = journal
                receipt = (
                    rollout(policy, env, i, seed)
                    if method == "ppo"
                    else search(Session(c, registry, journal), method, seed)
                )
                artifact = run_artifact(c, receipt, config.get("panel_size", 10))
                write_new(output / "final" / f"{c.name}-{method}-{seed}.json", artifact)
                records.append(
                    {
                        "target": c.target.gene,
                        "campaign": c.name,
                        "seed": seed,
                        "method": method,
                        "budget": c.requests,
                        "quality": receipt["final_quality"],
                        "auc": quality_auc(receipt, c.requests),
                        "requests": receipt["requests"],
                        "status": "complete",
                        "selection_seal": artifact["seal"],
                    }
                )
    primary = [r for r in records if r["method"] in {"ppo", baseline}]
    result = {
        "evidence": "synthetic_engineering_only"
        if registry.profile.purpose == "fixture"
        else "computational_optimization_pending_independent_assessment",
        "records": records,
        "paired": paired_summary(primary, baseline),
    }
    write_new(output / "results.json", seal(result))
    return result
