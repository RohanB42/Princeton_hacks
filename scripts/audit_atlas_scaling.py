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
        columns=["source_row_id", "natural_rna", "compound_key", "USPTO ID"],
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
        row = {"budget": part["budget"], "seed": part["seed"]}
        for key in ["natural_rna", "compound_key", "USPTO ID"]:
            row[f"cross_validation_{key}_identities"] = len(
                set(frame.loc[list(fit), key]) & set(frame.loc[list(val), key])
            )
        source_audit.append(row)
    for seed in cfg["source_seeds"]:
        selected = [p for p in parts["source"] if p["seed"] == seed]
        assert set(selected[0]["selected_ids"]) < set(selected[1]["selected_ids"])
    for part in parts["target"]:
        fit, val, test = map(
            set, [part["fit_ids"], part["validation_ids"], part["test_ids"]]
        )
        assert fit.isdisjoint(val) and (fit | val).isdisjoint(test | reserved)
        assert len(fit | val) == cfg["target_budget"]
        assert fit | val == set(part["acquired_ids"])
        assert set(part["fit_groups"]).isdisjoint(part["validation_groups"])
        assert source_allowed.isdisjoint(fit | val | test)
    neural, classical = 0, 0
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
                assert best["epoch"] == receipt["selected_epoch"]
                assert receipt["total_fit_validation_labels"] == len(fit | val)
        else:
            classical += 1
    result = {
        "status": "passed_for_completed_receipts",
        "source_partitions": len(parts["source"]),
        "target_partitions": len(parts["target"]),
        "neural_receipts_checked": neural,
        "classical_receipts_checked": classical,
        "source_internal_validation_identity_overlap": source_audit,
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
