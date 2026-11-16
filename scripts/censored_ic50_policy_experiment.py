"""Endpoint-explicit IC50 adjudication; no curve fitting or policy replay.

This consumes already adjudicated assay records, not raw dose curves. A trusted
assay adapter must establish the bounds and QC evidence first. The CLI exercises
synthetic cases only while the requested V3/Qwen artifacts remain unavailable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from typing import Literal

from oligo_engine.molecular_design.artifacts import seal, write_new

Kind = Literal[
    "point",
    "upper_bound",
    "lower_bound",
    "interval",
    "unresolved",
    "biological_failure",
    "assay_failure",
    "missing",
]
Endpoint = Literal["absolute_ic50", "relative_ic50"]
UNITS = {"M": 1e9, "mM": 1e6, "uM": 1e3, "µM": 1e3, "nM": 1.0, "pM": 1e-3}
KINDS = {
    "point",
    "upper_bound",
    "lower_bound",
    "interval",
    "unresolved",
    "biological_failure",
    "assay_failure",
    "missing",
}
QUANTITATIVE = {"point", "upper_bound", "lower_bound", "interval"}


def nanomolar(value: float, unit: str) -> float:
    """Convert explicit concentration units; never infer log or mass units."""
    if unit not in UNITS or not isfinite(value) or value <= 0:
        raise ValueError("Finite positive concentration and explicit molar unit needed")
    result = value * UNITS[unit]
    if not isfinite(result) or result <= 0:
        raise ValueError("Concentration conversion overflow or underflow")
    return result


@dataclass(frozen=True)
class PotencyRecord:
    """Point estimates are not exact biological truth; bounds retain inequalities."""

    record_id: str
    endpoint: Endpoint
    kind: Kind
    qc: Literal["accepted", "unresolved", "failed"]
    evidence: str
    unit: str = "nM"
    lower: float | None = None
    upper: float | None = None
    lower_closed: bool = False
    upper_closed: bool = False
    failure_reason: str = ""

    def __post_init__(self) -> None:
        if not self.record_id or not self.evidence:
            raise ValueError(
                "Source record identity and adjudication evidence required"
            )
        if self.kind not in KINDS or self.endpoint not in {
            "absolute_ic50",
            "relative_ic50",
        }:
            raise ValueError("Unknown endpoint or observation kind")
        if self.qc not in {"accepted", "unresolved", "failed"}:
            raise ValueError("Explicit QC status required")
        if type(self.lower_closed) is not bool or type(self.upper_closed) is not bool:
            raise ValueError("Bound closures must be booleans")
        lo = None if self.lower is None else nanomolar(self.lower, self.unit)
        hi = None if self.upper is None else nanomolar(self.upper, self.unit)
        if self.kind not in QUANTITATIVE:
            if lo is not None or hi is not None:
                raise ValueError(
                    "Nonquantitative record cannot smuggle a numeric label"
                )
        elif self.kind == "point":
            if lo is None or lo != hi or not (self.lower_closed and self.upper_closed):
                raise ValueError("Point estimate requires equal closed finite bounds")
        elif self.kind == "upper_bound":
            if lo is not None or hi is None or self.lower_closed:
                raise ValueError("Upper bound requires only an upper concentration")
        elif self.kind == "lower_bound":
            if lo is None or hi is not None or self.upper_closed:
                raise ValueError("Lower bound requires only a lower concentration")
        elif lo is None or hi is None or lo >= hi:
            raise ValueError("Interval needs strictly ordered finite endpoints")
        if self.kind == "biological_failure" and (
            self.endpoint != "absolute_ic50"
            or self.qc != "accepted"
            or self.failure_reason != "validated_maximum_inhibition_below_50_percent"
        ):
            raise ValueError(
                "Biological failure needs accepted absolute-response evidence"
            )


@dataclass(frozen=True)
class Decision:
    record_id: str
    category: str
    success: bool | None
    lower_nm: float | None
    upper_nm: float | None
    reason: str


def adjudicate(
    record: PotencyRecord, threshold_nm: float, endpoint: Endpoint
) -> Decision:
    """Classify success IC50 <= threshold only when the observation implies it."""
    nanomolar(threshold_nm, "nM")
    if endpoint not in {"absolute_ic50", "relative_ic50"}:
        raise ValueError("Unknown requested endpoint")
    if record.endpoint != endpoint:
        raise ValueError("Absolute and relative IC50 cannot be pooled")
    lo = None if record.lower is None else nanomolar(record.lower, record.unit)
    hi = None if record.upper is None else nanomolar(record.upper, record.unit)

    def result(category: str, success: bool | None, reason: str) -> Decision:
        return Decision(record.record_id, category, success, lo, hi, reason)

    if record.kind in {"missing", "assay_failure"}:
        return result(record.kind, None, "No interpretable potency outcome")
    if record.qc != "accepted" or record.kind == "unresolved":
        return result("unresolved", None, "QC or curve interpretation unresolved")
    if record.kind == "biological_failure":
        return result("biological_failure", False, record.failure_reason)
    if hi is not None and hi <= threshold_nm:
        return result(
            "point_success" if record.kind == "point" else "bound_success",
            True,
            "Every concentration allowed by the record meets IC50 <= threshold",
        )
    if lo is not None and (
        lo > threshold_nm or (lo == threshold_nm and not record.lower_closed)
    ):
        return result(
            "point_failure" if record.kind == "point" else "bound_failure",
            False,
            "Every concentration allowed by the record exceeds the threshold",
        )
    return result("unresolved", None, "Admissible potency spans the success boundary")


def yield_bounds(decisions: list[Decision]) -> dict:
    """Identification bounds retain unknown outcomes in the fixed denominator."""
    if len({d.record_id for d in decisions}) != len(decisions):
        raise ValueError("Deduplicate compound-assay discoveries before aggregation")
    n = len(decisions)
    successes = sum(d.success is True for d in decisions)
    failures = sum(d.success is False for d in decisions)
    unknown = n - successes - failures
    return {
        "records": n,
        "qualified_successes": successes,
        "qualified_failures": failures,
        "unresolved_or_unavailable": unknown,
        "success_count_lower": successes,
        "success_count_upper": successes + unknown,
        "yield_lower": successes / n if n else None,
        "yield_upper": (successes + unknown) / n if n else None,
        "interpretation": "identification bounds, not confidence intervals",
    }


def synthetic_check(output: Path) -> None:
    """Freeze a toy threshold and demonstrate boundary cases without real labels."""
    protocol = seal(
        {
            "schema": "censored-ic50-synthetic-v1",
            "purpose": (
                "synthetic adjudication plumbing; not a measured policy experiment"
            ),
            "threshold_nm": 10.0,
            "threshold_basis": "arbitrary toy constant; not a benchmark recommendation",
            "endpoint": "absolute_ic50",
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "measured_labels_read": 0,
            "policy_replays": 0,
            "missing_inputs": [
                "completed V3 and Qwen protocols and policy checkpoints",
                "saved original decisions and assay purchase ledgers",
                "curve QC and censoring records with exact endpoint and dose units",
                "original success cutoff, label-access roles and assay-cost contract",
            ],
        }
    )
    write_new(output / "protocol.json", protocol)
    common = {"endpoint": "absolute_ic50", "qc": "accepted", "evidence": "synthetic"}
    cases = [
        PotencyRecord(
            "point",
            kind="point",
            lower=8,
            upper=8,
            lower_closed=True,
            upper_closed=True,
            **common,
        ),
        PotencyRecord("below-lowest", kind="upper_bound", upper=5, **common),
        PotencyRecord("unresolved-upper", kind="upper_bound", upper=20, **common),
        PotencyRecord("above-highest", kind="lower_bound", lower=50, **common),
        PotencyRecord("right-boundary-open", kind="lower_bound", lower=10, **common),
        PotencyRecord(
            "right-boundary-closed",
            kind="lower_bound",
            lower=10,
            lower_closed=True,
            **common,
        ),
        PotencyRecord("curve-unresolved", kind="unresolved", **common),
        PotencyRecord("measurement-failed", kind="assay_failure", **common),
        PotencyRecord(
            "true-failure",
            kind="biological_failure",
            failure_reason="validated_maximum_inhibition_below_50_percent",
            **common,
        ),
    ]
    decisions = [adjudicate(r, 10.0, "absolute_ic50") for r in cases]
    result = seal(
        {
            "protocol_seal": protocol["seal"],
            "records": [asdict(r) for r in cases],
            "decisions": [asdict(d) for d in decisions],
            "summary": yield_bounds(decisions),
            "policy_ranking_result": None,
            "status": "synthetic_checks_only_missing_real_v3_qwen_inputs",
        }
    )
    write_new(output / "result.json", result)
    print(json.dumps(result["summary"], indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    synthetic_check(args.output)


if __name__ == "__main__":
    main()
