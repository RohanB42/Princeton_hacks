import pytest

from oligo_engine.design.scoring import ToyGScorer


@pytest.mark.parametrize("actions", [[0], [3, 0], [3, 1, 3, 7], [3, 1, 0]])
def test_shaping_preserves_episode_return(actions):
    pytest.importorskip("gymnasium")
    from oligo_engine.design.environment import BaseEditEnv, PotentialShaping

    plain = BaseEditEnv(("AAAA",), ToyGScorer(), edit_budget=4)
    shaped = PotentialShaping(BaseEditEnv(("AAAA",), ToyGScorer(), edit_budget=4))
    plain.reset(seed=0)
    shaped.reset(seed=0)
    totals = [0.0, 0.0]
    for action in actions:
        for i, env in enumerate((plain, shaped)):
            _, reward, done, _, _ = env.step(action)
            totals[i] += reward
    assert done
    assert totals[0] == pytest.approx(totals[1])
