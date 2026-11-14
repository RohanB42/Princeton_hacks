"""Scientific validity of every reachable fixed-template ASO and legal move."""

from dataclasses import replace

import pytest

from oligo_engine.design.aso_space import (
    Action,
    ASODesignSpace,
    TargetContext,
    candidate_identity,
)
from oligo_engine.design.candidates import reverse_complement
from oligo_engine.rl.fixture import fixture_space


def test_all_reachable_candidates_preserve_recognition_and_chemistry():
    space = fixture_space()
    for position in space.reachable():
        c = space.candidate(position)
        assert c.sequence == reverse_complement(space.target.sequence[c.start : c.end])
        assert c.end - c.start == 19
        units = c.helm[5:-5].split(".")
        assert len(units) == 19
        assert sum(u.startswith("[moe]") for u in units) == 9
        assert sum(u.startswith("d(") for u in units) == 10
        assert c.helm.count("[sp]") == 18
        assert not units[-1].endswith("[sp]")
        assert c.helm.count("[m5C]") == c.sequence.count("C")
        candidate_identity(c, space.target)
        for action in Action:
            if space.mask(position, 0)[action]:
                other = space.transition(position, 0, action)
                assert other in space.reachable()


def test_ambiguous_windows_are_barriers_not_enumerated_across():
    target = TargetContext("X", "X.1", "A" * 25 + "N" + "T" * 25, "human", "fixture")
    space = ASODesignSpace(target, 0, radius=50, horizon=50)
    assert space.reachable() == tuple(range(7))
    assert 26 in space.candidates  # Structurally valid, but unreachable across N.
    assert space.mask(6, 1) == (True, True, False)
    with pytest.raises(ValueError, match="Illegal"):
        space.transition(6, 1, Action.RIGHT)


def test_bounds_horizon_and_molecular_identity():
    space = fixture_space(start=0)
    assert space.mask(0, 0) == (True, False, True)
    assert space.mask(0, 8) == (True, False, False)
    c = space.candidate(0)
    with pytest.raises(ValueError, match="pinned"):
        candidate_identity(replace(c, helm=c.helm + "garbage"), space.target)
    assert candidate_identity(c, space.target) != candidate_identity(
        c, replace(space.target, source="new-source")
    )
    for kwargs in ({"start": 99}, {"radius": -1}, {"horizon": 0}, {"radius": 1.5}):
        with pytest.raises(ValueError):
            ASODesignSpace(space.target, **({"start": 0} | kwargs))
