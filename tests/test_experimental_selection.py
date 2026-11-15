"""Measured replay isolation and analytic UQ invariants."""

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
pytest.importorskip("gymnasium")

from gymnasium.utils.env_checker import check_env  # noqa: E402

from oligo_engine.experimental_rl.belief import (  # noqa: E402
    FrozenBelief,
    GPBelief,
    LinearBelief,
    uncertainty_metrics,
)
from oligo_engine.experimental_rl.cohort import disjoint, sequence_groups  # noqa: E402
from oligo_engine.experimental_rl.environment import (  # noqa: E402
    Campaign,
    ExperimentalSelectionEnv,
    Expert,
)


def toy(version="v1", labels=None, budget=7, allow_stop=False):
    pool = tuple("abcdefghij")
    campaign = Campaign(
        "test",
        "train",
        {"dosage_nm": 25, "treatment_period_hrs": 48},
        pool,
        ("sentinel",),
        np.arange(11.0) * 10,
        np.eye(11, 4),
        tuple("ACGU"[i % 4] * 19 for i in range(10)),
        10.0,
        {7: ("a", "b")},
    )
    y = {key: float(i * 12) for i, key in enumerate(pool)}
    return ExperimentalSelectionEnv(
        campaign,
        y if labels is None else labels,
        budget,
        2,
        80.0,
        version,
        allow_stop=allow_stop,
    )


def test_mask_checks_and_stop_semantics():
    env = toy()
    env.reset(seed=7)
    assert env.action_masks().tolist() == [True] * 4 + [False] * 5
    with pytest.raises(ValueError):
        env.step(Expert.LATENT)
    assert len(env.ledger) == 2
    full_pool = toy(budget=10)
    full_pool.reset(seed=7)
    for _ in range(8):
        _, _, done, truncated, info = full_pool.step(Expert.MEAN)
    assert done and not truncated and info["terminal_reason"] == "pool_exhausted"
    stop = toy("v2", allow_stop=True)
    check_env(stop, skip_render_check=True)
    stop.reset(seed=7)
    _, reward, terminated, truncated, _ = stop.step(Expert.STOP)
    assert terminated and not truncated and reward == 0
    assert len(stop.ledger) == 2


def test_randomized_replays_respect_budget_and_recorded_truth():
    rng = np.random.default_rng(31)
    y = {key: float(i * 12) for i, key in enumerate("abcdefghij")}
    for seed in range(100):
        env = toy("v1" if seed % 2 else "v2", y)
        obs, _ = env.reset(seed=seed)
        assert env.observation_space.contains(obs)
        for i in range(5):
            action = int(rng.choice(np.flatnonzero(env.action_masks())))
            obs, reward, done, truncated, info = env.step(action)
            assert env.observation_space.contains(obs)
            assert info["observed"] == y[info["id"]]
            assert reward == (y[info["id"]] > 80)
            assert not done and truncated == (i == 4)
        assert len({r["id"] for r in env.ledger}) == 7
        with pytest.raises(RuntimeError):
            env.step(Expert.RANDOM)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_poisoned_hidden_labels_affect_only_post_purchase_evidence(version):
    y = {key: float(i * 12) for i, key in enumerate("abcdefghij")}
    left, right = toy(version, y), toy(version, y | {"c": 10_000.0})
    before_left, _ = left.reset(seed=7)
    before_right, _ = right.reset(seed=7)
    np.testing.assert_array_equal(before_left, before_right)
    for _ in range(3):
        step1 = left.step(Expert.MEAN)
        step2 = right.step(Expert.MEAN)
        np.testing.assert_array_equal(step1[0], step2[0])
        assert step1[1:] == step2[1:]
    with pytest.raises(ValueError, match="exactly"):
        toy(version, y | {"sentinel": 1.0})


@pytest.mark.parametrize("kind", [LinearBelief, GPBelief])
def test_gaussian_posterior_matches_known_signal_and_noise(kind):
    mean = np.array([2.0, 2.0])
    # With unit features the residual kernel/prior variance is 2 * std^2.
    model = kind(mean, np.ones((2, 1)), noise=3.0)
    prior = model.predict()
    np.testing.assert_allclose(prior.latent_std**2, 18.0)
    model.update(0, 8.0)
    posterior = model.predict()
    np.testing.assert_allclose(posterior.mean, 6.0)
    np.testing.assert_allclose(posterior.latent_std**2, 6.0)
    np.testing.assert_allclose(posterior.predictive_std**2, 15.0)
    rng = np.random.default_rng(3)
    n = 20000
    draws = rng.normal(6.0, np.sqrt(15.0), n)
    from dataclasses import replace

    pred = replace(
        posterior, mean=np.repeat(6.0, n), predictive_std=np.repeat(np.sqrt(15.0), n)
    )
    metrics = uncertainty_metrics(draws, pred)
    assert metrics["intervals"]["0.9"]["coverage"] == pytest.approx(0.9, abs=0.01)
    assert posterior.aleatoric_std is None  # Noise is explicitly assumption-only.
    frozen = FrozenBelief(mean, 3.0)
    frozen.update(0, 8.0)
    np.testing.assert_array_equal(frozen.predict().mean, mean)


def test_partition_leakage_and_sequence_grouping_fail_closed():
    rows = pd.DataFrame(
        {
            "gene": ["A", "B"],
            "USPTO ID": ["P1", "P2"],
            "compound": ["C1", "C2"],
            "base": ["AAA", "CCC"],
            "scoped_compound": ["P1:7", "P2:7"],
        },
        index=["1", "2"],
    )
    groups = {"source": ["1"], "test": ["2"]}
    disjoint(rows, groups)
    for key in rows:
        poison = rows.copy()
        poison.loc["2", key] = poison.loc["1", key]
        with pytest.raises(ValueError, match="leakage"):
            disjoint(poison, groups)
    g = sequence_groups(["AACGCGAC", "CGCGACTG", "AACGCGAT", "CCCCCCCC"])
    assert g[0] == g[2] and g[0] != g[-1]
