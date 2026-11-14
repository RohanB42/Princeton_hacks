"""Coverage policy chooses eligible unique IDs without reading model outcomes."""

from random import Random

import numpy as np
import pytest

from oligo_engine.acquisition.pool_diversity import DiversityAcquisition
from oligo_engine.contracts import Observation


def row(identity):
    return Observation(identity, "ACGU", "target", "synthetic", "synthetic", "toy")


class ForbiddenPredictor:
    def predict(self, observations):
        raise AssertionError("Label-blind diversity must not query model predictions")


def test_max_min_batch_updates_distances_and_ignores_candidate_order():
    records = tuple(row(i) for i in ("labeled", "a", "b", "c"))
    vectors = [[1, 0], [0, 1], [-1, 0], [-0.98, 0.2]]
    policy = DiversityAcquisition(records, vectors, {})
    labeled = records[:1]
    eligible = records[1:]
    expected = ("b", "a")
    assert (
        policy.choose(eligible, labeled, 2, Random(0), ForbiddenPredictor()) == expected
    )
    assert (
        policy.choose(
            tuple(reversed(eligible)), labeled, 2, Random(999), ForbiddenPredictor()
        )
        == expected
    )


def test_exact_ties_use_immutable_id_and_zero_embeddings_are_defined():
    records = tuple(row(i) for i in ("b", "a", "labeled"))
    policy = DiversityAcquisition(records, np.zeros((3, 2)), {})
    assert policy.choose(records[:2], records[2:], 2, Random(0), None) == ("a", "b")
    assert policy.choose(records[:2], (), 1, Random(0), None) == ("a",)


@pytest.mark.parametrize("kind", ["overlap", "unknown", "duplicate", "budget"])
def test_invalid_eligibility_and_budget_fail_closed(kind):
    records = tuple(row(i) for i in ("a", "b", "c"))
    policy = DiversityAcquisition(records, np.eye(3), {})
    eligible, labeled, budget = records[:2], records[2:], 1
    if kind == "overlap":
        labeled = records[:1]
    elif kind == "unknown":
        eligible = (row("missing"),)
    elif kind == "duplicate":
        eligible = (records[0], records[0])
    else:
        budget = 3
    with pytest.raises(ValueError, match="Invalid"):
        policy.choose(eligible, labeled, budget, Random(0), None)


def test_invalid_embeddings_and_duplicate_pool_ids_fail():
    records = (row("a"), row("b"))
    for values in ([1, 2], [[1]], [[1, 2], [float("nan"), 0]]):
        with pytest.raises(ValueError, match="embeddings"):
            DiversityAcquisition(records, values, {})
    with pytest.raises(ValueError, match="unique"):
        DiversityAcquisition((records[0], records[0]), [[1], [2]], {})
