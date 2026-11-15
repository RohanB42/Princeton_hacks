"""Evaluator-only measured metrics, diagnostic curves and grouped comparisons."""

from math import ceil, isfinite, sqrt
from random import Random
from statistics import fmean

from oligo_engine.evaluation.metrics import regression_metrics
from oligo_engine.provenance import identity
from oligo_engine.robustness.guardrails import compound_risk


def rank(values: list[float]) -> list[float]:
    positions = {}
    ordered = sorted(values)
    for value in set(values):
        indices = [i + 1 for i, v in enumerate(ordered) if v == value]
        positions[value] = fmean(indices)
    return [positions[v] for v in values]


def predictive_metrics(records: list[dict], labels: dict[str, float]) -> dict:
    if set(labels) != {r["sample_id"] for r in records}:
        raise ValueError("Evaluation labels must align exactly with prediction rows")
    groups = []
    for group in sorted({r["group"] for r in records}):
        all_rows = [r for r in records if r["group"] == group]
        rows = [r for r in all_rows if r["mean"] is not None]
        if not rows:
            groups.append(
                {
                    "group": group,
                    "n": 0,
                    "total": len(all_rows),
                    "rmse": None,
                    "mae": None,
                    "pearson": None,
                    "spearman": None,
                    "reason": "no_scored_rows",
                }
            )
            continue
        truth = tuple(labels[r["sample_id"]] for r in rows)
        means = tuple(r["mean"] for r in rows)
        metrics = regression_metrics(truth, means)
        compounds: dict[str, list[float]] = {}
        for r in rows:
            compounds.setdefault(r["compound_id"], []).append(
                (r["mean"] - labels[r["sample_id"]]) ** 2
            )
        spearman = regression_metrics(
            tuple(rank(list(truth))), tuple(rank(list(means)))
        )
        groups.append(
            {
                "group": group,
                "n": len(rows),
                "total": len(all_rows),
                "compound_count": len(compounds),
                "rmse": sqrt(fmean(fmean(v) for v in compounds.values())),
                "mae": compound_risk(rows, labels),
                "pearson": metrics.pearson_r,
                "spearman": spearman.pearson_r,
                "correlation_reason": metrics.pearson_undefined_reason,
                "row_rmse": metrics.rmse,
            }
        )
    scored = [r for r in records if r["mean"] is not None]
    return {
        "groups": groups,
        "groups_total": len(groups),
        "groups_scored": sum(g["rmse"] is not None for g in groups),
        "inference_status": "limited_groups" if len(groups) < 5 else "descriptive",
        "macro_rmse": fmean(g["rmse"] for g in groups if g["rmse"] is not None)
        if scored
        else None,
        "macro_mae": fmean(g["mae"] for g in groups if g["mae"] is not None)
        if scored
        else None,
        "scored_rows": len(scored),
        "total_rows": len(records),
        "coverage": len(scored) / len(records) if records else 0.0,
        "weighting": "equal_group_then_equal_compound_within_group",
    }


def risk_coverage(
    records: list[dict],
    labels: dict[str, float],
    diagnostic: str,
    ordering: str = "diagnostic",
    seed: int = 1729,
) -> dict:
    if ordering not in ("diagnostic", "random", "oracle"):
        raise ValueError("Unknown diagnostic ordering")
    if set(labels) != {r["sample_id"] for r in records}:
        raise ValueError("Outcomes and diagnostic rows must align exactly")
    eligible = [
        r
        for r in records
        if r["mean"] is not None and r["diagnostics"].get(diagnostic) is not None
    ]
    if not eligible:
        return {
            "aurc": None,
            "reason": "diagnostic_unavailable",
            "curve": [],
            "coverage": 0.0,
            "scored_rows": 0,
        }
    ordered = {}
    for group in sorted({r["group"] for r in eligible}):
        compounds: dict[str, list[dict]] = {}
        for row in eligible:
            if row["group"] == group:
                compounds.setdefault(row["compound_id"], []).append(row)
        values = [
            {
                "compound": key,
                "risk": fmean(abs(r["mean"] - labels[r["sample_id"]]) for r in rows),
                "diagnostic": fmean(r["diagnostics"][diagnostic] for r in rows),
            }
            for key, rows in compounds.items()
        ]
        rng = Random(f"{seed}:{group}")
        random_order = {
            v["compound"]: rng.random()
            for v in sorted(values, key=lambda v: v["compound"])
        }
        key = (
            (lambda v: random_order[v["compound"]])
            if ordering == "random"
            else (
                lambda v: (
                    v["risk"] if ordering == "oracle" else v["diagnostic"],
                    identity([seed, v["compound"]]),
                )
            )
        )
        ordered[group] = sorted(values, key=key)
    curve = []
    for i in range(1, 11):
        coverage = i / 10
        risks, achieved = [], []
        for values in ordered.values():
            n = ceil(coverage * len(values))
            risks.append(fmean(v["risk"] for v in values[:n]))
            achieved.append(n / len(values))
        curve.append(
            {
                "coverage": coverage,
                "risk": fmean(risks),
                "achieved_compound_coverage": fmean(achieved),
                "groups": len(risks),
            }
        )
    area = (
        sum(
            (a["risk"] + b["risk"]) / 2 * (b["coverage"] - a["coverage"])
            for a, b in zip(curve, curve[1:])
        )
        / 0.9
    )
    signal = [r["diagnostics"][diagnostic] for r in eligible]
    errors = [abs(r["mean"] - labels[r["sample_id"]]) for r in eligible]
    association = regression_metrics(tuple(rank(signal)), tuple(rank(errors)))
    return {
        "aurc": area,
        "curve": curve,
        "coverage": len(eligible) / len(records),
        "scored_rows": len(eligible),
        "excluded_rows": len(records) - len(eligible),
        "uninformative_constant": len(set(signal)) == 1,
        "spearman_error": association.pearson_r,
        "association_reason": association.pearson_undefined_reason,
        "ordering": ordering,
        "weighting": "equal_group_compound_aggregated_before_ordering",
    }


def paired_groups(
    differences: dict[str, float], seed: int = 1729, repeats: int = 2000
) -> dict:
    values = [differences[k] for k in sorted(differences)]
    if any(not isfinite(v) for v in values) or repeats < 1:
        raise ValueError("Invalid grouped differences or bootstrap count")
    result = {
        "groups": len(values),
        "mean_difference": fmean(values) if values else None,
        "ci95": None,
        "status": "limited_groups",
    }
    if len(values) >= 5:
        rng = Random(seed)
        draws = sorted(
            fmean(rng.choices(values, k=len(values))) for _ in range(repeats)
        )
        result.update(
            ci95=[draws[int(0.025 * (repeats - 1))], draws[int(0.975 * (repeats - 1))]],
            status="grouped_bootstrap",
        )
    return result
