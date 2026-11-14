"""Audit actual Atlas scaling memberships and fit receipts without test labels."""

import argparse
import json
from pathlib import Path

import pandas as pd


def audit(output: Path) -> dict:
    cfg = json.loads((output / "config.json").read_text())
    parts = json.loads((output / "partitions.json").read_text())
    source_manifest = json.loads(Path(cfg["manifest"]).read_text())
    frame = pd.read_parquet(
        Path(cfg["manifest"]).parent / "cohort.parquet",
        columns=[
            "source_row_id",
            "natural_rna",
            "compound_key",
            "USPTO ID",
            "target_key",
        ],
    ).set_index("source_row_id")
    source_allowed = set(source_manifest["source_train_ids"])
    excluded = set(source_manifest["source_validation_ids"])
    reserved = {
        i
        for c in source_manifest["campaigns"]
        if c["role"] != "development"
        for i in c["pool_ids"] + c["test_ids"]
    }
    source_audit = []
    for part in parts["source"]:
        fit, val = set(part["fit_ids"]), set(part["validation_ids"])
        assert fit.isdisjoint(val)
        assert fit | val == set(part["selected_ids"])
        assert len(fit | val) == part["budget"]
        assert (fit | val) <= source_allowed
        assert (fit | val).isdisjoint(excluded | reserved)
        assert set(part["fit_groups"]).isdisjoint(part["validation_groups"])
        row = {
            "budget": part["budget"],
            "seed": part["seed"],
            "fit_patents": int(frame.loc[list(fit), "USPTO ID"].nunique()),
            "validation_patents": int(frame.loc[list(val), "USPTO ID"].nunique()),
            "fit_target_identifiers": int(frame.loc[list(fit), "target_key"].nunique()),
            "validation_target_identifiers": int(
                frame.loc[list(val), "target_key"].nunique()
            ),
            "fit_compound_identities": int(
                frame.loc[list(fit), "compound_key"].nunique()
            ),
        }
        for key in ["natural_rna", "compound_key", "USPTO ID"]:
            row[f"cross_validation_{key}_identities"] = len(
                set(frame.loc[list(fit), key]) & set(frame.loc[list(val), key])
            )
        source_audit.append(row)
    nesting = []
    for seed in cfg["source_seeds"]:
        selected = [p for p in parts["source"] if p["seed"] == seed]
        assert set(selected[0]["selected_ids"]) < set(selected[1]["selected_ids"])
        small, large = set(selected[0]["fit_ids"]), set(selected[1]["fit_ids"])
        nesting.append(
            {
                "seed": seed,
                "total_cohorts_nested": True,
                "inner_fitting_cohorts_nested": small <= large,
                "smaller_budget_fitting_ids_absent_from_larger_fit": len(small - large),
                "retained_fitting_ids": len(small & large),
            }
        )
    for part in parts["target"]:
        fit, val, test = map(
            set, [part["fit_ids"], part["validation_ids"], part["test_ids"]]
        )
        assert fit.isdisjoint(val) and (fit | val).isdisjoint(test | reserved)
        assert len(fit | val) == cfg["target_budget"]
        assert fit | val == set(part["acquired_ids"])
        assert set(part["fit_groups"]).isdisjoint(part["validation_groups"])
        assert source_allowed.isdisjoint(fit | val | test)
    neural, classical, equal_checkpoint_pairs = 0, 0, 0
    for path in output.glob("*/receipt.json"):
        receipt = json.loads(path.read_text())
        fit, val = set(receipt["ids"]), set(receipt.get("validation_ids", []))
        assert fit.isdisjoint(val)
        assert (fit | val).isdisjoint(reserved | excluded)
        if path.parent.name.startswith("source-"):
            _, budget, seed, _ = path.parent.name.split("-", 3)
            partition = next(
                p
                for p in parts["source"]
                if p["budget"] == int(budget) and p["seed"] == int(seed)
            )
            assert fit == set(partition["fit_ids"])
            assert val == set(partition["validation_ids"])
        if path.parent.name.startswith("target-"):
            saved = json.loads((path.parent / "predictions.json").read_text())
            meta = saved["metadata"]
            partition = next(
                p
                for p in parts["target"]
                if p["target"] == meta["target"] and p["seed"] == meta["target_seed"]
            )
            inner = meta["protocol"].endswith("inner")
            expected_fit = partition["fit_ids"] if inner else partition["acquired_ids"]
            expected_val = partition["validation_ids"] if inner else []
            assert fit == set(expected_fit) and val == set(expected_val)
            assert saved["test_ids"] == partition["test_ids"]
            assert len(saved["predictions"]) == len(partition["test_ids"])
            if "source_ids" in receipt:
                source_part = next(
                    p
                    for p in parts["source"]
                    if p["budget"] == meta["source_budget"]
                    and p["seed"] == meta["source_seed"]
                )
                assert receipt["source_ids"] == source_part["fit_ids"]
        if "history" in receipt:
            neural += 1
            assert receipt["base_unchanged"]
            if "lora_chemistry" in path.parent.name:
                assert receipt["adapters_changed"]
            assert receipt["epochs"] == len(receipt["history"])
            assert receipt["selected_epoch"] <= receipt["epochs"]
            if val:
                assert receipt["restored_best"]
                best = min(receipt["history"], key=lambda h: h["validation_rmse"])
                chosen = next(
                    h
                    for h in receipt["history"]
                    if h["epoch"] == receipt["selected_epoch"]
                )
                assert chosen["validation_rmse"] <= (
                    best["validation_rmse"] + receipt["min_delta_rmse"]
                )
                assert receipt["total_fit_validation_labels"] == len(fit | val)
        else:
            classical += 1
    for source_path in output.glob("source-*/receipt.json"):
        receipt = json.loads(source_path.read_text())
        if receipt.get("selected_epoch") != 3:
            continue
        _, budget, seed, name = source_path.parent.name.split("-", 3)
        for target in cfg["targets"]:
            prefix = f"target-{budget}-{seed}-{name}-{target}-"
            first = output / (prefix + "source3_target3_all") / "predictions.json"
            second = output / (prefix + "sourcebest_target3_all") / "predictions.json"
            if first.exists() and second.exists():
                a, b = json.loads(first.read_text()), json.loads(second.read_text())
                assert a["test_ids"] == b["test_ids"]
                assert a["predictions"] == b["predictions"]
                equal_checkpoint_pairs += 1
    report_count = None
    if (output / "report.json").exists():
        rows = json.loads((output / "report.json").read_text())["rows"]
        keys = {
            (
                r["model"],
                r["source_budget"],
                r["target_seed"],
                r["target"],
                r["protocol"],
            )
            for r in rows
        }
        report_count = len(rows)
        assert len(keys) == report_count == 216
        assert report_count == len(list(output.glob("target-*/predictions.json")))
    result = {
        "status": "passed_for_completed_receipts",
        "source_partitions": len(parts["source"]),
        "unique_finished_report_records": report_count,
        "target_partitions": len(parts["target"]),
        "neural_receipts_checked": neural,
        "classical_receipts_checked": classical,
        "equal_source_checkpoint_prediction_pairs": equal_checkpoint_pairs,
        "source_internal_validation_identity_overlap": source_audit,
        "source_cohort_nesting": nesting,
        "reserved_outcomes_read": False,
        "scope": "Metadata and completed receipts only; not numerical reproduction",
    }
    (output / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/atlas-rnafm/scaling-v1")
    )
    print(json.dumps(audit(parser.parse_args().output), indent=2))
