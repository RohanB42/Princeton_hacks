"""Censored potency is bounded evidence, never an invented point estimate."""

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "censored_ic50_experiment",
    Path(__file__).resolve().parents[1] / "scripts/censored_ic50_policy_experiment.py",
)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = audit
_SPEC.loader.exec_module(audit)


def record(kind="upper_bound", **kwargs):
    return audit.PotencyRecord(
        "source:1", "absolute_ic50", kind, "accepted", "synthetic test", **kwargs
    )


def test_left_censored_potency_qualifies_without_inventing_point():
    outcome = audit.adjudicate(record(upper=5), 10, "absolute_ic50")
    assert outcome.success is True and outcome.category == "bound_success"
    assert outcome.lower_nm is None and outcome.upper_nm == 5
    assert audit.adjudicate(record(upper=20), 10, "absolute_ic50").success is None


@pytest.mark.parametrize("closed,expected", [(False, False), (True, None)])
def test_right_censoring_preserves_strictness_at_threshold(closed, expected):
    outcome = audit.adjudicate(
        record("lower_bound", lower=10, lower_closed=closed), 10, "absolute_ic50"
    )
    assert outcome.success is expected


@pytest.mark.parametrize("closed", [False, True])
def test_upper_bound_at_inclusive_threshold_always_qualifies(closed):
    outcome = audit.adjudicate(
        record(upper=10, upper_closed=closed), 10, "absolute_ic50"
    )
    assert outcome.success is True


def test_unit_conversion_preserves_decision_and_rejects_implicit_scales():
    a = audit.adjudicate(record(upper=0.005, unit="uM"), 10, "absolute_ic50")
    b = audit.adjudicate(record(upper=5, unit="nM"), 10, "absolute_ic50")
    assert a == b
    for unit in ("logM", "pIC50", "mg/mL", "unknown"):
        with pytest.raises(ValueError):
            audit.nanomolar(5, unit)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_nonpositive_or_nonfinite_values_are_not_potency(value):
    with pytest.raises(ValueError):
        record(upper=value)


def test_relative_and_absolute_endpoints_never_share_success_labels():
    with pytest.raises(ValueError, match="cannot be pooled"):
        audit.adjudicate(record(upper=1), 10, "relative_ic50")


def test_qc_failure_prevents_apparent_potent_bound_from_qualifying():
    x = replace(record(upper=1), qc="failed")
    assert audit.adjudicate(x, 10, "absolute_ic50").success is None


@pytest.mark.parametrize("kind", ["unresolved", "assay_failure", "missing"])
def test_unknown_assays_never_become_biological_failures(kind):
    x = audit.adjudicate(record(kind), 10, "absolute_ic50")
    assert x.success is None


def test_true_failure_requires_accepted_absolute_maximum_effect_evidence():
    with pytest.raises(ValueError, match="Biological failure"):
        record("biological_failure")
    x = record(
        "biological_failure",
        failure_reason="validated_maximum_inhibition_below_50_percent",
    )
    assert audit.adjudicate(x, 10, "absolute_ic50").success is False
    with pytest.raises(ValueError, match="Biological failure"):
        replace(x, endpoint="relative_ic50")


def test_intervals_cannot_be_reversed_or_collapsed_into_false_exactness():
    for lo, hi in [(20, 5), (5, 5)]:
        with pytest.raises(ValueError):
            record("interval", lower=lo, upper=hi)
    x = record("interval", lower=5, upper=20)
    assert audit.adjudicate(x, 10, "absolute_ic50").success is None


def test_point_estimates_preserve_inclusive_cutoff():
    x = record("point", lower=10, upper=10, lower_closed=True, upper_closed=True)
    assert audit.adjudicate(x, 10, "absolute_ic50").success is True
    with pytest.raises(ValueError):
        replace(x, lower_closed=False)


def test_unknowns_stay_in_denominator_and_empty_yield_is_undefined():
    yes = audit.adjudicate(record(upper=5), 10, "absolute_ic50")
    unknown = audit.adjudicate(
        replace(record("missing"), record_id="source:2"), 10, "absolute_ic50"
    )
    result = audit.yield_bounds([yes, unknown])
    assert result["yield_lower"] == 0.5 and result["yield_upper"] == 1
    assert audit.yield_bounds([])["yield_lower"] is None
    with pytest.raises(ValueError, match="Deduplicate"):
        audit.yield_bounds([yes, yes])
