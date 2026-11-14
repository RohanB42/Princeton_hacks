"""Published-only selection, frozen scope and environment paths are reproducible."""

import copy
import hashlib
import json
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

from oligo_engine.efficacy_reproduction import (
    config_text,
    interpreter_path,
    select_best,
)
from oligo_engine.native_cache import native_monomer_cache
from oligo_engine.reproduce import serialize_parameters


def rows(alias, model, values):
    return [
        {
            "dataset": alias,
            "cross_validation": "nucleobase",
            "model": model,
            "model_args": "{'n_estimators': 100, 'max_depth': 20}",
            "featurizer": "OneHotEncoder",
            "featurizer_args": "{'encode_components': ['base']}",
            "test_pearson_correlation": str(value),
        }
        for value in values
    ]


def test_selection_requires_five_finite_source_results_and_keeps_tasks_separate():
    source = (
        rows("a", "winner", [0.6] * 5)
        + rows("a", "incomplete", [0.99] * 4)
        + rows("a", "undefined", [0.99] * 4 + [""])
        + rows("b", "other", [0.2] * 5)
    )
    result = select_best(source, {"a", "b"})
    assert result["a"]["model"]["name"] == "winner"
    assert result["a"]["model"]["max_depth"] == 20
    assert result["a"]["reference_mean_pearson"] == 0.6
    assert result["b"]["reference_mean_pearson"] == 0.2
    with pytest.raises(ValueError, match="No complete"):
        select_best(source, {"missing"})


def test_ties_are_resolved_without_using_row_order_or_local_scores():
    source = rows("a", "z", [0.5] * 5) + rows("a", "a", [0.5] * 5)
    assert select_best(source, {"a"})["a"]["model"]["name"] == "a"
    assert select_best(list(reversed(source)), {"a"})["a"]["model"]["name"] == "a"


def test_toml_round_trip_retains_nested_training_settings():
    value = {
        "seeds": [0, 1, 2, 3, 4],
        "training": {"early_stopping": True, "early_stopping_kwargs": {"patience": 5}},
        "model": {"name": "MLP", "hidden_dims": [128], "dropout": 0},
    }
    assert tomllib.loads(config_text(value)) == value


def test_frozen_manifest_contains_all_seven_winners_with_unchanged_configs():
    root = Path(__file__).parents[1] / "configs/gate1-efficacy"
    manifest = json.loads((root / "manifest.json").read_text())
    expected = {
        "Huesken": "CNN",
        "Ichihara": "MLP",
        "Shmushkovich": "RandomForestModel",
        "siRNAmod": "RandomForestModel",
        "OpenASO": "LinearModel",
        "ASOptimizer": "CNN",
        "Sherwood": "XGBoostModel",
    }
    assert len(manifest["datasets"]) == 7
    assert manifest["local_results_used_for_selection"] is False
    for entry in manifest["datasets"]:
        path = root / entry["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        settings = tomllib.loads(path.read_text())
        assert settings["model"]["name"] == expected[settings["loader_key"]]
        assert settings["seeds"] == [0, 1, 2, 3, 4]
        assert settings["tolerance"] == 0.03
        assert settings["execution_mode"] == "benchmark_helpers"
        assert len(entry["published"]["reference_values"]) == 5
        if settings["model"]["name"] in {"CNN", "MLP"}:
            assert settings["training"]["max_epochs"] == 100
            assert settings["trainer"]["enable_checkpointing"] is False


def test_virtualenv_interpreter_symlink_is_not_resolved(tmp_path):
    actual = tmp_path / "base-python"
    actual.touch()
    virtual = tmp_path / "venv" / "bin" / "python"
    virtual.parent.mkdir(parents=True)
    virtual.symlink_to(actual)
    assert interpreter_path(virtual) == virtual.absolute()
    assert interpreter_path(virtual) != actual.resolve()


def test_nonfinite_parameter_sentinel_is_explicit_valid_json():
    result = serialize_parameters({"missing": float("nan"), "dims": (1, 2)})
    assert result == {"missing": {"nonfinite_float": "nan"}, "dims": [1, 2]}
    json.dumps(result, allow_nan=False)


class Frame:
    def __init__(self, value):
        self.value = value

    def copy(self, deep=True):
        assert deep
        return copy.deepcopy(self)


def test_native_cache_returns_copies_and_restores_source_even_on_error(monkeypatch):
    calls = []
    features = ModuleType("oligogym.features")

    def original(helm, strands):
        calls.append((helm, strands))
        return Frame({"helm": helm, "strands": strands})

    features._extract_monomers = original
    package = ModuleType("oligogym")
    package.features = features
    monkeypatch.setitem(sys.modules, "oligogym", package)
    monkeypatch.setitem(sys.modules, "oligogym.features", features)
    with pytest.raises(RuntimeError, match="fixture error"):
        with native_monomer_cache(
            {"cache_native_monomers": True, "max_entries": 2}
        ) as info:
            changed = features._extract_monomers("ACGU")
            changed.value["helm"] = "mutated"
            assert features._extract_monomers("ACGU").value["helm"] == "ACGU"
            features._extract_monomers("ACGU", ["RNA1"])
            assert len(calls) == 2
            raise RuntimeError("fixture error")
    assert features._extract_monomers is original
    assert info["hits"] == 1 and info["misses"] == 2


def test_disabled_cache_never_imports_upstream_and_capacity_is_validated():
    with native_monomer_cache({}) as info:
        assert info == {"cache_native_monomers": False}
    with pytest.raises(ValueError, match="positive integer"):
        with native_monomer_cache({"cache_native_monomers": True, "max_entries": 0}):
            pass
