"""Scientific allocation invariants for independent non-RL studies."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from oligo_engine.research.__main__ import load_catalog
from oligo_engine.research.budgets import nested_budget_plan


def pool():
    return [{"id": f"row-{i:03d}", "group": f"patent-{i // 10}"} for i in range(100)]


def test_nested_fit_and_validation_membership_and_label_accounting():
    plan = nested_budget_plan(pool(), [10, 20, 50, 100], 12)
    assert set(plan["fit_groups"]).isdisjoint(plan["validation_groups"])
    group = {r["id"]: r["group"] for r in pool()}
    last_fit, last_val = set(), set()
    for allocation in plan["allocations"]:
        fit, val = set(allocation["fit_ids"]), set(allocation["validation_ids"])
        assert fit.isdisjoint(val)
        assert len(fit | val) == allocation["labels_total"]
        assert last_fit <= fit and last_val <= val
        assert {group[i] for i in fit}.isdisjoint({group[i] for i in val})
        last_fit, last_val = fit, val
    assert len(last_fit | last_val) == 100


def test_order_independence_and_budget_extension_do_not_change_old_ids():
    first = nested_budget_plan(pool(), [10, 20], 42)
    second = nested_budget_plan(list(reversed(pool())), [10, 20, 50], 42)
    assert first["pool_metadata_sha256"] == second["pool_metadata_sha256"]
    assert first["allocations"] == second["allocations"][:2]
    assert first["validation_groups"] == second["validation_groups"]


def test_reject_labels_duplicates_and_evaluation_ids():
    with pytest.raises(ValueError, match="no labels"):
        nested_budget_plan([r | {"Inhibition_pct": 50} for r in pool()], [10], 0)
    with pytest.raises(ValueError, match="unique"):
        nested_budget_plan(pool() + pool()[:1], [10], 0)
    with pytest.raises(ValueError, match="excluded"):
        nested_budget_plan(pool(), [10], 0, excluded_ids=["row-000"])


@pytest.mark.parametrize("budgets", [[20, 10], [10, 10], [1], [], [10.5], [True]])
def test_invalid_budgets_fail(budgets):
    with pytest.raises(ValueError):
        nested_budget_plan(pool(), budgets, 0)


def test_unbalanced_group_capacity_fails_without_changing_partition():
    records = [
        {"id": str(i), "group": "large" if i < 99 else "small"} for i in range(100)
    ]
    with pytest.raises(ValueError, match="fixed partition capacity"):
        nested_budget_plan(records, [100], 0)


def test_single_group_rejected():
    with pytest.raises(ValueError, match="two groups"):
        nested_budget_plan([r | {"group": "one"} for r in pool()], [10], 0)


def test_catalog_and_cli_no_overwrite(tmp_path):
    studies = load_catalog(Path("configs/research/studies.toml"))
    assert {s["track"] for s in studies} >= {
        "prediction-and-transfer",
        "experimental-selection",
        "robustness-and-augmentation",
    }
    source, output = tmp_path / "pool.json", tmp_path / "plan.json"
    source.write_text(json.dumps({"records": pool(), "excluded_ids": ["held-out"]}))
    command = [
        sys.executable,
        "-m",
        "oligo_engine.research",
        "plan",
        "--pool",
        str(source),
        "--output",
        str(output),
        "--budgets",
        "10",
        "20",
        "--seed",
        "7",
    ]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    original = output.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode != 0
    assert output.read_bytes() == original
    assert json.loads(original)["status"] == "allocation_only_no_training_or_results"
