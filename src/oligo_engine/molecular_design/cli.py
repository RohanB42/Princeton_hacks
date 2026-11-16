"""Molecular-design CLI: audit, search, train, evaluate policy and export."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .artifacts import QueryJournal, export_csv, run_artifact, seal, write_new
from .bundles import (
    atlas_bundle,
    attach_development_risk,
    fixture,
    inventory,
    portable_bundle,
)
from .contracts import Campaign, campaign_from_dict
from .optimizers import search
from .preflight import audit_partitions, preflight
from .scoring import FrozenRegistry, Session


def load_study(path: Path) -> tuple[dict, tuple[Campaign, ...], FrozenRegistry]:
    config = json.loads(path.read_text())
    campaigns = tuple(campaign_from_dict(c) for c in config["campaigns"])
    kind = config["bundle"]["kind"]
    if kind == "fixture":
        _, registry = fixture()
    elif kind == "portable_efficacy":
        _, registry = portable_bundle(
            Path(config["bundle"]["path"]), config["bundle"]["sha256"]
        )
    elif kind in {"atlas_ridge", "atlas_ridge_development_risk"}:
        registry = atlas_bundle(
            Path(config["bundle"]["path"]),
            config["bundle"]["sha256"],
            replace(campaigns[0].profile, purpose="efficacy_ablation"),
            config["bundle"]["context"],
            config["bundle"]["evidence"],
        )
        if kind == "atlas_ridge_development_risk":
            risk = config["bundle"]["risk"]
            registry = attach_development_risk(
                registry,
                campaigns[0].profile,
                Path(risk["path"]),
                risk["sha256"],
                Path(risk["protocol_path"]),
                risk["protocol_seal"],
            )
    else:
        raise ValueError("Unregistered bundle; explicit reviewed adapter required")
    if any(c.profile.key != registry.profile.key for c in campaigns):
        raise ValueError("Campaign and registry profiles differ")
    return config, campaigns, registry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--root", type=Path, default=Path("model_checkpoints"))
    inv.add_argument("--output", type=Path, required=True)
    metadata = sub.add_parser("metadata-audit")
    metadata.add_argument("--root", type=Path, default=Path("data/aso_atlas_2/release"))
    metadata.add_argument("--output", type=Path, required=True)
    for name in ("preflight", "search", "train", "policy-evaluate", "compare"):
        p = sub.add_parser(name)
        p.add_argument("--config", type=Path, required=True)
        p.add_argument("--output", type=Path, required=True)
        if name == "policy-evaluate":
            p.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "inventory":
        result = inventory(args.root)
        write_new(args.output, seal(result))
        print(json.dumps(result, indent=2))
        return
    if args.command == "metadata-audit":
        from .metadata_audit import audit_atlas

        result = audit_atlas(args.root)
        write_new(args.output, seal(result))
        print(json.dumps({"output": str(args.output), "outcomes_read": False}))
        return
    config, campaigns, registry = load_study(args.config)
    reports = [preflight(c, registry) for c in campaigns]
    if args.command == "preflight":
        result = {"campaigns": reports, "partitions": audit_partitions(campaigns)}
        write_new(args.output, seal(result))
        print(json.dumps(result, indent=2))
        return
    if any(r["status"] == "blocked" for r in reports):
        raise ValueError("Campaign coverage preflight blocked")
    if args.command == "compare":
        from .study import compare

        result = compare(campaigns, registry, config, args.output)
        print(json.dumps(result["paired"], indent=2))
        return
    if args.command == "train":
        from .training import TrainingConfig, train

        result = train(
            tuple(c for c in campaigns if c.partition == "training"),
            tuple(c for c in campaigns if c.partition == "validation"),
            registry,
            TrainingConfig(
                **(
                    {
                        "site_capacity": max(len(c.target.sequence) for c in campaigns),
                        "archive_capacity": max(c.requests for c in campaigns),
                    }
                    | config["training"]
                )
            ),
            args.output,
        )
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in ("status", "training_requests", "selected_tokens")
                }
            )
        )
        return
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    if args.command == "policy-evaluate":
        from .gym_env import MolecularEnv
        from .training import load_policy, rollout

        training = json.loads((args.policy / "training.json").read_text())
        env = MolecularEnv(
            campaigns,
            registry,
            training["protocol"]["site_capacity"],
            training["protocol"]["archive_capacity"],
            decoder=training["protocol"]["config"].get("decoder", "legacy-v1"),
            candidate_capacity=training["protocol"]["config"].get("candidate_capacity"),
            collapse_forced=training["protocol"]["config"].get(
                "collapse_forced", False
            ),
        )
        model = load_policy(args.policy, env)
    index = []
    for i, campaign in enumerate(campaigns):
        for seed in config["seeds"]:
            methods = config["methods"] if args.command == "search" else ["ppo"]
            for method in methods:
                stem = f"campaign-{i}-{method}-seed-{seed}"
                journal = QueryJournal(args.output / f"{stem}.queries.jsonl")
                if method == "ppo":
                    env.on_receipt = journal
                receipt = (
                    search(Session(campaign, registry, journal), method, seed)
                    if method != "ppo"
                    else rollout(model, env, i, seed)
                )
                artifact = run_artifact(campaign, receipt, config.get("panel_size", 10))
                write_new(args.output / f"{stem}.json", artifact)
                export_csv(artifact, args.output / f"{stem}.csv")
                index.append(
                    {
                        "campaign": campaign.name,
                        "method": method,
                        "seed": seed,
                        "requests": receipt["requests"],
                        "quality": receipt["final_quality"],
                        "artifact": stem + ".json",
                        "seal": artifact["seal"],
                    }
                )
    write_new(args.output / "index.json", seal({"runs": index, "config": config}))
    print(json.dumps({"completed": len(index), "output": str(args.output)}))


if __name__ == "__main__":
    main()
