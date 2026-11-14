"""Adversarial checks for reveal/evaluation boundaries and replay accounting."""

import json
import subprocess
import sys
from dataclasses import asdict, replace

import pytest

from oligo_engine.acquisition.random import RandomAcquisition
from oligo_engine.contracts import Prediction, RunConfig
from oligo_engine.data.fixture import make_fixture
from oligo_engine.data.oracle import LabelOracle
from oligo_engine.evaluation.metrics import HeldOutEvaluator, regression_metrics
from oligo_engine.evaluation.runner import run_campaign, validate_predictions
from oligo_engine.models.fixture import FixtureNearestNeighbor
from oligo_engine.reporting.artifacts import write_artifacts


def run(seed=0, policy=None, evaluator=None, factory=FixtureNearestNeighbor):
    dataset, split, oracle, default_evaluator = make_fixture()
    _, _, reference, _ = make_fixture()
    return run_campaign(
        dataset,
        split,
        oracle,
        evaluator or default_evaluator,
        factory,
        policy or RandomAcquisition(),
        RunConfig(seed, 8, 7, 32),
        reference,
    )


def decisions(artifact):
    return [c.acquired_ids for c in artifact.checkpoints]


def test_budget_partial_batch_and_deterministic_replay():
    first, second = run(), run()
    assert decisions(first) == decisions(second)
    assert [c.labels_used for c in first.checkpoints] == [8, 15, 22, 29, 32]
    assert [len(c.acquired_ids) for c in first.checkpoints] == [8, 7, 7, 7, 3]
    acquired = [i for c in first.checkpoints for i in c.acquired_ids]
    assert len(acquired) == len(set(acquired)) == 32
    assert not set(acquired) & set(first.split.test_ids)
    assert first.full_pool_labels == 36
    assert [c.metrics for c in first.checkpoints] == [
        c.metrics for c in second.checkpoints
    ]
    assert first.normalized_pearson_aulc is not None
    assert first.provenance == "synthetic"


def test_oracle_denies_test_unrevealed_and_repeated_ids_atomically():
    _, split, oracle, _ = make_fixture()
    train, test = split.train_ids[0], split.test_ids[0]
    with pytest.raises(ValueError, match="Unrevealed"):
        oracle.acquired_labels((train,))
    for batch in ((train, test), (train, train), ()):
        with pytest.raises(ValueError):
            oracle.reveal(batch)
        assert oracle.revealed_ids == ()
    oracle.reveal((train,))
    with pytest.raises(ValueError):
        oracle.reveal((train,))


class PredictivePolicy(RandomAcquisition):
    """Reads predictions so poisoned-label test exercises model state too."""

    def choose(self, eligible, labeled, budget, rng, predictor):
        predictions = predictor.predict(eligible)
        indices = sorted(range(len(eligible)), key=lambda i: predictions[i].mean)
        return tuple(eligible[i].sample_id for i in indices[:budget])


def test_poisoned_test_labels_change_only_reporting():
    _, split, _, _ = make_fixture()
    poisoned = HeldOutEvaluator(
        {
            sample_id: float(index * 1234)
            for index, sample_id in enumerate(split.test_ids)
        },
        split.test_ids,
    )
    fits, prediction_means = [], []

    class Spy(FixtureNearestNeighbor):
        def fit(self, observations, labels):
            fits.append(tuple(r.sample_id for r in observations))
            assert set(fits[-1]) <= set(split.train_ids)
            super().fit(observations, labels)

        def predict(self, observations):
            result = super().predict(observations)
            prediction_means.append(tuple(p.mean for p in result))
            return result

    first = run(policy=PredictivePolicy(), factory=Spy)
    expected_predictions = list(prediction_means)
    prediction_means.clear()
    second = run(policy=PredictivePolicy(), evaluator=poisoned, factory=Spy)
    assert decisions(first) == decisions(second)
    assert expected_predictions == prediction_means
    assert first.checkpoints[-1].metrics != second.checkpoints[-1].metrics
    for j in (0, 6):
        assert [len(ids) for ids in fits[j : j + 6]] == [8, 15, 22, 29, 32, 36]
    expected = set()
    for ids, point in zip(fits[:5], first.checkpoints, strict=True):
        expected.update(point.acquired_ids)
        assert set(ids) == expected


def test_unrevealed_labels_cannot_change_first_decision():
    dataset, split, oracle, evaluator = make_fixture()
    _, _, reference, _ = make_fixture()
    first = run(policy=PredictivePolicy())
    initial = set(first.initial_ids)
    original_values = oracle.reveal(split.train_ids)
    poisoned_values = {
        i: value if i in initial else 1e6
        for i, value in zip(split.train_ids, original_values, strict=True)
    }
    second = run_campaign(
        dataset,
        split,
        LabelOracle(poisoned_values, split.train_ids),
        evaluator,
        FixtureNearestNeighbor,
        PredictivePolicy(),
        RunConfig(0, 8, 7, 32),
        reference,
    )
    assert decisions(first)[:2] == decisions(second)[:2]


