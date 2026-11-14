"""Execution optimizations must preserve selections and label boundaries."""

import json
import tomllib
from dataclasses import asdict
from pathlib import Path

import pytest

from oligo_engine.acquisition.random import RandomAcquisition
from oligo_engine.acquisition.uncertainty import UncertaintyAcquisition
from oligo_engine.collection import effective_budget
from oligo_engine.data.catalog import Catalog
from oligo_engine.data.splits import make_split
from oligo_engine.evaluation.runner import run_campaign
from oligo_engine.models.forest import HelmFeatureCache, HelmHashForest
from oligo_engine.reporting.artifacts import write_artifacts


def test_feature_cache_exactly_matches_uncached_predictions():
    np = pytest.importorskip("numpy")
    pytest.importorskip("sklearn")
    observations = Catalog().load("TLR7", max_rows=32).dataset.observations
    cache = HelmFeatureCache(observations, 64)
    labels = tuple(float(i) for i in range(8))
    cached = HelmHashForest(seed=0, n_estimators=8, n_features=64, feature_cache=cache)
    direct = HelmHashForest(seed=0, n_estimators=8, n_features=64)
    cached.fit(observations[:8], labels)
    direct.fit(observations[:8], labels)
    assert cached.predict(observations) == direct.predict(observations)
    np.testing.assert_allclose(
        [p.mean for p in direct.predict(observations)],
        direct.model.predict(
            direct.encoder.transform([r.sequence for r in observations])
        ),
        atol=1e-12,
    )
    assert not hasattr(cache, "labels")


def test_reference_cache_isolated_and_keyed_by_model_seed():
    pytest.importorskip("sklearn")
    loaded = Catalog().load("TLR7", max_rows=48)
    split = make_split(loaded.dataset, "sequence_group", seed=0)
    reference_cache = {}
    fits = []

    class Spy(HelmHashForest):
        def fit(self, rows, labels):
            fits.append(tuple(row.sample_id for row in rows))
            super().fit(rows, labels)

    artifacts = []
    for seed in (0, 0, 1):
        oracle, evaluator, reference = loaded.capabilities(split)
        artifacts.append(
            run_campaign(
                loaded.dataset,
                split,
                oracle,
                evaluator,
                lambda: Spy(seed=seed, n_estimators=4, n_features=64),
                RandomAcquisition(),
                effective_budget(
                    0,
                    {"initial_labels": 8, "batch_size": 4, "max_labels": 12},
                    len(split.train_ids),
                ),
                reference,
                reference_cache=reference_cache,
            )
        )
        assert len(reference.revealed_ids) == len(split.train_ids)
    assert [a.execution["full_reference_reused"] for a in artifacts] == [
        False,
        True,
        False,
    ]
    assert sum(len(ids) == len(split.train_ids) for ids in fits) == 2
    assert artifacts[0].checkpoints == artifacts[1].checkpoints
    assert artifacts[0].full_pool_metrics == artifacts[1].full_pool_metrics


def test_incremental_results_never_overwrite_different_runs(tmp_path):
    from oligo_engine.data.fixture import make_fixture
    from oligo_engine.models.fixture import FixtureNearestNeighbor

    dataset, split, oracle, evaluator = make_fixture()
    _, _, reference, _ = make_fixture()
    result = run_campaign(
        dataset,
        split,
        oracle,
        evaluator,
        FixtureNearestNeighbor,
        RandomAcquisition(),
        effective_budget(
            0,
            {"initial_labels": 8, "batch_size": 4, "max_labels": 12},
            len(split.train_ids),
        ),
        reference,
    )
    path = tmp_path / "run-seed-0.json"
    path.write_text(json.dumps(asdict(result)))
    write_artifacts((result,), tmp_path, allow_completed_runs=True)
    with pytest.raises(ValueError, match="previous runs"):
        write_artifacts((result,), tmp_path, allow_completed_runs=True)


def test_full_matrix_plan_is_uncapped_and_five_seed():
    plan = tomllib.loads(Path("configs/all-datasets-full.toml").read_text())
    assert len(plan["dataset"]) == len(set(plan["dataset"])) == 12
    assert plan["seeds"] == list(range(5))
    assert "max_rows" not in plan
    assert plan["policies"] == ["random", "uncertainty"]
    assert plan["budget"] == {"initial_labels": 50, "batch_size": 50, "max_labels": 500}


def test_full_pool_models_match_regardless_of_acquisition_order():
    pytest.importorskip("sklearn")
    loaded = Catalog().load("TLR7", max_rows=32)
    split = make_split(loaded.dataset, "sequence_group", seed=0)
    artifacts = []
    for policy in (RandomAcquisition(), UncertaintyAcquisition()):
        oracle, evaluator, reference = loaded.capabilities(split)
        artifacts.append(
            run_campaign(
                loaded.dataset,
                split,
                oracle,
                evaluator,
                lambda: HelmHashForest(seed=0, n_estimators=8, n_features=64),
                policy,
                effective_budget(
                    0,
                    {"initial_labels": 8, "batch_size": 8, "max_labels": 100},
                    len(split.train_ids),
                ),
                reference,
            )
        )
    for artifact in artifacts:
        assert artifact.checkpoints[-1].metrics == artifact.full_pool_metrics
        assert artifact.execution["fit_order"] == "sample_id_lexicographic"
    assert artifacts[0].checkpoints[-1].metrics == artifacts[1].checkpoints[-1].metrics
