"""Frozen split/selection protocol and final reporting integrity checks."""

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from oligo_engine.contracts import Dataset, Observation, SplitManifest
from oligo_engine.huesken_learning import (
    load_config,
    make_diversity,
    verify_previous_splits,
)

spec = importlib.util.spec_from_file_location(
    "huesken_report",
    Path(__file__).parents[1] / "scripts/report_huesken_learning.py",
)
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


def config():
    return load_config(Path(__file__).parents[1] / "configs/huesken-learning.toml")[0]


def test_frozen_config_and_baseline_hash_are_verified(tmp_path):
    value, baseline = load_config(
        Path(__file__).parents[1] / "configs/huesken-learning.toml"
    )
    assert value["seeds"] == [0, 1, 2, 3, 4]
    assert baseline["model"] == {
        "name": "CNN",
        "depth": 1,
        "hidden_dim": 64,
        "kernel_size": 3,
        "pooling_operation": "max",
    }
    path = tmp_path / "altered.toml"
    text = (Path(__file__).parents[1] / "configs/huesken-learning.toml").read_text()
    path.write_text(text.replace("max_labels = 500", "max_labels = 450"))
    with pytest.raises(ValueError, match="frozen"):
        load_config(path)
    path.write_text(
        text.replace(
            "threshold_is_reporting_only = true", "threshold_is_reporting_only = false"
        )
    )
    with pytest.raises(ValueError, match="Analysis"):
        load_config(path)
    path.write_text(text.replace("59e79e4b83", "0000000000"))
    with pytest.raises(ValueError, match="hash"):
        load_config(path)


def test_diversity_embedding_fits_pool_only_without_evaluation_sequences(monkeypatch):
    seen = []
    features = ModuleType("oligogym.features")

    class Encoder:
        def __init__(self, **kwargs):
            assert kwargs == {
                "k": [1, 2, 3],
                "modification_abundance": False,
                "strands": None,
            }

        def fit_transform(self, sequences):
            seen.extend(sequences)
            return np.eye(len(sequences))

    features.KMersCounts = Encoder
    package = ModuleType("oligogym")
    package.features = features
    monkeypatch.setitem(sys.modules, "oligogym", package)
    monkeypatch.setitem(sys.modules, "oligogym.features", features)
    rows = tuple(
        Observation(str(i), seq, "target", "synthetic", "toy", "toy")
        for i, seq in enumerate(("AAAA", "CCCC", "GGGG"))
    )
    dataset = Dataset(rows, "toy", "toy", "toy", "toy", "synthetic")
    split = SplitManifest("nucleobase", 0, ("0", "1"), ("2",))
    policy = make_diversity(dataset, split, config()["diversity"])
    assert seen == ["AAAA", "CCCC"]
    assert policy.config["name"] == "diversity"


def test_baseline_split_comparison_preserves_order_and_rejects_differences(tmp_path):
    split = SplitManifest("nucleobase", 0, ("a", "b"), ("c",))
    path = tmp_path / "baseline.json"
    value = {
        "source_audit": {"source_revision": "97f5b9f58d9e445a8ecb0218037af7465c3708c0"},
        "runs": [{"seed": 0, "train_ids": ["a", "b"], "test_ids": ["c"]}],
    }
    path.write_text(json.dumps(value))
    assert (
        verify_previous_splits((split,), path)["status"]
        == "exact_ordered_split_ids_match"
    )
    value["runs"][0]["train_ids"].reverse()
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="split IDs"):
        verify_previous_splits((split,), path)


def pair():
    train = [f"id-{i}" for i in range(2300)]
    test = [f"id-{i}" for i in range(2300, 2431)]
    run = {
        "dataset": {"name": "synthetic schema fixture"},
        "split": {
            "strategy": "nucleobase",
            "seed": 0,
            "train_ids": train,
            "test_ids": test,
        },
        "config": {"seed": 0, "purpose": "diagnostic"},
        "provenance": "measured",
        "model": {"name": "upstream_one_hot_cnn"},
        "policy": {"name": "random"},
        "initial_ids": train[:50],
        "checkpoints": [
            {
                "labels_used": 50,
                "acquired_ids": train[:50],
                "metrics": {"pearson_r": 0.4},
            },
            {
                "labels_used": 100,
                "acquired_ids": train[50:100],
                "metrics": {"pearson_r": 0.5},
            },
        ],
        "full_pool_labels": len(train),
        "full_pool_metrics": {"pearson_r": 0.6},
        "normalized_pearson_aulc": 0.45,
        "execution": {
            "fit_order": "sample_id_lexicographic",
            "full_reference_reused": False,
        },
    }
    other = copy.deepcopy(run)
    other["policy"]["name"] = "diversity"
    other["execution"]["full_reference_reused"] = True
    return run, other


def test_reporting_rejects_unpaired_ids_missing_budgets_and_bad_reference():
    left, right = pair()
    reporter.validate_pair(left, right, [50, 100])
    right["initial_ids"].reverse()
    with pytest.raises(ValueError, match="initial_ids"):
        reporter.validate_pair(left, right, [50, 100])
    left, right = pair()
    right["checkpoints"].pop()
    with pytest.raises(ValueError, match="checkpoints"):
        reporter.validate_pair(left, right, [50, 100])
    left, right = pair()
    right["full_pool_metrics"]["pearson_r"] = 0.9
    with pytest.raises(ValueError, match="reference"):
        reporter.validate_pair(left, right, [50, 100])
    left, right = pair()
    left["checkpoints"][1]["acquired_ids"][0] = left["split"]["test_ids"][0]
    with pytest.raises(ValueError, match="held-out"):
        reporter.validate_pair(left, right, [50, 100])


def test_threshold_reporting_and_undefined_statistics_are_not_filled():
    run, _ = pair()
    assert reporter.efficiency(run, 0.03, 0.5)["status"] == "not_reached"
    run["checkpoints"][1]["metrics"]["pearson_r"] = 0.59
    assert reporter.efficiency(run, 0.03, 0.5)["labels"] == 100
    run["full_pool_metrics"]["pearson_r"] = None
    assert reporter.efficiency(run, 0.03, 0.5)["labels"] is None
    assert reporter.statistics([None, 0.5]) == {"n": 1, "mean": 0.5, "sample_sd": None}
    assert reporter.statistics([None])["mean"] is None


def test_reporting_recomputes_aulc_instead_of_trusting_a_favorable_header():
    left, right = pair()
    right["normalized_pearson_aulc"] = 0.9
    with pytest.raises(ValueError, match="AULC"):
        reporter.validate_pair(left, right, [50, 100])
