"""Leakage, pairing and accounting tests with explicit synthetic representations."""

import copy
from dataclasses import replace

import numpy as np
import pytest

from oligo_engine.data.catalog import LoadedDataset
from oligo_engine.data.fixture import make_fixture
from oligo_engine.models.rnafm_heads import CachedRepresentation, RepresentationRidge
from oligo_engine.reporting.rnafm import audit_seed, aulc, threshold
from oligo_engine.rnafm_study import nested_order, run_seed


def fixture():
    dataset, split, oracle, evaluator = make_fixture()
    values = oracle.reveal(split.train_ids)
    # Synthetic truth values are only exposed to capability owner here.
    labels = dict(zip(split.train_ids, values, strict=True))
    labels.update({i: float(j) for j, i in enumerate(split.test_ids)})
    loaded = LoadedDataset(dataset, labels)
    matrix = np.asarray([row.features for row in dataset.observations])
    reps = {
        "onehot": CachedRepresentation(dataset.observations, matrix, {"fixture": True}),
        "frozen_rnafm": CachedRepresentation(
            dataset.observations, matrix.copy(), {"fixture": True}
        ),
    }
    return dataset, split, labels, loaded, reps


def test_cache_identity_copies_values_and_rejects_changed_records():
    dataset, _, _, _, reps = fixture()
    row = dataset.observations[0]
    x = reps["onehot"].encode((row,))
    x[:] = 1000
    assert not np.array_equal(x, reps["onehot"].encode((row,)))
    with pytest.raises(ValueError, match="changed"):
        reps["onehot"].encode((replace(row, sequence="other"),))
    with pytest.raises(ValueError):
        CachedRepresentation(dataset.observations, np.zeros((2, 3)), {})


def test_nested_order_reproducible_and_training_only():
    _, split, _, _, _ = fixture()
    order = nested_order(split, 0, 8)
    assert order == nested_order(split, 0, 8)
    assert set(order) == set(split.train_ids)
    assert len(order) == len(set(order))
    assert not set(order) & set(split.test_ids)


def test_head_scaler_fit_scope_and_held_out_features_cannot_change_alpha():
    dataset, split, _, _, reps = fixture()
    by_id = {row.sample_id: row for row in dataset.observations}
    rows = tuple(by_id[i] for i in split.train_ids[:12])
    labels = tuple(float(i) for i in range(12))
    first = RepresentationRidge(reps["onehot"], 0)
    with pytest.raises(RuntimeError):
        first.predict(rows)
    first.fit(rows, labels)
    expected_mean = reps["onehot"].encode(rows).mean(axis=0)
    np.testing.assert_allclose(first._scaler.mean_, expected_mean)
    matrix = reps["onehot"].encode(dataset.observations)
    train_set = {row.sample_id for row in rows}
    for i, row in enumerate(dataset.observations):
        if row.sample_id not in train_set:
            matrix[i] = 1e9
    poisoned = CachedRepresentation(dataset.observations, matrix, {"fixture": True})
    second = RepresentationRidge(poisoned, 0)
    second.fit(rows, labels)
    assert first.fit_record == second.fit_record
    assert first.predict(rows) == second.predict(rows)


def test_prediction_study_pairing_and_poisoned_label_boundaries():
    dataset, split, labels, loaded, reps = fixture()
    first = run_seed(loaded, split, reps, (8, 16, 24), (1.0, 10.0), 3)
    audit_seed(first, [8, 16, 24], list(reps))
    poisoned = {i: y if i in split.train_ids else y + 1e5 for i, y in labels.items()}
    second = run_seed(
        LoadedDataset(dataset, poisoned), split, reps, (8, 16, 24), (1.0, 10.0), 3
    )
    for name in reps:
        a = first["representations"][name]
        b = second["representations"][name]
        for left, right in zip(a["checkpoints"], b["checkpoints"], strict=True):
            assert left["fit"] == right["fit"]
            assert left["acquired_ids"] == right["acquired_ids"]
            assert left["metrics"]["rmse"] != right["metrics"]["rmse"]
    initial = set(first["initial_ids"])
    hidden = {
        i: y if i in initial or i in split.test_ids else y * 100
        for i, y in labels.items()
    }
    third = run_seed(
        LoadedDataset(dataset, hidden), split, reps, (8, 16, 24), (1.0, 10.0), 3
    )
    for name in reps:
        assert (
            first["representations"][name]["checkpoints"][0]["fit"]
            == third["representations"][name]["checkpoints"][0]["fit"]
        )
        assert (
            first["representations"][name]["checkpoints"][0]["metrics"]
            == third["representations"][name]["checkpoints"][0]["metrics"]
        )


