"""Costed, training-only initialization from frozen surrogate responses.

These are pseudo-targets, never measured labels or a replacement reward model.
Validation/development campaigns cannot enter this interface. The fixed sample
and epoch counts are specified before querying, with no outcome-based stopping.
"""

from dataclasses import replace
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from .artifacts import QueryJournal, seal, write_new
from .candidate_encoding import encode_candidate
from .contracts import Campaign
from .scoring import FrozenRegistry, Session


def pretrain_candidates(
    policy,
    campaigns: tuple[Campaign, ...],
    registry: FrozenRegistry,
    output: Path,
    seed: int,
    requests: int,
    epochs: int,
) -> dict:
    if not campaigns or any(c.partition != "training" for c in campaigns):
        raise ValueError("Pretraining requires exclusively training campaigns")
    if registry.profile.objective != "constrained_efficacy":
        raise ValueError("Candidate warm start requires constrained efficacy")
    if requests < 2 or epochs < 1:
        raise ValueError("Positive pretraining budget and epochs required")
    rng = np.random.default_rng(seed)
    examples, labels, identities = [], [], []
    total_requests = total_calls = 0
    max_length = policy.observation_space["candidates"].shape[1]
    journal = QueryJournal(output / "pretraining-queries.jsonl")
    for campaign in campaigns:
        if requests < len(campaign.starts):
            raise ValueError("Pretraining budget excludes starting designs")
        session = Session(replace(campaign, requests=requests), registry, journal)
        pool = [d for d in campaign.designs() if d.key not in session.archive]
        rng.shuffle(pool)
        for d in pool[: session.remaining]:
            session.query(d)
        for d, score in session.archive.values():
            p = next(p for p in campaign.profile.patterns if p.name == d.pattern)
            if not score.objectives:
                raise ValueError("Pretraining objective missing; cannot impute")
            examples.append(encode_candidate(d, p, max_length))
            labels.append([float(score.eligible), float(score.objectives[0])])
            identities.append(
                {
                    "campaign_id": campaign.key,
                    "design_id": d.key,
                    "compound_id": d.compound_id,
                }
            )
        total_requests += session.requests
        total_calls += sum(session.receipt()["per_head_calls"].values())
    x = torch.as_tensor(np.stack(examples), device=policy.device)
    y = torch.as_tensor(labels, dtype=torch.float32, device=policy.device)
    optimizer = torch.optim.Adam(
        list(policy.molecule.parameters()) + list(policy.endpoint.parameters()), lr=1e-3
    )
    history = []
    for _ in range(epochs):
        losses = []
        batches = np.array_split(rng.permutation(len(x)), max(1, (len(x) + 63) // 64))
        for indices in batches:
            pred = policy.molecular_predictions(x[indices])
            loss = F.binary_cross_entropy_with_logits(
                pred[:, 0], y[indices, 0]
            ) + F.mse_loss(torch.sigmoid(pred[:, 1]), y[indices, 1])
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.detach()))
        history.append(float(np.mean(losses)))
    receipt = seal(
        {
            "kind": "training-only-surrogate-warm-start-v1",
            "seed": seed,
            "requests": total_requests,
            "head_calls": total_calls,
            "epochs": epochs,
            "examples": len(examples),
            "unique_compounds": len({x["compound_id"] for x in identities}),
            "identities": identities,
            "loss_history": history,
            "eligible_fraction": float(y[:, 0].mean()),
            "targets": sorted({c.target.gene for c in campaigns}),
            "biological_labels_read": False,
        }
    )
    write_new(output / "pretraining.json", receipt)
    return receipt
