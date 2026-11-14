"""Acquisition and schedule invariants for the GP development study."""

from dataclasses import replace
from random import Random

import numpy as np
import pytest

from oligo_engine.acquisition.hybrid import HybridAcquisition
from oligo_engine.acquisition.pool_diversity import DiversityAcquisition
from oligo_engine.acquisition.random import RandomAcquisition
from oligo_engine.active_learning import schedule
from oligo_engine.contracts import Prediction, RunConfig
from oligo_engine.data.fixture import make_fixture
from oligo_engine.data.oracle import LabelOracle
from oligo_engine.evaluation.metrics import HeldOutEvaluator
from oligo_engine.evaluation.runner import run_campaign
from oligo_engine.models.fixture import FixtureNearestNeighbor
from oligo_engine.reporting.active_learning import area, threshold


def test_hybrid_combines_uncertainty_and_coverage_without_duplicates():
    dataset, _, _, _ = make_fixture()
    rows = dataset.observations[:6]
    # Candidate 1 is uncertain, candidate 2 is redundant with it, candidate 3 far.
    vectors = np.array([[1, 0], [0, 1], [0, 1], [-1, 0], [1, 0.1], [1, 0.2]])
    policy = HybridAcquisition(DiversityAcquisition(rows, vectors, {}))

    class Scores:
        def predict(self, observations):
            return tuple(
                Prediction(0, 100 if row == rows[1] else 1, "test_sd")
                for row in observations
            )

    chosen = policy.choose(rows[1:], rows[:1], 2, Random(0), Scores())
    assert chosen == (rows[1].sample_id, rows[3].sample_id)
    for size in (1, 3, 5):
        selected = policy.choose(rows[1:], rows[:1], size, Random(0), Scores())
        assert len(set(selected)) == size
        assert set(selected) <= {row.sample_id for row in rows[1:]}


def scheduled_run(checkpoints=(8, 15, 36), poison=False, hidden_poison=False):
    dataset, split, oracle, evaluator = make_fixture()
    _, _, reference, _ = make_fixture()
    records = tuple(
        row for row in dataset.observations if row.sample_id in split.train_ids
    )
    vectors = np.array([row.features for row in records])
    policy = HybridAcquisition(DiversityAcquisition(records, vectors, {}))

    class Predictor(FixtureNearestNeighbor):
        def predict(self, observations):
            return tuple(
                replace(p, uncertainty=abs(p.mean), uncertainty_type="test")
                for p in super().predict(observations)
            )

    if poison:
        evaluator = HeldOutEvaluator(
            {i: float(j * 1000) for j, i in enumerate(split.test_ids)}, split.test_ids
        )
    if hidden_poison:
        initial = set(Random(0).sample(list(split.train_ids), 8))
        labels = oracle.reveal(split.train_ids)
        oracle = LabelOracle(
            {i: y if i in initial else 1e6 for i, y in zip(split.train_ids, labels)},
            split.train_ids,
        )
    return run_campaign(
        dataset,
        split,
        oracle,
        evaluator,
        Predictor,
        policy,
        RunConfig(0, 8, 7, 36),
        reference,
        checkpoint_labels=checkpoints,
    )


def test_schedule_and_hybrid_label_isolation():
    first = scheduled_run()
    poisoned = scheduled_run(poison=True)
    hidden = scheduled_run(hidden_poison=True)
    assert [p.labels_used for p in first.checkpoints] == [8, 15, 36]
    assert [p.acquired_ids for p in first.checkpoints] == [
        p.acquired_ids for p in poisoned.checkpoints
    ]
    assert [p.acquired_ids for p in first.checkpoints[:2]] == [
        p.acquired_ids for p in hidden.checkpoints[:2]
    ]
    assert first.checkpoints[-1].metrics == first.full_pool_metrics
    assert first.checkpoints[-1].metrics != poisoned.checkpoints[-1].metrics


@pytest.mark.parametrize("checkpoints", [(), (8, 8, 36), (8, 36, 15), (7, 36), (8, 35)])
def test_bad_schedule_rejected_before_reveals(checkpoints):
    dataset, split, oracle, evaluator = make_fixture()
    _, _, reference, _ = make_fixture()
    with pytest.raises(ValueError, match="schedule"):
        run_campaign(
            dataset,
            split,
            oracle,
            evaluator,
            FixtureNearestNeighbor,
            RandomAcquisition(),
            RunConfig(0, 8, 7, 36),
            reference,
            checkpoint_labels=checkpoints,
        )
    assert oracle.revealed_ids == ()


def test_budget_generation_and_censored_reporting():
    assert schedule(1719)[-3:] == (1250, 1500, 1719)
    assert schedule(1100)[-1] == 1100
    assert schedule(1719, True) == (50, 100)
    with pytest.raises(ValueError):
        schedule(999)
    points = [
        {"labels_used": 50, "metrics": {"pearson_r": 0.2}},
        {"labels_used": 100, "metrics": {"pearson_r": 0.4}},
    ]
    assert area(points, 100) == pytest.approx(0.3)
    assert area(points, 1000) is None
    run = {"checkpoints": points, "full_pool_metrics": {"pearson_r": 0.6}}
    assert threshold(run)["status"] == "not_reached"
    assert threshold(run)["labels"] is None
    run["full_pool_metrics"]["pearson_r"] = 0.01
    assert threshold(run)["labels"] is None


def test_kernel_selection_never_fits_on_inner_validation(monkeypatch):
    from oligo_engine import active_learning as module
    from oligo_engine.contracts import Observation

    rows = tuple(
        Observation(str(i), str(i), str(i % 5), "siRNA", "", "") for i in range(50)
    )
    labels = tuple(float(i) for i in range(50))
    calls = []

    class Spy:
        def __init__(self, *args):
            pass

        def fit(self, observations, values):
            self.ids = {row.sample_id for row in observations}
            assert values == tuple(float(row.sample_id) for row in observations)
            calls.append(self.ids)

        def predict(self, observations):
            assert not self.ids & {row.sample_id for row in observations}
            return tuple(Prediction(float(row.sample_id)) for row in observations)

    monkeypatch.setattr(module, "OneHotGaussianProcess", Spy)
    result = module.select_kernel(rows, labels, 0)
    assert len(calls) == len(module.KERNEL_GRID) * 3
    assert set(result["initial_ids"]) == {str(i) for i in range(50)}
    assert result["selected"]["family"] == module.KERNEL_GRID[0][0]
    for fold in result["folds"]:
        train, valid = set(fold["train_ids"]), set(fold["validation_ids"])
        assert train | valid == set(result["initial_ids"])
        assert not train & valid
