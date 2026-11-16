"""Gymnasium acquisition controller with a measured, capability-scoped oracle."""

from dataclasses import dataclass
from enum import IntEnum

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from scipy.stats import rankdata
from sklearn.feature_extraction import FeatureHasher
from sklearn.preprocessing import normalize

from oligo_engine.data.oracle import LabelOracle
from oligo_engine.experimental_rl.belief import FrozenBelief, GPBelief, LinearBelief


class Expert(IntEnum):
    RANDOM = 0
    MEAN = 1
    SEQ_DIVERSITY = 2
    CHEM_DIVERSITY = 3
    LATENT = 4
    TOTAL = 5
    HYBRID = 6
    SOURCE_MEAN = 7
    STOP = 8


OBSERVATION = (
    "assay_fraction",
    "episodes_remaining_pool_fraction",
    "observed_best",
    "confirmed_hit_fraction",
    "last_outcome",
    "last_hit",
    "mean_q10",
    "mean_q50",
    "mean_q90",
    "max_mean",
    "latent_q50",
    "latent_q90",
    "chem_coverage_gap",
    "updated_label_fraction",
    "log_dose",
    "log_treatment_hours",
)


@dataclass(frozen=True)
class Campaign:
    name: str
    role: str
    context: dict
    pool: tuple[str, ...]
    sentinel: tuple[str, ...]
    prior: np.ndarray  # Pool followed by sentinel; env receives pool slice only.
    features: np.ndarray
    sequence: tuple[str, ...]
    noise: float
    initial: dict[int, tuple[str, ...]]

    def __post_init__(self) -> None:
        size = len(self.pool) + len(self.sentinel)
        if (
            not self.pool
            or len(set(self.pool + self.sentinel)) != size
            or self.prior.shape != (size,)
            or self.features.shape[0] != size
            or len(self.sequence) != len(self.pool)
            or not np.isfinite(self.prior).all()
            or not np.isfinite(self.features).all()
            or not np.isfinite(self.noise)
            or self.noise <= 0
        ):
            raise ValueError("Invalid label-free campaign data")


def sequence_vectors(sequences: tuple[str, ...]) -> np.ndarray:
    return normalize(
        FeatureHasher(n_features=64, input_type="string").transform(
            [
                [
                    sequence[j : j + k]
                    for k in (1, 2, 3)
                    for j in range(len(sequence) - k + 1)
                ]
                for sequence in sequences
            ]
        )
    ).toarray()


def make_belief(
    version: str, prior: np.ndarray, features: np.ndarray, noise: float
) -> FrozenBelief:
    if version == "v1":
        return FrozenBelief(prior, noise)
    if version == "gp":
        return GPBelief(prior, features, noise)
    if version == "v2":
        return LinearBelief(prior, features, noise)
    raise ValueError("Unknown belief version")


