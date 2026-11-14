"""The CNN wrapper fits only acquired rows and preserves independent RNG state."""

import copy
import random
import tomllib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from oligo_engine.contracts import Observation
from oligo_engine.models import upstream_cnn


def baseline():
    return tomllib.loads(
        (Path(__file__).parents[1] / "configs/gate1-efficacy/Huesken.toml").read_text()
    )


def observations():
    return tuple(
        Observation(str(i), sequence, "target", "synthetic", "toy", "toy")
        for i, sequence in enumerate(("AAAA", "CCCC", "GGGG", "UUUU"))
    )


class FakeTorch:
    state = 10

    def get_rng_state(self):
        return self.state

    def set_rng_state(self, value):
        self.state = value

    def manual_seed(self, value):
        self.state = value


def native_fixture(monkeypatch):
    calls = {"fit_sequences": [], "transform_sequences": [], "labels": []}
    torch = FakeTorch()

    class Encoder:
        def __init__(self, **kwargs):
            assert kwargs == {"encode_components": ["base", "sugar", "phosphate"]}

        def fit_transform(self, sequences):
            calls["fit_sequences"].append(tuple(sequences))
            return np.asarray([[[ord(s[0])]] for s in sequences])

        def transform(self, sequences):
            calls["transform_sequences"].append(tuple(sequences))
            return np.asarray([[[ord(s[0])]] for s in sequences])

    class Model:
        def __init__(self, **kwargs):
            assert kwargs["input_dim"] == 1
            self.trainer = SimpleNamespace(current_epoch=7)

        def fit(self, features, labels, **kwargs):
            assert len(features) == len(labels)
            calls["labels"].append(tuple(labels))
            self.mean = float(np.mean(labels))
            random.random()
            np.random.random()
            torch.state += 1

        def predict(self, features):
            return np.asarray(
                [[self.mean + float(row[0][0]) / 100] for row in features]
            )

    monkeypatch.setattr(
        upstream_cnn, "_native_components", lambda path: (np, torch, Encoder, Model)
    )
    return calls, torch


def test_fit_uses_only_acquired_sequences_and_predict_never_refits(
    monkeypatch, tmp_path
):
    calls, _ = native_fixture(monkeypatch)
    rows = observations()
    predictor = upstream_cnn.UpstreamCNN(tmp_path, 0, baseline())
    original_config = predictor.config
    predictor.fit(rows[:2], (10.0, 30.0))
    predictions = predictor.predict(rows[2:])
    assert calls["fit_sequences"] == [("AAAA", "CCCC")]
    assert calls["transform_sequences"] == [("GGGG", "UUUU")]
    assert calls["labels"] == [(10.0, 30.0)]
    assert all(
        p.uncertainty is None and p.uncertainty_type is None for p in predictions
    )
    predictor.fit(rows[:3], (10.0, 30.0, 40.0))
    assert predictor.config == original_config
    assert predictor.fit_diagnostics["sample_ids"] == ["0", "1", "2"]


def test_rng_states_are_restored_and_seeded_fits_repeat(monkeypatch, tmp_path):
    _, torch = native_fixture(monkeypatch)
    random.seed(32)
    np.random.seed(41)
    python_state, numpy_state, torch_state = (
        random.getstate(),
        np.random.get_state(),
        torch.state,
    )
    predictor = upstream_cnn.UpstreamCNN(tmp_path, 3, baseline())
    predictor.fit(observations()[:2], (1.0, 2.0))
    assert random.getstate() == python_state
    assert np.array_equal(np.random.get_state()[1], numpy_state[1])
    assert np.random.get_state()[2:] == numpy_state[2:]
    assert torch.state == torch_state
    first = predictor.predict(observations()[2:])
    predictor.fit(observations()[:2], (1.0, 2.0))
    assert predictor.predict(observations()[2:]) == first


def test_invalid_labels_ids_and_unfitted_prediction_fail_before_native_access(tmp_path):
    predictor = upstream_cnn.UpstreamCNN(tmp_path, 0, baseline())
    rows = observations()
    with pytest.raises(ValueError, match="fitted"):
        predictor.predict(rows)
    for records, labels in (((), ()), (rows[:2], (1.0,)), (rows[:1], (float("nan"),))):
        with pytest.raises(ValueError):
            predictor.fit(records, labels)
    with pytest.raises(ValueError, match="Repeated"):
        predictor.fit((rows[0], rows[0]), (1.0, 2.0))
    wrong = copy.deepcopy(baseline())
    wrong["upstream_revision"] = "unverified"
    with pytest.raises(ValueError, match="frozen"):
        upstream_cnn.UpstreamCNN(tmp_path, 0, wrong)
