"""Outcome isolation and lossless metadata recovery for DGAT2 transfer testing."""

import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from oligo_engine.robustness import dgat2
from oligo_engine.robustness.adapters import OutcomeCapability
from oligo_engine.robustness.contracts import AuditObservation
from oligo_engine.robustness.optimization import verify_seal

HELM = (
    "RNA1{"
    + ".".join(
        ("[moe](C)" if i < 5 or i >= 15 else "d(A)") + ("[sp]" if i < 19 else "")
        for i in range(20)
    )
    + "}$$$$V2.0"
)


def record(key: str) -> AuditObservation:
    return AuditObservation(
        key,
        HELM,
        "DGAT2",
        "asoptimizer_inhibition",
        "percent",
        "source",
        (("cell_line", "HepG2"), ("concentration", "0.12")),
    )


def metadata() -> dict:
    return {
        "Sequence": "C" * 5 + "A" * 10 + "C" * 5,
        "Chemical_Pattern": "M" * 5 + "d" * 10 + "M" * 5,
        "Cell_line": "HepG2",
        "ASO_volume(nM)": "120",
        "Treatment_Period(hours)": "24",
        "Transfection": "Lipofectin reagent",
        "Modification": "MOE/5-methylcytosines/deoxy",
        "Linkage": "phosphorothioate",
        "source_row": 0,
        "ISIS": "one",
    }


def test_metadata_crosswalk_restores_units_without_altering_chemistry() -> None:
    rows = dgat2.join_original_metadata((record("a"),), [metadata()])
    row = rows[0]
    assert row["dosage_nm"] == 120
    assert row["source_concentration"] == "0.12"
    assert row["treatment_period_hrs"] == 24
    assert row["raw_helm"] == HELM
    assert "[5meC]" not in row["helm"]
    assert row["helm"] == HELM[:-4]
    assert row["chemistry_annotation_conflict"]


def test_metadata_join_rejects_missing_or_conflicting_assay_annotations() -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        dgat2.join_original_metadata((record("a"),), [])
    bad = {**metadata(), "Treatment_Period(hours)": "16", "source_row": 1}
    with pytest.raises(ValueError, match="ambiguous"):
        dgat2.join_original_metadata((record("a"),), [metadata(), bad])
    # Identical metadata from repeated original source rows is retained, not
    # arbitrarily reduced to one source identity or selected by an outcome.
    duplicate = {**metadata(), "source_row": 1, "ISIS": "two"}
    row = dgat2.join_original_metadata((record("a"),), [metadata(), duplicate])[0]
    assert row["original_source_rows"] == [0, 1]
    assert row["original_compound_ids"] == ["one", "two"]


def install_fake_study(monkeypatch, directory: Path, truth: dict) -> dict:
    source_rows = (record("a"), record("b"))

    def outcomes(ids):
        for stage in (
            "protocol.json",
            "preflight.json",
            "predictions.json",
            "sealed-search.json",
        ):
            assert (directory / stage).is_file(), (
                "Endpoint read before sealed decisions"
            )
        return OutcomeCapability(ids, lambda selected: {i: truth[i] for i in selected})

    source = SimpleNamespace(rows=source_rows, receipt={}, outcomes=outcomes)
    monkeypatch.setattr(dgat2, "load_asoptimizer", lambda: source)

    def recovered(*_):
        rows = dgat2.join_original_metadata(source_rows, [metadata()])
        for row in rows:
            row["group"] = "one-context"
        return rows

    monkeypatch.setattr(dgat2, "recover_original", recovered)
    monkeypatch.setattr(dgat2, "pinned_loader", lambda _: {})
    monkeypatch.setattr(
        dgat2,
        "inference_guard",
        lambda: nullcontext(
            {"fit_attempts": 0, "protected_interfaces": ["fake predictor has no fit"]}
        ),
    )
    monkeypatch.setattr(dgat2, "atlas_metadata", lambda _: (None, [], {}))
    monkeypatch.setattr(
        dgat2,
        "frozen_models",
        lambda *_: ({"fixed": object()}, {"fixed": {"checkpoint_hashes": {}}}, set()),
    )
    monkeypatch.setattr(
        dgat2,
        "scope_audit",
        lambda *_: {
            "eligible_ids": ["a", "b"],
            "eligible_rows": 2,
            "original_rows": 2,
            "excluded_exposed_sequence_rows": 0,
        },
    )

    def predictions(rows, *_):
        return {
            "fixed": {
                "records": [
                    {
                        "sample_id": row["sample_id"],
                        "compound_id": row["compound_id"],
                        "group": row["group"],
                        "mean": 10.0,
                        "secondary_mean": 11.0,
                        "diagnostics": {"disagreement": 1.0},
                    }
                    for row in rows
                ],
                "parity_max_abs": {},
                "unknown_context_categories": {},
                "training_DGAT2_rows": 1,
            }
        }

    monkeypatch.setattr(dgat2, "predict_transfer", predictions)
    return {
        "schema": "dgat2-existing-transfer-v1",
        "atlas_source": "unused",
        "minimum_eligible_rows": 2,
        "runtime": {},
        "query_seeds": [0, 1],
        "query_budget": 2,
        "shortlist_k": 1,
        "disagreement_thresholds": [10, 20, 40],
        "primary_disagreement_threshold": 20,
    }


