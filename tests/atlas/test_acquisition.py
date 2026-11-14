import numpy as np
import pytest

from oligo_engine.atlas.acquisition import select_batch


def test_maxdet_reduces_batch_redundancy():
    x = np.array([[0.0, 0.0], [10.0, 0.0], [9.9, 0.0], [0.0, 9.0]])
    rng = np.random.default_rng(1)
    assert select_batch("uncertainty", x, [0], [1, 2, 3], 2, rng) == [1, 2]
    assert select_batch("maxdet", x, [0], [1, 2, 3], 2, rng) == [1, 3]


@pytest.mark.parametrize("kind", ["random", "diversity", "uncertainty", "maxdet"])
def test_unique_eligible_deterministic(kind):
    x = np.random.default_rng(4).normal(size=(20, 4))
    a = select_batch(
        kind, x, list(range(5)), list(range(5, 20)), 10, np.random.default_rng(9)
    )
    b = select_batch(
        kind, x, list(range(5)), list(range(5, 20)), 10, np.random.default_rng(9)
    )
    assert a == b and len(set(a)) == 10 and not set(a) & set(range(5))


def test_invalid_pool_fails_closed():
    with pytest.raises(ValueError):
        select_batch(
            "maxdet", np.ones((2, 2)), [0], [0, 1], 1, np.random.default_rng(0)
        )
