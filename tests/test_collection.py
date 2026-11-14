"""Real-data integrity, dataset independence and diagnostic replay invariants."""

import json
import shutil
import subprocess
import sys
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from oligo_engine.acquisition.random import RandomAcquisition
from oligo_engine.acquisition.uncertainty import UncertaintyAcquisition
from oligo_engine.collection import effective_budget, run_collection
from oligo_engine.contracts import Dataset, Observation, Prediction
from oligo_engine.data.audit import audit_split
from oligo_engine.data.catalog import Catalog
from oligo_engine.data.splits import UnsupportedSplit, make_split
from oligo_engine.evaluation.runner import run_campaign


@pytest.fixture(scope="module")
def catalog():
    return Catalog()


def test_complete_release_and_all_raw_bytes(catalog):
    report = catalog.validate_all()
    assert report["total_rows"] == 337593
    assert len(report["datasets"]) == 12
    assert len(catalog.manifest["files"]) == 26
    assert catalog.resolve("sirna1")["key"] == "Huesken"
    assert catalog.resolve("acute_neurotox_moe_cleaned")["key"] == "Neurotox MOE"
    asoptimizer = next(r for r in report["datasets"] if r["key"] == "ASOptimizer")
    assert asoptimizer["repeated_sequence_rows"] == 11853
    assert {"cell_line", "concentration"} <= set(asoptimizer["columns"])
    assert (
        next(r for r in report["datasets"] if r["key"] == "Cytotox LNA")[
            "target_split_supported"
        ]
        is False
    )


def test_corruption_fails_before_labels_are_used(tmp_path, catalog):
    entry = catalog.resolve("Huesken")
    shutil.copyfile(catalog.root / "manifest.json", tmp_path / "manifest.json")
    shutil.copyfile(
        catalog.root / entry["metadata_file"], tmp_path / entry["metadata_file"]
    )
    (tmp_path / entry["data_file"]).write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="integrity"):
        Catalog(tmp_path).load("Huesken")


def test_unknown_key_and_unsafe_path_fail(catalog):
    with pytest.raises(ValueError, match="Unknown dataset"):
        catalog.resolve("not-a-dataset")
    with pytest.raises(ValueError, match="outside"):
        catalog.verify_file("../manifest.json")


def test_observation_ids_are_source_rows_not_subset_positions(catalog):
    a = catalog.load("TLR7", max_rows=64, selection_seed=10)
    b = catalog.load("Alharbi_2020_1", max_rows=64, selection_seed=10)
    full = catalog.load("TLR7")
    expected = {row.sample_id: row for row in full.dataset.observations}
    assert a.dataset == b.dataset
    assert all(expected[row.sample_id] == row for row in a.dataset.observations)
    assert a.dataset.metadata["source_rows"] == 192
    assert a.dataset.metadata["selected_rows"] == 64
    assert a.dataset.metadata["caveats"]
    assert not hasattr(a.dataset.observations[0], "label")


def test_assay_context_is_preserved(catalog):
    dataset = catalog.load("ASOptimizer", max_rows=8).dataset
    for row in dataset.observations:
        assert {"cell_line", "concentration"} <= dict(row.context).keys()
    assert dataset.metadata["endpoint_direction"] == "not_assumed"
    assert dataset.observations[0].modality == "ASO"


def test_undefined_targets_are_missing_without_changing_source(catalog):
    validation = catalog.validate_all()
    for name, expected in (("Shmushkovich", 356), ("siRNAmod", 907)):
        loaded = catalog.load(name)
        assert all(not row.target_id for row in loaded.dataset.observations)
        assert all(
            dict(row.context)["source_target_id"] == "undefined"
            for row in loaded.dataset.observations
        )
        report = next(row for row in validation["datasets"] if row["key"] == name)
        assert report["missing_target_rows"] == expected
        assert report["known_targets"] == 0


def toy_dataset(targets=("a", "a", "b", "b")):
    return Dataset(
        tuple(
            Observation(str(i), s, t, "ASO", "source", "assay")
            for i, (s, t) in enumerate(zip(("AAA", "AAA", "CCC", "GGG"), targets))
        ),
        "toy",
        "v1",
        "hash",
        "toy_response",
        "synthetic",
    )


