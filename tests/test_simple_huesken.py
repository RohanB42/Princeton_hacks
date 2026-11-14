"""Check simple-baseline nested-validation and saved split boundaries."""

import json
import subprocess
import sys


def test_simple_huesken_cli_keeps_inner_validation_inside_outer_training(tmp_path):
    output = tmp_path / "baselines"
    subprocess.run(
        [
            sys.executable,
            "scripts/train_simple_huesken.py",
            "--output",
            str(output),
            "--seeds",
            "0",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    protocol = json.loads((output / "protocol.json").read_text())
    assert protocol["benchmark_comparable"] is False
    assert protocol["feature"] == "RNA1_19_position_onehot_A_reference_57_columns"
    assert len(protocol["script_sha256"]) == 64
    for strategy in ("sequence_group", "target"):
        run = json.loads((output / f"{strategy}-seed-0.json").read_text())
        split = run["split"]
        training = set(split["train_ids"])
        held_out = set(split["test_ids"])
        folds = run["inner_validation"]["validation_ids_by_fold"]
        assert len(folds) == 5
        assert set().union(*(set(ids) for ids in folds)) == training
        assert sum(len(ids) for ids in folds) == len(training)
        assert not training & held_out
        assert run["data_audit"]["sequence_overlap_groups"] == 0
        assert all(
            result["training_metrics"]["rmse"] >= 0 for result in run["models"].values()
        )
        assert run["models"]["ridge"]["settings"]["alpha"] in (
            0.01,
            0.1,
            1.0,
            10.0,
            100.0,
            1000.0,
        )
        if strategy == "target":
            assert run["inner_validation"]["method"] == "GroupKFold_5_by_target"
            assert run["data_audit"]["target_overlap_groups"] == 0
