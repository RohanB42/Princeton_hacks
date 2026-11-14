"""A repeatability claim requires matching predictions, provenance and all seeds."""

import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "baseline_repeat", Path(__file__).parents[1] / "scripts/check_baseline_repeat.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def pair():
    first = {
        "config": {"seeds": [0]},
        "config_sha256": "fixture-config",
        "dataset": {"name": "synthetic"},
        "source_audit": {"source_revision": "fixture"},
        "published_configuration_reference": {"n": 1, "mean": 0.6},
        "versions": {},
        "installed_distribution_versions": {},
        "mean_pearson_r": 0.5,
        "sample_sd_pearson_r": None,
        "n_defined_seeds": 1,
        "delta_from_published_configuration": -0.1,
        "within_numeric_tolerance": False,
        "environment": {
            "python": "fixture",
            "platform": "fixture",
            "code_revision": "fixture",
            "source_sha256": {},
        },
        "runs": [
            {
                "seed": 0,
                "train_ids": ["train"],
                "test_ids": ["test"],
                "train_rows": 1,
                "test_rows": 1,
                "metrics": {"pearson_r": 0.5},
                "model_execution": {},
                "feature_shape_train": [1, 2],
                "feature_shape_test": [1, 2],
                "prediction_sha256": "fixture-prediction",
                "runtime_seconds": 1,
            }
        ],
    }
    return first, copy.deepcopy(first)


def test_repeatability_does_not_upgrade_historical_reproduction_or_tolerance():
    first, repeated = pair()
    repeated["runs"][0]["runtime_seconds"] = 999
    result = checker.compare(first, repeated)
    assert result["status"] == "exact_within_environment_repeat"
    assert result["gate_1_exact_reproduction"] is False
    assert result["within_numeric_tolerance"] is False


@pytest.mark.parametrize(
    "field", ["prediction_sha256", "test_ids", "model_execution", "metrics"]
)
def test_matching_mean_is_insufficient_for_repeatability(field):
    first, repeated = pair()
    repeated["runs"][0][field] = "changed"
    with pytest.raises(ValueError, match=field):
        checker.compare(first, repeated)


def test_source_and_environment_changes_are_rejected():
    first, repeated = pair()
    repeated["environment"]["source_sha256"] = {"changed.py": "different"}
    with pytest.raises(ValueError, match="source_sha256"):
        checker.compare(first, repeated)
    first, repeated = pair()
    repeated["installed_distribution_versions"] = {"numpy": "different"}
    with pytest.raises(ValueError, match="installed_distribution_versions"):
        checker.compare(first, repeated)


def test_missing_seed_or_prediction_hash_is_rejected():
    first, repeated = pair()
    repeated["runs"] = []
    with pytest.raises(ValueError, match="Incomplete"):
        checker.compare(first, repeated)
    first, repeated = pair()
    del first["runs"][0]["prediction_sha256"]
    with pytest.raises(ValueError, match="prediction_sha256"):
        checker.compare(first, repeated)
