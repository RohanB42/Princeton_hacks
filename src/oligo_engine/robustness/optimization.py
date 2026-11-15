"""Recorded-pool black-box search: no assay outcomes or final evaluator feedback."""

from dataclasses import asdict
from math import isfinite
from random import Random
from time import perf_counter
from typing import Callable

from oligo_engine.design.aso_space import identity
from oligo_engine.robustness.contracts import AuditObservation
from oligo_engine.robustness.guardrails import GuardrailPolicy


def optimize(
    rows: tuple[AuditObservation, ...],
    score: Callable[[AuditObservation], dict],
    method: str,
    seed: int,
    budget: int,
    k: int,
    guardrail: GuardrailPolicy | None = None,
) -> dict:
    """Uniform random proposals or fully charged enumeration on arbitrary source rows.

    There is no invented transcript graph. Site-local/genetic/PPO comparisons use
    the existing RL design-space bridge separately when a real space exists.
    """
    if method not in ("random", "exhaustive"):
        raise ValueError("not_applicable: source pool has no declared proposal graph")
    if type(budget) is not int or budget < 1 or type(k) is not int or k < 1:
        raise ValueError("Positive integer scoring budget and shortlist size required")
    if len({r.sample_id for r in rows}) != len(rows):
        raise ValueError("Duplicate pool IDs")
    # One immutable representative per exact compound-assay identity, preserving
    # every source ID for evaluator-only replicate accounting.
    representatives = {}
    for row in sorted(rows, key=lambda r: r.sample_id):
        representatives.setdefault(row.assessment_id, row)
    proposals = sorted(representatives.values(), key=lambda r: r.sample_id)
    if method == "random":
        Random(seed).shuffle(proposals)
    started, archive, trace = perf_counter(), [], []
    for row in proposals[:budget]:
        result = score(row)
        if result["sample_id"] != row.sample_id:
            raise ValueError("Scorer returned the wrong record")
        if result["mean"] is not None and not isfinite(result["mean"]):
            raise ValueError("Nonfinite optimizer prediction")
        accepted = result["mean"] is not None and (
            guardrail is None or guardrail.accepts(result)
        )
        archive.append(
            {
                "sample_id": row.sample_id,
                "assessment_id": row.assessment_id,
                "prediction": result,
                "accepted": accepted,
            }
        )
        trace.append(
            {
                "request": len(archive),
                "unique_scores": len(archive),
                "sample_id": row.sample_id,
                "accepted": accepted,
            }
        )
    selected = sorted(
        (r for r in archive if r["accepted"]),
        key=lambda r: (-r["prediction"]["mean"], r["assessment_id"]),
    )[:k]
    payload = {
        "method": method,
        "seed": seed,
        "max_unique": budget,
        "k": k,
        "candidate_pool_hash": identity(
            [asdict(r) for r in sorted(rows, key=lambda r: r.sample_id)]
        ),
        "guardrail_hash": guardrail.identity if guardrail else None,
        "pool_records": len(rows),
        "eligible_compound_assays": len(proposals),
        "requests": len(archive),
        "unique_scores": len(archive),
        "archive": archive,
        "trace": trace,
        "shortlist": [r["sample_id"] for r in selected],
        "status": "space_exhausted" if len(proposals) <= budget else "budget_exhausted",
    }
    return {
        **payload,
        "seal": identity(payload),
        "wall_seconds": perf_counter() - started,
    }


def verify_seal(receipt: dict) -> None:
    payload = {k: v for k, v in receipt.items() if k not in ("seal", "wall_seconds")}
    if identity(payload) != receipt["seal"]:
        raise ValueError("Optimization archive changed after sealing")
