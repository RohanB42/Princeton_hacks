"""Portable inference, exact profile gating, and equal local scoring access."""

import hashlib
import json
from dataclasses import asdict, replace

import pytest

from oligo_engine.design.aso_space import ASODesignSpace, TargetContext
from oligo_engine.design.candidates import build_helm
from oligo_engine.reward.atlas import atlas_helm
from oligo_engine.reward.portable import CHEMISTRY, PortableEfficacy, supported_sequence
from oligo_engine.reward.scoring import BudgetExhausted, ScoringSession
from oligo_engine.rl.fixture import ASSAY, fixture_scorer, fixture_space
from oligo_engine.rl.local_costs import LocalScoringSession
from oligo_engine.rl.search import search


def bundle(tmp_path):
    raw = {
        "schema": "supported-aso-ridge-v1",
        "chemistry": CHEMISTRY,
        "assay": asdict(ASSAY),
        "coefficients": [float(i) / 100 for i in range(80)],
        "intercept": 3.0,
        "training_prediction_reference": [0.0, 5.0, 10.0],
        "training_sequences": ["ACGT" * 5],
        "training_ids": ["train-only"],
        "split_hash": "fixture-split",
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(raw))
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_explicit20_template_and_alias_preserve_structure():
    target = TargetContext("G", "G.1", "ACGT" * 12, "synthetic", "fixture")
    space = ASODesignSpace(target, 1, chemistry=CHEMISTRY)
    assert space.length == 20
    candidate = space.candidate(1)
    assert supported_sequence(candidate.helm) == candidate.sequence
    assert supported_sequence(atlas_helm(candidate, target)) == candidate.sequence
    with pytest.raises(ValueError, match="20-mer"):
        supported_sequence(build_helm("A" * 19, "ps_moe_gapmer"))
    with pytest.raises(ValueError, match="chemistry"):
        supported_sequence(candidate.helm.replace("[sp]", "p", 1))
    with pytest.raises(ValueError, match="chemistry"):
        supported_sequence(candidate.helm.replace("[m5C]", "C"))


def test_bundle_hash_assay_and_direct_scorer_parity(tmp_path):
    path, sha = bundle(tmp_path)
    model = PortableEfficacy(path, sha)
    target = TargetContext("G", "G.1", "ACGT" * 12, "synthetic", "fixture")
    space = ASODesignSpace(target, 1, chemistry=CHEMISTRY)
    c = space.candidate(1)
    raw = model.predict_helm(c.helm, ASSAY)
    scored = ScoringSession(model.scorer(), target, ASSAY, 10, 100).score(c)
    assert scored.endpoints[0].raw == raw
    assert scored.endpoints[1].status == "unavailable"
    assert scored.endpoints[0].uncertainty is None
    with pytest.raises(ValueError, match="Assay"):
        model.predict_helm(c.helm, replace(ASSAY, dosage_nm=500))
    with pytest.raises(ValueError, match="hash"):
        PortableEfficacy(path, "wrong")
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="hash"):
        PortableEfficacy(path, sha)


def test_invalid_bundle_coefficients_fail_even_with_matching_file_hash(tmp_path):
    path, _ = bundle(tmp_path)
    data = json.loads(path.read_text())
    data["coefficients"][0] = float("nan")
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="parameters"):
        PortableEfficacy(path, hashlib.sha256(path.read_bytes()).hexdigest())


def test_jump_charges_every_intermediate_score_and_truncates_atomically():
    space = fixture_space()
    session = LocalScoringSession(space, fixture_scorer(), space.target, ASSAY, 6, 100)
    session.score(space.candidate(1))
    with pytest.raises(BudgetExhausted):
        session.score(space.candidate(9))
    assert session.position == 6 and session.moves == 5
    assert session.requests == 6 and session.misses == 6
    assert [r["candidate"]["start"] for r in session.archive.values()] == list(
        range(1, 7)
    )


def test_equal_local_access_prevents_random_and_genetic_teleportation():
    space = fixture_space()
    for method in ("random", "greedy", "genetic"):
        session = LocalScoringSession(
            space, fixture_scorer(), space.target, ASSAY, 6, 100
        )
        result = search(space, session, method, 7)
        assert result["best_reward"] <= 0.65
        assert result["moves"] <= space.horizon and result["unique_scores"] <= 6


def test_local_move_horizon_counts_revisits():
    space = replace(fixture_space(), horizon=3)
    session = LocalScoringSession(space, fixture_scorer(), space.target, ASSAY, 10, 100)
    for site in (1, 0, 1, 0):
        session.score(space.candidate(site))
    with pytest.raises(BudgetExhausted):
        session.score(space.candidate(1))
    assert session.moves == 3 and session.misses == 2 and session.requests == 4