def test_no_eligible_cohort_stops_before_outcome_read(
    monkeypatch, tmp_path: Path
) -> None:
    directory = tmp_path / "blocked"
    cfg = install_fake_study(monkeypatch, directory, {})
    cfg["minimum_eligible_rows"] = 3
    with pytest.raises(ValueError, match="Insufficient"):
        dgat2.run_dgat2(cfg, Path("unused"), directory, True)
    assert (directory / "preflight.json").is_file()
    assert not (directory / "predictions.json").exists()


def test_final_outcome_poisoning_cannot_change_frozen_decisions(
    monkeypatch, tmp_path: Path
) -> None:
    seals, reports = [], []
    for name, truth in (
        ("first", {"a": 0.0, "b": 100.0}),
        ("poisoned", {"a": -9999.0, "b": -9999.0}),
    ):
        directory = tmp_path / name
        cfg = install_fake_study(monkeypatch, directory, truth)
        dgat2.run_dgat2(cfg, Path("unused"), directory, True)
        runs = json.loads((directory / "sealed-search.json").read_text())["runs"]
        for run in runs:
            verify_seal(run)
        seals.append([r["seal"] for r in runs])
        reports.append(json.loads((directory / "report.json").read_text()))
    assert seals[0] == seals[1]
    assert (
        reports[0]["results"]["fixed"]["ridge"]
        != reports[1]["results"]["fixed"]["ridge"]
    )
    assert reports[0]["fit_calls"] == reports[1]["fit_calls"] == 0
    # Both selected source records represent one compound; evaluate all assay
    # replicates rather than assigning a representative's arbitrary value.
    assert all(
        r["measured_mean"] == 50 for r in reports[0]["results"]["fixed"]["selection"]
    )


def test_inference_guard_rejects_fit_and_restores_interfaces(monkeypatch) -> None:
    import sys
    from types import ModuleType

    classes = {}
    for module_name, names in {
        "sklearn.compose": ["ColumnTransformer"],
        "sklearn.linear_model": ["Ridge"],
        "sklearn.preprocessing": ["OneHotEncoder", "StandardScaler"],
        "xgboost": ["XGBRegressor"],
        "oligo_engine.atlas.baselines": ["Classical", "Features"],
        "oligo_engine.atlas.scaling": ["HoldoutClassical"],
    }.items():
        module = ModuleType(module_name)
        for name in names:
            method = "fit_validation" if name == "HoldoutClassical" else "fit"
            owner = type(name, (), {method: lambda *_: "original"})
            classes[name] = owner
            setattr(module, name, owner)
        monkeypatch.setitem(sys.modules, module_name, module)
    original = classes["Features"].fit
    with dgat2.inference_guard() as receipt:
        with pytest.raises(RuntimeError, match="Fitting is forbidden"):
            classes["Features"]().fit()
        assert receipt["fit_attempts"] == 1
        assert len(receipt["protected_interfaces"]) == 8
    assert classes["Features"].fit is original
