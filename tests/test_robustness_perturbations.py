"""Perturbations preserve chemistry and never manufacture variant measurements."""

from dataclasses import asdict

import pytest

from oligo_engine.robustness.diagnostics import DomainReference
from oligo_engine.robustness.fixture import SyntheticAuditModel, source
from oligo_engine.robustness.generated import audit_generated_archive
from oligo_engine.robustness.perturbations import (
    context_change,
    representation_cases,
)
from scoring_helpers import candidate_panel


def test_equivalent_variants_retain_structure_and_malformed_is_rejected():
    row = source().rows[0]
    cases = representation_cases(row)
    assert cases[0][1].compound_id == row.compound_id
    assert cases[0][1].sample_id != row.sample_id
    assert cases[1][0].legal is False and cases[1][1] is None
    assert all(case.measurement_status == "unmeasured_variant" for case, _ in cases)
    assert all("label" not in asdict(variant) for _, variant in cases if variant)


def test_context_probe_changes_identity_and_rejects_unsupported_context():
    row = source().rows[0]
    context = (("assay", "supported-alternative"),)
    case, variant = context_change(
        row, "assay", "supported-alternative", frozenset((context,))
    )
    assert case.legal and variant.assessment_id != row.assessment_id
    assert variant.compound_id == row.compound_id
    case, variant = context_change(row, "assay", "unknown", frozenset((context,)))
    assert not case.legal and variant is None


def test_generated_bridge_is_computational_only_and_checks_target_manifest():
    space = candidate_panel("ps_moe_20_gapmer")
    candidate = space.candidate(1)
    receipt = {
        "target_manifest": asdict(space.target),
        "target_identity": space.target.identity,
        "scorer_identity": "frozen-fixture",
        "assay": {"assay": "synthetic"},
        "archive": [{"candidate": asdict(candidate)}],
        "requests": 1,
        "unique_scores": 1,
        "head_calls": 1,
    }
    reference = DomainReference(source().rows[:10])
    model = SyntheticAuditModel(reference.rows)
    result = audit_generated_archive(
        receipt, reference, "synthetic_potency", "fixture units", model
    )
    assert result["status"] == "computational_only"
    assert result["exact_measured_outcomes"] == 0
    assert result["evaluator_independence"] == "not_established_by_this_function"
    with pytest.raises(ValueError, match="manifest"):
        audit_generated_archive(
            receipt | {"target_identity": "changed"},
            reference,
            "synthetic_potency",
            "fixture units",
        )
