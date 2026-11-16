"""Exact planning bounds use beliefs, conserve costs and preserve information."""

import importlib.util
from itertools import product
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "planning_model",
    Path(__file__).resolve().parents[1] / "experiments/value_of_planning/model.py",
)
assert _SPEC is not None and _SPEC.loader is not None
model = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(model)


@pytest.mark.parametrize("prevalence", [0.25, 0.5, 0.75])
def test_uncertainty_changes_entropy_without_changing_mean_prevalence(prevalence):
    entropy = []
    for u in [0.1, 0.5, 1.0]:
        probabilities = model.panel_probabilities(prevalence, u)
        assert sum(probabilities) / 4 == pytest.approx(prevalence)
        entropy.append(model.mean_entropy(probabilities))
        for coupling in [0, 0.75]:
            p = model.BeliefProblem(model.joint_prior(probabilities, coupling), 3, 6)
            assert sum(p.prior) == pytest.approx(1)
            assert [p.marginal(p.initial, i) for i in range(4)] == pytest.approx(
                probabilities
            )
    assert entropy == sorted(entropy)


def test_branch_probabilities_and_bayesian_martingale():
    p = model.BeliefProblem(model.joint_prior((0.2, 0.4, 0.6, 0.8), 0.75), 3, 6)
    for action in p.actions(p.initial):
        branches = p.branches(p.initial, action)
        assert sum(x[0] for x in branches) == pytest.approx(1)
        for i in range(4):
            expected = sum(w * p.marginal(s, i) for w, s, _ in branches)
            assert expected == pytest.approx(p.marginal(p.initial, i))


def test_all_assays_are_charged_and_confirmations_cannot_repeat():
    p = model.BeliefProblem(model.joint_prior((0.5,) * 4, 0.75), 3, 4)
    _, screened, reward = p.branches(p.initial, 4)[0]
    assert reward == 0 and p.remaining(screened) == 3
    assert 4 not in p.actions(screened)
    _, confirmed, reward = p.branches(screened, 0)[1]
    assert reward == 1 and p.remaining(confirmed) == 0
    assert p.actions(confirmed) == ()
    with pytest.raises(ValueError, match="Illegal"):
        p.branches(confirmed, 0)


@pytest.mark.parametrize("budget", [2, 4, 6])
def test_no_information_independent_control_is_greedy_optimal(budget):
    p = model.BeliefProblem(
        model.joint_prior((0.8, 0.6, 0.4, 0.2), 0), 2, budget, accuracy=0.5
    )
    expected = sum((0.8, 0.6, 0.4, 0.2)[: budget // 2])
    assert p.optimal_value(p.initial) == pytest.approx(expected)
    assert p.greedy_value(p.initial) == pytest.approx(expected)


def test_optimal_dominates_rollout_and_greedy_but_is_not_clairvoyant():
    p = model.BeliefProblem(model.joint_prior((0.5,) * 4, 0.75), 3, 8)
    exact = p.optimal_value(p.initial)
    assert exact >= p.rollout_value(p.initial) >= p.greedy_value(p.initial)
    assert exact > p.greedy_value(p.initial) + 0.1
    assert exact < p.clairvoyant_bound()


def test_candidate_permutation_preserves_bayesian_optimum():
    prior = model.joint_prior((0.1, 0.7, 0.3, 0.9), 0.75)
    worlds = tuple(product((0, 1), repeat=4))
    perm = (2, 0, 3, 1)
    remapped = {tuple(y[i] for i in perm): w for w, y in zip(prior, worlds)}
    other = tuple(remapped[y] for y in worlds)
    a = model.BeliefProblem(prior, 3, 6)
    b = model.BeliefProblem(other, 3, 6)
    assert a.optimal_value(a.initial) == pytest.approx(b.optimal_value(b.initial))


def test_complete_confirmation_budget_reaches_expected_total_hits():
    p = model.BeliefProblem(model.joint_prior((0.1, 0.2, 0.8, 0.9), 0.75), 2, 8)
    assert p.optimal_value(p.initial) == pytest.approx(2)
    assert p.greedy_value(p.initial) == pytest.approx(2)


def test_observation_contains_posterior_and_paid_history_only():
    p = model.BeliefProblem(model.joint_prior((0.5,) * 4, 0.75), 3, 6)
    observed = p.observation(p.initial)
    assert observed[:16] == list(p.prior)
    assert observed[16:24] == [0] * 8
    assert len(observed) == 26
    assert not hasattr(p, "hidden")
    assert all(0 <= x <= 1 for x in observed)
