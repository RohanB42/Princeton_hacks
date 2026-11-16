"""Synthetic assay simulator; sampled world never appears in policy observation."""

import gymnasium as gym
import numpy as np
from model import BeliefProblem, joint_prior, panel_probabilities


class PlanningEnv(gym.Env):
    def __init__(self, cells: list[dict]) -> None:
        self.cells = cells
        self.action_space = gym.spaces.Discrete(9)
        self.observation_space = gym.spaces.Box(0, 1, shape=(26,), dtype=np.float32)
        self.total_cost = self.total_confirmations = self.total_screens = 0

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        cell = self.cells[int(self.np_random.integers(len(self.cells)))]
        self.problem = BeliefProblem(
            joint_prior(
                panel_probabilities(cell["prevalence"], cell["uncertainty"]),
                cell["coupling"],
            ),
            cell["confirm_cost"],
            cell["budget"],
        )
        self.state = self.problem.initial
        index = self.np_random.choice(16, p=self.problem.prior)
        self.hidden = self.problem.worlds[index]
        return self._observation(), {}

    def _observation(self):
        return np.asarray(self.problem.observation(self.state), np.float32)

    def action_masks(self):
        mask = np.zeros(9, bool)
        choices = self.problem.actions(self.state)
        mask[list(choices)] = True
        mask[8] = True
        return mask

    def step(self, action):
        p = self.problem
        if not self.action_masks()[action]:
            raise ValueError("Invalid masked action")
        if action == 8:
            return self._observation(), 0.0, True, False, {}
        confirm, i = action < 4, action % 4
        outcome = self.hidden[i]
        if not confirm and self.np_random.random() > p.accuracy:
            outcome = 1 - outcome
        updated = list(self.state)
        updated[4 + i if confirm else i] = outcome
        self.state = tuple(updated)
        self.total_cost += p.confirm_cost if confirm else 1
        self.total_confirmations += int(confirm)
        self.total_screens += int(not confirm)
        return (
            self._observation(),
            float(outcome if confirm else 0),
            not p.actions(self.state),
            False,
            {},
        )
