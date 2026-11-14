"""Validation of the frozen multi-endpoint reward boundary."""

from dataclasses import replace
from math import nan

import pytest

from oligo_engine.design.reward import (
    Candidate,
    ComplementarityConstraint,
    DisagreementGroup,
    EndpointMetadata,
    LengthConstraint,
    MaxEndpointConstraint,
    MockPredictor,
    MultiEndpointReward,
    NoveltyReference,
    RawPrediction,
    RewardConfig,
)


def metadata(endpoint_id, direction="higher_is_better", chemistry=("PS_2MOE",)):
    return EndpointMetadata(
        endpoint_id=endpoint_id,
        endpoint_kind=endpoint_id,
        modality="ASO",
        direction=direction,
        units="percent",
        chemistry_scope=chemistry,
        label_range=(0.0, 100.0),
        artifact_hash=f"artifact-{endpoint_id}",
        training_hash="fixture-train",
        split_hash="fixture-split",
    )


def adapter(*predictors, **config_kwargs):
    config = RewardConfig(
        required_endpoints=tuple(p.metadata.endpoint_id for p in predictors),
        weights=tuple((p.metadata.endpoint_id, 1.0) for p in predictors),
        **config_kwargs,
    )
    return MultiEndpointReward(
        predictors, config, novelty_reference=NoveltyReference(("AAAA",), "PS_2MOE")
    )


def test_valid_candidate_preserves_raw_prediction_and_composes_reward():
    predictor = MockPredictor(metadata("potency"), 80.0)
    result = adapter(predictor).score(Candidate("AAAA", "ASO", "PS_2MOE"))

    assert result.status == "accepted"
    assert result.reward == 0.8
    assert result.endpoint_scores[0].raw.value == 80.0
    assert result.endpoint_scores[0].raw.units == "percent"
    assert dict(result.provenance)["candidate_hash"] == result.candidate_id


def test_lower_is_better_endpoint_is_inverted_for_reward_only():
    predictor = MockPredictor(metadata("tox", "lower_is_better"), 20.0)
    result = adapter(predictor).score(Candidate("AAAA", "ASO", "PS_2MOE"))

    assert result.status == "accepted"
    assert result.reward == 0.8
    assert result.endpoint_scores[0].raw.value == 20.0


def test_unsupported_chemistry_fails_closed_without_reward():
    predictor = MockPredictor(metadata("potency"), 99.0)
    result = adapter(predictor).score(Candidate("AAAA", "ASO", "2OMe"))

    assert result.status == "rejected"
    assert result.reward is None
    assert "CHEMISTRY_UNSUPPORTED" in result.reason_codes


def test_required_context_is_checked_before_prediction():
    model_metadata = EndpointMetadata(
        **{**metadata("potency").__dict__, "required_context": ("dose",)}
    )
    predictor = MockPredictor(model_metadata, 50.0)
    result = adapter(predictor).score(Candidate("AAAA", "ASO", "PS_2MOE"))

    assert result.status == "rejected"
    assert "MISSING_CONTEXT" in result.reason_codes


def test_novelty_threshold_rejects_out_of_reference_candidate():
    predictor = MockPredictor(metadata("potency"), 80.0)
    reward = adapter(predictor, novelty_threshold=0.0, novelty_penalty=0.1)
    result = reward.score(Candidate("CCCC", "ASO", "PS_2MOE"))

    assert result.status == "rejected"
    assert result.reward is None
    assert "NOVELTY_THRESHOLD" in result.reason_codes


def test_duplicate_endpoint_ids_are_rejected():
    predictor = MockPredictor(metadata("potency"), 80.0)
    with pytest.raises(ValueError, match="unique"):
        MultiEndpointReward(
            (predictor, predictor),
            RewardConfig(("potency",), (("potency", 1.0),)),
        )


def test_raw_clipping_identity_and_repeatability():
    model = MockPredictor(metadata("potency"), 120.0)
    engine = adapter(model)
    first = engine.score(Candidate("AAAA", "ASO", "PS_2MOE"))
    assert first == engine.score(Candidate("AAAA", "ASO", "PS_2MOE"))
    assert first.endpoint_scores[0].raw.value == 120.0
    assert first.endpoint_scores[0].clipped_value == 100.0
    assert first.reward == 1.0
    assert engine.predictor_calls == 2
    changed = engine.score(
        Candidate("AAAA", "ASO", "PS_2MOE", assay_context=(("dose", "1"),))
    )
    assert changed.candidate_id != first.candidate_id


def test_missing_ranges_nonfinite_inputs_and_duplicate_context_fail():
    with pytest.raises(ValueError, match="range"):
        adapter(MockPredictor(replace(metadata("p"), label_range=None), 1.0))
    with pytest.raises(ValueError, match="finite"):
        RewardConfig(("p",), (("p", nan),))
    with pytest.raises(ValueError, match="context"):
        Candidate(
            "AAAA",
            "ASO",
            "PS_2MOE",
            target_context=(("dose", "1"),),
            assay_context=(("dose", "2"),),
        )
    with pytest.raises(ValueError, match="reference"):
        NoveltyReference(("AAAA", "AAA"), "PS_2MOE")


