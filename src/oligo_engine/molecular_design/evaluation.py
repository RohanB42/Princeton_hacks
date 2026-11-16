"""Independent sealed assessment. Never imported by environment or policy code."""

import random
import statistics
from collections import defaultdict
from collections.abc import Callable

from .artifacts import verify


def assess_exact(
    artifact: dict,
    locked_seal: str,
    endpoint: str,
    allowed_ids: frozenset[str],
    read_outcomes: Callable[[tuple[str, ...]], dict[str, float]],
) -> dict:
    """Only exact selected compound-assay identities can be measured here."""
    verify(artifact, locked_seal)
    selected = []
    for row in artifact["panel"]:
        for p in row["predictions"]:
            if p["endpoint"] == endpoint:
                selected.append(p["assessment_id"])
    selected = tuple(dict.fromkeys(selected))
    admitted = tuple(i for i in selected if i in allowed_ids)
    results = read_outcomes(admitted) if admitted else {}
    if set(results) != set(admitted):
        raise ValueError("Outcome capability returned different identities")
    import math

    if any(not math.isfinite(v) for v in results.values()):
        raise ValueError("Nonfinite measured outcome")
    return {
        "endpoint": endpoint,
        "selected": len(selected),
        "measured": len(results),
        "missing": len(selected) - len(results),
        "measured_mean": statistics.mean(results.values()) if results else None,
        "status": "exact_recorded_compound_assessment"
        if results
        else "no_exact_measurements",
        "selection_seal": locked_seal,
        "claim": "recorded compounds only; missing outcomes remain missing",
    }


def corroborate(
    artifact: dict,
    locked_seal: str,
    evaluator_manifest: dict,
    predict: Callable[[list[dict]], list[dict]],
) -> dict:
    verify(artifact, locked_seal)
    required = {
        "artifact_hash",
        "endpoint",
        "units",
        "context",
        "chemistry_scope",
        "training_overlap",
        "shared_representation",
        "validation_evidence",
    }
    if not required <= evaluator_manifest.keys():
        raise ValueError("Independent evaluator audit is incomplete")
    inputs = [r["design"] for r in artifact["panel"]]
    predictions = predict(inputs)
    if len(predictions) != len(inputs):
        raise ValueError("Independent evaluator output cardinality mismatch")
    return {
        "selection_seal": locked_seal,
        "evaluator": evaluator_manifest,
        "predictions": predictions,
        "evidence": "computational_corroboration_only",
        "independence": "qualified_by_declared_overlap_not_architecture",
    }


def quality_auc(receipt: dict, budget: int) -> float:
    """Discrete request-indexed mean; stopping explicitly carries the archive."""
    qualities = {e["request"]: e["quality"] for e in receipt["trace"]}
    current, total = 0.0, 0.0
    for request in range(1, budget + 1):
        current = qualities.get(request, current)
        total += current
    return total / budget


def paired_summary(
    records: list[dict], baseline: str, resamples: int = 2000, seed: int = 1729
) -> dict:
    """Equal target weight, average paired seeds/campaigns within target first."""
    by_pair = defaultdict(dict)
    for r in records:
        key = (r["target"], r["campaign"], r["seed"], r["budget"])
        if r["method"] in by_pair[key]:
            raise ValueError("Duplicate paired study arm")
        by_pair[key][r["method"]] = r
    grouped = defaultdict(list)
    for (target, campaign, seed_value, budget), methods in by_pair.items():
        if "ppo" not in methods or baseline not in methods:
            raise ValueError("Incomplete paired comparison; do not drop failed arms")
        pair = (methods["ppo"], methods[baseline])
        if any(r.get("status", "complete") != "complete" for r in pair):
            raise ValueError("Failed arm requires explicit failure analysis")
        grouped[(budget, target)].append(pair[0]["quality"] - pair[1]["quality"])
    reports = []
    rng = random.Random(seed)
    for budget in sorted({b for b, _ in grouped}):
        target_means = [
            statistics.mean(v) for (b, _), v in grouped.items() if b == budget
        ]
        sampled = sorted(
            statistics.mean(rng.choices(target_means, k=len(target_means)))
            for _ in range(resamples)
        )
        reports.append(
            {
                "budget": budget,
                "target_groups": len(target_means),
                "mean_paired_difference": statistics.mean(target_means),
                "target_bootstrap_95_percentile": [
                    sampled[int(0.025 * resamples)],
                    sampled[min(resamples - 1, int(0.975 * resamples))],
                ]
                if len(target_means) >= 5
                else None,
                "interval_reason": "fewer_than_five_groups"
                if len(target_means) < 5
                else "target_bootstrap; five groups do not guarantee precision",
                "within_target_seed_campaign_sample_sd": {
                    target: statistics.stdev(v) if len(v) > 1 else None
                    for (b, target), v in grouped.items()
                    if b == budget
                },
            }
        )
    return {
        "primary_contrast": f"ppo minus development-selected {baseline}",
        "budgets": reports,
        "bootstrap_resamples": resamples,
    }
