"""Full-budget pretrained-prior control, with a separately frozen supplement."""

import argparse
import hashlib
import json
import statistics
from dataclasses import replace
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO

from oligo_engine.molecular_design.artifacts import (
    QueryJournal,
    run_artifact,
    seal,
    verify,
    write_new,
)
from oligo_engine.molecular_design.candidate_encoding import encode_candidate
from oligo_engine.molecular_design.cli import load_study
from oligo_engine.molecular_design.gym_env import MolecularEnv
from oligo_engine.molecular_design.scoring import Session


def run(output: Path) -> None:
    protocol = json.loads((output / "protocol.json").read_text())
    supplement = json.loads((output / "prior-control-protocol.json").read_text())
    verify(protocol)
    verify(supplement)
    if supplement["parent_protocol_seal"] != protocol["seal"]:
        raise ValueError("Supplement identity differs")
    for name, expected in protocol["sources"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen source changed")
    if (
        hashlib.sha256((output / "config.json").read_bytes()).hexdigest()
        != protocol["config_sha256"]
    ):
        raise ValueError("Frozen configuration changed")
    _, campaigns, registry = load_study(output / "config.json")
    if registry.key != protocol["registry"]:
        raise ValueError("Frozen registry changed")
    cfg = protocol["arms"]["full"]
    evaluation = tuple(
        c for c in campaigns if c.key in supplement["evaluation_campaigns"]
    )
    torch.set_num_threads(1)
    rows = []
    for seed in supplement["seeds"]:
        directory = output / f"full-{seed}"
        receipt = json.loads((directory / "training.json").read_text())
        verify(receipt)
        warm = directory / "warm-start-policy.zip"
        if (
            hashlib.sha256(warm.read_bytes()).hexdigest()
            != receipt["warm_start_sha256"]
        ):
            raise ValueError("Warm-start model changed")
        env = MolecularEnv(
            evaluation,
            registry,
            cfg["site_capacity"],
            cfg["archive_capacity"],
            candidate_capacity=cfg["candidate_capacity"],
            collapse_forced=True,
        )
        model = MaskablePPO.load(warm, env=env, device="cpu")
        model.policy.set_training_mode(False)
        for c in evaluation:
            designs = tuple(c.designs())
            patterns = {p.name: p for p in c.profile.patterns}
            x = np.stack(
                [
                    encode_candidate(d, patterns[d.pattern], env.max_length)
                    for d in designs
                ]
            )
            with torch.no_grad():
                pred = torch.sigmoid(
                    model.policy.molecular_predictions(torch.as_tensor(x))
                )
                scores = (pred[:, 0] * pred[:, 1]).numpy()
            order = sorted(
                range(len(designs)), key=lambda i: (-float(scores[i]), designs[i].key)
            )
            for budget in supplement["budgets"]:
                campaign = replace(c, requests=budget, tokens=max(c.tokens, budget * 8))
                stem = f"{c.target.gene}-prior-{seed}-b{budget}"
                session = Session(
                    campaign,
                    registry,
                    QueryJournal(output / "prior-runs" / f"{stem}.jsonl"),
                )
                for i in order:
                    if not session.remaining:
                        break
                    if designs[i].key not in session.archive:
                        session.query(designs[i])
                result = {
                    "method": "pretrained_prior_ranking",
                    "seed": seed,
                    "end_reason": "request_budget"
                    if not session.remaining
                    else "space_enumerated",
                    **session.receipt(),
                }
                artifact = run_artifact(campaign, result)
                path = output / "prior-runs" / f"{stem}.json"
                write_new(path, artifact)
                rows.append(
                    {
                        "target": c.target.gene,
                        "seed": seed,
                        "budget": budget,
                        "quality": session.quality,
                        "requests": session.requests,
                        "artifact": str(path),
                        "seal": artifact["seal"],
                    }
                )
    summaries = []
    for c in evaluation:
        for budget in supplement["budgets"]:
            group = [
                r
                for r in rows
                if r["target"] == c.target.gene and r["budget"] == budget
            ]
            summaries.append(
                {
                    "target": c.target.gene,
                    "budget": budget,
                    "mean": statistics.mean(r["quality"] for r in group),
                    "sd": statistics.stdev(r["quality"] for r in group),
                }
            )
    write_new(
        output / "prior-control-results.json",
        seal(
            {
                "protocol_seal": supplement["seal"],
                "rows": rows,
                "summaries": summaries,
                "driver_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "prior_training_requests_per_seed": cfg["pretrain_requests"]
                * len([c for c in campaigns if c.partition == "training"]),
            }
        ),
    )
    print(json.dumps({"completed_runs": len(rows)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
