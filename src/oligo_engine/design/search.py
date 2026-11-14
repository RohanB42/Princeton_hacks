"""Bounded search comparators using the same candidate domain and scorer."""

from random import Random

from oligo_engine.design.huesken_bundle import BASES
from oligo_engine.design.scoring import FrozenRidgeScorer, ScoreResult


def mutate(sequence: str, rng: Random) -> str:
    position = rng.randrange(len(sequence))
    replacement = rng.choice(
        tuple(base for base in BASES if base != sequence[position])
    )
    return sequence[:position] + replacement + sequence[position + 1 :]


def hamming(a: str, b: str) -> int:
    if len(a) != len(b):
        raise ValueError("Hamming distance requires equal length")
    return sum(left != right for left, right in zip(a, b, strict=True))


def random_candidate(starts: tuple[str, ...], rng: Random, edit_budget: int) -> str:
    sequence = rng.choice(starts)
    for _ in range(rng.randrange(edit_budget + 1)):
        sequence = mutate(sequence, rng)
    return sequence


def search(
    method: str,
    scorer: FrozenRidgeScorer,
    starts: tuple[str, ...],
    unique_budget: int,
    seed: int,
    edit_budget: int = 8,
) -> dict:
    if method not in {"random", "evolutionary"}:
        raise ValueError("Unknown search baseline")
    if unique_budget < 1 or edit_budget < 0 or not starts:
        raise ValueError("Invalid baseline budget or starts")
    rng = Random(seed)
    trace = []
    incumbent = rng.choice(starts)
    incumbent_start = incumbent
    incumbent_score: ScoreResult | None = None
    best: ScoreResult | None = None
    request_cap = max(100, unique_budget * 20)
    while scorer.unique_evaluations < unique_budget and scorer.requests < request_cap:
        if method == "random":
            proposal = random_candidate(starts, rng, edit_budget)
        elif incumbent_score is None or rng.random() < 0.1:
            incumbent_start = rng.choice(starts)
            incumbent = incumbent_start
            incumbent_score = None
            proposal = incumbent
        else:
            proposal = mutate(incumbent, rng)
            if hamming(proposal, incumbent_start) > edit_budget:
                continue
        was_new = proposal not in scorer.cache
        score = scorer.score(proposal)
        if method == "evolutionary" and (
            incumbent_score is None or score.reward >= incumbent_score.reward
        ):
            incumbent, incumbent_score = proposal, score
        if best is None or score.reward > best.reward:
            best = score
        if was_new:
            trace.append(
                {
                    "unique_scores": scorer.unique_evaluations,
                    "requests": scorer.requests,
                    "best_reward": best.reward,
                    "best_raw_prediction": best.raw_prediction,
                }
            )
    return {
        "method": method,
        "seed": seed,
        "unique_budget": unique_budget,
        "unique_scores": scorer.unique_evaluations,
        "requests": scorer.requests,
        "request_cap": request_cap,
        "status": "complete"
        if scorer.unique_evaluations == unique_budget
        else "request_cap_reached",
        "best_sequence": best.sequence if best is not None else None,
        "best_reward": best.reward if best is not None else None,
        "best_raw_prediction": best.raw_prediction if best is not None else None,
        "trace": trace,
    }
