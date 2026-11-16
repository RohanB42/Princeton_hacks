"""Complete-proposal controls sharing the same scorer, starts and query costs."""

import random

from .contracts import Campaign, Design
from .scoring import Session, hypervolume


class DesignSpace:
    def __init__(self, campaign: Campaign) -> None:
        self.campaign = campaign
        self.blocks = [
            (p, campaign.target.sites(p.length)) for p in campaign.profile.patterns
        ]
        self.capacity = sum(len(sites) * len(p.terminals) for p, sites in self.blocks)

    def at(self, index: int) -> Design:
        if not 0 <= index < self.capacity:
            raise IndexError(index)
        for pattern, sites in self.blocks:
            width = len(sites) * len(pattern.terminals)
            if index < width:
                site, terminal = divmod(index, len(pattern.terminals))
                return self.campaign.construct(
                    sites[site], pattern.name, pattern.terminals[terminal]
                )
            index -= width
        raise AssertionError("Unreachable design index")

    def sample(self, rng: random.Random) -> Design:
        return self.at(rng.randrange(self.capacity))

    def neighbors(self, parent: Design) -> list[Design]:
        designs = {}
        for p, sites in self.blocks:
            # Joint chemistry/length alternatives at the same site; local site moves.
            choices = [parent.start]
            if p.name == parent.pattern:
                choices += [parent.start - 1, parent.start + 1]
            for site in choices:
                if site in sites:
                    for terminal in p.terminals:
                        d = self.campaign.construct(site, p.name, terminal, parent.key)
                        if d.key != parent.key:
                            designs[d.key] = d
        return list(designs.values())


def candidate_utility(session: Session, design: Design) -> float:
    score = session.archive[design.key][1]
    if score.eligible and session.campaign.profile.objective == "hypervolume":
        points = tuple(
            s.objectives
            for key, (_, s) in session.archive.items()
            if key != design.key and s.eligible
        )
        reference = session.campaign.profile.hypervolume_reference
        return hypervolume(points + (score.objectives,), reference) - hypervolume(
            points, reference
        )
    return sum(score.objectives) / len(score.objectives) if score.eligible else -1.0


def search(
    session: Session,
    method: str,
    seed: int,
    population: int = 8,
    avoid_repeats: bool = True,
) -> dict:
    """Run to the cap or declared natural completion; no hidden surrogate calls."""
    if method not in {"initial", "random", "greedy", "genetic", "exhaustive", "sweep"}:
        raise ValueError("Unknown conventional optimizer")
    if population < 2:
        raise ValueError("Population must be at least two")
    if avoid_repeats and method in {"random", "greedy"}:
        return _unique_search(session, method, seed)
    rng, space = random.Random(seed), DesignSpace(session.campaign)
    if method == "initial":
        return {
            "method": method,
            "seed": seed,
            "end_reason": "initial_only",
            **session.receipt(),
        }
    if method == "exhaustive" and space.capacity > session.campaign.requests:
        raise ValueError("Exhaustive enumeration must be costed in full")
    proposals = 0
    if method in {"exhaustive", "sweep"}:
        for index in range(space.capacity):
            if not session.remaining:
                break
            design = space.at(index)
            if design.key in session.archive:
                continue
            session.query(design)
            proposals += 1
    elif method == "random":
        # Uniform complete designs, without replacement until space exhausted.
        for index in rng.sample(
            range(space.capacity), min(session.remaining, space.capacity)
        ):
            session.query(space.at(index))
            proposals += 1
    elif method == "greedy":
        parent = max(
            session.parents, key=lambda d: candidate_utility(session, d), default=None
        )
        while session.remaining:
            if parent is None:
                parent = space.sample(rng)
                session.query(parent)
                proposals += 1
            previous = candidate_utility(session, parent)
            neighbors = space.neighbors(parent)
            rng.shuffle(neighbors)
            best = parent
            for d in neighbors:
                if not session.remaining:
                    break
                session.query(d)
                proposals += 1
                if candidate_utility(session, d) > candidate_utility(session, best):
                    best = d
            parent = best if candidate_utility(session, best) > previous else None
    else:
        pool = list(session.parents)
        while session.remaining:
            if len(pool) < population or rng.random() < 0.2:
                d = space.sample(rng)
            else:
                a = max(
                    rng.sample(pool, min(3, len(pool))),
                    key=lambda x: candidate_utility(session, x),
                )
                b = rng.choice(pool)
                pattern = next(
                    p for p in session.campaign.profile.patterns if p.name == b.pattern
                )
                if a.start in session.campaign.target.sites(pattern.length):
                    d = session.campaign.construct(
                        a.start, b.pattern, b.terminal, a.key
                    )
                else:
                    d = space.sample(rng)
                neighbors = space.neighbors(d)
                if neighbors and rng.random() < 0.5:
                    d = rng.choice(neighbors)
            session.query(d)
            proposals += 1
            pool = list({x.key: x for x in pool + [d]}.values())
            pool.sort(key=lambda x: (-candidate_utility(session, x), x.key))
            pool = pool[:population]
    return {
        "method": method,
        "optimizer_version": "original-v1",
        "seed": seed,
        "proposal_count": proposals,
        "end_reason": "request_budget" if not session.remaining else "space_enumerated",
        "sampling": "uniform_complete_designs_without_replacement"
        if method == "random"
        else None,
        "population": population if method == "genetic" else None,
        **session.receipt(),
    }


def _unique_search(session: Session, method: str, seed: int) -> dict:
    """Use queried history without spending requests on known deterministic scores."""
    rng, space = random.Random(seed), DesignSpace(session.campaign)
    remaining = {
        d.key: d for d in session.campaign.designs() if d.key not in session.archive
    }
    proposals = reused = restarts = 0
    if method == "random":
        keys = list(remaining)
        # One uniform permutation gives consistent prefixes at different budgets.
        rng.shuffle(keys)
        for key in keys:
            if not session.remaining:
                break
            session.query(remaining.pop(key))
            proposals += 1
    else:
        parent = max(
            session.parents, key=lambda d: candidate_utility(session, d), default=None
        )
        while session.remaining and remaining:
            if parent is None:
                key = rng.choice(list(remaining))
                parent = remaining.pop(key)
                session.query(parent)
                proposals += 1
                restarts += 1
            previous = candidate_utility(session, parent)
            neighbors = space.neighbors(parent)
            rng.shuffle(neighbors)
            best = parent
            for design in neighbors:
                if design.key not in session.archive:
                    if not session.remaining:
                        break
                    session.query(design)
                    remaining.pop(design.key)
                    proposals += 1
                else:
                    reused += 1
                if candidate_utility(session, design) > candidate_utility(
                    session, best
                ):
                    best = design
            parent = best if candidate_utility(session, best) > previous else None
    return {
        "method": method,
        "seed": seed,
        "optimizer_version": "queried-history-v2",
        "proposal_count": proposals,
        "cached_neighbor_reads": reused,
        "restarts": restarts,
        "sampling": "uniform_unqueried_complete_designs_without_replacement"
        if method == "random"
        else "multistart_greedy_using_queried_history",
        "end_reason": "request_budget" if not session.remaining else "space_enumerated",
        **session.receipt(),
    }
