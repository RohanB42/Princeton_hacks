"""Seed-worker resumption preserves artifacts and rejects different science."""

import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from oligo_engine.acquisition.random import RandomAcquisition
from oligo_engine.contracts import RunConfig
from oligo_engine.data.fixture import make_fixture
from oligo_engine.evaluation.runner import run_campaign
from oligo_engine.models.fixture import FixtureNearestNeighbor

spec = importlib.util.spec_from_file_location(
    "worker_merge", Path(__file__).parents[1] / "scripts/merge_seed_workers.py"
)
worker_merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker_merge)


def test_run_round_trip_preserves_experiment_contents(tmp_path):
    dataset, split, oracle, evaluator = make_fixture()
    _, _, reference, _ = make_fixture()
    run = run_campaign(
        dataset,
        split,
        oracle,
        evaluator,
        FixtureNearestNeighbor,
        RandomAcquisition(),
        RunConfig(0, 8, 4, 12),
        reference,
    )
    path = tmp_path / "run.json"
    path.write_text(json.dumps(asdict(run)))
    assert worker_merge.read_run(path) == run


def test_worker_merge_rejects_model_changes_before_copying(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    suite = {
        "config": {"seeds": [0], "model": {"n_estimators": 100}},
        "datasets": [{"name": "example"}],
    }
    (parent / "suite.json").write_text(json.dumps(suite))
    child = tmp_path / "workers" / "seed-0"
    child.mkdir(parents=True)
    (child / "suite.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "config": {"seeds": [0], "model": {"n_estimators": 10}},
            }
        )
    )
    with pytest.raises(ValueError, match="science settings differ: model"):
        worker_merge.merge(parent, tmp_path / "workers", "example")
    assert list(parent.iterdir()) == [parent / "suite.json"]
