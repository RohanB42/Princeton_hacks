"""Diversity and uncertainty+diversity policies: geometry, determinism, isolation."""

from random import Random

import pytest

from oligo_engine.contracts import Observation, Prediction

np = pytest.importorskip("numpy")

from oligo_engine.acquisition.diversity import (  # noqa: E402
    DiversityAcquisition,
    UncertaintyDiversityAcquisition,
)


class LineFeaturizer:
    """Maps sequence 'x<float>' to a 1-D coordinate; stateless and label-free."""

    config = {"name": "line_fixture"}

    def transform(self, observations):
        return np.array([[float(row.sequence[1:])] for row in observations])


class SpyPredictor:
    def __init__(self, uncertainty):
        self.uncertainty = uncertainty
        self.config = {"name": "spy"}

    def predict(self, observations):
        return tuple(
            Prediction(0.0, self.uncertainty[row.sample_id], "fixture")
            for row in observations
        )


def rows(coordinates):
    return tuple(
        Observation(f"id{i:02d}", f"x{c}", "t", "siRNA", "c", "a")
        for i, c in enumerate(coordinates)
    )


def test_diversity_is_greedy_farthest_point_and_deterministic():
    labeled = rows([0.0])
    pool = rows([1.0, 2.0, 10.0, 11.0, 5.0])
    policy = DiversityAcquisition(LineFeaturizer())
    first = policy.choose(pool, labeled, 3, Random(0), SpyPredictor({}))
    # Farthest from {0} is 11, then 5 (dist 5 from both), then 2 or 1... check order.
    assert first[0] == "id03"  # coordinate 11.0
    assert first[1] == "id04"  # coordinate 5.0 (max min-distance to {0, 11})
    assert len(set(first)) == 3
    assert first == policy.choose(pool, labeled, 3, Random(99), SpyPredictor({}))


def test_diversity_ties_break_on_stable_sample_id():
    labeled = rows([0.0])
    pool = (
        Observation("b", "x4.0", "t", "siRNA", "c", "a"),
        Observation("a", "x-4.0", "t", "siRNA", "c", "a"),
    )
    chosen = DiversityAcquisition(LineFeaturizer()).choose(
        pool, labeled, 1, Random(0), SpyPredictor({})
    )
    assert chosen == ("a",)


def test_diversity_never_returns_labeled_or_duplicate_ids_and_rejects_overdraw():
    labeled = rows([0.0, 1.0])
    pool = tuple(
        Observation(f"p{i}", f"x{i + 2.0}", "t", "siRNA", "c", "a") for i in range(6)
    )
    policy = DiversityAcquisition(LineFeaturizer())
    chosen = policy.choose(pool, labeled, 6, Random(0), SpyPredictor({}))
    assert set(chosen) == {row.sample_id for row in pool}
    with pytest.raises(ValueError):
        policy.choose(pool, labeled, 7, Random(0), SpyPredictor({}))
    with pytest.raises(ValueError, match="initial labeled"):
        policy.choose(pool, (), 1, Random(0), SpyPredictor({}))


def test_hybrid_restricts_to_high_uncertainty_pool_then_spreads_out():
    labeled = rows([0.0])
    pool = rows([1.0, 2.0, 3.0, 4.0, 100.0, 101.0])
    ids = [row.sample_id for row in pool]
    # The two far points are the LEAST uncertain, so they must be excluded.
    uncertainty = dict(zip(ids, [9, 8, 7, 6, 1, 0], strict=True))
    policy = UncertaintyDiversityAcquisition(LineFeaturizer(), pool_multiplier=2)
    chosen = policy.choose(pool, labeled, 2, Random(0), SpyPredictor(uncertainty))
    assert set(chosen) <= set(ids[:4])  # pool = top 4 by uncertainty
    assert chosen[0] == "id03"  # farthest from {0} inside the pool (coordinate 4)


def test_hybrid_requires_uncertainty_and_validates_multiplier():
    labeled, pool = rows([0.0]), rows([1.0, 2.0])

    class NoUncertainty:
        config = {"name": "none"}

        def predict(self, observations):
            return tuple(Prediction(0.0) for _ in observations)

    with pytest.raises(ValueError, match="uncertainty"):
        UncertaintyDiversityAcquisition(LineFeaturizer()).choose(
            pool, labeled, 1, Random(0), NoUncertainty()
        )
    with pytest.raises(ValueError):
        UncertaintyDiversityAcquisition(LineFeaturizer(), pool_multiplier=0)


def test_configs_declare_label_free_and_name_the_featurizer():
    assert DiversityAcquisition(LineFeaturizer()).config["uses_labels"] is False
    config = UncertaintyDiversityAcquisition(LineFeaturizer()).config
    assert config["featurizer"] == {"name": "line_fixture"}
    assert config["pool_multiplier"] == 4
