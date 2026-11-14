"""Behavior of the one-hot RF/GP predictors against real Huesken rows."""

import csv
import gzip
from dataclasses import replace

import numpy as np
import pytest

from oligo_engine.audit_upstream import PINNED_REVISION
from oligo_engine.contracts import Prediction
from oligo_engine.data.catalog import DEFAULT_DATA_ROOT, Catalog
from oligo_engine.features.upstream import OneHotBaseFeaturizer
from oligo_engine.models.baseline import (
    GP_LATENT_SD,
    RF_TREE_SD,
    OneHotGaussianProcess,
    OneHotRandomForest,
)

N_TRAIN, N_TEST = 80, 30


@pytest.fixture(scope="module")
def rows():
    observations = Catalog().load("Huesken").dataset.observations[: N_TRAIN + N_TEST]
    path = DEFAULT_DATA_ROOT / "Ichihara_2007_1_processed.csv.gz"
    with gzip.open(path, "rt", newline="") as file:
        labels = [
            float(r["y"])
            for _, r in zip(range(len(observations)), csv.DictReader(file))
        ]
    return observations[:N_TRAIN], tuple(labels[:N_TRAIN]), observations[N_TRAIN:]


def test_featurizer_is_stateless_fixed_width_and_one_hot(rows):
    train, _, test = rows
    featurizer = OneHotBaseFeaturizer()
    batch = featurizer.transform(train + test)
    assert batch.shape == (N_TRAIN + N_TEST, 42 * 5)
    assert np.all(batch.sum(axis=1) == 42)  # one active channel per monomer
    alone = featurizer.transform(test[:1])
    assert np.array_equal(alone[0], batch[N_TRAIN])  # no dependence on other rows


def test_featurizer_rejects_unrepresentable_inputs(rows):
    train, _, _ = rows
    with pytest.raises(ValueError, match="exceed"):
        OneHotBaseFeaturizer(max_sequence_length=21).transform(train[:1])
    with pytest.raises(ValueError, match="unsupported"):
        OneHotBaseFeaturizer(alphabet=("A", "C", "G", "U")).transform(train[:1])


@pytest.mark.parametrize("factory", [OneHotRandomForest, OneHotGaussianProcess])
def test_contract_determinism_and_unfitted_guard(rows, factory):
    train, labels, test = rows
    model = factory(seed=3)
    with pytest.raises(RuntimeError):
        model.predict(test)
    with pytest.raises(ValueError):
        model.fit(train, labels[:-1])
    model.fit(train, labels)
    first = model.predict(test)
    again = factory(seed=3)
    again.fit(train, labels)
    assert first == again.predict(test)
    assert len(first) == len(test) and all(isinstance(p, Prediction) for p in first)
    assert model.config["upstream"]["oligogym_revision"] == PINNED_REVISION
    assert model.config["n_features"] == 210


def test_uncertainty_types_are_named_and_not_called_calibrated(rows):
    train, labels, test = rows
    rf, gp = OneHotRandomForest(seed=0, n_estimators=20), OneHotGaussianProcess(0)
    rf.fit(train, labels)
    gp.fit(train, labels)
    assert {p.uncertainty_type for p in rf.predict(test)} == {RF_TREE_SD}
    assert {p.uncertainty_type for p in gp.predict(test)} == {GP_LATENT_SD}
    assert "uncalibrated" in RF_TREE_SD and "uncalibrated" in GP_LATENT_SD


def test_gp_uncertainty_excludes_observation_noise(rows):
    train, labels, test = rows
    gp = OneHotGaussianProcess(seed=0)
    gp.fit(train, labels)
    parts = gp.predict_components(test)
    assert parts["noise_sd"] > 0
    assert np.all(parts["latent_sd"] <= parts["total_sd"] + 1e-9)
    recovered = parts["total_sd"] ** 2 - parts["latent_sd"] ** 2
    assert np.allclose(recovered, parts["noise_sd"] ** 2, atol=1e-6)
    served = np.array([p.uncertainty for p in gp.predict(test)])
    assert np.array_equal(served, parts["latent_sd"])


@pytest.mark.parametrize("factory", [OneHotRandomForest, OneHotGaussianProcess])
def test_only_fit_rows_and_requested_rows_are_featurized(rows, factory):
    train, labels, test = rows
    model = factory(seed=1)
    seen: list[str] = []
    original = model.featurizer.transform

    def spy(observations):
        seen.extend(row.sample_id for row in observations)
        return original(observations)

    model.featurizer.transform = spy
    model.fit(train, labels)
    assert set(seen) == {row.sample_id for row in train}
    seen.clear()
    model.predict(test)
    assert set(seen) == {row.sample_id for row in test}


def test_labels_drive_fit_and_nothing_else_does(rows):
    train, labels, test = rows
    base = OneHotGaussianProcess(seed=0)
    base.fit(train, labels)
    changed = OneHotGaussianProcess(seed=0)
    changed.fit(train, tuple(reversed(labels)))
    assert base.predict(test) != changed.predict(test)  # labels matter
    renamed = tuple(
        replace(r, sample_id=f"x{i}", target_id="other") for i, r in enumerate(train)
    )
    third = OneHotGaussianProcess(seed=0)
    third.fit(renamed, labels)
    assert base.predict(test) == third.predict(test)  # IDs/targets are ignored