def test_evaluation_waits_until_all_representation_fits(monkeypatch):
    from oligo_engine import rnafm_study

    _, split, _, loaded, reps = fixture()
    original = loaded.capabilities
    fits = []

    class Spy(RepresentationRidge):
        def fit(self, observations, labels):
            fits.append(tuple(row.sample_id for row in observations))
            return super().fit(observations, labels)

    class Deferred:
        def __init__(self, evaluator):
            self.evaluator = evaluator

        def score(self, predictions):
            assert len(fits) == 2 * (3 + 1)
            return self.evaluator.score(predictions)

    def capabilities(partition):
        oracle, evaluator, reference = original(partition)
        return oracle, Deferred(evaluator), reference

    monkeypatch.setattr(loaded, "capabilities", capabilities)
    monkeypatch.setattr(rnafm_study, "RepresentationRidge", Spy)
    run_seed(loaded, split, reps, (8, 16, 24), (1.0,), 3)


def test_report_rejects_unmatched_pools_and_tuning_leaks():
    _, split, _, loaded, reps = fixture()
    result = run_seed(loaded, split, reps, (8, 16, 24), (1.0,), 3)
    changed = copy.deepcopy(result)
    changed["representations"]["frozen_rnafm"]["checkpoints"][0][
        "acquired_ids"
    ].reverse()
    with pytest.raises(ValueError, match="identical"):
        audit_seed(changed, [8, 16, 24], list(reps))
    changed = copy.deepcopy(result)
    changed["representations"]["onehot"]["checkpoints"][0]["fit"]["folds"][0][
        "train_ids"
    ].append(split.test_ids[0])
    with pytest.raises(ValueError, match="boundary"):
        audit_seed(changed, [8, 16, 24], list(reps))


def test_threshold_is_shared_absolute_and_censoring_is_explicit():
    points = [
        {"labels_used": 50, "metrics": {"pearson_r": 0.3}},
        {"labels_used": 100, "metrics": {"pearson_r": 0.5}},
    ]
    run = {
        "checkpoints": points,
        "full_reference": {"labels_used": 1500, "metrics": {"pearson_r": 0.61}},
    }
    assert threshold(run, 0.6)["status"] == "reached_at_full_reference"
    assert threshold(run, 0.5)["labels"] == 100
    assert threshold(run, 0.7)["labels"] is None
    assert aulc(points) == pytest.approx(0.4)
    points[0]["metrics"]["pearson_r"] = None
    assert aulc(points) is None


def test_geometry_smoke_keeps_predictor_fixed_and_audits_divergent_selection(
    tmp_path, monkeypatch
):
    import json
    from pathlib import Path

    from oligo_engine import rnafm_study as module
    from oligo_engine.contracts import Dataset, Observation, SplitManifest

    rng = np.random.default_rng(0)
    rows = tuple(
        Observation(str(i), f"sequence{i}", str(i % 10), "siRNA", "", "fixture")
        for i in range(120)
    )
    dataset = Dataset(
        rows, "Huesken", "fixture", "fixture_hash", "synthetic", "synthetic"
    )
    split = SplitManifest(
        "nucleobase",
        300,
        tuple(str(i) for i in range(110)),
        tuple(str(i) for i in range(110, 120)),
    )
    labels = {str(i): float(i % 17) for i in range(120)}
    loaded = LoadedDataset(dataset, labels)
    reps = {
        name: CachedRepresentation(rows, rng.normal(size=(120, 4)), {"fixture": name})
        for name in ("onehot", "frozen_rnafm", "random_rnafm")
    }

    class Catalog:
        def load(self, name):
            return loaded

        def resolve(self, name):
            return {"data_file": "fixture"}

    monkeypatch.setattr(module, "Catalog", Catalog)
    monkeypatch.setattr(
        module,
        "audit_checkout",
        lambda checkout: {
            "files_sha256": {"oligogym/resources/pkg_dataset/fixture": "fixture_hash"}
        },
    )
    monkeypatch.setattr(module, "official_split", lambda *args: split)
    monkeypatch.setattr(module, "materialize_representations", lambda *args: reps)
    monkeypatch.setattr(module, "source_hashes", lambda: {})
    root = tmp_path / "output"
    module.run_geometry_study(
        Path("configs/rnafm-geometry.toml"),
        tmp_path,
        tmp_path / "unused",
        tmp_path / "cache",
        root,
        smoke=True,
    )
    report = json.loads((root / "report.json").read_text())
    assert len(report["paired"]) == 4
    assert report["fixed_predictor"] == "onehot plus acquired-only tuned Ridge"
    assert report["interval"] == [50, 100]
    runs = [json.loads(p.read_text()) for p in root.glob("*-300.json")]
    assert all(run["model"] == runs[0]["model"] for run in runs)
    assert all(run["full_pool_metrics"] == runs[0]["full_pool_metrics"] for run in runs)
    assert len({tuple(run["checkpoints"][1]["acquired_ids"]) for run in runs}) > 1
