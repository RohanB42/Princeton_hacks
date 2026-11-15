"""Explicit opt-in tests: pytest tests/test_aso_rl_optional.py in the RL runtime."""

from dataclasses import replace

import numpy as np
import pytest

from oligo_engine.design.aso_space import Action
from oligo_engine.reward.scoring import FrozenEndpoint, FrozenScorer, ScoringSession
from oligo_engine.rl.environment import ASOEnv
from oligo_engine.rl.fixture import ASSAY, fixture_session, fixture_space
from oligo_engine.rl.ppo import load_policy, rollout, train, verify_runtime


def test_atlas_label_free_inference_parity_and_chemistry_tracks():
    from oligo_engine.reward.atlas import AtlasInference, atlas_helm
    from oligo_engine.reward.chemistry import parse_helm

    space = fixture_space()
    candidate = space.candidate(1)
    projected = atlas_helm(candidate, space.target)
    parsed = parse_helm(projected)
    assert parsed.sugars == ("MOE",) * 5 + ("DNA",) * 10 + ("MOE",) * 4
    assert parsed.links == ("PS",) * 18 + ("END",)
    assert parsed.bases.count("5meC") == candidate.sequence.count("C")
    assert parsed.terminal == "none"
    with pytest.raises(ValueError):
        parse_helm(candidate.helm)  # Confirm the reported alias mismatch.

    class Predictor:
        def predict(self, frame):
            assert list(frame.columns) == [
                "HELM Annotation",
                "cell_line",
                "cell_line_species",
                "transfection_method",
                "dosage_nm",
                "treatment_period_hrs",
            ]
            assert "Inhibition_pct" not in frame
            assert frame.iloc[0]["HELM Annotation"] == projected
            return np.asarray([42.5])

    predictor = Predictor()
    adapter = AtlasInference(predictor)
    assert adapter(candidate, space.target, ASSAY) == 42.5


def test_reset_move_stop_direct_score_parity_and_masks():
    space = fixture_space(start=0)
    session = fixture_session(space)
    env = ASOEnv(space, session)
    obs, info = env.reset(seed=3)
    assert env.observation_space.contains(obs)
    assert env.action_masks().tolist() == [True, False, True]
    with pytest.raises(ValueError, match="masked"):
        env.step(Action.LEFT)
    obs, reward, terminated, truncated, info = env.step(Action.RIGHT)
    assert reward == 0 and not terminated and not truncated
    assert session.requests == 2 and info["position"] == 1
    direct = session.scorer.score(space.candidate(1), space.target, ASSAY)
    assert info["score"]["reward"] == direct.reward
    obs, reward, terminated, truncated, _ = env.step(Action.STOP)
    assert reward == direct.reward and terminated and not truncated
    assert session.requests == 2  # STOP reuses a scored candidate.
    with pytest.raises(RuntimeError, match="Reset"):
        env.step(Action.STOP)


def test_budget_truncation_is_atomic_and_not_a_rejected_molecule():
    space = fixture_space()
    env = ASOEnv(space, fixture_session(space, max_unique=1))
    before, _ = env.reset(seed=0)
    after, reward, terminated, truncated, info = env.step(Action.RIGHT)
    assert np.array_equal(before, after)
    assert reward == 0 and truncated and not terminated
    assert info["position"] == space.start
    assert info["attempted_position"] == space.start + 1
    assert info["transition_applied"] is False
    assert env.session.misses == 1


def test_horizon_is_terminal_and_rejection_is_finite():
    space = replace(fixture_space(), horizon=1)
    objective = fixture_session(space).scorer._endpoints[0]
    screen = replace(
        objective.manifest,
        endpoint_id="screen",
        model_id="screen",
        role="required_screen",
        maximum=0.0,
        screening_evidence="fixture-only",
    )
    scorer = FrozenScorer(
        (objective, FrozenEndpoint(screen, lambda c, t, a: 1)), "fixture"
    )
    session = ScoringSession(scorer, space.target, ASSAY, 5, 10)
    env = ASOEnv(space, session)
    env.reset()
    obs, reward, terminal, truncated, info = env.step(Action.RIGHT)
    assert terminal and not truncated and reward == -1.0
    assert info["score"]["reward"] is None
    assert env.observation_space.contains(obs)


def test_twenty_base_environment_and_required_chemistry_gate():
    from oligo_engine.reward.portable import CHEMISTRY

    legacy = fixture_space()
    space = replace(legacy, chemistry=CHEMISTRY)
    objective = fixture_session(legacy).scorer._endpoints[0]
    head = FrozenEndpoint(
        replace(objective.manifest, chemistry=CHEMISTRY), lambda c, t, a: 0.5
    )
    scorer = FrozenScorer((head,), "twenty-base-test")
    session = ScoringSession(scorer, space.target, ASSAY, 10, 100)
    env = ASOEnv(space, session)
    observation, _ = env.reset()
    assert observation.shape == (80 + 6 + 3,)
    assert "onehot20x4" in env.observation_schema
    assert env.observation_space.contains(observation)
    observation, _, _, _, _ = env.step(Action.RIGHT)
    assert env.observation_space.contains(observation)
    assert len(space.candidate(env.position).sequence) == 20
    with pytest.raises(ValueError, match="chemistry"):
        ASOEnv(space, fixture_session(legacy))


def test_ppo_learns_known_fixture_optimum_and_reload_identity(tmp_path):
    verify_runtime()
    train_space, validation = fixture_space("TRAIN"), fixture_space("VALIDATION")
    train_env = ASOEnv(train_space, fixture_session(train_space, max_requests=10000))
    val_env = ASOEnv(validation, fixture_session(validation, max_requests=1000))
    model, manifest = train(train_env, val_env, tmp_path / "policy", steps=2048, seed=7)
    final = fixture_space("FINAL")
    env = ASOEnv(final, fixture_session(final))
    first = rollout(model, env)
    loaded = load_policy(tmp_path / "policy", env)
    second = rollout(loaded, ASOEnv(final, fixture_session(final)))
    assert first["terminal_reward"] == 0.95
    assert first["actions"] == second["actions"]
    assert first["archive"] == second["archive"]
    assert manifest["training_cost"]["requests"] > 0
    assert manifest["validation_cost"]["requests"] > 0
    changed = ASOEnv(replace(final, horizon=7), fixture_session(final))
    with pytest.raises(ValueError, match="mismatch"):
        load_policy(tmp_path / "policy", changed)
