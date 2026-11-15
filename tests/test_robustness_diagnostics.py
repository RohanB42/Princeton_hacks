"""Chemistry-aware distance, calibration, abstention and undefined metrics."""

from dataclasses import replace

import pytest

from oligo_engine.robustness.calibration import ResidualIntervals
from oligo_engine.robustness.diagnostics import DomainReference, structural_distance
from oligo_engine.robustness.evaluate import (
    paired_groups,
    predictive_metrics,
    risk_coverage,
)
from oligo_engine.robustness.fixture import source
from oligo_engine.robustness.guardrails import select_guardrail


def records():
    return [
        {
            "sample_id": str(i),
            "group": "G",
            "compound_id": str(i),
            "mean": float(i),
            "diagnostics": {"warning": float(i)},
        }
        for i in range(20)
    ]


def test_domain_excludes_all_same_compound_not_just_same_row():
    row, other = source().rows[:2]
    clone = replace(row, sample_id="replicate")
    ref = DomainReference((row, clone))
    assert ref.nearest(row)["status"] == "not_comparable"
    ref = DomainReference((row, clone, other))
    assert ref.nearest(row)["nearest_id"] == other.sample_id
    assert structural_distance(row, row) == 0
    assert (
        structural_distance(row, replace(row, helm=row.helm.replace("[sp]", "p"))) > 0
    )
    shortened = replace(row, helm="RNA1{d(A)p.d(C)}$$$$")
    assert structural_distance(row, shortened) is None
    assert structural_distance(row, replace(other, units="incompatible units")) is None
    assert (
        ref.diagnose(row, ref.reference_values())["reference_identity"] == ref.identity
    )


def test_conformal_finite_sample_index_and_insufficient_calibration():
    ids = tuple(str(i) for i in range(20))
    cal = ResidualIntervals.fit(ids, (0.0,) * 20, tuple(float(i) for i in range(20)))
    assert cal.interval(10, 0.1)["upper"] == 28.0
    assert cal.interval(10, 0.05)["lower"] == -9.0
    tiny = ResidualIntervals.fit(("x",), (0.0,), (1.0,))
    assert tiny.interval(0, 0.05)["status"] == "insufficient_calibration"
    assert cal.interval(0, 0.1)["guarantee_under_group_shift"] is False


def test_guardrail_selected_on_development_and_retention_is_per_group():
    rows = records()
    labels = {r["sample_id"]: 0.0 for r in rows}
    policy = select_guardrail(rows, labels, "warning", (5.0, 10.0, 20.0), 0.5)
    assert policy.threshold == 10
    assert sum(policy.accepts(r) for r in rows) == 11
    impossible = select_guardrail(rows, labels, "warning", (0.0,), 0.9)
    assert impossible.status == "no_supported_guardrail"
    assert not impossible.accepts(rows[0])
    bad_group = rows + [
        {
            **rows[0],
            "sample_id": "other",
            "group": "other",
            "diagnostics": {"warning": 100.0},
        }
    ]
    outcomes = labels | {"other": 0.0}
    assert (
        select_guardrail(bad_group, outcomes, "warning", (20.0,), 0.5).status
        == "no_supported_guardrail"
    )


def test_risk_coverage_ordering_and_limited_group_inference():
    rows = records()
    labels = {r["sample_id"]: 0.0 for r in rows}
    useful = risk_coverage(rows, labels, "warning")
    oracle = risk_coverage(rows, labels, "warning", "oracle")
    random = risk_coverage(rows, labels, "warning", "random")
    assert useful["aurc"] == oracle["aurc"] < random["aurc"]
    assert useful["curve"][-1]["risk"] == 9.5
    empty = risk_coverage(rows, labels, "missing")
    assert empty["aurc"] is None and empty["reason"] == "diagnostic_unavailable"
    assert paired_groups({"one-target": 3.0})["ci95"] is None
    assert paired_groups({str(i): float(i) for i in range(5)})["ci95"] is not None


def test_constant_and_unscored_predictions_never_become_zero_correlation():
    rows = records()
    labels = {r["sample_id"]: 1.0 for r in rows}
    result = predictive_metrics(rows, labels)
    assert result["groups"][0]["pearson"] is None
    assert result["groups"][0]["correlation_reason"] == "constant_truth_or_prediction"
    absent = [{**r, "mean": None} for r in rows]
    result = predictive_metrics(absent, labels)
    assert result["macro_rmse"] is None and result["coverage"] == 0
    with pytest.raises(ValueError, match="align"):
        predictive_metrics(rows, {})
