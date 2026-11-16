"""Explicitly selected tests require real Gymnasium/SB3/Torch, never silently skip."""

from dataclasses import replace

import numpy as np
import pytest

from oligo_engine.molecular_design.bundles import fixture
from oligo_engine.molecular_design.grammar import Token
from oligo_engine.molecular_design.gym_env import MolecularEnv
from oligo_engine.molecular_design.scoring import FrozenRegistry, Head
from oligo_engine.molecular_design.training import (
    TrainingConfig,
    load_policy,
    rollout,
    train,
)


def test_gym_construction_and_schema_inspection_have_no_hidden_predictor_calls():
    c, registry = fixture(requests=3)
    calls = []

    def counted(design, context):
        calls.append(design.key)
        return registry.heads[0].predict(design, context)

    wrapped = FrozenRegistry(
        c.profile,
        (
            Head(registry.heads[0].manifest, counted),
            registry.heads[1],
        ),
    )
    env = MolecularEnv((c,), wrapped)
    assert env.schema_id and not calls
    env.reset(seed=1)
    assert len(calls) == len(c.starts)
    assert env.core.session.requests == len(c.starts)


def test_gym_full_context_history_budget_and_invalid_mask():
    c, r = fixture(requests=3)
    env = MolecularEnv((c,), r)
    obs, _ = env.reset(seed=7)
    assert env.observation_space.contains(obs)
    assert obs["history_mask"].sum() == 1
    first = obs["target"].copy()
    changed = replace(
        c,
        target=replace(
            c.target,
            sequence=c.target.sequence[:-1]
            + ("A" if c.target.sequence[-1] != "A" else "C"),
        ),
    )
    other = MolecularEnv((changed,), r)
    second, _ = other.reset(seed=7)
    assert not np.array_equal(first, second["target"])
    assert env.schema_id == other.schema_id
    with pytest.raises(ValueError):
        env.step(env.core.grammar.tokens.index(Token("COMMIT")))
    assert not env.action_masks()[0]
    while env.core.session.requests == len(c.starts):
        action = int(np.flatnonzero(env.action_masks())[0])
        env.step(action)
    _, reward, terminal, truncated, _ = env.step(0)
    assert reward == 0 and terminal and not truncated


def test_actual_maskable_ppo_train_reload_and_schema_refusal(tmp_path):
    train_c, r = fixture(30, requests=3, partition="training")
    val_c, _ = fixture(31, requests=3, partition="validation")
    result = train(
        (train_c,),
        (val_c,),
        r,
        TrainingConfig(
            5, 64, rollout_tokens=32, batch_size=16, epochs=1, validation_interval=32
        ),
        tmp_path / "policy",
    )
    env = MolecularEnv((val_c,), r)
    model = load_policy(tmp_path / "policy", env)
    a = rollout(model, env, seed=10)
    b = rollout(load_policy(tmp_path / "policy", env), env, seed=10)
    assert a["actions"] == b["actions"]
    assert a["final_quality"] == b["final_quality"]
    assert result["training_requests"] >= 1
    assert [r["tokens"] for r in result["optimization_history"]] == [32, 64]
    assert all(r["metrics"]["value_loss"] >= 0 for r in result["optimization_history"])
    wrong = MolecularEnv((replace(val_c, requests=4),), r)
    with pytest.raises(ValueError, match="schema"):
        load_policy(tmp_path / "policy", wrong)
    from oligo_engine.molecular_design.resume import load_resume

    resumed_env = MolecularEnv((train_c,), r)
    resumed = load_resume(tmp_path / "policy/resume", resumed_env)
    resumed.learn(total_timesteps=32, reset_num_timesteps=False)
    weights = {k: v.detach().clone() for k, v in resumed.policy.state_dict().items()}
    actions = resumed_env.core.actions.copy()
    second_env = MolecularEnv((train_c,), r)
    second = load_resume(tmp_path / "policy/resume", second_env)
    second.learn(total_timesteps=32, reset_num_timesteps=False)
    assert actions == second_env.core.actions
    assert all(
        np.array_equal(v.numpy(), second.policy.state_dict()[k].numpy())
        for k, v in weights.items()
    )


def test_resume_matches_uninterrupted_updates(tmp_path):
    import torch
    from sb3_contrib import MaskablePPO

    from oligo_engine.molecular_design.policy import SearchEncoder
    from oligo_engine.molecular_design.resume import load_resume, save_resume

    torch.set_num_threads(1)
    c, registry = fixture(40, requests=3, partition="training")
    env = MolecularEnv((c,), registry)
    model = MaskablePPO(
        "MultiInputPolicy",
        env,
        seed=8,
        n_steps=16,
        batch_size=8,
        n_epochs=1,
        gamma=1,
        gae_lambda=1,
        policy_kwargs={"features_extractor_class": SearchEncoder},
    )
    model.learn(16)
    save_resume(model, env, tmp_path / "resume")
    model.learn(16, reset_num_timesteps=False)
    expected = {k: v.detach().clone() for k, v in model.policy.state_dict().items()}
    expected_actions = env.core.actions.copy()
    other_env = MolecularEnv((c,), registry)
    restored = load_resume(tmp_path / "resume", other_env)
    restored.learn(16, reset_num_timesteps=False)
    assert expected_actions == other_env.core.actions
    assert all(
        torch.equal(value, restored.policy.state_dict()[key])
        for key, value in expected.items()
    )