def test_sequence_groups_stay_together_and_target_limitations_are_explicit():
    dataset = toy_dataset()
    split = make_split(dataset, "sequence_group", seed=12)
    assert ("0" in split.train_ids) == ("1" in split.train_ids)
    split.validate(dataset)
    assert split == make_split(dataset, "sequence_group", seed=12)
    audit = audit_split(dataset, split)
    assert audit["sequence_overlap_groups"] == 0
    assert (
        sum(part["repeated_helm_extra_rows"] for part in audit["partitions"].values())
        == 1
    )
    assert sum(part["rows"] for part in audit["partitions"].values()) == 4
    assert (
        sum(
            part["target_row_counts"].get("a", 0)
            for part in audit["partitions"].values()
        )
        == 2
    )
    with pytest.raises(UnsupportedSplit, match="known targets"):
        make_split(toy_dataset(("a", "a", "", "b")), "target", seed=0)
    with pytest.raises(UnsupportedSplit, match="two distinct"):
        make_split(toy_dataset(("a",) * 4), "target", seed=0)
    with pytest.raises(UnsupportedSplit, match="duplicates cross"):
        make_split(toy_dataset(("a", "b", "c", "d")), "target", seed=0, test_size=0.5)
    with pytest.raises(UnsupportedSplit, match="Official nucleobase"):
        make_split(dataset, "nucleobase", seed=0)


def test_budget_adaptation_is_explicit_and_counts_are_exact():
    actual = effective_budget(
        0, {"initial_labels": 50, "batch_size": 50, "max_labels": 500}, 23
    )
    assert actual.initial_labels == actual.max_labels == 23
    assert actual.purpose == "diagnostic" and actual.pearson_threshold is None
    with pytest.raises(ValueError):
        effective_budget(
            0, {"initial_labels": -5, "batch_size": 50, "max_labels": 500}, 23
        )


@pytest.mark.parametrize("name", [entry["key"] for entry in Catalog().entries])
def test_real_end_to_end_each_dataset(name, catalog, tmp_path):
    pytest.importorskip("sklearn")
    from oligo_engine.models.forest import HelmHashForest

    loaded = catalog.load(name, max_rows=48)
    split = make_split(loaded.dataset, "sequence_group", seed=23)
    initial_ids = []
    for policy in (RandomAcquisition(), UncertaintyAcquisition()):
        oracle, evaluator, reference = loaded.capabilities(split)
        result = run_campaign(
            loaded.dataset,
            split,
            oracle,
            evaluator,
            lambda: HelmHashForest(seed=23, n_estimators=4, n_features=64),
            policy,
            effective_budget(
                23,
                {"initial_labels": 8, "batch_size": 4, "max_labels": 12},
                len(split.train_ids),
            ),
            reference,
        )
        assert result.provenance == "measured"
        assert result.status == "complete_measured_diagnostic"
        assert result.config.purpose == "diagnostic"
        assert result.threshold_status == "not_requested"
        assert [p.labels_used for p in result.checkpoints] == [8, 12]
        assert result.full_pool_labels == len(split.train_ids)
        assert result.dataset["metadata"]["source_rows"] >= 192
        assert len(result.checkpoints[-1].acquired_ids) == 4
        assert not set(oracle.revealed_ids) & set(split.test_ids)
        audit = result.execution["data_audit"]
        assert audit["sequence_overlap_groups"] == 0
        assert sum(p["rows"] for p in audit["partitions"].values()) == 48
        assert (
            sum(
                p["missing_target_rows"] + sum(p["target_row_counts"].values())
                for p in audit["partitions"].values()
            )
            == 48
        )
        initial_ids.append(result.initial_ids)
    assert initial_ids[0] == initial_ids[1]


def test_diagnostic_model_feature_shape_and_scale_independence(catalog):
    pytest.importorskip("sklearn")
    from oligo_engine.models.forest import HelmHashForest

    # Fit only short training strings, then predict longer modified/duplex HELM.
    records = catalog.load("TLR7", max_rows=4).dataset.observations
    model = HelmHashForest(seed=0, n_estimators=4, n_features=64)
    model.fit(records, (-4.0, 0.0, 1000.0, 22.0))
    new_record = replace(records[0], sequence=records[0].sequence * 3)
    predictions = model.predict((new_record,))
    assert predictions[0].uncertainty_type == "tree_prediction_sd_uncalibrated"
    assert predictions[0].uncertainty >= 0
    assert model.encoder.transform([r.sequence for r in records]).shape[1] == 64
    assert model.encoder.transform([new_record.sequence]).shape[1] == 64
    chunked = HelmHashForest(
        seed=0, n_estimators=4, n_features=64, prediction_batch_size=1
    )
    chunked.fit(records, (-4.0, 0.0, 1000.0, 22.0))
    assert chunked.predict(records + (new_record,)) == model.predict(
        records + (new_record,)
    )
    assert chunked.predict(()) == ()