def test_nonfinite_and_wrong_unit_predictions_fail_closed():
    class Bad:
        metadata = metadata("potency")

        def __init__(self, raw):
            self.raw = raw

        def predict(self, candidate):
            return self.raw

    candidate = Candidate("AAAA", "ASO", "PS_2MOE")
    for raw in (
        RawPrediction(nan, "percent"),
        RawPrediction(50, "wrong"),
        RawPrediction(50, "percent", nan, "gp_std"),
    ):
        result = adapter(Bad(raw)).score(candidate)
        assert result.reward is None
        assert "INVALID_PREDICTION" in result.reason_codes
        with pytest.raises(ValueError, match="rejected"):
            adapter(Bad(raw)).policy_reward(candidate)


def test_hard_toxicity_length_and_complementarity_constraints():
    models = (
        MockPredictor(metadata("potency"), 80.0),
        MockPredictor(metadata("tox", "lower_is_better"), 70.0),
    )
    config = RewardConfig(("potency", "tox"), (("potency", 1.0), ("tox", 1.0)))
    engine = MultiEndpointReward(
        models,
        config,
        constraints=(
            LengthConstraint(4, 4),
            MaxEndpointConstraint("tox", 30, "percent"),
            ComplementarityConstraint(),
        ),
    )
    rejected = engine.score(Candidate("AAAA", "ASO", "PS_2MOE"))
    assert rejected.reward is None
    assert "ENDPOINT_LIMIT_EXCEEDED" in rejected.reason_codes
    assert "COMPLEMENTARITY_UNVERIFIED" in rejected.reason_codes
    safe = MultiEndpointReward(
        (models[0], MockPredictor(metadata("tox", "lower_is_better"), 20.0)),
        config,
        constraints=(LengthConstraint(4, 4), ComplementarityConstraint()),
    )
    accepted = safe.score(
        Candidate(
            "AAAA", "ASO", "PS_2MOE", target_context=(("verified_target_site", "TTTT"),)
        )
    )
    assert accepted.reward == pytest.approx(1.6)
    assert all(g.passed for g in accepted.constraints)


def test_disagreement_requires_same_endpoint_and_frozen_normalization():
    first = MockPredictor(replace(metadata("potency"), model_id="a"), 80)
    second = MockPredictor(replace(metadata("potency"), model_id="b"), 20)
    group = DisagreementGroup("potency_pair", ("a", "b"), 0.2)
    config = RewardConfig(
        ("potency",), (("potency", 1.0),), disagreement_groups=(group,)
    )
    engine = MultiEndpointReward((first, second), config)
    result = engine.score(Candidate("AAAA", "ASO", "PS_2MOE"))
    assert result.reward is None
    assert result.disagreements[0].value == pytest.approx(0.6)
    assert result.disagreements[0].status == "rejected"
    with pytest.raises(ValueError, match="Incompatible"):
        MultiEndpointReward(
            (first, MockPredictor(replace(metadata("tox"), model_id="b"), 20)), config
        )
    penalized = MultiEndpointReward(
        (first, second),
        replace(
            config,
            disagreement_groups=(replace(group, disposition="penalize", penalty=0.1),),
        ),
    ).score(Candidate("AAAA", "ASO", "PS_2MOE"))
    assert penalized.reward == pytest.approx(0.4)
    assert ("disagreement:potency_pair", -0.1) in penalized.contributions


def test_novelty_boundaries_and_provenance_invalidation():
    model = MockPredictor(metadata("potency"), 80)
    candidate = Candidate("AAAC", "ASO", "PS_2MOE")
    config = RewardConfig(("potency",), (("potency", 1.0),), novelty_threshold=0.25)
    base = MultiEndpointReward((model,), config, NoveltyReference(("AAAA",), "PS_2MOE"))
    accepted = base.score(candidate)
    assert accepted.novelty.distance == 0.25
    assert accepted.reward == 0.8
    other = MultiEndpointReward(
        (model,), config, NoveltyReference(("CCCC",), "PS_2MOE")
    )
    assert other.score(candidate).reward is None
    assert (
        dict(other.score(candidate).provenance)["reference_hash"]
        != dict(accepted.provenance)["reference_hash"]
    )
    changed_model = MockPredictor(replace(model.metadata, artifact_hash="other"), 80)
    assert (
        dict(
            MultiEndpointReward(
                (changed_model,), config, NoveltyReference(("AAAA",), "PS_2MOE")
            )
            .score(candidate)
            .provenance
        )["model_hash"]
        != dict(accepted.provenance)["model_hash"]
    )
    penalized = MultiEndpointReward(
        (model,),
        replace(config, novelty_disposition="penalize", novelty_penalty=0.1),
        NoveltyReference(("CCCC",), "PS_2MOE"),
    ).score(candidate)
    assert penalized.reward == pytest.approx(0.7)


def test_fixture_parser_and_optional_incompatible_head():
    model = MockPredictor(metadata("potency"), 80)
    tlr = MockPredictor(metadata("tlr", chemistry=("2OMe",)), 20)
    config = RewardConfig(
        ("potency",), (("potency", 1.0),), optional_endpoints=("tlr",)
    )
    engine = MultiEndpointReward((model, tlr), config)
    candidate = Candidate("AAAA", "ASO", "PS_2MOE")
    score = engine.score(candidate)
    assert score.reward == 0.8
    assert score.endpoint_scores[1].raw is None
    invalid = engine.score(Candidate("AA?A", "ASO", "PS_2MOE"))
    assert invalid.reward is None
    assert "PARTIAL_PARSE" in invalid.reason_codes
