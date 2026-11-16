"""Recorded-panel acquisition with operational absolute-IC50 censoring.

All policy inputs are built from public metadata and already purchased panels.
The complete recorded oracle never enters a policy call.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from typing import Any, Callable


def identity(value: Any) -> str:
    """Stable identity independent of dictionary insertion order."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def isotonic(values: list[float]) -> list[float]:
    """Unweighted increasing PAVA; no clipping or invented replicate variance."""
    blocks: list[list[float]] = []
    for value in values:
        blocks.append([float(value), 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            b = blocks.pop()
            a = blocks.pop()
            n = a[1] + b[1]
            blocks.append([(a[0] * a[1] + b[0] * b[1]) / n, n])
    return [mean for mean, n in blocks for _ in range(int(n))]


def curve_record(
    doses: list[float], responses: list[float], max_adjustment: float = 15.0
) -> dict:
    """Operational monotone 50% crossing; not a validated biological IC50.

    Single source values per dose, no untreated/viability/replicate controls.
    Outside-grid results retain bounds rather than extrapolated fitted points.
    """
    if (
        len(doses) != len(responses)
        or len(doses) < 4
        or len(set(doses)) != len(doses)
        or doses != sorted(doses)
        or any(not math.isfinite(x) or x <= 0 for x in doses)
    ):
        raise ValueError("Require >=4 distinct increasing positive finite doses")
    if max_adjustment < 0 or not math.isfinite(max_adjustment):
        raise ValueError("Invalid fixed QC tolerance")
    try:
        responses = [float(y) for y in responses]
    except (TypeError, ValueError):
        return {"kind": "unresolved", "reason": "missing_or_nonnumeric_response"}
    if any(not math.isfinite(y) for y in responses):
        return {"kind": "unresolved", "reason": "nonfinite_response"}
    fitted = isotonic(responses)
    adjustment = max(abs(a - b) for a, b in zip(fitted, responses, strict=True))
    base = {"maximum_adjustment_pp": adjustment, "fitted_inhibition": fitted}
    if any(y < -20 or y > 120 for y in responses):
        return {**base, "kind": "unresolved", "reason": "outside_fixed_QC_range"}
    if adjustment > max_adjustment:
        return {**base, "kind": "unresolved", "reason": "nonmonotone_QC"}
    if fitted[0] >= 50:
        return {
            **base,
            "kind": "upper_bound",
            "upper_nm": doses[0],
            "upper_closed": True,
        }
    if fitted[-1] < 50:
        return {
            **base,
            "kind": "lower_bound",
            "lower_nm": doses[-1],
            "lower_closed": False,
        }
    for i in range(1, len(doses)):
        if fitted[i] >= 50:
            weight = (50 - fitted[i - 1]) / (fitted[i] - fitted[i - 1])
            point = math.exp(
                math.log(doses[i - 1])
                + weight * (math.log(doses[i]) - math.log(doses[i - 1]))
            )
            return {
                **base,
                "kind": "interpolated",
                "estimate_nm": point,
                "bracket_nm": [doses[i - 1], doses[i]],
            }
    raise AssertionError("Crossing should have been identified")


def success(record: dict, threshold: float, rule: str) -> bool | None:
    """Exact-only is a constructed counterfactual, not a historic V3 rule."""
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("Positive finite prespecified threshold required")
    if rule not in {"exact_only", "bound_aware"}:
        raise ValueError("Unknown objective")
    if record["kind"] == "interpolated":
        return record["estimate_nm"] <= threshold
    if record["kind"] == "upper_bound":
        if record["upper_nm"] <= threshold:
            return rule == "bound_aware"
        return None
    if record["kind"] == "lower_bound":
        return False if record["lower_nm"] >= threshold else None
    if record["kind"] == "unresolved":
        return None
    raise ValueError("Unknown curve category")


def features(sequence: str, pattern: dict) -> dict:
    """Small explicitly label-free molecular descriptor set."""
    gc = sum(x in "GC" for x in sequence) / len(sequence)
    return {
        "sequence": sequence,
        "length": len(sequence),
        "gc_fraction": round(gc, 4),
        "gc_bin": min(3, int(gc * 4)),
        **pattern,
    }


def public_candidates(campaign: dict, purchased: set[str]) -> list[dict]:
    """Positive policy-field allowlist; no row IDs or unpurchased outcomes."""
    return [
        {"id": c["id"], **c["features"]}
        for c in campaign["candidates"]
        if c["id"] not in purchased
    ]


def observation(
    campaign: dict, history: list[dict], rule: str, budget: int, threshold: float
) -> dict:
    """The model sees anonymous candidates and only paid curve interpretations."""
    purchased = {h["id"] for h in history}
    return {
        "rule": rule,
        "threshold_nm": threshold,
        "remaining_panel_budget": budget - len(history),
        "dose_grid_nm": campaign["dose_grid_nm"],
        "candidates": public_candidates(campaign, purchased),
        "history": [
            {
                "id": h["id"],
                "gc_bin": h["features"]["gc_bin"],
                "sequence": h["features"]["sequence"],
                "curve": h["curve"],
                "credited_success": h["success"],
            }
            for h in history
        ],
    }


def choose(
    method: str,
    obs: dict,
    rng: random.Random,
    qwen: Callable[[dict], tuple[str, dict]] | None = None,
) -> tuple[str, dict]:
    """Random, group-greedy, exact group-Beta Thompson, or actual Qwen choice."""
    candidates = obs["candidates"]
    if not candidates:
        raise ValueError("No legal candidates")
    if method == "random":
        return rng.choice(candidates)["id"], {}
    if method == "qwen":
        if qwen is None:
            raise ValueError("Actual Qwen inference is required; no silent substitute")
        selected, receipt = qwen(obs)
        if selected not in {c["id"] for c in candidates}:
            raise ValueError("Qwen selected unavailable candidate")
        return selected, receipt
    if method not in {"greedy", "bayesian_group_thompson"}:
        raise ValueError("Unknown policy")
    groups: dict[int, list[int]] = defaultdict(lambda: [1, 1])
    for h in obs["history"]:
        if h["credited_success"] is not None:
            groups[h["gc_bin"]][0 if h["credited_success"] else 1] += 1
    scores = {}
    for group in sorted({c["gc_bin"] for c in candidates}):
        a, b = groups[group]
        scores[group] = (
            rng.betavariate(a, b)
            if method == "bayesian_group_thompson"
            else a / (a + b)
        )
    best = max(scores.values())
    available = [c for c in candidates if scores[c["gc_bin"]] == best]
    return rng.choice(available)["id"], {"group_scores": scores}


def replay(
    campaign: dict,
    oracle: dict[str, dict],
    method: str,
    rule: str,
    seed: int,
    budget: int = 8,
    threshold: float = 100.0,
    qwen: Callable[[dict], tuple[str, dict]] | None = None,
) -> dict:
    """Fixed-cap recorded-panel purchases; full oracle is never passed to policy."""
    if budget < 2 or budget > len(campaign["candidates"]):
        raise ValueError("Budget must include two starts and fit the candidate pool")
    rng = random.Random(seed)
    candidates = {c["id"]: c for c in campaign["candidates"]}
    starts = random.Random(seed).sample(sorted(candidates), 2)
    history, decisions = [], []
    for index in range(budget):
        if index < 2:
            selected, decision = starts[index], {"initial": True}
        else:
            obs = observation(campaign, history, rule, budget, threshold)
            selected, decision = choose(method, obs, rng, qwen)
        if selected in {h["id"] for h in history} or selected not in candidates:
            raise ValueError("Duplicate or unavailable panel purchase")
        curve = oracle[selected]
        history.append(
            {
                "id": selected,
                "features": candidates[selected]["features"],
                "curve": curve,
                "success": success(curve, threshold, rule),
                "initial": index < 2,
            }
        )
        decisions.append(decision)
    return {
        "method": method,
        "rule": rule,
        "seed": seed,
        "campaign": campaign["id"],
        "target": campaign["target"],
        "panels_purchased": budget,
        "source_dose_measurements": budget * len(campaign["dose_grid_nm"]),
        "initial_ids": starts,
        "history": history,
        "decisions": decisions,
        "credited_hits": sum(h["success"] is True for h in history),
        "new_credited_hits": sum(h["success"] is True for h in history[2:]),
        "unknown_panels": sum(h["success"] is None for h in history),
        "counterfactual_rescore": {
            label: sum(success(h["curve"], threshold, label) is True for h in history)
            for label in ("exact_only", "bound_aware")
        },
        "sensitivity_rescore": {
            str(t): {
                label: sum(success(h["curve"], t, label) is True for h in history)
                for label in ("exact_only", "bound_aware")
            }
            for t in (10.0, 100.0, 1000.0)
        },
    }
