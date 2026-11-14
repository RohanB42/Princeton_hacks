"""Frozen surrogate and toy reward interfaces for sequence-design experiments."""

import hashlib
import json
from dataclasses import asdict, dataclass
from math import isfinite, tanh

from oligo_engine.design.huesken_bundle import HueskenRidgeBundle, encode_rna1


@dataclass(frozen=True)
class ScoreResult:
    sequence: str
    raw_prediction: float
    utility: float
    nearest_training_distance: int | None
    domain_penalty: float
    reward: float
    uncertainty: float | None
    provenance: str


class FrozenRidgeScorer:
    """Fixed Huesken scorer with explicit source-domain penalty and cache."""

    def __init__(self, bundle: HueskenRidgeBundle, penalty_per_base: float = 0.1):
        if not isfinite(penalty_per_base) or penalty_per_base < 0:
            raise ValueError("Domain penalty must be finite and nonnegative")
        self.bundle = bundle
        self.penalty_per_base = penalty_per_base
        self.requests = 0
        self.cache: dict[str, ScoreResult] = {}
        self.identity = hashlib.sha256(
            json.dumps(
                {
                    "bundle": bundle.identity(),
                    "utility": "tanh_training_mean_sd",
                    "domain_penalty": "max_zero_nearest_hamming_minus_four",
                    "penalty_per_base": penalty_per_base,
                    "version": 1,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()

    @property
    def unique_evaluations(self) -> int:
        return len(self.cache)

    def score(self, sequence: str) -> ScoreResult:
        encode_rna1(sequence)
        self.requests += 1
        if sequence not in self.cache:
            predicted = float(self.bundle.predict((sequence,))[0])
            distance = self.bundle.nearest_training_distance(sequence)
            utility = tanh(
                (predicted - self.bundle.training_mean) / self.bundle.training_sd
            )
            penalty = self.penalty_per_base * max(0, distance - 4)
            reward = utility - penalty
            if not all(isfinite(x) for x in (predicted, utility, penalty, reward)):
                raise ValueError("Nonfinite frozen scorer output")
            self.cache[sequence] = ScoreResult(
                sequence=sequence,
                raw_prediction=predicted,
                utility=utility,
                nearest_training_distance=distance,
                domain_penalty=penalty,
                reward=reward,
                uncertainty=None,
                provenance="frozen_Huesken_Ridge_prediction_unvalidated",
            )
        return self.cache[sequence]

    def records(self) -> list[dict]:
        return [asdict(item) for item in self.cache.values()]


class ToyGScorer:
    """Deterministic engineering-only toy with an obvious optimum."""

    def __init__(self, length: int = 4):
        if length < 1:
            raise ValueError("Toy length must be positive")
        self.length = length
        self.requests = 0
        self.cache: dict[str, ScoreResult] = {}
        self.identity = f"toy_count_G_v1_length_{length}"

    @property
    def unique_evaluations(self) -> int:
        return len(self.cache)

    def score(self, sequence: str) -> ScoreResult:
        if len(sequence) != self.length or set(sequence) - set("ACGU"):
            raise ValueError("Invalid toy sequence")
        self.requests += 1
        if sequence not in self.cache:
            utility = sequence.count("G") / self.length
            self.cache[sequence] = ScoreResult(
                sequence=sequence,
                raw_prediction=utility,
                utility=utility,
                nearest_training_distance=None,
                domain_penalty=0.0,
                reward=utility,
                uncertainty=None,
                provenance="synthetic_engineering_fixture",
            )
        return self.cache[sequence]
