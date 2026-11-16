"""Scientific boundary invariants for the outcome-blind exposure audit."""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "molecular_generalization_audit",
    Path(__file__).parents[1] / "scripts/molecular_generalization_audit.py",
)
assert _SPEC and _SPEC.loader
audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit)


@pytest.mark.parametrize("column", ["Inhibition_pct", "FOB_score", "finite_endpoint"])
def test_outcomes_and_unapproved_derived_fields_rejected_before_io(column: str) -> None:
    with pytest.raises(ValueError, match="metadata columns"):
        audit.projected_metadata(Path("must_not_be_opened.parquet"), (column,))


def test_reserved_and_selection_exposure_cannot_be_relabelled_fresh() -> None:
    assert audit.classification(["historical_reserved"], 0, 0).startswith("reserved_")
    assert audit.classification([], 0, 1).startswith("predictor_exposed_")
    assert audit.classification(["policy_training"], 0, 0).startswith("development_")
    assert audit.classification([], 0, 0).endswith("pending_independence_audit")


def test_shared_seed_variance_does_not_vanish_with_more_targets() -> None:
    small = audit.crossed_precision(5, 5, 0.0, 0.2, 0.0)
    large = audit.crossed_precision(500, 5, 0.0, 0.2, 0.0)
    assert small == large
    assert small["se"] == pytest.approx(0.2 / 5**0.5)


def test_target_variance_does_not_vanish_with_more_seeds() -> None:
    small = audit.crossed_precision(5, 5, 0.2, 0.0, 0.0)
    large = audit.crossed_precision(5, 500, 0.2, 0.0, 0.0)
    assert small == large
