"""Scientific invariants of the recorded-panel IC50 pilot; no Qwen mock results."""

import importlib.util
import json
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "ic50_qwen_core",
    Path(__file__).resolve().parents[1] / "experiments/ic50_qwen/core.py",
)
assert _SPEC is not None and _SPEC.loader is not None
core = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(core)


def test_pava_preserves_valid_curves_and_pools_monotone_violations():
    assert core.isotonic([0, 30, 60, 90]) == [0, 30, 60, 90]
    assert core.isotonic([0, 60, 40, 90]) == [0, 50, 50, 90]
    assert core.isotonic([90, 60, 30, 0]) == [45, 45, 45, 45]


def test_lower_than_lowest_is_bound_not_imputed_potency():
    record = core.curve_record([1, 10, 100, 1000], [60, 70, 80, 90])
    assert record["kind"] == "upper_bound"
    assert record["upper_nm"] == 1
    assert "estimate_nm" not in record
    assert core.success(record, 100, "bound_aware") is True
    assert core.success(record, 100, "exact_only") is False
    assert core.success(record, 0.5, "bound_aware") is None
    assert core.success(record, 0.5, "exact_only") is None


def test_right_censoring_is_not_automatically_biological_failure():
    record = core.curve_record([1, 10, 100, 1000], [5, 10, 20, 30])
    assert record["kind"] == "lower_bound"
    assert core.success(record, 1000, "bound_aware") is False
    assert core.success(record, 2000, "bound_aware") is None


def test_interpolation_respects_absolute_response_and_log_dose():
    r = core.curve_record([1, 10, 100, 1000], [0, 25, 75, 100])
    assert r["kind"] == "interpolated"
    assert r["estimate_nm"] == pytest.approx(1000**0.5)
    assert r["bracket_nm"] == [10, 100]
    # A low partial-response midpoint never becomes absolute IC50.
    r = core.curve_record([1, 10, 100, 1000], [0, 10, 20, 40])
    assert r["kind"] == "lower_bound"


@pytest.mark.parametrize(
    "responses",
    [[90, 10, 80, 100], [0, 30, 60, 121], [0, 20, float("nan"), 90], [0, 20, None, 90]],
)
def test_qc_failures_remain_unknown_for_both_objectives(responses):
    r = core.curve_record([1, 10, 100, 1000], responses)
    assert r["kind"] == "unresolved"
    assert core.success(r, 100, "exact_only") is None
    assert core.success(r, 100, "bound_aware") is None


@pytest.mark.parametrize(
    "doses", [[1, 10, 100], [1, 10, 10, 100], [0, 1, 10, 100], [10, 1, 100, 1000]]
)
def test_curve_identity_requires_complete_unique_ordered_positive_doses(doses):
    with pytest.raises(ValueError):
        core.curve_record(doses, [20] * len(doses))


def study():
    candidates = [
        {
            "id": str(i),
            "features": {"sequence": "ACGT", "gc_bin": i % 4},
            "row_ids": [f"private:{i}"],
            "secret_unqueried_outcome": 999,
        }
        for i in range(12)
    ]
    campaign = {
        "id": "demo",
        "target": "synthetic",
        "candidates": candidates,
        "dose_grid_nm": [1, 10, 100, 1000],
    }
    oracle = {str(i): {"kind": "upper_bound", "upper_nm": 1} for i in range(12)}
    return campaign, oracle


def test_policy_view_excludes_unpurchased_rows_and_outcome_fields():
    c, _ = study()
    obs = core.observation(c, [], "bound_aware", 8, 100)
    serialized = json.dumps(obs)
    assert "secret_unqueried_outcome" not in serialized
    assert "private:" not in serialized
    assert "upper_nm" not in serialized
    assert "oracle" not in obs


def test_policy_receives_only_charged_history_and_cannot_rebuy():
    c, oracle = study()
    seen = []

    def policy(obs):
        assert len(obs["history"]) == 8 - obs["remaining_panel_budget"]
        assert not {h["id"] for h in obs["history"]} & {
            r["id"] for r in obs["candidates"]
        }
        seen.append(obs)
        return obs["candidates"][0]["id"], {"unit_test_callback": True}

    result = core.replay(c, oracle, "qwen", "bound_aware", 1900, qwen=policy)
    assert len(seen) == 6
    assert len({r["id"] for r in result["history"]}) == 8
    assert result["source_dose_measurements"] == 32
    assert sum(r["initial"] for r in result["history"]) == 2


def test_random_has_identical_trajectory_under_changed_feedback():
    c, oracle = study()
    a = core.replay(c, oracle, "random", "exact_only", 1900)
    b = core.replay(c, oracle, "random", "bound_aware", 1900)
    assert [h["id"] for h in a["history"]] == [h["id"] for h in b["history"]]
    assert a["credited_hits"] == 0 and b["credited_hits"] == 8
    assert a["counterfactual_rescore"]["bound_aware"] == 8


def test_qwen_never_silently_falls_back_to_another_policy():
    c, oracle = study()
    with pytest.raises(ValueError, match="Actual Qwen"):
        core.replay(c, oracle, "qwen", "bound_aware", 1900)
    with pytest.raises(ValueError, match="unavailable"):
        core.replay(
            c, oracle, "qwen", "bound_aware", 1900, qwen=lambda obs: ("nonexistent", {})
        )


def test_zero_tolerance_is_a_separate_frozen_qc_sensitivity():
    d, y = [1, 10, 100, 1000], [0, 60, 40, 90]
    assert core.curve_record(d, y)["kind"] == "interpolated"
    assert core.curve_record(d, y, max_adjustment=0)["kind"] == "unresolved"