@pytest.mark.parametrize("kind", ["duplicate", "held_out", "too_many", "acquired"])
def test_runner_rejects_bad_policy(kind):
    _, split, _, _ = make_fixture()

    class Invalid(RandomAcquisition):
        def choose(self, eligible, labeled, budget, rng, predictor):
            if kind == "duplicate":
                return (eligible[0].sample_id,) * budget
            if kind == "held_out":
                return split.test_ids[:budget]
            if kind == "acquired":
                return tuple(row.sample_id for row in labeled[:budget])
            return tuple(row.sample_id for row in eligible[: budget + 1])

    with pytest.raises(ValueError, match="unique eligible"):
        run(policy=Invalid())


def test_evaluation_happens_after_acquisition_and_reference_fit():
    dataset, split, oracle, evaluator = make_fixture()
    _, _, reference, _ = make_fixture()

    class Deferred:
        ids = evaluator.ids

        def score(self, predictions):
            assert len(oracle.revealed_ids) == 32
            assert len(reference.revealed_ids) == 36
            return evaluator.score(predictions)

    run_campaign(
        dataset,
        split,
        oracle,
        Deferred(),
        FixtureNearestNeighbor,
        RandomAcquisition(),
        RunConfig(0, 8, 7, 32),
        reference,
    )


def test_invalid_partitions_and_real_data_gate():
    dataset, split, oracle, evaluator = make_fixture()
    _, _, reference, _ = make_fixture()
    with pytest.raises(ValueError, match="overlap"):
        replace(split, test_ids=split.test_ids + split.train_ids[:1]).validate(dataset)
    with pytest.raises(ValueError, match="Target groups"):
        replace(split, strategy="target").validate(dataset)
    duplicate = replace(
        dataset.observations[-1], sequence=dataset.observations[0].sequence
    )
    with pytest.raises(ValueError, match="duplicates cross"):
        split.validate(
            replace(dataset, observations=dataset.observations[:-1] + (duplicate,))
        )
    with pytest.raises(ValueError, match="Gate 1"):
        run_campaign(
            replace(dataset, provenance="measured"),
            split,
            oracle,
            evaluator,
            FixtureNearestNeighbor,
            RandomAcquisition(),
            RunConfig(0, 8, 7, 32),
            reference,
        )


@pytest.mark.parametrize("sizes", [(0, 7, 32), (8, -1, 32), (33, 7, 32), (8.0, 7, 32)])
def test_invalid_budgets(sizes):
    with pytest.raises(ValueError):
        RunConfig(0, *sizes)


def test_over_budget_and_wrong_oracle_pool():
    dataset, split, oracle, evaluator = make_fixture()
    _, _, reference, _ = make_fixture()
    with pytest.raises(ValueError, match="exceeds eligible"):
        run_campaign(
            dataset,
            split,
            oracle,
            evaluator,
            FixtureNearestNeighbor,
            RandomAcquisition(),
            RunConfig(0, 8, 7, 37),
            reference,
        )
    bad = LabelOracle({"unknown": 1.0}, ("unknown",))
    with pytest.raises(ValueError, match="manifest training"):
        run_campaign(
            dataset,
            split,
            bad,
            evaluator,
            FixtureNearestNeighbor,
            RandomAcquisition(),
            RunConfig(0, 8, 7, 32),
            reference,
        )


def test_metrics_and_undefined_values():
    m = regression_metrics((1.0, 2.0, 3.0), (2.0, 4.0, 6.0))
    assert m.pearson_r == pytest.approx(1)
    assert m.mae == 2
    assert m.rmse == pytest.approx((14 / 3) ** 0.5)
    constant = regression_metrics((1.0, 2.0), (3.0, 3.0))
    assert constant.pearson_r is None
    assert constant.pearson_undefined_reason == "constant_truth_or_prediction"
    with pytest.raises(ValueError):
        regression_metrics((float("nan"),), (1.0,))
    for predictions in (
        (Prediction(float("nan")),),
        (Prediction(1.0, 0.2),),
        (Prediction(1.0, -1.0, "sd"),),
    ):
        with pytest.raises(ValueError):
            validate_predictions(predictions, 1)


def test_artifacts_are_strict_json_and_report_seed_counts(tmp_path):
    runs = tuple(run(seed) for seed in range(5))
    write_artifacts(runs, tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["seeds"] == list(range(5))
    assert summary["checkpoints"][-1]["pearson_r"]["n"] == 5
    assert "not confidence interval" in summary["band_method"]
    artifact = json.loads((tmp_path / "run-seed-0.json").read_text())
    assert artifact["provenance"] == "synthetic"
    assert "labels" not in artifact
    json.dumps(asdict(runs[0]), allow_nan=False)
    with pytest.raises(ValueError, match="previous runs"):
        write_artifacts(runs, tmp_path)


def test_one_command_fixture(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "oligo_engine", "--output", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "5 SYNTHETIC" in result.stdout
    assert len(list(tmp_path.glob("run-seed-*.json"))) == 5
