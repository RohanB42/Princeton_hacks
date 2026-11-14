"""Baseline comparison refuses missing seeds, row caps and forged aggregates."""

import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "efficacy_report",
    Path(__file__).parents[1] / "scripts/report_efficacy_reproduction.py",
)
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


def fixture():
    entry = {
        "key": "synthetic",
        "name": "fixture",
        "rows": 2,
        "data_file": "fixture.csv.gz",
        "modality": "synthetic",
    }
    config = {
        "seeds": [0, 1, 2, 3, 4],
        "model": {"name": "RandomForestModel", "n_estimators": 100},
        "reference_mean_pearson": 0.52,
        "tolerance": 0.03,
    }
    run = {
        "seed": 0,
        "train_ids": ["aaaaaaaaaaaaaaaa:fixture:0"],
        "test_ids": ["aaaaaaaaaaaaaaaa:fixture:1"],
        "train_rows": 1,
        "test_rows": 1,
        "metrics": {"pearson_r": 0.5},
        "model_execution": {
            "execution_mode": "benchmark_helpers",
            "requested_model_args": {"n_estimators": 100},
        },
        "prediction_sha256": "b" * 64,
    }
    result = {
        "config": copy.deepcopy(config),
        "dataset": dict(entry),
        "source_audit": {
            "files_sha256": {"oligogym/resources/pkg_dataset/fixture.csv.gz": "a" * 64}
        },
        "runs": [{**copy.deepcopy(run), "seed": seed} for seed in config["seeds"]],
        "mean_pearson_r": 0.5,
        "sample_sd_pearson_r": 0,
        "published_configuration_reference": {"n": 5, "mean": 0.52},
    }
    return result, entry, config


def test_complete_baseline_reports_actual_per_seed_values_and_tolerance():
    result, entry, config = fixture()
    summary = reporter.validate_baseline(result, entry, config)
    assert summary["per_seed_pearson"] == [0.5] * 5
    assert summary["within_tolerance"] is True
    config["reference_mean_pearson"] = 0.8
    result["config"] = copy.deepcopy(config)
    result["published_configuration_reference"]["mean"] = 0.8
    assert (
        reporter.validate_baseline(result, entry, config)["within_tolerance"] is False
    )


def test_missing_seed_and_overlapping_or_capped_rows_are_rejected():
    result, entry, config = fixture()
    result["runs"].pop()
    with pytest.raises(ValueError, match="all five"):
        reporter.validate_baseline(result, entry, config)
    result, entry, config = fixture()
    result["runs"][0]["test_ids"] = result["runs"][0]["train_ids"]
    with pytest.raises(ValueError, match="overlapping"):
        reporter.validate_baseline(result, entry, config)
    result, entry, config = fixture()
    result["runs"][0]["test_ids"] = []
    result["runs"][0]["test_rows"] = 0
    with pytest.raises(ValueError, match="capped"):
        reporter.validate_baseline(result, entry, config)


def test_forged_mean_and_wrong_observation_source_are_rejected():
    result, entry, config = fixture()
    result["mean_pearson_r"] = 0.9
    with pytest.raises(ValueError, match="Aggregate"):
        reporter.validate_baseline(result, entry, config)
    result, entry, config = fixture()
    result["runs"][0]["test_ids"] = ["wrong-source:1"]
    with pytest.raises(ValueError, match="source-qualified"):
        reporter.validate_baseline(result, entry, config)
