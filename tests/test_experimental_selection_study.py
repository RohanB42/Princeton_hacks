"""Capacity, pairing, checkpoint architecture and acquired-label invariants."""

from copy import deepcopy
from dataclasses import replace

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("pandas")
pytest.importorskip("gymnasium")
pytest.importorskip("sb3_contrib")

from oligo_engine.experimental_rl.belief import LinearBelief  # noqa: E402
from oligo_engine.experimental_rl.cohort import (  # noqa: E402
    CampaignCapacityError,
    restrict_pools,
)
from oligo_engine.experimental_rl.environment import (  # noqa: E402
    Campaign,
    ExperimentalSelectionEnv,
    Expert,
)
from oligo_engine.experimental_rl.run import (  # noqa: E402
    rollout,
    sentinel_score,
    train_ppo,
)
from oligo_engine.experimental_rl.study import paired_summary  # noqa: E402


def campaign(name="example", role="train"):
    return Campaign(
        name,
        role,
        {"dosage_nm": 25, "treatment_period_hrs": 48},
        tuple(str(i) for i in range(12)),
        ("sentinel",),
        np.arange(13, dtype=float) * 9,
        np.eye(13, 4),
        tuple("ACGU"[i % 4] * 19 for i in range(12)),
        10.0,
        {7: ("0", "1"), 8: ("1", "2"), 9: ("2", "3")},
    )


def environment(c=None):
    c = c or campaign()
    return ExperimentalSelectionEnv(
        c, {str(i): i * 10.0 for i in range(12)}, 7, 2, 80, "v2"
    )


def test_cap_is_exact_disjoint_deterministic_and_leaves_roles_unchanged():
    rows = [
        {
            "name": f"{role}{i}",
            "key": f"{role}{i}",
            "role": role,
            "pool": [f"{role}{i}:{j}" for j in range(800)],
            "sentinel": [f"{role}{i}:sentinel"],
            "initial": {},
        }
        for role in ("train", "dev", "test")
        for i in range(2)
    ]
    rows.append(
        {
            "name": "small",
            "role": "test",
            "key": "small",
            "pool": ["small"],
            "sentinel": [],
            "initial": {},
        }
    )
    config = {
        "candidate_pool_size": 600,
        "total_assays": 50,
        "initial_assays": 10,
        "evaluation_seeds": [71, 72],
        "partition_seed": 20261114,
    }
    before = deepcopy(rows)
    actual, excluded = restrict_pools(rows, config)
    assert rows == before
    assert (actual, excluded) == restrict_pools(rows, config)
    assert excluded[0]["name"] == "small"
    for entry in actual:
        assert len(entry["pool"]) == len(set(entry["pool"])) == 600
        assert not set(entry["pool"]) & set(entry["sentinel"])
        assert len(entry["initial"]["71"]) == 10
        assert set(entry["initial"]["71"]) <= set(entry["pool"])
    with pytest.raises(CampaignCapacityError, match="Insufficient campaigns"):
        restrict_pools(rows[1:], config)


def test_6000_capacity_failure_cannot_relabel_duplicate_or_repurpose_sentinels():
    rows = [
        {
            "name": f"{role}{i}",
            "key": f"{role}{i}",
            "role": role,
            "pool": [f"{role}{i}:{j}" for j in range(800)],
            "sentinel": [f"{role}{i}:heldout:{j}" for j in range(6000)],
            "initial": {},
        }
        for role in ("train", "dev", "test")
        for i in range(2)
    ]
    before = deepcopy(rows)
    config = {
        "candidate_pool_size": 6000,
        "total_assays": 50,
        "initial_assays": 10,
        "evaluation_seeds": [71],
        "partition_seed": 20261114,
    }
    with pytest.raises(CampaignCapacityError) as failure:
        restrict_pools(rows, config)
    receipt = failure.value.receipt
    assert rows == before
    assert receipt["role_counts"] == {"train": 2, "dev": 0, "test": 0}
    assert len(receipt["capacity_exclusions"]) == 4
    assert not receipt["outcomes_read"] and not receipt["policies_trained"]


