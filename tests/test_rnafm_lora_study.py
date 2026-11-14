"""Budget, validation and deferred-scoring boundaries in adaptation comparison."""

import copy

import numpy as np
import pytest

from oligo_engine.contracts import Dataset, Observation, Prediction, SplitManifest
from oligo_engine.data.catalog import LoadedDataset
from oligo_engine.models.rnafm_heads import CachedRepresentation
from oligo_engine.reporting.rnafm_lora_study import audit_run
from oligo_engine.rnafm_lora_study import fit_selected_neural, run_seed


class Spy:
    def __init__(self, epochs=1):
        self.epochs = epochs
        self.config = {"name": "synthetic_spy", "epochs": epochs}

    def fit(self, records, labels):
        self.mean = float(np.mean(labels))
        self.fit_audit = {
            "train_ids": [r.sample_id for r in records],
            "base_unchanged": True,
            "adapter_changed": True,
        }

    def predict(self, records):
        return tuple(
            Prediction(self.mean + float(r.features[0]) * 0.5) for r in records
        )


def fixture():
    rows = tuple(
        Observation(
            str(i), f"SEQ{i}", str(i % 5), "siRNA", "", "", (float(i), float(i % 3))
        )
        for i in range(40)
    )
    dataset = Dataset(rows, "fixture", "test", "hash", "efficacy", "synthetic")
    split = SplitManifest(
        "fixture",
        400,
        tuple(str(i) for i in range(30)),
        tuple(str(i) for i in range(30, 40)),
    )
    labels = {str(i): float(i) + np.sin(i) for i in range(40)}
    reps = {
        name: CachedRepresentation(
            rows, np.array([r.features for r in rows]), {"name": name}
        )
        for name in ("onehot", "frozen_rnafm")
    }
    cfg = {
        "budgets": [10, 20],
        "arms": ["onehot_ridge", "frozen_ridge", "frozen_head", "lora_head"],
        "ridge_alphas": [0.1, 1.0],
        "ridge_folds": 3,
        "inner_validation_fraction": 0.2,
        "epoch_candidates": [1, 2],
    }
    return dataset, split, labels, reps, cfg


def execute(labels, cls=LoadedDataset):
    dataset, split, _, reps, cfg = fixture()
    fits = []

    class LoggingSpy(Spy):
        def fit(self, records, values):
            fits.append((tuple(r.sample_id for r in records), tuple(values)))
            super().fit(records, values)

    run = run_seed(
        cls(dataset, labels),
        split,
        reps,
        cfg,
        lambda arm, seed, e: LoggingSpy(e),
        lambda *args: None,
        lambda: None,
    )
    return run, fits


def test_poisoned_heldout_labels_do_not_change_training_or_tuning():
    _, split, labels, _, cfg = fixture()
    a, fits = execute(labels)
    poisoned = dict(labels)
    poisoned.update({i: 1e6 + int(i) * 100 for i in split.test_ids})
    b, other = execute(poisoned)
    assert fits == other
    for arm in cfg["arms"]:
        for p, q in zip(a["arms"][arm], b["arms"][arm], strict=True):
            assert p["fit"] == q["fit"]
            assert p["acquired_ids"] == q["acquired_ids"]
            assert p["metrics"] != q["metrics"]
    audit_run(a, cfg)


def test_poisoned_unrevealed_labels_do_not_change_budget_prefix():
    _, _, labels, _, cfg = fixture()
    a, _ = execute(labels)
    acquired = set(a["arms"]["onehot_ridge"][0]["training_ids"])
    poisoned = {i: y if i in acquired else 100000.0 + int(i) for i, y in labels.items()}
    b, _ = execute(poisoned)
    for arm in cfg["arms"]:
        assert a["arms"][arm][0]["fit"] == b["arms"][arm][0]["fit"]


def test_audit_rejects_invalid_neural_validation_and_unmatched_ids():
    *_, labels, reps, cfg = fixture()
    run, _ = execute(labels)
    broken = copy.deepcopy(run)
    broken["arms"]["lora_head"][0]["fit"]["validation_ids"].append("39")
    with pytest.raises(ValueError, match="validation"):
        audit_run(broken, cfg)
    broken = copy.deepcopy(run)
    broken["arms"]["lora_head"][0]["acquired_ids"][0] = "39"
    with pytest.raises(ValueError):
        audit_run(broken, cfg)


def test_selection_candidates_train_on_inner_fit_only_then_refit_every_label():
    dataset, _, labels, _, cfg = fixture()
    records = dataset.observations[:20]
    seen = []

    class Guard(Spy):
        def fit(self, records, values):
            self.ids = {r.sample_id for r in records}
            seen.append(self.ids)
            super().fit(records, values)

        def predict(self, records):
            assert not self.ids & {r.sample_id for r in records}
            return super().predict(records)

    _, audit = fit_selected_neural(
        records,
        tuple(labels[r.sample_id] for r in records),
        400,
        cfg,
        lambda e: Guard(e),
    )
    assert seen[:2] == [set(audit["fit_ids"])] * 2
    assert seen[-1] == {r.sample_id for r in records}
    assert set(audit["validation_ids"]) & seen[0] == set()


def test_scoring_occurs_only_after_all_arm_choices_and_references():
    dataset, split, labels, reps, cfg = fixture()
    events = []

    class Deferred(LoadedDataset):
        def capabilities(self, split):
            oracle, evaluator, ref = super().capabilities(split)

            class Scorer:
                def score(self, predictions):
                    assert len(events) == 8
                    return evaluator.score(predictions)

            return oracle, Scorer(), ref

    run_seed(
        Deferred(dataset, labels),
        split,
        reps,
        cfg,
        lambda arm, seed, e: Spy(e),
        lambda *args: events.append(args),
        lambda: None,
    )
