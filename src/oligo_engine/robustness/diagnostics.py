"""Fitting-only chemistry-aware distances and leakage-safe reference percentiles."""

from dataclasses import dataclass
from functools import cached_property
from statistics import fmean

from oligo_engine.robustness.contracts import AuditObservation, chemistry, records_hash


def structural_distance(
    left: AuditObservation, right: AuditObservation
) -> float | None:
    a, b = chemistry(left.helm), chemistry(right.helm)
    if (
        left.endpoint != right.endpoint
        or left.units != right.units
        or len(a.bases) != len(b.bases)
        or len(a.bases) < 2
        or a.terminal != b.terminal
    ):
        return None
    if set(a.sugars + b.sugars) - {"DNA", "MOE"}:
        return None
    fractions = [
        sum(x != y for x, y in zip(u, v, strict=True)) / len(u)
        for u, v in (
            (a.bases, b.bases),
            (a.sugars, b.sugars),
            (a.links[:-1], b.links[:-1]),
        )
    ]
    return fmean(fractions)


@dataclass(frozen=True)
class DomainReference:
    rows: tuple[AuditObservation, ...]

    def __post_init__(self) -> None:
        if not self.rows or len({r.sample_id for r in self.rows}) != len(self.rows):
            raise ValueError("Unique nonempty fitting reference required")
        if len({(r.endpoint, r.units) for r in self.rows}) != 1:
            raise ValueError("Domain references cannot pool endpoints or units")

    @cached_property
    def identity(self) -> str:
        return records_hash(self.rows)

    def nearest(self, query: AuditObservation) -> dict:
        values = [
            (structural_distance(query, row), row.sample_id)
            for row in self.rows
            if row.compound_id != query.compound_id
        ]
        comparable = [(v, i) for v, i in values if v is not None]
        if not comparable:
            return {"distance": None, "nearest_id": None, "status": "not_comparable"}
        distance, row_id = min(comparable)
        return {"distance": distance, "nearest_id": row_id, "status": "scored"}

    def reference_values(self) -> tuple[float, ...]:
        values = [self.nearest(row)["distance"] for row in self.rows]
        return tuple(v for v in values if v is not None)

    def diagnose(self, query: AuditObservation, reference: tuple[float, ...]) -> dict:
        result = self.nearest(query)
        value = result["distance"]
        result["percentile"] = (
            (
                sum(v < value for v in reference)
                + 0.5 * sum(v == value for v in reference)
            )
            / len(reference)
            if value is not None and reference
            else None
        )
        result["reference_identity"] = self.identity
        result["representation"] = "aso-track-hamming-v1"
        result["self_exclusion"] = "all_same_normalized_compound"
        result["context_supported"] = query.context in {r.context for r in self.rows}
        return result
