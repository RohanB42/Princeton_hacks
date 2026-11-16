"""Metadata feasibility must never silently become measured model evaluation."""

import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from oligo_engine.molecular_design.bundles import fixture
from oligo_engine.reward.chemistry import parse_helm

_SPEC = importlib.util.spec_from_file_location(
    "validity_experiment",
    Path(__file__).resolve().parents[1] / "scripts/molecular_validity_experiment.py",
)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit)


@pytest.mark.parametrize("outcome", ["Inhibition_pct", "FOB_score", "IC50", "x"])
def test_metadata_projection_rejects_outcomes_and_unregistered_columns(outcome):
    with pytest.raises(ValueError, match="metadata"):
        audit.projection("in_vitro_inhibition", ["HELM Annotation", outcome])


def test_family_preserves_methylation_linkages_terminal_and_unknown_positions():
    campaign, _ = fixture()
    pattern = campaign.profile.patterns[0]
    sequence = "C" + "A" * (pattern.length - 1)
    plain = replace(pattern, methyl_c=(False,) * pattern.length)
    methyl = replace(pattern, methyl_c=(True,) * pattern.length)
    a = audit.uniform_family(parse_helm(plain.helm(sequence, "none")))
    b = audit.uniform_family(parse_helm(methyl.helm(sequence, "none")))
    assert a and b and a != b
    assert not a["methyl_c"] and b["methyl_c"]
    terminal = replace(plain, terminals=("PS",))
    assert audit.uniform_family(parse_helm(terminal.helm(sequence, "PS"))) != a
    links = replace(plain, links=("PO",) * (pattern.length - 1))
    assert audit.uniform_family(parse_helm(links.helm(sequence, "none"))) != a
    assert (
        audit.uniform_family(parse_helm(plain.helm("A" * pattern.length, "none")))
        is None
    )
    mixed = replace(plain, methyl_c=(True, False) + (False,) * (pattern.length - 2))
    assert (
        audit.uniform_family(
            parse_helm(mixed.helm("CC" + "A" * (pattern.length - 2), "none"))
        )
        is None
    )


def test_protected_partition_exclusion_closes_transitive_metadata_connections():
    records = [
        {"id": "final", "sequence": "AAA", "patent": "P1"},
        {"id": "bridge", "sequence": "AAA", "patent": "P2"},
        {"id": "unseen", "sequence": "CCC", "patent": "P2"},
        {"id": "separate", "sequence": "GGG", "patent": "P3"},
        {"id": "missing1", "sequence": "TTT", "patent": "<missing>"},
        {"id": "missing2", "sequence": "TTG", "patent": "<missing>"},
    ]
    protected = {"final", "missing1"}
    expected = {"final", "bridge", "unseen", "missing1"}
    assert audit.protected_connections(records, protected) == expected
    assert audit.protected_connections(list(reversed(records)), protected) == expected


def test_context_normalizes_numbers_but_does_not_invent_biological_aliases():
    assert audit.normalized(4500.0) == audit.normalized("4500")
    assert audit.normalized(None) == audit.normalized(float("nan")) == "<missing>"
    assert audit.normalized("HepG2") != audit.normalized("HEPG2")
