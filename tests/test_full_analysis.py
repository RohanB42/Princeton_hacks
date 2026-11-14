"""Comparison reporting rejects unmatched or incomplete experiment ledgers."""

import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "full_analysis", Path(__file__).parents[1] / "scripts/analyze_full_experiments.py"
)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def pair():
    metrics = {"pearson_r": 0.5, "rmse": 2.0, "mae": 1.0}
    run = {
        "dataset": {"metadata": {"selected_rows": 3, "source_rows": 3}},
        "split": {"train_ids": ["a", "b"], "test_ids": ["c"]},
        "config": {"max_labels": 2},
        "model": {"seed": 0},
        "initial_ids": ["a"],
        "full_pool_labels": 2,
        "full_pool_metrics": metrics,
        "execution": {"fit_order": "sample_id_lexicographic"},
        "checkpoints": [
            {"labels_used": 1, "acquired_ids": ["a"], "metrics": metrics},
            {"labels_used": 2, "acquired_ids": ["b"], "metrics": metrics},
        ],
    }
    return run, copy.deepcopy(run)


def test_pairing_and_actual_label_accounting():
    random, uncertainty = pair()
    analysis.validate_pair(random, uncertainty)
    uncertainty["model"]["seed"] = 1
    with pytest.raises(ValueError, match="paired on model"):
        analysis.validate_pair(random, uncertainty)
    random, uncertainty = pair()
    uncertainty["checkpoints"][0]["labels_used"] = 2
    with pytest.raises(ValueError, match="Checkpoint label counts"):
        analysis.validate_pair(random, uncertainty)


def test_superseded_fit_order_and_sampling_rejected():
    random, uncertainty = pair()
    random["execution"]["fit_order"] = "acquisition_order"
    with pytest.raises(ValueError, match="fit order"):
        analysis.validate_pair(random, uncertainty)
    random, uncertainty = pair()
    random["dataset"]["metadata"]["source_rows"] = 100
    uncertainty["dataset"]["metadata"]["source_rows"] = 100
    with pytest.raises(ValueError, match="sampled"):
        analysis.validate_pair(random, uncertainty)


def test_statistics_do_not_fill_undefined_correlations():
    assert analysis.statistics([None, 0.4])["n"] == 1
    assert analysis.statistics([None, 0.4])["sample_sd"] is None
    assert analysis.statistics([None])["mean"] is None
    random, _ = pair()
    assert analysis.efficiency(random, 0.03, 0.5)["labels"] == 1
    random["full_pool_metrics"] = {"pearson_r": -0.1}
    assert analysis.efficiency(random, 0.03, 0.5)["status"] == "reference_not_positive"


def test_single_checkpoint_area_is_distinct_from_undefined_pearson():
    run, _ = pair()
    run["normalized_pearson_aulc"] = None
    run["checkpoints"] = run["checkpoints"][:1]
    assert run["checkpoints"][0]["metrics"]["pearson_r"] == 0.5
    assert analysis.aulc_reason(run) == "single_checkpoint_no_budget_interval"
    run["checkpoints"] *= 2
    run["checkpoints"][0]["metrics"]["pearson_r"] = None
    assert analysis.aulc_reason(run) == "undefined_checkpoint_pearson"


def test_curve_tracks_contributing_seed_identity():
    runs = [
        {
            "config": {"seed": 0},
            "checkpoints": [
                {"labels_used": 32, "metrics": {"pearson_r": 0.1}},
            ],
        },
        {
            "config": {"seed": 1},
            "checkpoints": [
                {"labels_used": 50, "metrics": {"pearson_r": 0.3}},
                {"labels_used": 100, "metrics": {"pearson_r": 0.4}},
            ],
        },
    ]
    curve = analysis.curve(runs, "pearson_r")
    assert [p["valid_seeds"] for p in curve] == [[0], [1], [1]]
    assert all(p["sample_sd"] is None for p in curve)
