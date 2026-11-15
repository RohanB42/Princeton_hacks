"""Development-only abstention selection with explicit per-group retention."""

from dataclasses import asdict, dataclass
from math import isfinite
from statistics import fmean

from oligo_engine.design.aso_space import identity


def compound_risk(records: list[dict], labels: dict[str, float]) -> float | None:
    grouped: dict[str, list[float]] = {}
    for r in records:
        grouped.setdefault(r["compound_id"], []).append(
            abs(r["mean"] - labels[r["sample_id"]])
        )
    return fmean(fmean(v) for v in grouped.values()) if grouped else None


@dataclass(frozen=True)
class GuardrailPolicy:
    diagnostic: str
    threshold: float | None
    status: str
    development_ids: tuple[str, ...]
    minimum_retention: float
    receipt: tuple[tuple[float, float, float], ...] = ()

    @property
    def identity(self) -> str:
        return identity(asdict(self))

    def accepts(self, record: dict) -> bool:
        value = record["diagnostics"].get(self.diagnostic)
        return bool(
            self.status == "selected"
            and record["mean"] is not None
            and value is not None
            and isfinite(value)
            and value <= self.threshold
        )


def select_guardrail(
    records: list[dict],
    labels: dict[str, float],
    diagnostic: str,
    thresholds: tuple[float, ...],
    minimum_retention: float = 0.5,
    maximum_mae: float | None = None,
) -> GuardrailPolicy:
    ids = tuple(sorted(r["sample_id"] for r in records))
    if set(labels) != set(ids) or len(set(ids)) != len(records):
        raise ValueError("Development labels and prediction rows must align exactly")
    if not 0 < minimum_retention <= 1 or not thresholds:
        raise ValueError(
            "Positive minimum retention and frozen threshold grid required"
        )
    if any(not isfinite(v) for v in thresholds) or (
        maximum_mae is not None and (not isfinite(maximum_mae) or maximum_mae < 0)
    ):
        raise ValueError("Invalid guardrail thresholds")
    groups = sorted({r["group"] for r in records})
    eligible, trials = [], []
    for threshold in sorted(set(thresholds)):
        policy = GuardrailPolicy(
            diagnostic, threshold, "selected", ids, minimum_retention
        )
        accepted = [r for r in records if policy.accepts(r)]
        retention = len(accepted) / len(records) if records else 0.0
        group_retention = [
            sum(r["group"] == g for r in accepted)
            / sum(r["group"] == g for r in records)
            for g in groups
        ]
        if (
            not accepted
            or retention < minimum_retention
            or min(group_retention) < minimum_retention
        ):
            continue
        risk = fmean(
            compound_risk([r for r in accepted if r["group"] == g], labels)
            for g in groups
        )
        trials.append((threshold, risk, retention))
        if maximum_mae is None or risk <= maximum_mae:
            eligible.append((risk, -retention, threshold))
    if not eligible:
        return GuardrailPolicy(
            diagnostic,
            None,
            "no_supported_guardrail",
            ids,
            minimum_retention,
            tuple(trials),
        )
    _, _, chosen = min(eligible)
    return GuardrailPolicy(
        diagnostic, chosen, "selected", ids, minimum_retention, tuple(trials)
    )
