"""Scientific boundary tests for replaying existing predictors without refitting."""

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from oligo_engine.robustness.existing import (
    ExistingSource,
    load_existing,
    validate_membership,
)
from oligo_engine.robustness.existing_study import preflight, select_and_seal
from oligo_engine.robustness.optimization import verify_seal


def source() -> ExistingSource:
    rows = [
        {"sample_id": key, "compound_id": key, "group": "g", "helm": key, "context": {}}
        for key in ("fit", "dev1", "dev2", "final1", "final2")
    ]
    return ExistingSource(
        "atlas",
        rows,
        {
            "fit": ["fit"],
            "development": ["dev1", "dev2"],
            "final": ["final1", "final2"],
        },
        Path("unused"),
        "unused",
        {"context_coverage": {"development": 1.0, "final": 1.0}},
    )


def config() -> dict:
    return {
        "minimum_development_rows": 2,
        "minimum_final_rows": 2,
        "required_coverage": 1.0,
        "minimum_retention": 0.5,
        "optimizer_seeds": [0, 1],
        "query_budget": 2,
        "shortlist_k": 1,
        "atlas": {"diagnostic": "distance", "thresholds": [0.1, 1.0]},
    }


def test_hash_failure_and_trust_failure_before_deserialization(tmp_path: Path) -> None:
    checkpoint = tmp_path / "invalid.joblib"
    checkpoint.write_bytes(b"not serialized code")
    with pytest.raises(ValueError, match="Hash mismatch"):
        load_existing(checkpoint, "wrong", "unused", True)
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="trust must be explicit"):
        load_existing(checkpoint, digest, "unused", False)


def test_membership_rejects_training_compound_and_id_overlap() -> None:
    data = source()
    assert validate_membership(data.rows, data.roles)["training_overlap"] == 0
    data.rows[-1]["compound_id"] = "fit"
    with pytest.raises(ValueError, match="chemical overlap"):
        validate_membership(data.rows, data.roles)
    data = source()
    data.roles["final"].append("fit")
    with pytest.raises(ValueError, match="overlapping"):
        validate_membership(data.rows, data.roles)


def test_zero_context_preflight_stops_before_outcomes(monkeypatch) -> None:
    data = source()
    monkeypatch.setattr(
        ExistingSource, "outcomes", lambda *_: pytest.fail("label read")
    )
    data.receipt["context_coverage"]["final"] = 0.0
    with pytest.raises(ValueError, match="no evaluable final context"):
        preflight(data, config())
    data.receipt["context_coverage"]["final"] = 1.0
    assert preflight(data, config())["outcomes_read"] is False
    with pytest.raises(ValueError, match="insufficient final"):
        preflight(replace(data, roles={**data.roles, "final": []}), config())


def test_final_label_poison_cannot_change_policy_or_search(monkeypatch) -> None:
    from oligo_engine.robustness.adapters import OutcomeCapability

    data, predictions = source(), {"partitions": {}}
    for role in ("development", "final"):
        predictions["partitions"][role] = [
            {
                **row,
                "assessment_id": row["sample_id"],
                "mean": 10.0 + i,
                "diagnostics": {"distance": 0.1 + i * 0.5},
            }
            for i, row in enumerate(data.rows)
            if row["sample_id"] in data.roles[role]
        ]
    final_values = {"final1": 1.0, "final2": 100.0}
    accesses = []

    def outcomes(self, role):
        accesses.append(role)
        labels = {"dev1": 11.0, "dev2": 12.0} if role == "development" else final_values
        return OutcomeCapability(
            tuple(self.roles[role]), lambda ids: {i: labels[i] for i in ids}
        )

    monkeypatch.setattr(ExistingSource, "outcomes", outcomes)
    first_policy, first_runs = select_and_seal(data, predictions, config())
    final_values.update(final1=-99999.0, final2=99999.0)
    second_policy, second_runs = select_and_seal(data, predictions, config())
    assert first_policy == second_policy
    assert accesses == ["development", "development"]
    assert [r["seal"] for r in first_runs] == [r["seal"] for r in second_runs]
    for run in first_runs:
        verify_seal(run)
    first_runs[0]["shortlist"].append("fit")
    with pytest.raises(ValueError, match="changed after sealing"):
        verify_seal(first_runs[0])


