"""Identity, grouped leakage boundaries and outcome-capability invariants."""

from dataclasses import asdict, replace

import pytest

from oligo_engine.robustness.adapters import OutcomeCapability, load_asoptimizer
from oligo_engine.robustness.contracts import (
    AuditObservation,
    AuditPrediction,
    chemistry,
)
from oligo_engine.robustness.fixture import source
from oligo_engine.robustness.splits import audit_artifact, make_split


def test_four_way_splits_are_group_disjoint_order_independent_and_complete():
    rows = source().rows
    first, audit = make_split(rows)
    second, _ = make_split(tuple(reversed(rows)))
    assert first == second
    first.validate(rows)
    assert audit["independent_components"] == 8
    audit_artifact(first.fit, first)
    for ids in (first.final, (), first.fit + first.fit):
        with pytest.raises(ValueError, match="artifact_overlap"):
            audit_artifact(ids, first)
    with pytest.raises(ValueError, match="metadata"):
        first.validate((replace(rows[0], source_hash="changed"),) + rows[1:])


def test_equivalent_structures_link_groups_and_missing_patents_fail_closed():
    rows = source().rows
    linked = rows + (replace(rows[0], sample_id="shared", target_id="another-target"),)
    split, audit = make_split(linked)
    part = next(
        p
        for p in ("fit", "development", "calibration", "final")
        if rows[0].sample_id in getattr(split, p)
    )
    assert "shared" in getattr(split, part)
    with pytest.raises(ValueError, match="infeasible_split"):
        make_split(tuple(replace(r, patent_id="") for r in rows), "patent_id")
    with pytest.raises(ValueError, match="Duplicate"):
        make_split(rows + rows[:1])


def test_source_versions_and_methylcytosine_aliases_preserve_original():
    row = source().rows[0]
    alias = replace(row, helm=row.helm + "V2.0")
    assert row.compound_id == alias.compound_id
    assert alias.helm.endswith("V2.0")
    natural = row.helm.replace("([m5C])", "(C)")
    methyl = natural.replace("(C)", "([m5C])")
    assert (
        chemistry(methyl).identity == chemistry(methyl.replace("m5C", "5meC")).identity
    )
    assert chemistry(methyl).identity != chemistry(natural).identity
    with pytest.raises(ValueError):
        chemistry(row.helm + "V9.0")
    assert "outcome" not in asdict(row)
    with pytest.raises(TypeError):
        AuditObservation.from_dict(asdict(row) | {"outcome": 3.0})


def test_outcome_capability_denies_test_ids_before_reader_call():
    called = []

    def reader(ids):
        called.append(ids)
        return {i: 1.0 for i in ids}

    capability = OutcomeCapability(("fit",), reader)
    assert capability.read(("fit",)) == {"fit": 1.0}
    with pytest.raises(ValueError, match="Denied"):
        capability.read(("final",))
    assert called == [("fit",)]
    with pytest.raises(ValueError):
        AuditPrediction("x", "m", float("nan"))


def test_real_metadata_adapter_recovers_original_subset_without_numeric_labels():
    dataset = load_asoptimizer()
    assert len(dataset.rows) == 5586
    assert dataset.receipt["label_values_read"] is False
    assert dataset.receipt["patent_metadata_available"] is False
    assert {r.target_id for r in dataset.rows} == {
        "DGAT2",
        "HBV",
        "KLKB1",
        "SOD1",
        "MALAT1",
    }
    assert any(r.helm.endswith("V2.0") for r in dataset.rows)
    assert all("source_hash" in asdict(r) for r in dataset.rows)
