"""Actual acquisition oracle rejects test IDs and duplicate/atomic reveals."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "atlas_campaign",
    Path(__file__).resolve().parents[1] / "scripts/run_atlas_acquisition.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_oracle_denies_unrevealed_and_heldout_ids_atomically():
    oracle = module.PoolOracle({"a": 1.0, "b": 2.0})
    with pytest.raises(ValueError):
        oracle.labels(["a"])
    with pytest.raises(ValueError):
        oracle.reveal(["a", "heldout"])
    assert oracle.revealed == {}
    oracle.reveal(["a"])
    assert oracle.labels(["a"]).tolist() == [1.0]
    with pytest.raises(ValueError):
        oracle.reveal(["a", "b"])
    assert set(oracle.revealed) == {"a"}
    with pytest.raises(ValueError):
        oracle.reveal(["b", "b"])


def test_unrevealed_labels_do_not_change_revealed_observations():
    a = module.PoolOracle({"a": 1.0, "b": 2.0})
    b = module.PoolOracle({"a": 1.0, "b": -9999.0})
    a.reveal(["a"])
    b.reveal(["a"])
    assert a.labels(["a"]).tolist() == b.labels(["a"]).tolist()