def test_published_supported_bundle_inference_without_fitting() -> None:
    from oligo_engine.design.candidates import build_helm
    from oligo_engine.reward.portable import (
        CHEMISTRY,
        PortableEfficacy,
        encode_sequence,
    )

    model = PortableEfficacy(
        Path("model_checkpoints/supported-aso-v1/efficacy.json"),
        "44f975ae47c1a073ec52bde1e3403baa21de8a1b0b733e4bcac1a9b236252a84",
    )
    assert len(model.bundle["training_ids"]) == 2000
    sequence = model.training_sequences[0]
    expected = model.intercept + sum(
        a * b
        for a, b in zip(encode_sequence(sequence), model.coefficients, strict=True)
    )
    assert model.predict_helm(build_helm(sequence, CHEMISTRY), model.assay) == expected
    assert expected == pytest.approx(model.reference[0], abs=1e-8)
    with pytest.raises(ValueError, match="Assay context"):
        model.predict_helm(
            build_helm(sequence, CHEMISTRY), replace(model.assay, dosage_nm=1.0)
        )
    with pytest.raises(ValueError, match="20-mer"):
        model.predict_helm(build_helm("A" * 19, CHEMISTRY), model.assay)


def test_fixed_chemistry_hamming_threshold_ties_are_exact() -> None:
    np = pytest.importorskip("numpy")
    pytest.importorskip("sklearn")
    from oligo_engine.reward.portable import encode_sequence
    from oligo_engine.robustness.existing_study import frozen_predictions

    data = source()

    class Pair:
        cfg = {"primary_sha256": "one", "secondary_sha256": "two"}

        def features(self, ids):
            return np.asarray(
                [
                    encode_sequence("A" * 20 if key == "fit" else "C" * 8 + "A" * 12)
                    for key in ids
                ]
            )

        def predict(self, ids):
            return [1.0] * len(ids), [2.0] * len(ids), [None] * len(ids)

        def parity(self, ids):
            return {"refit_calls": 0}

    result = frozen_predictions(data, Pair())
    for role in ("development", "final"):
        assert all(
            r["diagnostics"]["distance"] == 0.4 for r in result["partitions"][role]
        )


def test_shortlist_evaluation_averages_assay_replicates(monkeypatch) -> None:
    from oligo_engine.robustness.adapters import OutcomeCapability
    from oligo_engine.robustness.existing_study import deferred_evaluation

    data = source()
    for row in data.rows[-2:]:
        row["compound_id"] = "one-compound"
    labels = {"dev1": 10.0, "dev2": 10.0, "final1": 0.0, "final2": 100.0}
    monkeypatch.setattr(
        ExistingSource,
        "outcomes",
        lambda self, role: OutcomeCapability(
            tuple(self.roles[role]), lambda ids: {i: labels[i] for i in ids}
        ),
    )
    predictions = {
        "partitions": {
            role: [
                {
                    **row,
                    "mean": 10.0,
                    "secondary_mean": 10.0,
                    "diagnostics": {
                        "distance": 0.1,
                        "uncertainty": None,
                        "disagreement": 0.0,
                    },
                }
                for row in data.rows
                if row["sample_id"] in data.roles[role]
            ]
            for role in ("development", "final")
        }
    }
    policy, runs = select_and_seal(data, predictions, config())
    result = deferred_evaluation(data, predictions, policy, runs)
    assert all(r["n"] == 1 for r in result["selection"])
    assert all(r["measured_mean"] == 50.0 for r in result["selection"])