def test_legacy_policy_requires_explicit_legacy_schema(tmp_path):
    c, registry = fixture(60, requests=3, partition="training")
    validation, _ = fixture(61, requests=3, partition="validation")
    train(
        (c,),
        (validation,),
        registry,
        TrainingConfig(
            8,
            32,
            rollout_tokens=16,
            batch_size=8,
            epochs=1,
            validation_interval=16,
            decoder="legacy-v1",
        ),
        tmp_path / "legacy",
    )
    legacy = MolecularEnv((validation,), registry, decoder="legacy-v1")
    result = rollout(load_policy(tmp_path / "legacy", legacy), legacy)
    assert result["decoder"] == "legacy-v1"
    fixed = MolecularEnv((validation,), registry)
    assert fixed.schema_id != legacy.schema_id
    with pytest.raises(ValueError, match="schema"):
        load_policy(tmp_path / "legacy", fixed)


def test_untrained_masked_policy_must_complete_a_new_proposal():
    import torch
    from sb3_contrib import MaskablePPO

    from oligo_engine.molecular_design.policy import SearchEncoder

    torch.set_num_threads(1)
    c, registry = fixture(70, requests=4)
    env = MolecularEnv((c,), registry)
    model = MaskablePPO(
        "MultiInputPolicy",
        env,
        seed=11,
        n_steps=16,
        batch_size=8,
        policy_kwargs={"features_extractor_class": SearchEncoder},
    )
    for deterministic in (False, True):
        receipt = rollout(model, env, seed=11, deterministic=deterministic)
        assert receipt["requests"] > len(c.starts)
        assert receipt["requests"] == receipt["unique_designs"]
        assert all(not event["cache_hit"] for event in receipt["trace"])
        assert receipt["episode_return"] == pytest.approx(
            receipt["final_quality"] - receipt["initial_quality"]
        )


def test_candidate_policy_shares_scores_across_sites_and_propagates_gradients():
    from dataclasses import asdict

    import torch
    from sb3_contrib import MaskablePPO

    from oligo_engine.molecular_design.candidate_policy import CandidatePolicy
    from oligo_engine.molecular_design.grammar import Grammar

    torch.set_num_threads(1)
    c, r = fixture(91, requests=3)
    cap = sum(1 for _ in c.designs())
    env = MolecularEnv((c,), r, candidate_capacity=cap)
    obs, _ = env.reset(seed=2)
    assert env.observation_space.contains(obs)
    model = MaskablePPO(
        CandidatePolicy,
        env,
        n_steps=16,
        batch_size=8,
        seed=1,
        policy_kwargs={"action_tokens": [asdict(t) for t in Grammar(c, 32, 3).tokens]},
    )
    policy = model.policy
    tensors, _ = policy.obs_to_tensor(obs)
    latent = torch.zeros((1, policy.mlp_extractor.latent_dim_pi))
    first = policy.candidate_scores(tensors, latent)
    order = torch.arange(cap - 1, -1, -1)
    permuted = {k: v.clone() for k, v in tensors.items()}
    permuted["candidates"] = tensors["candidates"][:, order]
    second = policy.candidate_scores(permuted, latent)
    assert torch.allclose(first[:, order], second)
    # Absolute SITE identities never enter the molecular scorer.
    permuted["candidate_tokens"][:, :, 1] += 1
    assert torch.equal(second, policy.candidate_scores(permuted, latent))
    first.sum().backward()
    assert policy.molecule[0].weight.grad.abs().sum() > 0
    assert policy.action_net.out_features < env.action_space.n
    # Catalog row ordering is not an action preference, including at SITE stage.
    env.step(env.core.grammar.tokens.index(Token("NEW")))
    lengths = np.flatnonzero(env.action_masks())
    obs, _, _, _, _ = env.step(int(lengths[0]))
    obs_t, _ = policy.obs_to_tensor(obs)
    permuted = {k: v.clone() for k, v in obs_t.items()}
    for key in ("candidates", "candidate_tokens", "candidate_mask", "completion_mask"):
        permuted[key] = permuted[key][:, order]
    original = policy.get_distribution(
        obs_t, env.action_masks()
    ).distribution.probs.clone()
    reordered = policy.get_distribution(permuted, env.action_masks()).distribution.probs
    assert torch.allclose(original, reordered, atol=1e-6)
    for _ in range(3):
        legal = env.action_masks()
        obs_t, _ = policy.obs_to_tensor(obs)
        actions, _, logp = policy(obs_t, action_masks=legal)
        _, reevaluated, entropy = policy.evaluate_actions(
            obs_t, actions, action_masks=legal
        )
        assert torch.allclose(logp, reevaluated) and torch.isfinite(entropy).all()
        obs, _, done, _, _ = env.step(int(actions[0]))
        if done:
            break