def test_larger_evaluation_pools_preserve_training_and_dev_memberships():
    rows = [
        {
            "name": f"{role}{i}",
            "key": f"{role}{i}",
            "role": role,
            "pool": [f"{role}{i}:{j}" for j in range(800)],
            "sentinel": [f"{role}{i}:sentinel"],
            "initial": {},
        }
        for role in ("train", "dev", "test")
        for i in range(3)
    ]
    config = {
        "candidate_pool_size": 600,
        "total_assays": 50,
        "initial_assays": 10,
        "evaluation_seeds": [71, 72],
        "partition_seed": 20261114,
    }
    before = deepcopy(rows)
    original, _ = restrict_pools(rows, config)
    enlarged, excluded = restrict_pools(
        rows, config | {"evaluation_pool_sizes": {"test0": 800, "test1": 700}}
    )
    assert rows == before
    assert [e for e in original if e["role"] != "test"] == [
        e for e in enlarged if e["role"] != "test"
    ]
    final = {e["name"]: e for e in enlarged if e["role"] == "test"}
    assert len(final["test0"]["pool"]) == 800
    assert len(final["test1"]["pool"]) == 700
    assert set(final["test0"]["pool"]) == set(rows[6]["pool"])
    assert final["test0"]["sentinel"] == rows[6]["sentinel"]
    assert excluded[0]["name"] == "test2"
    with pytest.raises(ValueError, match="missing or undersized"):
        restrict_pools(
            rows, config | {"evaluation_pool_sizes": {"test0": 801, "test1": 700}}
        )


def test_online_fit_sees_only_acquired_measurements(monkeypatch):
    updates = []
    original = LinearBelief.update

    def spy(self, index, outcome):
        updates.append((index, outcome))
        original(self, index, outcome)

    monkeypatch.setattr(LinearBelief, "update", spy)
    env = environment()
    env.reset(seed=7)
    assert updates == [(0, 0.0), (1, 10.0)]
    _, _, _, _, record = env.step(Expert.MEAN)
    assert len(updates) == 3
    assert updates[-1] == (int(record["id"]), record["observed"])
    assert record["fit_labels_before"] == 2
    assert record["reward"] == (record["observed"] > 80)


def test_sentinel_truth_cannot_change_decisions_and_reset_isolates_history():
    env = environment()
    first = rollout(env, "mean", 7)
    before = deepcopy(first["ledger"])
    low = sentinel_score(campaign(), {"sentinel": -1000}, before, "v2", [7])
    high = sentinel_score(campaign(), {"sentinel": 1000}, before, "v2", [7])
    assert low != high
    assert before == first["ledger"] == rollout(env, "mean", 7)["ledger"]
    with pytest.raises(ValueError, match="Sentinel capability"):
        sentinel_score(campaign(), {"0": 1}, before, "v2", [7])


def test_pairing_rejects_duplicates_missing_policy_and_changed_initials():
    records = []
    for target in ("a", "b"):
        for seed in (7, 8):
            for method in ("ppo", "random", "mean", "source_mean"):
                for policy in (11, 12) if method == "ppo" else (None,):
                    r = rollout(
                        environment(), "mean" if method == "ppo" else method, seed
                    )
                    r |= {
                        "campaign": target,
                        "method": method,
                        "policy_seed": policy,
                        "candidate_pool_identity": "fixed",
                    }
                    records.append(r)
    report = paired_summary(records, [11, 12])
    assert report["methods"]["ppo"]["ppo_minus_method"] == 0
    assert report["methods"]["mean"]["ppo_minus_method"] == 0
    for broken in (records + [records[0]], records[1:]):
        with pytest.raises(ValueError):
            paired_summary(broken, [11, 12])
    broken = deepcopy(records)
    broken[0]["ledger"][0]["id"] = "wrong_initial"
    with pytest.raises(ValueError, match="Unpaired"):
        paired_summary(broken, [11, 12])


@pytest.mark.parametrize("width", [32, 64])
def test_real_three_layer_checkpoint_reload_and_no_final_training_access(
    tmp_path, width
):
    torch = pytest.importorskip("torch")
    train = [environment(campaign("train1")), environment(campaign("train2"))]
    dev = [
        environment(replace(campaign(), name="dev1", role="dev")),
        environment(replace(campaign(), name="dev2", role="dev")),
    ]
    config = {
        "hidden_layers": [width, width, width],
        "ppo_steps": 1024,
        "ppo_seed": 41,
        "evaluation_seeds": [7, 8, 9],
    }
    model, receipt = train_ppo(train, dev, tmp_path, config)
    for network in (
        model.policy.mlp_extractor.policy_net,
        model.policy.mlp_extractor.value_net,
    ):
        layers = [m for m in network if isinstance(m, torch.nn.Linear)]
        assert [m.out_features for m in layers] == [width, width, width]
    assert receipt["reload_ledger_equal"]
    assert receipt["selected_steps"] == 1024
    assert (tmp_path / "reload_probe.json").exists()
    assert receipt["hidden_layers"] == [width, width, width]
