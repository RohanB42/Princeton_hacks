"""Scientific invariants for artifact-only, paired PPO attribution."""

import runpy
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from oligo_engine.molecular_design.artifacts import QueryJournal

MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/molecular_ppo_attribution.py")
)


def example():
    return {
        "campaign_id": "campaign",
        "registry_id": "registry",
        "requests": 3,
        "initial_quality": 0.2,
        "final_quality": 0.7,
        "trace": [
            {
                "request": i + 1,
                "design_id": str(i),
                "quality": q,
                "initial": i == 0,
                "status": "scored",
                "cache_hit": False,
            }
            for i, q in enumerate([0.2, 0.4, 0.7])
        ],
    }


def test_incomplete_trajectories_cannot_silently_pad():
    run = example()
    run["trace"].pop()
    with pytest.raises(ValueError, match="Incomplete"):
        MODULE["trajectory"](run, 3)


@pytest.mark.parametrize("change", ["decrease", "duplicate", "nonfinite"])
def test_invalid_archive_trajectories_rejected(change):
    run = example()
    if change == "decrease":
        run["trace"][1]["quality"] = 0.1
    elif change == "duplicate":
        run["trace"][1]["design_id"] = "0"
    else:
        run["trace"][1]["quality"] = float("nan")
    with pytest.raises(ValueError):
        MODULE["trajectory"](run, 3)


def test_pairing_requires_common_start_and_registry():
    left = example()
    right = deepcopy(left)
    right["trace"][1]["quality"] = 0.5
    assert MODULE["paired_difference"](left, right) == pytest.approx([0, -0.1, 0])
    right["trace"][0]["design_id"] = "different"
    with pytest.raises(ValueError, match="starting archive"):
        MODULE["paired_difference"](left, right)
    right = deepcopy(left)
    right["registry_id"] = "different"
    with pytest.raises(ValueError, match="registry"):
        MODULE["paired_difference"](left, right)


def test_shared_seed_dependence_is_not_independently_resampled_within_target():
    # Twenty targets share exactly the same five trained-policy effects. Adding
    # target rows cannot manufacture twenty independent copies of each policy.
    matrix = np.tile(np.arange(5, dtype=float), (20, 1))
    result = MODULE["crossed_resample"](matrix, 2000, 7)
    low, high = result["crossed_resampling_95_percent_range"]
    assert high - low >= 2.0
    assert result["seed_aggregate_sd"] == pytest.approx(np.std(range(5), ddof=1))
    assert result["target_aggregate_sd"] == 0


def test_valid_sealed_journal_must_match_receipt_and_chain(tmp_path):
    path = tmp_path / "query.jsonl"
    journal = QueryJournal(path)
    journal({"request": 1})
    journal({"request": 2})
    MODULE["journal_matches"](path, [{"request": 1}, {"request": 2}])
    with pytest.raises(ValueError, match="differ"):
        MODULE["journal_matches"](path, [{"request": 1}])
    lines = path.read_text().splitlines()
    path.write_text("\n".join(reversed(lines)) + "\n")
    with pytest.raises(ValueError, match="chain"):
        MODULE["journal_events"](path)


def test_cumulative_head_calls_are_counted_once_per_episode_including_partial():
    events = [
        {"request": 1, "head_calls": {"a": 1, "b": 1}},
        {"request": 2, "head_calls": {"a": 2, "b": 2}},
        {"request": 3, "head_calls": {"a": 3, "b": 3}},
        {"request": 1, "head_calls": {"a": 1, "b": 1}},
    ]
    assert MODULE["journal_head_calls"](events) == 8
    events[2]["request"] = 4
    with pytest.raises(ValueError, match="counters"):
        MODULE["journal_head_calls"](events)
