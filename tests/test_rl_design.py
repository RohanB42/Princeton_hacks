"""Validate the restricted frozen scorer and masked design environment."""

import json
import subprocess
import sys

import numpy as np
import pytest

from oligo_engine.design.huesken_bundle import HueskenRidgeBundle, encode_rna1
from oligo_engine.design.scoring import FrozenRidgeScorer, ToyGScorer


def fake_bundle() -> HueskenRidgeBundle:
    return HueskenRidgeBundle(
        coefficients=(1.0,) * 57,
        intercept=5.0,
        alpha=1.0,
        training_mean=5.0,
        training_sd=2.0,
        training_sequences=("A" * 19, "C" * 19),
        training_ids_sha256="a" * 64,
        source_sha256="b" * 64,
        source_revision="toy_source",
        split_strategy="sequence_group",
        split_seed=0,
        label_description="engineering_fixture",
        sklearn_version="test",
        numpy_version="test",
    )


def test_frozen_bundle_reload_and_restricted_features(tmp_path):
    with pytest.raises(ValueError):
        encode_rna1("A" * 18)
    with pytest.raises(ValueError):
        encode_rna1("N" * 19)
    bundle = fake_bundle()
    path = tmp_path / "bundle.json"
    bundle.save(path)
    loaded = HueskenRidgeBundle.load(path)
    sequences = ("A" * 19, "C" * 19, "G" * 19)
    assert np.array_equal(bundle.predict(sequences), loaded.predict(sequences))
    assert loaded.identity() == bundle.identity()
    scorer = FrozenRidgeScorer(loaded)
    result = scorer.score("G" * 19)
    assert result.nearest_training_distance == 19
    assert result.domain_penalty == pytest.approx(1.5)
    assert result.uncertainty is None
    assert result.provenance.endswith("unvalidated")
    assert scorer.score("G" * 19) == result
    assert scorer.requests == 2 and scorer.unique_evaluations == 1
    tampered = json.loads(path.read_text())
    tampered["target_context_supported"] = True
    path.write_text(json.dumps(tampered))
    with pytest.raises(ValueError):
        HueskenRidgeBundle.load(path)


def test_freeze_uses_training_only_labels_and_existing_feature_encoding(tmp_path):
    output = tmp_path / "frozen"
    subprocess.run(
        [
            sys.executable,
            "scripts/freeze_huesken_ridge.py",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    audit = json.loads((output / "fit_audit.json").read_text())
    assert audit["features_verified_on_all_source_rows"] == 2431
    assert audit["test_labels_used"] is False
    assert audit["split_audit"]["sequence_overlap_groups"] == 0
    assert audit["golden_reload_max_absolute_prediction_error"] < 1e-10
    bundle = HueskenRidgeBundle.load(output / "ridge_bundle.json")
    assert len(bundle.training_sequences) == audit["training_rows"]
    assert bundle.training_ids_sha256 == audit["training_ids_sha256"]


def test_masks_stop_horizon_and_terminal_only_reward():
    pytest.importorskip("gymnasium")
    from oligo_engine.design.environment import BaseEditEnv

    scorer = ToyGScorer(4)
    env = BaseEditEnv(("AAAA",), scorer, edit_budget=2)
    _, _ = env.reset(seed=0)
    assert env.action_masks()[0]
    assert not env.action_masks()[1]
    _, reward, terminated, truncated, _ = env.step(3)
    assert reward == 0 and not terminated and not truncated
    assert scorer.requests == 0
    _, reward, terminated, truncated, info = env.step(7)
    assert terminated and not truncated
    assert reward == 0.5 and info["sequence"] == "GGAA"
    assert scorer.requests == 1
    env.reset()
    _, reward, terminated, _, _ = env.step(0)
    assert terminated and reward == 0.0
    zero = BaseEditEnv(("AAAA",), ToyGScorer(4), edit_budget=0)
    zero.reset()
    assert zero.action_masks().sum() == 1
    _, _, terminated, truncated, _ = zero.step(0)
    assert terminated and not truncated
    env.reset()
    _, reward, terminated, truncated, info = env.step(1)
    assert terminated and not truncated and reward == -1.0
    assert info["invalid_action"] is True


def test_maskable_ppo_toy_smoke_learns_and_reloads(tmp_path):
    pytest.importorskip("sb3_contrib")
    from oligo_engine.design.rl import run_training

    output = tmp_path / "toy"
    report = run_training(output, 11, "toy", None, updates=4, n_steps=128)
    assert report["policy_parameters_changed"]
    assert report["checkpoint_reload_equal"]
    assert report["untrained_validation"]["mean_reward"] < 1.0
    assert report["final_heldout_start_evaluation"]["mean_reward"] == 1.0
    assert (output / "best.zip").stat().st_size > 0
    assert (output / "status.json").read_text().find('"complete"') > 0


def test_restricted_pilot_matches_unique_scorer_budget(tmp_path):
    pytest.importorskip("sb3_contrib")
    from oligo_engine.design.rl import infer_checkpoint, run_training

    frozen = tmp_path / "frozen"
    subprocess.run(
        [sys.executable, "scripts/freeze_huesken_ridge.py", "--output", str(frozen)],
        check=True,
        capture_output=True,
        text=True,
    )
    bundle_path = frozen / "ridge_bundle.json"
    source = HueskenRidgeBundle.load(bundle_path)
    report = run_training(tmp_path / "pilot", 11, "huesken", bundle_path, 1, 64)
    assert report["measured_efficacy_claim"] is False
    assert report["bundle_identity"] == source.identity()
    for method in ("random", "evolutionary"):
        baseline = report["comparators"][method]
        assert baseline["unique_budget"] == report["training_unique_scores"]
        assert baseline["unique_scores"] <= baseline["unique_budget"]
    assert (tmp_path / "pilot" / "search_comparison.png").stat().st_size > 0
    inference = infer_checkpoint(
        tmp_path / "pilot" / "best.zip",
        bundle_path,
        tmp_path / "generated.json",
        "final",
        20,
    )
    assert inference["requested_count"] == 20
    assert inference["returned_count"] <= 16
    assert inference["shortfall"] == 20 - inference["returned_count"]
    assert inference["measured_efficacy_claim"] is False
    assert (
        len({x["sequence"] for x in inference["candidates"]})
        == inference["returned_count"]
    )
    with pytest.raises(FileExistsError):
        infer_checkpoint(
            tmp_path / "pilot" / "best.zip",
            bundle_path,
            tmp_path / "generated.json",
            "final",
            20,
        )
