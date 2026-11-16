"""Finite, outcome-blind belief MDP for model-based multifidelity active search."""

from __future__ import annotations

from functools import cache
from itertools import product
from math import isclose, log2

State = tuple[int, ...]


def joint_prior(probabilities: tuple[float, ...], coupling: float) -> tuple[float, ...]:
    """Independent two-candidate families; mixture adds within-family dependence.

    A coupled pair shares U~Uniform(0,1), with Yi=1[U<qi]. Mixing this with
    independent Bernoullis preserves every marginal. Coupling is not Pearson rho.
    """
    if len(probabilities) % 2 or not 0 <= coupling <= 1:
        raise ValueError("Even panel size and coupling in [0,1] required")
    if any(not 0 <= p <= 1 for p in probabilities):
        raise ValueError("Invalid hit probability")
    weights = []
    for labels in product((0, 1), repeat=len(probabilities)):
        weight = 1.0
        for j in range(0, len(labels), 2):
            q, r = probabilities[j : j + 2]
            a, b = labels[j : j + 2]
            independent = (q if a else 1 - q) * (r if b else 1 - r)
            lo = max([0.0] + [p for p, y in ((q, a), (r, b)) if not y])
            hi = min([1.0] + [p for p, y in ((q, a), (r, b)) if y])
            weight *= (1 - coupling) * independent + coupling * max(0, hi - lo)
        weights.append(weight)
    return tuple(weights)


def panel_probabilities(prevalence: float, uncertainty: float) -> tuple[float, ...]:
    """Move known 0/1 propensities toward a fixed panel-average prevalence."""
    templates = {
        0.25: (1, 0, 0, 0),
        0.5: (1, 0, 1, 0),
        0.75: (1, 1, 1, 0),
    }
    if prevalence not in templates or not 0 <= uncertainty <= 1:
        raise ValueError("Declared four-candidate prevalence/uncertainty required")
    return tuple(
        (1 - uncertainty) * z + uncertainty * prevalence for z in templates[prevalence]
    )


def mean_entropy(probabilities: tuple[float, ...]) -> float:
    """Average Bernoulli entropy, in bits; separate from observation noise."""
    return sum(
        -p * log2(p) - (1 - p) * log2(1 - p) if 0 < p < 1 else 0 for p in probabilities
    ) / len(probabilities)


