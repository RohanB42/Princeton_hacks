"""Evaluation eligibility must not inherit the new-fitting exclusion rule."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "evaluation_inventory",
    Path(__file__).resolve().parents[1] / "scripts/molecular_evaluation_data_audit.py",
)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_reserved_evaluation_is_preserved_not_called_fitting_or_fresh():
    assert audit.evaluation_role("r", set(), set(), set(), {"r"}, {"r"}) == (
        "original_reserved_evaluation_keep_sealed"
    )


@pytest.mark.parametrize("role", ["fit", "selection", "calibration"])
def test_actual_head_exposure_takes_priority_over_reserved_metadata(role):
    sets = {k: set() for k in ("fit", "selection", "calibration")}
    sets[role].add("r")
    assert (
        audit.evaluation_role(
            "r", sets["fit"], sets["selection"], sets["calibration"], {"r"}, {"r"}
        )
        == "head_" + role
    )


def test_other_membership_is_neither_head_fit_nor_proven_outcome_access():
    assert audit.evaluation_role("r", set(), set(), set(), set(), {"r"}) == (
        "other_study_membership_exposure_audit_required"
    )
    assert audit.evaluation_role("r", set(), set(), set(), set(), set()) == (
        "unassigned_metadata_candidate"
    )


def test_column_projection_cannot_request_measured_endpoints():
    for endpoint in ("in_vitro_inhibition", "neurotoxicity"):
        assert not set(audit.columns(endpoint)) & {
            "Inhibition_pct",
            "FOB_score",
            "IC50",
            "y",
            "y_raw",
        }
    with pytest.raises(ValueError):
        audit.columns("IC50")


def test_context_format_normalization_does_not_equate_doses_or_cell_aliases():
    assert audit.normalize("4500.0") == audit.normalize(4500)
    assert audit.normalize("4500") != audit.normalize("4000")
    assert audit.normalize("HepG2") != audit.normalize("HEPG2")