def test_measured_predictor_fit_and_test_label_isolation(catalog):
    pytest.importorskip("sklearn")
    from oligo_engine.evaluation.metrics import HeldOutEvaluator
    from oligo_engine.models.forest import HelmHashForest

    loaded = catalog.load("TLR7", max_rows=48)
    split = make_split(loaded.dataset, "sequence_group", seed=0)
    predictions_by_run, batches = [], []
    for poison in (False, True):
        predictions, fitted_ids = [], []

        class Spy(HelmHashForest):
            def fit(self, observations, labels):
                fitted_ids.append(tuple(row.sample_id for row in observations))
                super().fit(observations, labels)

            def predict(self, observations):
                values = super().predict(observations)
                predictions.append(values)
                return values

        oracle, evaluator, reference = loaded.capabilities(split)
        if poison:
            evaluator = HeldOutEvaluator(
                {i: float(j * 100) for j, i in enumerate(split.test_ids)},
                split.test_ids,
            )
        result = run_campaign(
            loaded.dataset,
            split,
            oracle,
            evaluator,
            lambda: Spy(seed=0, n_estimators=4, n_features=64),
            UncertaintyAcquisition(),
            effective_budget(
                0,
                {"initial_labels": 8, "batch_size": 4, "max_labels": 12},
                len(split.train_ids),
            ),
            reference,
        )
        expected = set()
        for fit_ids, step in zip(fitted_ids[:-1], result.checkpoints, strict=True):
            expected.update(step.acquired_ids)
            assert set(fit_ids) == expected
        assert set(fitted_ids[-1]) == set(split.train_ids)
        predictions_by_run.append(predictions)
        batches.append([p.acquired_ids for p in result.checkpoints])
    assert predictions_by_run[0] == predictions_by_run[1]
    assert batches[0] == batches[1]


def test_suite_preserves_unsupported_dataset_in_ledger(tmp_path, catalog):
    config = tomllib.loads(Path("configs/all-datasets-smoke.toml").read_text())
    config.update(dataset="siRNAmod")
    config["split"]["strategy"] = "target"
    result = run_collection(catalog, config, tmp_path)
    assert result["status"] == "incomplete"
    assert result["datasets"][0]["status"] == "unsupported_split"
    assert (tmp_path / "suite.json").exists()


def test_uncertainty_policy_requires_named_uncertainty(catalog):
    rows = catalog.load("TLR7", max_rows=4).dataset.observations

    class MissingUncertainty:
        def predict(self, observations):
            return tuple(Prediction(1.0) for _ in observations)

    with pytest.raises(ValueError, match="requires uncertainty"):
        UncertaintyAcquisition().choose(rows, (), 1, None, MissingUncertainty())


def test_target_holdout_on_eligible_real_dataset(catalog):
    loaded = catalog.load("Huesken", max_rows=96)
    split = make_split(loaded.dataset, "target", seed=0)
    train = set(split.train_ids)
    train_targets = {
        r.target_id for r in loaded.dataset.observations if r.sample_id in train
    }
    test_targets = {
        r.target_id for r in loaded.dataset.observations if r.sample_id not in train
    }
    assert train_targets and test_targets and not train_targets & test_targets
    audit = audit_split(loaded.dataset, split)
    assert audit["sequence_overlap_groups"] == 0
    assert audit["target_overlap_groups"] == 0


def test_shared_entry_point_and_multi_seed_summary(tmp_path):
    pytest.importorskip("sklearn")
    config = tmp_path / "config.toml"
    config.write_text("""dataset = "OpenASO"
purpose = "diagnostic"
max_rows = 32
seeds = [0, 1]
policies = ["random", "uncertainty"]
[split]
strategy = "sequence_group"
test_size = 0.2
[budget]
initial_labels = 4
batch_size = 4
max_labels = 8
[model]
n_estimators = 4
n_features = 64
""")
    output = tmp_path / "output"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "oligo_engine",
            "--config",
            str(config),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    suite = json.loads((output / "suite.json").read_text())
    assert suite["status"] == "complete"
    assert len(suite["datasets"][0]["runs"]) == 4
    saved_run = json.loads(
        (output / "McQuisten_2007_1/random/run-seed-0.json").read_text()
    )
    assert saved_run["execution"]["data_audit"]["sequence_overlap_groups"] == 0
    assert (
        sum(
            part["rows"]
            for part in saved_run["execution"]["data_audit"]["partitions"].values()
        )
        == 32
    )
    summary = json.loads((output / "McQuisten_2007_1/random/summary.json").read_text())
    assert summary["schema_version"] == "0.2"
    assert summary["seeds"] == [0, 1]
    assert summary["provenance"] == "measured"
    assert [p["run_count"] for p in summary["checkpoints"]] == [2, 2]
    assert len(summary["full_pool_references"]) == 2
