"""Invariants for dose-selection provenance, stopping, bounds and information."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.adaptive_dose_response import core  # noqa: E402
from experiments.adaptive_dose_response.run import near  # noqa: E402


def test_threshold_witnesses_are_directional_and_inclusive():
    ds = [10, 100, 500, 1000]
    assert core.certificate(ds, {2: 50}, 0) is True
    assert core.certificate(ds, {2: 49}, 0) is False
    assert core.certificate(ds, {1: 49}, 0) is None
    assert core.certificate(ds, {3: 51}, 0) is None


def test_paid_nearest_bracket_interpolation_is_strong_fixed_baseline():
    ds = [10, 100, 1000, 10000]
    assert core.certificate(ds, {1: 30, 2: 70}, 0) is True
    assert core.certificate(ds, {1: 10, 2: 60}, 0) is False
    assert core.certificate(ds, {1: 30}, 0) is None


def test_reference_preserves_bounds_and_bad_curve_unknowns():
    ds = [10, 100, 1000, 10000]
    assert core.reference(ds, [60, 70, 80, 90])["kind"] == "upper_bound"
    assert core.reference(ds, [0, 10, 20, 30])["label"] is False
    assert core.reference(ds, [90, 0, 80, 20])["label"] is None
    assert core.reference([1000, 2000, 3000, 4000], [60, 70, 80, 90])["label"] is None


def test_no_prior_only_stopping_and_budget_conservation():
    ds = [10, 100, 500, 1000]
    bought = []

    def buy(i):
        bought.append(i)
        return [0, 20, 60, 80][i]

    trace = core.trajectory(ds, buy, "fixed_early")
    assert len(bought) == len(set(bought)) == 4
    out = core.stopped(ds, trace, "fixed_early", 0.0)
    assert out["n"] == 1 and out["decision"] is True
    with pytest.raises(ValueError):
        core.stopped(ds, trace, "fixed_early", 0.0, 0)


@pytest.mark.parametrize("method", ["information_gain", "decision_aware"])
def test_poison_unpurchased_outcomes_cannot_change_next_action(method):
    ds = [10, 100, 500, 1000]
    first = core.Belief(ds).next_dose(method)
    a = [10, 20, 60, 80]
    b = [110, 110, 110, 110]
    b[first] = a[first]
    ta = core.trajectory(ds, lambda i: a[i], method)
    tb = core.trajectory(ds, lambda i: b[i], method)
    assert ta[0] == tb[0]
    assert ta[1]["index"] == tb[1]["index"]
    for confidence in core.CONFIDENCES:
        assert core.stopped(ds, ta, method, confidence, 1) == core.stopped(
            ds, tb, method, confidence, 1
        )


def test_stopped_prefix_does_not_read_poisoned_suffix():
    ds = [10, 100, 500, 1000]
    trace = core.trajectory(ds, lambda i: [0, 20, 60, 80][i], "fixed_early")
    poisoned = [trace[0], {"will_fail_if_accessed": True}]
    assert core.stopped(ds, trace, "fixed_early", 0.0) == core.stopped(
        ds, poisoned, "fixed_early", 0.0
    )


def test_full_paid_grid_fallback_matches_reference_and_never_free():
    ds = [10, 100, 500, 1000]
    ys = [0, 20, 60, 80]
    trace = core.trajectory(ds, lambda i: ys[i], "information_gain")
    assert core.stopped(ds, trace, "information_gain", 1.0) == {
        "n": 4,
        "decision": core.reference(ds, ys)["label"],
        "reason": "full_paid_grid",
    }
    assert core.stopped(ds, trace, "information_gain", 1.0, 3)["decision"] is None


def test_posterior_stays_normalized_and_sub50_plateaus_exist():
    b = core.Belief([10, 100, 500, 1000])
    assert not b.potent.all() and b.potent.any()
    b.update(0, -20)
    b.update(1, 120)
    assert b.weights.sum() == pytest.approx(1)
    assert 0 <= b.probability() <= 1
    for likelihood in b.likelihoods:
        assert likelihood.sum(axis=1) == pytest.approx(1)
    with pytest.raises(ValueError):
        b.update(0, 0)


def test_unresolved_predictions_not_hidden_in_accuracy():
    rows = [
        {"reference": True, "decision": None, "n": 1},
        {"reference": False, "decision": True, "n": 2},
        {"reference": None, "decision": False, "n": 1},
    ]
    m = core.metrics(rows)
    assert m["fpr"] == 1 and m["fnr"] == 0
    assert m["resolved_coverage"] == 0.5
    assert m["unknown_assertion_rate"] == 1
    assert not core.qualified(m)


def test_absent_class_is_undefined_and_fails_error_qualification():
    m = core.metrics([{"reference": True, "decision": True, "n": 1}])
    assert m["fpr"] is None
    assert not core.qualified(m)


def test_near_sequence_split_guard():
    assert near("AACCGG", "AATCGG")
    assert near("AACCGG", "ACCGGA")
    assert not near("AAAAAA", "CCCCCC")