def test_forced_collapse_preserves_every_action_query_and_reward():
    c, r = fixture(92, requests=4)
    plain = MolecularEnv((c,), r)
    collapsed = MolecularEnv((c,), r, collapse_forced=True)
    plain.reset(seed=1)
    collapsed.reset(seed=1)
    total = 0
    while not collapsed.core.done:
        # Avoid STOP to test all proposals and terminal forced COMMIT.
        legal = np.flatnonzero(collapsed.action_masks())
        action = int(next((a for a in legal if a != 0), legal[0]))
        before = len(collapsed.core.actions)
        _, reward, _, _, _ = collapsed.step(action)
        replay_reward = 0
        for event in collapsed.core.actions[before:]:
            _, earned, _, _, _ = plain.step(event["action"])
            replay_reward += earned
        assert reward == pytest.approx(replay_reward)
        total += reward
    assert plain.core.actions == collapsed.core.actions
    assert total == pytest.approx(
        collapsed.core.session.quality - collapsed.core.session.initial_quality
    )
    assert collapsed.policy_decisions < collapsed.core.steps
    assert collapsed.core.session.requests == c.requests


def test_candidate_catalog_is_score_blind_and_exactly_encodes_antisense():
    c, registry = fixture(96, requests=3)
    calls = []

    def counted(design, context):
        calls.append(design.key)
        return registry.heads[0].predict(design, context)

    wrapped = FrozenRegistry(
        c.profile, (Head(registry.heads[0].manifest, counted), registry.heads[1])
    )
    cap = sum(1 for _ in c.designs())
    env = MolecularEnv((c,), wrapped, candidate_capacity=cap)
    assert not calls
    obs, _ = env.reset(seed=1)
    assert len(calls) == len(c.starts)
    for row, design in zip(obs["candidates"], c.designs(), strict=True):
        assert (
            "".join("ACGT"[i] for i in row[: len(design.sequence), :4].argmax(1))
            == design.sequence
        )
        assert not row[len(design.sequence) :].any()
    for _ in range(5):
        env._observation()
    assert len(calls) == len(c.starts)
    with pytest.raises(ValueError, match="every legal design"):
        MolecularEnv((c,), wrapped, candidate_capacity=cap - 1)


def test_candidate_pretraining_reload_resume_and_partition_boundary(tmp_path):
    import torch

    from oligo_engine.molecular_design.pretraining import pretrain_candidates
    from oligo_engine.molecular_design.resume import load_resume, save_resume

    c, r = fixture(93, requests=3, partition="training")
    v, _ = fixture(94, requests=3, partition="validation")
    cap = sum(1 for _ in c.designs())
    config = TrainingConfig(
        8,
        32,
        rollout_tokens=16,
        batch_size=8,
        epochs=1,
        validation_interval=16,
        policy="candidate-v3",
        candidate_capacity=cap,
        collapse_forced=True,
        pretrain_requests=8,
        pretrain_epochs=2,
    )
    result = train((c,), (v,), r, config, tmp_path / "policy")
    assert result["pretraining_requests"] == 8
    env = MolecularEnv((v,), r, candidate_capacity=cap, collapse_forced=True)
    model = load_policy(tmp_path / "policy", env)
    a = rollout(model, env, seed=10)
    b = rollout(load_policy(tmp_path / "policy", env), env, seed=10)
    assert a["actions"] == b["actions"]
    with pytest.raises(ValueError, match="training campaigns"):
        pretrain_candidates(model.policy, (v,), r, tmp_path, 1, 8, 2)
    training_env = MolecularEnv((c,), r, candidate_capacity=cap, collapse_forced=True)
    continued = load_resume(tmp_path / "policy/resume", training_env)
    save_resume(continued, training_env, tmp_path / "boundary")
    continued.learn(16, reset_num_timesteps=False)
    expected = {k: t.detach().clone() for k, t in continued.policy.state_dict().items()}
    other = MolecularEnv((c,), r, candidate_capacity=cap, collapse_forced=True)
    restored = load_resume(tmp_path / "boundary", other)
    restored.learn(16, reset_num_timesteps=False)
    assert other.core.actions == training_env.core.actions
    assert other.policy_decisions == training_env.policy_decisions
    assert all(
        torch.equal(t, restored.policy.state_dict()[k]) for k, t in expected.items()
    )
