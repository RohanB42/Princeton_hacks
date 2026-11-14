"""Matched search costs, reference scope and final-assay isolation."""

import copy
import json
import subprocess
import sys

import pytest

from oligo_engine.rl.evaluate import (
    PolicyPartitions,
    deferred_assay_report,
    paired_summary,
)
from oligo_engine.rl.fixture import fixture_session, fixture_space
from oligo_engine.rl.search import METHODS, search


def test_all_baselines_obey_same_budget_and_reference():
    space = fixture_space()
    reference = search(space, fixture_session(space), "exhaustive")
    assert reference["status"] == "space_exhausted"
    assert reference["best_reward"] == 0.95
    runs = [search(space, fixture_session(space, 4), method) for method in METHODS]
    report = paired_summary(runs, reference)
    assert report["reference_complete"]
    for run in runs:
        assert run["unique_scores"] <= 4
        assert run["head_calls"] == run["unique_scores"] * 2
        assert all(r["candidate"]["start"] in space.reachable() for r in run["archive"])
    broken = copy.deepcopy(runs)
    broken[0]["max_unique"] = 99
    with pytest.raises(ValueError, match="Unpaired"):
        paired_summary(broken, reference)


def test_incomplete_enumeration_does_not_claim_reference_optimum():
    space = fixture_space()
    run = search(space, fixture_session(space, 1), "exhaustive")
    result = paired_summary([run], run)
    assert result["reference_complete"] is False
    assert result["results"][0]["regret"] is None


def test_empty_feasible_set_keeps_undefined_values():
    from dataclasses import replace

    from oligo_engine.reward.scoring import FrozenEndpoint, FrozenScorer, ScoringSession
    from oligo_engine.rl.fixture import ASSAY, fixture_scorer

    space = fixture_space()
    objective = fixture_scorer()._endpoints[0]
    screen = replace(
        objective.manifest,
        model_id="screen",
        endpoint_id="screen",
        role="required_screen",
        maximum=0.0,
        screening_evidence="fixture-only",
    )
    scorer = FrozenScorer(
        (objective, FrozenEndpoint(screen, lambda c, t, a: 1)), "fixture"
    )
    session = ScoringSession(scorer, space.target, ASSAY, 10, 20)
    run = search(space, session, "exhaustive")
    assert run["best_reward"] is None and run["shortlist"] == []
    assert run["feasible_fraction"] == 0.0
    assert run["mean_pairwise_sequence_distance"] is None
    assert all(row["best_reward"] is None for row in run["best_reward_curve"])
    assert paired_summary([run], run)["results"][0]["regret"] is None


def test_final_outcomes_cannot_change_optimization():
    space = fixture_space()
    first = search(space, fixture_session(space, 4), "random", 42)
    selected = tuple(r["score"]["assessment_id"] for r in first["shortlist"])
    good = deferred_assay_report(selected, {key: 10.0 for key in selected})
    bad = deferred_assay_report(selected, {key: -10000.0 for key in selected})
    second = search(space, fixture_session(space, 4), "random", 42)
    assert first["archive"] == second["archive"]
    assert first["trace"] == second["trace"]
    assert good != bad
    assert deferred_assay_report(("unmeasured",), {})["measured_mean"] is None
    with pytest.raises(ValueError, match="disjoint"):
        PolicyPartitions(("x",), ("x",), ("y",))


def test_fixture_cli_writes_honest_receipt_and_refuses_overwrite(tmp_path):
    output = tmp_path / "fixture"
    command = [
        sys.executable,
        "-m",
        "oligo_engine.rl",
        "smoke",
        "--output",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True)
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "synthetic_fixture"
    assert report["reference_optimum"] == 0.95
    assert report["code_revision"] and "code_dirty" in report
    assert subprocess.run(command, capture_output=True).returncode != 0
