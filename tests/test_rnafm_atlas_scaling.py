"""Budget, selection, checkpoint and held-out-label invariants for optional study."""

import copy
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch
from torch import nn

from oligo_engine.atlas.scaling import grouped_validation
from oligo_engine.models.aso_rnafm import ASOPredictor


class Context:
    def fit(self, frame):
        self.ids = frame.source_row_id.tolist()

    def transform(self, frame):
        return np.zeros((len(frame), 1))


class TinyPredictor(ASOPredictor):
    def __init__(self):
        self.seed, self.adapt = 12, True
        backbone = nn.Module()
        backbone.register_parameter("base", nn.Parameter(torch.ones(1), False))
        backbone.register_parameter("adapter", nn.Parameter(torch.zeros(1)))
        self.encoder = SimpleNamespace(backbone=backbone, identity="fixture")
        self.context, self.head, self.receipts = Context(), None, []
        self.gradient_ids = []

    def _base(self):
        return {"base": self.encoder.backbone.base}

    def _batch(self, frame, frozen=None):
        if torch.is_grad_enabled():
            self.gradient_ids.extend(frame.source_row_id)
        x = torch.tensor(frame.x.to_numpy(), dtype=torch.float32)[:, None]
        return self.head(x).flatten() + self.encoder.backbone.adapter


def frames():
    frame = pd.DataFrame({"source_row_id": list("abcdef"), "x": np.arange(6)})
    return frame.iloc[:4], frame.iloc[4:]


def patch_head(monkeypatch):
    monkeypatch.setattr(
        "oligo_engine.models.aso_rnafm.ChemistryHead", lambda _: nn.Linear(1, 1)
    )


def test_group_split_is_disjoint_and_budgeted():
    split = grouped_validation(list("abcdef"), ["p1", "p1", "p2", "p3", "p4", "p4"], 7)
    assert not set(split["fit_groups"]) & set(split["validation_groups"])
    assert split["fit_labels"] + split["validation_labels"] == 6
    assert set(split["fit_ids"] + split["validation_ids"]) == set("abcdef")
    with pytest.raises(ValueError):
        grouped_validation(["a", "b"], ["p", "p"], 7)


def test_history_selection_restores_full_state_and_denies_val_gradients(monkeypatch):
    patch_head(monkeypatch)
    train, val = frames()
    model = TinyPredictor()
    receipt = model.fit(
        train,
        np.arange(4.0),
        epochs=8,
        validation=(val, np.array([100.0, 100.0])),
        patience=2,
        min_epochs=3,
        min_delta=1e6,
        checkpoint_epochs=(1, 3, 8),
    )
    assert receipt["epochs"] == 3 and receipt["selected_epoch"] == 1
    assert receipt["base_unchanged"] and receipt["adapters_changed"]
    assert set(model.gradient_ids) == set(train.source_row_id)
    assert model.context.ids == train.source_row_id.tolist()
    state = model.snapshot()
    for section in ["head", "adapters"]:
        for k, v in state[section].items():
            torch.testing.assert_close(v, model.checkpoints[1][section][k])
    assert receipt["total_fit_validation_labels"] == 6
    assert len(receipt["history"]) == 3
    assert receipt["history"][0]["train_mse"] >= 0


def test_evaluation_label_poisoning_cannot_change_fitting(monkeypatch, tmp_path):
    patch_head(monkeypatch)
    train, val = frames()
    from oligo_engine.atlas.scaling import read_label_subset

    states, histories = [], []
    # Exercise the real filtered endpoint reader before the fitting boundary.
    for poisoned in [False, True]:
        cohort = pd.concat([train, val], ignore_index=True)
        cohort["Inhibition_pct"] = np.arange(6.0)
        cohort.loc[len(cohort)] = ["heldout", 99.0, 1e12 if poisoned else 1.0]
        path = tmp_path / f"cohort-{poisoned}.parquet"
        cohort.to_parquet(path)
        permitted = train.source_row_id.tolist() + val.source_row_id.tolist()
        labels = read_label_subset(path, permitted)
        model = TinyPredictor()
        receipt = model.fit(
            train,
            labels.loc[train.source_row_id].to_numpy(),
            epochs=4,
            validation=(val, labels.loc[val.source_row_id].to_numpy()),
        )
        histories.append(
            [
                {k: v for k, v in r.items() if k != "elapsed_s"}
                for r in receipt["history"]
            ]
        )
        states.append(model.snapshot())
    assert histories[0] == histories[1]
    for section in ["head", "adapters"]:
        for k, v in states[0][section].items():
            torch.testing.assert_close(v, states[1][section][k])


def test_legacy_fixed_epochs_and_overlap_rejection(monkeypatch):
    patch_head(monkeypatch)
    train, val = frames()
    model = TinyPredictor()
    receipt = model.fit(train, np.arange(4.0), epochs=3)
    assert receipt["epochs"] == 3 and not receipt["history"]
    prior = copy.deepcopy(model.snapshot())
    model.context.ids = ["wrong"]
    model.restore(prior)
    assert model.context.ids == train.source_row_id.tolist()
    with pytest.raises(ValueError, match="overlap"):
        TinyPredictor().fit(train, np.arange(4.0), validation=(train, np.arange(4.0)))
    with pytest.raises(ValueError, match="validation"):
        TinyPredictor().fit(
            train, np.arange(4.0), validation=(val.assign(Inhibition_pct=0), np.ones(2))
        )


def test_history_does_not_change_fixed_epoch_optimization(monkeypatch):
    patch_head(monkeypatch)
    train, _ = frames()
    states = []
    for logging in [False, True]:
        model = TinyPredictor()
        model.fit(train, np.arange(4.0), epochs=3, record_history=logging)
        states.append(model.snapshot())
    for section in ["head", "adapters"]:
        for key, value in states[0][section].items():
            torch.testing.assert_close(value, states[1][section][key], rtol=0, atol=0)


def test_endpoint_reader_filters_reserved_rows_before_return(tmp_path):
    from oligo_engine.atlas.scaling import read_label_subset

    path = tmp_path / "cohort.parquet"
    pd.DataFrame(
        {"source_row_id": ["fit", "reserved"], "Inhibition_pct": [4.0, float("nan")]}
    ).to_parquet(path)
    selected = read_label_subset(path, ["fit"])
    assert selected.index.tolist() == ["fit"] and selected.iloc[0] == 4.0
    with pytest.raises(ValueError):
        read_label_subset(path, ["missing"])