class BeliefProblem:
    """Actions confirm i, screen n+i, or STOP=2n; only confirmation yields hits."""

    def __init__(
        self,
        prior: tuple[float, ...],
        confirm_cost: int,
        budget: int,
        accuracy: float = 0.9,
    ) -> None:
        n = len(prior).bit_length() - 1
        if len(prior) != 2**n or n < 1 or any(p < 0 for p in prior):
            raise ValueError("Complete nonnegative binary joint prior required")
        if not isclose(sum(prior), 1, abs_tol=1e-12):
            raise ValueError("Prior must normalize")
        if confirm_cost < 1 or budget < 0 or not 0.5 <= accuracy <= 1:
            raise ValueError("Invalid assay costs/budget/noise")
        self.prior, self.n = prior, n
        self.confirm_cost, self.budget, self.accuracy = confirm_cost, budget, accuracy
        self.worlds = tuple(product((0, 1), repeat=n))
        self.initial = (-1,) * (2 * n)
        self.posterior = cache(self._posterior)
        self.branches = cache(self._branches)
        self.greedy_value = cache(self._greedy_value)
        self.optimal_value = cache(self._optimal_value)
        self.rollout_action = cache(self._rollout_action)
        self.rollout_value = cache(self._rollout_value)
        self.random_value = cache(self._random_value)

    def remaining(self, state: State) -> int:
        """Every screen/confirmation is charged once, including repeated compound."""
        return (
            self.budget
            - sum(x >= 0 for x in state[: self.n])
            - self.confirm_cost * sum(x >= 0 for x in state[self.n :])
        )

    def actions(self, state: State) -> tuple[int, ...]:
        """All affordable nonrepeated assays; STOP is only needed when none remain."""
        remaining = self.remaining(state)
        confirms = tuple(
            i
            for i in range(self.n)
            if state[self.n + i] < 0 and remaining >= self.confirm_cost
        )
        screens = tuple(
            self.n + i
            for i in range(self.n)
            if state[i] < 0 and state[self.n + i] < 0 and remaining >= 1
        )
        return confirms + screens

    def _posterior(self, state: State) -> tuple[float, ...]:
        weights = []
        for probability, labels in zip(self.prior, self.worlds, strict=True):
            for i, y in enumerate(labels):
                if state[self.n + i] >= 0 and state[self.n + i] != y:
                    probability = 0
                    break
                if state[i] >= 0:
                    probability *= self.accuracy if state[i] == y else 1 - self.accuracy
            weights.append(probability)
        total = sum(weights)
        if total <= 0:
            raise ValueError("Impossible observation state")
        return tuple(w / total for w in weights)

    def marginal(self, state: State, i: int) -> float:
        return sum(
            p * y[i] for p, y in zip(self.posterior(state), self.worlds, strict=True)
        )

    def _branches(self, state: State, action: int) -> tuple:
        if action not in self.actions(state):
            raise ValueError("Illegal or unaffordable assay")
        confirm, i = action < self.n, action % self.n
        hit = self.marginal(state, i)
        positive = (
            hit if confirm else self.accuracy * hit + (1 - self.accuracy) * (1 - hit)
        )
        result = []
        for outcome, probability in ((0, 1 - positive), (1, positive)):
            if probability > 1e-14:
                updated = list(state)
                updated[self.n + i if confirm else i] = outcome
                result.append((probability, tuple(updated), outcome if confirm else 0))
        return tuple(result)

    def expected(self, state: State, action: int, continuation) -> float:
        return sum(
            p * (reward + continuation(next_state))
            for p, next_state, reward in self.branches(state, action)
        )

    def greedy_action(self, state: State) -> int:
        """Maximum immediate expected confirmed hits; exact Bayesian updates."""
        choices = [a for a in self.actions(state) if a < self.n]
        return (
            max(choices, key=lambda a: (self.marginal(state, a), -a))
            if choices
            else 2 * self.n
        )

    def _greedy_value(self, state: State) -> float:
        action = self.greedy_action(state)
        return (
            0.0
            if action == 2 * self.n
            else self.expected(state, action, self.greedy_value)
        )

    def _optimal_value(self, state: State) -> float:
        return max(
            [0.0]
            + [self.expected(state, a, self.optimal_value) for a in self.actions(state)]
        )

    def _rollout_action(self, state: State) -> int:
        """One exploratory action then exact greedy-to-budget continuation."""
        actions = self.actions(state)
        return (
            max(actions, key=lambda a: (self.expected(state, a, self.greedy_value), -a))
            if actions
            else 2 * self.n
        )

    def _rollout_value(self, state: State) -> float:
        action = self.rollout_action(state)
        return (
            0.0
            if action == 2 * self.n
            else self.expected(state, action, self.rollout_value)
        )

    def _random_value(self, state: State) -> float:
        actions = self.actions(state)
        return (
            sum(self.expected(state, a, self.random_value) for a in actions)
            / len(actions)
            if actions
            else 0.0
        )

    def clairvoyant_bound(self) -> float:
        """Separate nonattainable bound; this is NOT the Bayesian optimum."""
        count = self.budget // self.confirm_cost
        return sum(
            p * min(sum(y), count) for p, y in zip(self.prior, self.worlds, strict=True)
        )

    def observation(self, state: State) -> list[float]:
        """Sufficient belief and paid history, never the sampled hidden world."""
        return [
            *self.posterior(state),
            *((x + 1) / 2 for x in state),
            self.remaining(state) / 8,
            self.confirm_cost / 4,
        ]
