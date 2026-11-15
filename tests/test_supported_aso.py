"""Portable inference and exact chemistry/assay profile gating."""

import hashlib
import json
from dataclasses import asdict, replace

import pytest

from oligo_engine.design.candidates import build_helm
from oligo_engine.reward.atlas import atlas_helm
from oligo_engine.reward.portable import CHEMISTRY, PortableEfficacy, supported_sequence
from oligo_engine.reward.scoring import ScoringSession
from scoring_helpers import ASSAY, candidate_panel


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
    panel = candidate_panel(CHEMISTRY)
    target = panel.target
    candidate = panel.candidate(1)
    assert len(candidate.sequence) == 20
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
    panel = candidate_panel(CHEMISTRY)
    target, c = panel.target, panel.candidate(1)
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
