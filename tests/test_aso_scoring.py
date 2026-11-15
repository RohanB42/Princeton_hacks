"""Frozen real-candidate scoring, missingness, raw screens and exact accounting."""

import hashlib
from dataclasses import replace

import pytest

from oligo_engine.reward.atlas import atlas_helm
from oligo_engine.reward.bundle import TrustedArtifact, load_endpoint
from oligo_engine.reward.scoring import (
    BudgetExhausted,
    FrozenEndpoint,
    FrozenScorer,
    ScorerError,
    ScoringSession,
)
from scoring_helpers import (
    ASSAY,
    candidate_panel,
    constant_scorer,
    scoring_session,
)


def test_percentile_ties_missingness_and_cache_cost():
    space = candidate_panel()
    session = scoring_session(space, 1, 3)
    candidate = space.candidate(space.start)
    first = session.score(candidate)
    assert first.reward == 0.15
    assert first.endpoints[0].raw == 1.0
    assert first.endpoints[2].status == "not_applicable"
    assert first.endpoints[3].status == "unavailable"
    assert first.endpoints[3].raw is None
    assert session.score(candidate) is first
    assert (session.requests, session.misses, session.head_calls) == (2, 1, 2)
    with pytest.raises(BudgetExhausted):
        session.score(space.candidate(2))
    assert session.requests == 2
    session.score(candidate)
    with pytest.raises(BudgetExhausted):
        session.score(candidate)


def test_raw_screen_precedes_normalization_and_optional_is_advisory():
    space = candidate_panel()
    objective = constant_scorer()._endpoints[0]
    metadata = replace(
        objective.manifest,
        endpoint_id="tox",
        model_id="tox",
        role="required_screen",
        maximum=7.0,
        screening_evidence="held-out-screen-validation-receipt",
    )
    scorer = FrozenScorer(
        (
            objective,
            FrozenEndpoint(metadata, lambda c, t, a: 20.0),
        ),
        "synthetic",
    )
    score = scorer.score(space.candidate(1), space.target, ASSAY)
    assert score.reward is None
    assert score.endpoints[1].raw == 20.0
    assert score.endpoints[1].reason == "SCREEN_MAXIMUM"
    with pytest.raises(ValueError, match="evidence"):
        replace(metadata, screening_evidence="")
    with pytest.raises(ScorerError, match="unavailable"):
        FrozenScorer((objective, FrozenEndpoint(metadata, None)), "synthetic")


def test_wrong_context_rejects_without_call_and_failures_abort():
    space = candidate_panel()
    scorer = constant_scorer()
    with pytest.raises(ScorerError, match="fixed assay"):
        ScoringSession(scorer, space.target, replace(ASSAY, dosage_nm=11), 10, 20)
    score = scorer.score(space.candidate(1), space.target, replace(ASSAY, dosage_nm=11))
    assert score.reward is None and "ASSAY_UNSUPPORTED" in score.reasons[0]
    for value in (float("nan"), float("inf")):
        bad = FrozenScorer(
            (
                FrozenEndpoint(
                    scorer.manifests[0],
                    lambda c, t, a: value,
                ),
            ),
            "synthetic",
        )
        with pytest.raises(ScorerError, match="Nonfinite"):
            bad.score(space.candidate(1), space.target, ASSAY)

    def broken(c, t, a):
        raise RuntimeError("failed model")

    bad = FrozenScorer((FrozenEndpoint(scorer.manifests[0], broken),), "synthetic")
    session = ScoringSession(bad, space.target, ASSAY, 10, 20)
    with pytest.raises(ScorerError, match="Inference"):
        session.score(space.candidate(1))
    assert session.misses == session.head_calls == 1


def test_manifest_roles_reference_and_scorer_identity():
    base = constant_scorer().manifests[0]
    with pytest.raises(ValueError, match="reference"):
        replace(base, reference=())
    space = candidate_panel()
    session = scoring_session(space)
    session.scorer.identity = "mutated"
    with pytest.raises(ScorerError, match="changed"):
        session.score(space.candidate(1))
    changed = FrozenScorer(
        (
            FrozenEndpoint(
                replace(base, reference=(0.0, 1.0)),
                lambda c, t, a: 1.0,
            ),
        ),
        "synthetic",
    )
    assert changed.identity != constant_scorer().identity


def test_alias_projection_preserves_molecular_tracks_and_original():
    space = candidate_panel()
    candidate = space.candidate(1)
    projected = atlas_helm(candidate, space.target)
    assert "[5meC]" in projected and "[m5C]" in candidate.helm
    assert projected.replace("[5meC]", "[m5C]") == candidate.helm
    assert projected.count("[moe]") == 9
    assert projected.count("[sp]") == 18
    assert projected.endswith(")" + "}$$$$")


def test_trusted_artifact_hash_checked_before_reconstruction(tmp_path):
    path = tmp_path / "model.json"
    path.write_bytes(b'{"constant":1}')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    artifact = TrustedArtifact(path, digest, "source-revision", "explicit-json-loader")
    manifest = replace(constant_scorer().manifests[0], artifact_hash=digest)
    endpoint = load_endpoint(manifest, artifact, lambda raw: lambda c, t, a: 1.0)
    assert endpoint.manifest.artifact_hash == digest
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash"):
        load_endpoint(
            manifest, artifact, lambda raw: pytest.fail("must not reconstruct")
        )


def test_oligogym_frozen_bridge_retains_uncertainty_and_endpoint_identity():
    from oligo_engine.reward.oligogym import OligoGymInference

    class AlreadyFitted:
        def predict(self, candidates):
            return [
                {
                    "endpoint": "potency",
                    "value": 4.0,
                    "uncertainty": 0.2,
                    "uncertainty_type": "gp_latent_sd",
                }
            ]

    space = candidate_panel()
    base = constant_scorer().manifests[0]
    scorer = FrozenScorer(
        (
            FrozenEndpoint(
                base,
                OligoGymInference(AlreadyFitted(), "potency"),
            ),
        ),
        "synthetic-adapter-probe",
    )
    score = scorer.score(space.candidate(1), space.target, ASSAY)
    assert score.endpoints[0].uncertainty == 0.2
    assert score.endpoints[0].uncertainty_type == "gp_latent_sd"
    assert score.endpoints[0].raw == 4.0
    other_assay = scorer.score(
        space.candidate(1),
        space.target,
        replace(ASSAY, dosage_nm=11),
    )
    assert score.candidate_id == other_assay.candidate_id
    assert score.assessment_id != other_assay.assessment_id
