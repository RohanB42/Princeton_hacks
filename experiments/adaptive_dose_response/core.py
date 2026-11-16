"""Paid-dose-only Bayesian selection and threshold classification.

The full-curve reference is never a policy input. Posterior probabilities are
conditional on an explicit finite model, not calibrated assay guarantees.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
from experiments.ic50_qwen.core import curve_record, isotonic, success
from scipy.special import ndtr

THRESHOLD = 500.0
CONFIDENCES = (0.90, 0.95, 0.975, 0.99, 0.995, 1.0)
MARGINS = (0.0, 5.0, 10.0, 15.0, None)


def reference(doses: list[float], values: list[float], adjustment: float = 15) -> dict:
    """Full paid-grid operational reference, with unresolved outcomes retained."""
    record = curve_record(doses, values, max_adjustment=adjustment)
    return {**record, "label": success(record, THRESHOLD, "bound_aware")}


def fixed_order(doses: list[float]) -> list[int]:
    """Nearest log-dose to threshold first; numeric dose breaks ties."""
    return sorted(range(len(doses)), key=lambda i: (abs(math.log(doses[i] / 500)), i))


def certificate(
    doses: list[float], history: dict[int, float], margin: float
) -> bool | None:
    """Monotonic witnesses or an observed local log-dose interpolation.

    Later hidden QC violations cannot be known at an early stop. Evaluator records
    definitive decisions on reference-unresolved curves rather than filtering them.
    """
    if any(not math.isfinite(y) or y < -20 or y > 120 for y in history.values()):
        return None
    points = sorted((doses[i], y) for i, y in history.items())
    if any(y1 > y2 for (_, y1), (_, y2) in zip(points, points[1:])):
        return None
    positive = any(d <= 500 and y >= 50 + margin for d, y in points)
    negative = any(d >= 500 and y < 50 - margin for d, y in points)
    if positive or negative:
        return True if positive and not negative else False if negative else None
    # Use nearest available bracket only after purchasing both endpoints.
    below = max((i for i, d in enumerate(doses) if d < 500), default=None)
    above = min((i for i, d in enumerate(doses) if d > 500), default=None)
    if below in history and above in history:
        lo, hi = history[below], history[above]
        if lo <= 50 - margin and hi >= 50 + margin and hi > lo:
            crossing = math.exp(
                math.log(doses[below])
                + (50 - lo) / (hi - lo) * math.log(doses[above] / doses[below])
            )
            return crossing <= 500
    return None


@dataclass
class Belief:
    """Finite prior over bottom/top/Hill slope/log-midpoint, Gaussian assay noise."""

    doses: list[float]
    sigma: float = 10.0

    def __post_init__(self) -> None:
        axes = np.meshgrid(
            [-10.0, 0.0, 10.0],
            [30.0, 60.0, 80.0, 100.0, 120.0],
            [0.5, 1.0, 2.0, 4.0],
            np.linspace(-1, 5, 25),
            indexing="ij",
        )
        bottom, top, slope, midpoint = (a.ravel() for a in axes)
        x = np.log10(np.array([*self.doses, 500.0]))
        fitted = bottom[:, None] + (top - bottom)[:, None] / (
            1 + 10 ** (slope[:, None] * (midpoint[:, None] - x[None, :]))
        )
        self.means = fitted[:, :-1]
        self.potent = fitted[:, -1] >= 50
        self.weights = np.ones(len(bottom)) / len(bottom)
        self.seen: set[int] = set()
        # Integrate prospective responses over 16 finite bins plus two tails.
        edges = np.array([-np.inf, *np.arange(-30, 131, 10), np.inf])
        self.likelihoods = []
        for i in range(len(self.doses)):
            cdf = ndtr((edges[None, :] - self.means[:, i, None]) / self.sigma)
            self.likelihoods.append(np.diff(cdf, axis=1))

    def update(self, index: int, value: float) -> None:
        """Bayesian update only from a newly purchased finite response."""
        if index in self.seen or not 0 <= index < len(self.doses):
            raise ValueError("Dose index invalid or already purchased")
        self.seen.add(index)
        if not math.isfinite(value):
            return
        logw = np.log(np.maximum(self.weights, 1e-300))
        logw -= 0.5 * ((value - self.means[:, index]) / self.sigma) ** 2
        self.weights = np.exp(logw - logw.max())
        self.weights /= self.weights.sum()

    def probability(self) -> float:
        """Model probability of absolute inhibition at500 being at least50%."""
        return float(np.clip(self.weights[self.potent].sum(), 0, 1))

    def next_dose(self, method: str) -> int:
        """Maximize full-parameter information or reduction in binary Bayes risk."""
        if method not in {"information_gain", "decision_aware"}:
            raise ValueError(method)
        available = [i for i in fixed_order(self.doses) if i not in self.seen]
        if not available:
            raise ValueError("No unpurchased dose remains")
        scores = []
        for index in available:
            likelihood = self.likelihoods[index]
            joint = self.weights[:, None] * likelihood
            predictive = joint.sum(axis=0)
            if method == "decision_aware":
                positive = joint[self.potent].sum(axis=0)
                negative = predictive - positive
                score = -float(np.minimum(positive, negative).sum())
            else:
                log_ratio = np.log(np.maximum(likelihood, 1e-300)) - np.log(
                    np.maximum(predictive[None, :], 1e-300)
                )
                score = float((joint * log_ratio).sum())
            scores.append(score)
        return available[int(np.argmax(scores))]


def trajectory(
    doses: list[float], buy: Callable[[int], float], method: str
) -> list[dict]:
    """Generate a complete ordering using only sequential paid observations.

    All stopping operating points are deterministic prefixes of this trajectory;
    unused suffix outcomes are never supplied to a stopped policy.
    """
    if len(set(doses)) != len(doses) or doses != sorted(doses):
        raise ValueError("Distinct increasing dose grid required")
    belief = Belief(doses)
    history: dict[int, float] = {}
    result = []
    for step in range(len(doses)):
        index = (
            fixed_order(doses)[step]
            if method in {"full_grid", "fixed_early"}
            else belief.next_dose(method)
        )
        y = buy(index)
        history[index] = y
        belief.update(index, y)
        ordered_values = [history[i] for i in sorted(history)]
        prefix_adjustment = max(
            abs(a - b)
            for a, b in zip(ordered_values, isotonic(ordered_values), strict=True)
        )
        result.append(
            {
                "index": index,
                "dose_nm": doses[index],
                "value": y if math.isfinite(y) else None,
                "probability": belief.probability(),
                "fixed_decisions": {
                    str(m): certificate(doses, history, m) for m in MARGINS[:-1]
                },
                "observed_valid": all(
                    math.isfinite(v) and -20 <= v <= 120 for v in history.values()
                )
                and prefix_adjustment <= 15,
            }
        )
    return result


def stopped(
    doses: list[float],
    trace: list[dict],
    method: str,
    setting: float | None,
    cap: int | None = None,
) -> dict:
    """Materialize a costed prefix without using unpurchased suffix values."""
    cap = len(doses) if cap is None else min(cap, len(doses))
    if cap < 1:
        raise ValueError("At least one paid measurement is required")
    for k, state in enumerate(trace[:cap], 1):
        if k == len(doses):
            by_index = {s["index"]: s["value"] for s in trace[:k]}
            ref = reference(doses, [by_index[i] for i in range(len(doses))])
            return {"n": k, "decision": ref["label"], "reason": "full_paid_grid"}
        label = None
        if method == "fixed_early" and setting is not None:
            label = state["fixed_decisions"][str(setting)]
        elif method in {"information_gain", "decision_aware"} and setting < 1:
            if state["observed_valid"]:
                p = state["probability"]
                if p >= setting:
                    label = True
                elif p <= 1 - setting:
                    label = False
        if label is not None:
            return {"n": k, "decision": label, "reason": "early"}
    return {"n": cap, "decision": None, "reason": "budget_inconclusive"}


def metrics(rows: list[dict]) -> dict:
    """Abstention-aware error rates; undefined denominators remain null."""
    n = len(rows)
    positives = sum(r["reference"] is True for r in rows)
    negatives = sum(r["reference"] is False for r in rows)
    unknown = sum(r["reference"] is None for r in rows)
    fp = sum(r["reference"] is False and r["decision"] is True for r in rows)
    fn = sum(r["reference"] is True and r["decision"] is False for r in rows)
    decided = sum(r["decision"] is not None for r in rows)
    known_decided = sum(
        r["reference"] is not None and r["decision"] is not None for r in rows
    )
    asserted_unknown = sum(
        r["reference"] is None and r["decision"] is not None for r in rows
    )
    correct = sum(
        r["reference"] is not None and r["reference"] is r["decision"] for r in rows
    )
    classified_positive = sum(
        r["reference"] is True and r["decision"] is not None for r in rows
    )
    classified_negative = sum(
        r["reference"] is False and r["decision"] is not None for r in rows
    )
    positive_calls = sum(
        r["reference"] is not None and r["decision"] is True for r in rows
    )
    negative_calls = sum(
        r["reference"] is not None and r["decision"] is False for r in rows
    )
    return {
        "selective_fpr": fp / classified_negative if classified_negative else None,
        "selective_fnr": fn / classified_positive if classified_positive else None,
        "false_discovery_rate": fp / positive_calls if positive_calls else None,
        "false_omission_rate": fn / negative_calls if negative_calls else None,
        "panels": n,
        "reference_positive": positives,
        "reference_negative": negatives,
        "reference_unknown": unknown,
        "false_positive": fp,
        "false_negative": fn,
        "fpr": fp / negatives if negatives else None,
        "fnr": fn / positives if positives else None,
        "resolved_coverage": known_decided / (positives + negatives)
        if positives + negatives
        else None,
        "selective_accuracy": correct / known_decided if known_decided else None,
        "correct_decision_rate": correct / (positives + negatives)
        if positives + negatives
        else None,
        "inconclusive_rate": 1 - decided / n if n else None,
        "unknown_assertions": asserted_unknown,
        "unknown_assertion_rate": asserted_unknown / unknown if unknown else None,
        "mean_measurements": sum(r["n"] for r in rows) / n if n else None,
    }


def qualified(result: dict, coverage: float = 0.95) -> bool:
    """Empirical development gate, not a population error guarantee."""
    return (
        result["fpr"] is not None
        and result["fnr"] is not None
        and result["fpr"] <= 0.05
        and result["fnr"] <= 0.05
        and result["resolved_coverage"] >= coverage
        and (
            result["unknown_assertion_rate"] is None
            or result["unknown_assertion_rate"] <= 0.05
        )
    )