class ExperimentalSelectionEnv(gym.Env):
    """Only seed and acquired outcomes feed policy inputs, actions, and rewards."""

    def __init__(
        self,
        campaign: Campaign,
        labels: dict[str, float],
        budget: int,
        seed_count: int,
        threshold: float,
        version: str = "v1",
        *,
        allow_stop: bool = False,
    ) -> None:
        super().__init__()
        self._ids = campaign.pool
        self._index = {i: k for k, i in enumerate(self._ids)}
        # Validates exact pool equality. Passing even one sentinel ID is rejected.
        LabelOracle(labels, self._ids)
        self.__labels = dict(labels)
        if (
            not 0 < seed_count < budget <= len(self._ids)
            or version not in {"v1", "v2", "gp"}
            or not np.isfinite(threshold)
        ):
            raise ValueError("Infeasible budget, threshold, or run version")
        self.campaign_name = campaign.name
        self.assay_context = dict(campaign.context)
        self._prior = campaign.prior[: len(self._ids)].copy()
        self._chem = campaign.features[: len(self._ids)].copy()
        self._seq = sequence_vectors(campaign.sequence)
        self._noise = campaign.noise
        self._initial = dict(campaign.initial)
        self.budget = budget
        self.seed_count = seed_count
        self.threshold = threshold
        self.version = version
        self.allow_stop = allow_stop
        self.action_space = spaces.Discrete(len(Expert))
        self.observation_space = spaces.Box(
            -1, 1, (len(OBSERVATION),), dtype=np.float32
        )
        self.done = True

    def reset(self, *, seed: int | None = None, options: dict | None = None) -> tuple:
        super().reset(seed=seed)
        if options:
            raise ValueError("Episode options must be declared in the manifest")
        self.__oracle = LabelOracle(self.__labels, self._ids)
        self._belief = make_belief(self.version, self._prior, self._chem, self._noise)
        self._prediction = self._belief.predict()
        self._remaining = np.ones(len(self._ids), dtype=bool)
        self._seq_gap = np.full(len(self._ids), np.inf)
        self._chem_gap = np.full(len(self._ids), np.inf)
        self.ledger = []
        self.done = False
        initial = self._initial.get(seed)
        if initial is None:
            picks = self.np_random.choice(
                len(self._ids), self.seed_count, replace=False
            )
            initial = tuple(self._ids[int(i)] for i in picks)
        if len(initial) != self.seed_count or len(set(initial)) != self.seed_count:
            raise ValueError("Manifest initial assays disagree with episode")
        for sample in initial:
            self._acquire(self._index[sample], "seed")
        return self._observation(), {"seed_ids": tuple(initial)}

    def action_masks(self) -> np.ndarray:
        mask = np.zeros(len(Expert), dtype=bool)
        if not self.done:
            mask[: Expert.LATENT] = True
            mask[Expert.LATENT : Expert.STOP] = self.version != "v1"
            mask[Expert.STOP] = self.allow_stop
        else:
            mask[Expert.STOP] = True
        return mask

    def _observation(self) -> np.ndarray:
        values = self._prediction.mean[self._remaining]
        spread = self._prediction.latent_std
        spread = spread[self._remaining] if spread is not None else np.zeros(1)
        spread = spread if len(spread) else np.zeros(1)
        values = values if len(values) else np.zeros(1)
        observed = [r["observed"] for r in self.ledger]
        remaining = self._remaining.sum()
        return np.array(
            [
                len(observed) / self.budget,
                remaining / len(self._ids),
                np.tanh(max(observed) / 100),
                np.mean(np.array(observed) > self.threshold),
                np.tanh(observed[-1] / 100),
                float(observed[-1] > self.threshold),
                *np.tanh(np.quantile(values, (0.1, 0.5, 0.9)) / 100),
                np.tanh(max(values) / 100),
                *np.tanh(np.quantile(spread, (0.5, 0.9)) / 50),
                np.tanh(np.mean(self._chem_gap[self._remaining])) if remaining else 0,
                self._prediction.fit_label_count / self.budget,
                np.tanh(np.log1p(self.assay_context["dosage_nm"]) / 10),
                np.tanh(np.log1p(self.assay_context["treatment_period_hrs"]) / 5),
            ],
            dtype=np.float32,
        )

    def propose(self, expert: Expert) -> int:
        """Resolve an eligible candidate solely from public/observed evidence."""
        if not self.action_masks()[expert] or expert == Expert.STOP:
            raise ValueError("Masked or non-acquisition expert")
        pool = np.flatnonzero(self._remaining)
        if expert == Expert.RANDOM:
            return int(self.np_random.choice(pool))
        pred = self._prediction
        if expert == Expert.HYBRID:
            priorities = (
                rankdata(pred.mean[pool])
                + rankdata(pred.latent_std[pool])
                + rankdata(self._chem_gap[pool])
            )
        else:
            all_scores = {
                Expert.MEAN: pred.mean,
                Expert.SEQ_DIVERSITY: self._seq_gap,
                Expert.CHEM_DIVERSITY: self._chem_gap,
                Expert.LATENT: pred.latent_std,
                Expert.TOTAL: pred.predictive_std,
                Expert.SOURCE_MEAN: self._prior,
            }
            priorities = all_scores[expert][pool]
        return int(pool[int(np.argmax(priorities))])

    def _acquire(self, index: int, expert: str) -> dict:
        sample = self._ids[index]
        if not self._remaining[index] or len(self.ledger) >= self.budget:
            raise ValueError("Repeated or over-budget measurement")
        (value,) = self.__oracle.reveal((sample,))
        prediction = self._prediction
        self._remaining[index] = False
        self._seq_gap = np.minimum(
            self._seq_gap, np.maximum(1 - self._seq @ self._seq[index], 0)
        )
        self._chem_gap = np.minimum(
            self._chem_gap, np.maximum(1 - self._chem @ self._chem[index], 0)
        )
        self._belief.update(index, value)
        self._prediction = self._belief.predict()
        record = {
            "id": sample,
            "expert": expert,
            "observed": value,
            "predicted_mean": float(prediction.mean[index]),
            "latent_std": None
            if prediction.latent_std is None
            else float(prediction.latent_std[index]),
            "predictive_std": float(prediction.predictive_std[index]),
            "noise_assumption_std": prediction.noise_assumption_std,
            "model_version": prediction.model_version,
            "fit_labels_before": prediction.fit_label_count,
            "hit": bool(value > self.threshold),
            "cost": 1,
            "reward": float(expert != "seed" and value > self.threshold),
            "budget_remaining": self.budget - len(self.ledger) - 1,
        }
        self.ledger.append(record)
        return record

    def step(self, action: int) -> tuple:
        if self.done:
            raise RuntimeError("Reset required")
        if not self.action_space.contains(action) or not self.action_masks()[action]:
            raise ValueError("Invalid action")
        expert = Expert(action)
        if expert == Expert.STOP:
            self.done = True
            return self._observation(), 0.0, True, False, {"terminal_reason": "stop"}
        record = self._acquire(self.propose(expert), expert.name.lower())
        terminated = not self._remaining.any()
        truncated = not terminated and len(self.ledger) == self.budget
        self.done = terminated or truncated
        reason = (
            "pool_exhausted" if terminated else "assay_budget" if truncated else None
        )
        return (
            self._observation(),
            record["reward"],
            terminated,
            truncated,
            {
                **record,
                "terminal_reason": reason,
            },
        )
