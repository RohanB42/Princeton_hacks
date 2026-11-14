"""Short-horizon masked base-edit environment for sequence proposals."""

from collections.abc import Sequence
from dataclasses import asdict
from typing import Protocol

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from oligo_engine.design.huesken_bundle import BASES
from oligo_engine.design.scoring import ScoreResult


class SequenceScorer(Protocol):
    identity: str

    def score(self, sequence: str) -> ScoreResult: ...


class BaseEditEnv(gym.Env):
    """A complete sequence proposal earns one terminal frozen-scorer reward."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        starts: Sequence[str],
        scorer: SequenceScorer,
        edit_budget: int = 8,
    ):
        super().__init__()
        if not starts or edit_budget < 0:
            raise ValueError("Starts must be nonempty and edit budget nonnegative")
        length = len(starts[0])
        if length < 1 or any(
            len(sequence) != length or set(sequence) - set(BASES) for sequence in starts
        ):
            raise ValueError("All starts must be equal-length A/C/G/U sequences")
        self.starts = tuple(starts)
        self.scorer = scorer
        self.length = length
        self.edit_budget = edit_budget
        self.action_vocabulary = ("STOP",) + tuple(
            f"substitute:{position}:{base}"
            for position in range(length)
            for base in BASES
        )
        self.action_space = spaces.Discrete(len(self.action_vocabulary))
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(length * 4 + 1,), dtype=np.float32
        )
        self.sequence = self.starts[0]
        self.edits = 0
        self.done = False

    def _observation(self) -> np.ndarray:
        values = np.zeros(self.length * 4 + 1, dtype=np.float32)
        for position, base in enumerate(self.sequence):
            values[position * 4 + BASES.index(base)] = 1.0
        values[-1] = (
            (self.edit_budget - self.edits) / self.edit_budget
            if self.edit_budget
            else 0.0
        )
        return values

    def action_masks(self) -> np.ndarray:
        valid = np.zeros(self.action_space.n, dtype=np.bool_)
        valid[0] = True
        if self.done or self.edits >= self.edit_budget:
            return valid
        for position, base in enumerate(self.sequence):
            for replacement in BASES:
                action = 1 + position * 4 + BASES.index(replacement)
                valid[action] = replacement != base
        return valid

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict | None = None,
    ) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        requested = (options or {}).get("start")
        if requested is not None and requested not in self.starts:
            raise ValueError("Requested start is outside the declared manifest")
        index = int(self.np_random.integers(0, len(self.starts)))
        self.sequence = requested if requested is not None else self.starts[index]
        self.edits = 0
        self.done = False
        return self._observation(), {"start": self.sequence}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        if self.done:
            raise RuntimeError("Reset the environment after termination")
        if not self.action_space.contains(action) or not self.action_masks()[action]:
            # Gymnasium's generic check_env samples actions without applying masks.
            self.done = True
            return (
                self._observation(),
                -1.0,
                True,
                False,
                {
                    "invalid_action": True,
                    "sequence": self.sequence,
                },
            )
        if action != 0:
            position, base_index = divmod(action - 1, 4)
            updated = list(self.sequence)
            updated[position] = BASES[base_index]
            self.sequence = "".join(updated)
            self.edits += 1
        terminated = action == 0 or self.edits == self.edit_budget
        self.done = terminated
        if not terminated:
            return (
                self._observation(),
                0.0,
                False,
                False,
                {
                    "sequence": self.sequence,
                    "edits": self.edits,
                },
            )
        result = self.scorer.score(self.sequence)
        return (
            self._observation(),
            result.reward,
            True,
            False,
            {
                "sequence": self.sequence,
                "edits": self.edits,
                "score": asdict(result),
                "invalid_action": False,
            },
        )


class PotentialShaping(gym.Wrapper):
    """Gamma-one shaping; zero initial/terminal potentials preserve total return."""

    def reset(self, **kwargs):
        self.potential = 0.0
        return self.env.reset(**kwargs)

    def action_masks(self):
        return self.env.action_masks()

    def step(self, action):
        observation, reward, terminated, truncated, info = self.env.step(action)
        next_potential = (
            0.0
            if terminated or truncated
            else self.env.scorer.score(info["sequence"]).reward
        )
        shaped = reward + next_potential - self.potential
        self.potential = next_potential
        return observation, shaped, terminated, truncated, info
