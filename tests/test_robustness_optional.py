"""Explicit science-runtime checks, including fitting-label and feature scope."""

from dataclasses import replace

import pytest

from oligo_engine.robustness.adapters import fit_model, portable_adapter
from oligo_engine.robustness.fixture import source, synthetic_truth
from oligo_engine.robustness.perturbations import probe


@pytest.mark.parametrize("kind", ["ridge", "rf"])
def test_frozen_classical_prediction_parity_order_and_context_scope(kind):
    rows = source().rows[:40]
    labels = {r.sample_id: synthetic_truth(r) for r in rows}
    model = fit_model(rows, labels, kind, 10)
    assert not hasattr(model, "fit")
    forward = model.predict(rows)
    reversed_predictions = model.predict(tuple(reversed(rows)))
    assert forward == tuple(reversed(reversed_predictions))
    assert probe(model, rows, 4)["rejected_before_inference"] == 4
    outside = replace(rows[0], context=(("assay", "unknown"),))
    assert model.predict((outside,))[0].mean is None
    assert (
        model.predict((replace(rows[0], units="incompatible units"),))[0].mean is None
    )
    if kind == "rf":
        assert forward[0].uncertainty_type == "rf_tree_sd_uncalibrated"
    with pytest.raises(ValueError, match="permitted"):
        fit_model(rows, labels | {"final": 1000.0}, kind, 10)


def test_latest_main_portable_bundle_training_overlap_checked_before_use(tmp_path):
    import hashlib
    import json
    from dataclasses import asdict

    from oligo_engine.reward.portable import CHEMISTRY
    from scoring_helpers import ASSAY

    path = tmp_path / "bundle.json"
    path.write_text(
        json.dumps(
            {
                "schema": "supported-aso-ridge-v1",
                "chemistry": CHEMISTRY,
                "assay": asdict(ASSAY),
                "coefficients": [0.0] * 80,
                "intercept": 1.0,
                "training_prediction_reference": [1.0],
                "training_sequences": ["A" * 20],
                "training_ids": ["final-overlap"],
                "split_hash": "split",
            }
        )
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="artifact_overlap"):
        portable_adapter(path, digest, ("fit",))
