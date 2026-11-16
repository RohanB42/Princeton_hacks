"""Protected memberships must survive cross-source and near-sequence joins."""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "compatible_data",
    Path(__file__).resolve().parents[1]
    / "scripts/molecular_compatible_data_experiment.py",
)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(audit)


def test_projection_is_metadata_only_and_rejects_unknown_endpoints():
    for endpoint in audit.ENDPOINTS:
        assert not set(audit.metadata_columns(endpoint)) & {
            "Inhibition_pct",
            "FOB_score",
            "IC50",
            "y",
            "y_raw",
        }
    with pytest.raises(ValueError):
        audit.metadata_columns("IC50")


@pytest.mark.parametrize(
    "role",
    [
        "source_calibration",
        "source_validation",
        "reserved_pool",
        "final_pool",
        "training_sentinel",
        "measured_assessment",
        "test_ids",
    ],
)
def test_roles_that_cannot_be_moved_into_training(role):
    assert audit.protected_role(role)
    assert not audit.protected_role("source_fit")


def test_near_graph_preserves_lengths_and_transitive_exclusions():
    rows = [
        {"id": "final", "sequences": ["AAAAAA"], "patent": "P1"},
        {"id": "near", "sequences": ["AACCAA"], "patent": "P2"},
        {"id": "bridge", "sequences": ["CCCCCC"], "patent": "P2"},
        {"id": "far", "sequences": ["GGGGGG"], "patent": "<missing>"},
        {"id": "short", "sequences": ["AAAAA"], "patent": "<missing>"},
    ]
    graph = audit.Components()
    audit.add_exact(graph, rows)
    audit.add_near(graph, {s for r in rows for s in r["sequences"]})
    assert audit.excluded(graph, rows, {"final"}) == {"final", "near", "bridge"}


def test_one_base_shift_is_linked_without_hamming_similarity():
    graph = audit.Components()
    audit.add_near(graph, {"ACGTAC", "CGTACA", "TTTTTT"})
    assert graph.find("seq:ACGTAC") == graph.find("seq:CGTACA")
    assert graph.find("seq:ACGTAC") != graph.find("seq:TTTTTT")


def test_memberships_ignore_metrics_and_preserve_validation_identity():
    ids = ["in_vitro_inhibition:1"]
    recovered = audit.recover(
        {
            "fit": {"ids": ids, "validation_ids": ["in_vitro_inhibition:2"]},
            "metrics": {"ids": ["in_vitro_inhibition:3"]},
        }
    )
    assert set().union(*recovered.values()) == set(ids + ["in_vitro_inhibition:2"])
    protected = set().union(
        *(values for role, values in recovered.items() if audit.protected_role(role))
    )
    assert protected == {"in_vitro_inhibition:2"}


def test_receipt_directory_name_does_not_override_explicit_fit_role(tmp_path):
    import json

    path = tmp_path / "development-study" / "receipt.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"ids": ["in_vitro_inhibition:1"]}))
    memberships, provenance = audit.receipt_memberships([path])
    assert len(memberships) == 1
    role = next(iter(memberships))
    assert not audit.protected_role(role)
    assert provenance[role]["path"] == str(path)
