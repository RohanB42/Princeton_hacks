"""Charge every intermediate local move for conventional search proposals."""

from oligo_engine.design.aso_space import ASODesignSpace
from oligo_engine.design.candidates import Candidate
from oligo_engine.reward.scoring import BudgetExhausted, CandidateScore, ScoringSession


class LocalScoringSession(ScoringSession):
    """All optimizers share ±1 access, horizon, reset and cache/request accounting.

    A jump proposal is executed as local moves; scoring each intermediate candidate
    charges the same information and motion as the environment. Budget exhaustion
    leaves the last valid position. Genetic search here proposes endpoints, but no
    free teleportation is permitted. Use a fresh session for each optimizer run.
    """

    def __init__(self, space: ASODesignSpace, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.target != space.target:
            raise ValueError("Local session target mismatch")
        self.space, self.position, self.moves = space, None, 0

    def score(self, candidate: Candidate) -> CandidateScore:
        if candidate != self.space.candidate(candidate.start):
            raise ValueError("Candidate differs from shared design space")
        if self.position is None:
            if candidate.start != self.space.start:
                raise ValueError("First evaluation must be the common start")
            result = super().score(candidate)
            self.position = candidate.start
            return result
        if candidate.start == self.position:
            return super().score(candidate)
        while self.position != candidate.start:
            if self.moves >= self.space.horizon:
                raise BudgetExhausted("Shared local movement horizon exhausted")
            next_position = self.position + (
                1 if candidate.start > self.position else -1
            )
            result = super().score(self.space.candidate(next_position))
            self.position, self.moves = next_position, self.moves + 1
        return result

    def receipt(self) -> dict:
        return super().receipt() | {
            "proposal_access": "local_plus_minus_one",
            "movement_horizon": self.space.horizon,
            "moves": self.moves,
            "last_position": self.position,
            "space_identity": self.space.identity,
        }
