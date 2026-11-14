"""Audit completed Atlas development receipts without training or scoring again."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("artifacts/atlas-rnafm")


def read(name: str) -> dict:
    return json.loads((ROOT / name).read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = read("preparation-v1/manifests.json")
    classical = read("classical-development-v1/report.json")
    fm = read("fm-development-v1/report.json")
    suite = read("fm-development-v1/suite.json")
    acq = read("acquisition-development-v1/report.json")
    source_ids = suite["source_ids"]
    assert len(source_ids) == len(set(source_ids)) == 1000
    assert set(source_ids) <= set(manifest["source_train_ids"])
    assert not set(manifest["source_train_ids"]) & set(
        manifest["source_validation_ids"]
    )
    dev = {c["target"]: c for c in manifest["campaigns"] if c["role"] == "development"}
    reserved = [c for c in manifest["campaigns"] if c["role"] != "development"]
    assert set(dev) == {"F7", "STAT3", "NLRP3"} and len(reserved) == 7
    for campaign in manifest["campaigns"]:
        assert not set(campaign["pool_ids"]) & set(campaign["test_ids"])
        assert not set(source_ids) & set(campaign["pool_ids"] + campaign["test_ids"])
    for row in classical["rows"]:
        if row["stage"] == "source" and row["budget"] == 1000 and row["seed"] == 510:
            assert row["ids"] == source_ids
    assert suite["status"] == "complete" and len(suite["receipts"]) == 56
    assert all(r["base_unchanged"] for r in suite["receipts"])
    assert sum(r["adapters_changed"] for r in suite["receipts"]) == 28
    for receipt in suite["receipts"]:
        assert receipt["source_ids"] == source_ids
        assert receipt["n_labels"] == len(set(receipt["ids"]))
        if receipt["stage"] == "target":
            assert set(receipt["ids"]) <= set(dev[receipt["target"]]["pool_ids"])
            peers = [
                r
                for r in classical["rows"]
                if r["stage"] == "target"
                and r["model"] == "ridge_offset"
                and r["target"] == receipt["target"]
                and r["seed"] == receipt["seed"]
                and r["budget"] == receipt["budget"]
            ]
            assert len(peers) == 1 and peers[0]["ids"] == receipt["ids"]
    for path, expected in suite["source_hashes"].items():
        assert digest(Path(path)) == expected, f"Executed FM code changed: {path}"
    for name, expected in acq["source_checkpoint_hashes"].items():
        path = ROOT / f"fm-development-v1/{name}_chemistry-source.pt"
        assert digest(path) == expected
    assert len(acq["ledgers"]) == 54 and len(acq["rows"]) == 378
    for ledger in acq["ledgers"]:
        assert ledger["source_ids"] == source_ids
        chosen = ledger["initial_ids"] + sum(ledger["batches"], [])
        assert len(chosen) == len(set(chosen)) == 200
        assert set(chosen) <= set(dev[ledger["target"]]["pool_ids"])
    for target in dev:
        for seed in acq["config"]["seeds"]:
            peers = [
                r for r in acq["ledgers"] if r["target"] == target and r["seed"] == seed
            ]
            assert len(peers) == 6
            assert all(r["initial_ids"] == peers[0]["initial_ids"] for r in peers)
            initial = [
                r["metrics"]
                for r in acq["rows"]
                if r["target"] == target and r["seed"] == seed and r["budget"] == 50
            ]
            assert all(m == initial[0] for m in initial)
    assert not fm["reserved_targets_scored"] and not acq["reserved_targets_scored"]
    assert {r["target"] for r in fm["rows"] + acq["rows"]} == set(dev)
    artifacts = [
        ROOT / name
        for name in [
            "preparation-v1/audit.json",
            "preparation-v1/manifests.json",
            "native-linear-anchor/report.json",
            "classical-development-v1/report.json",
            "fm-profile-v1/report.json",
            "fm-development-v1/report.json",
            "fm-development-v1/suite.json",
            "acquisition-development-v1/report.json",
            "summary-v1/summary.json",
        ]
    ]
    evidence = {
        "audited_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "checks": [
            "same historical source IDs across classical/FM/acquisition",
            "same target IDs across matched prediction arms",
            "56 fit receipts preserve base; all 28 LoRA fits update adapters",
            "pre-run FM code digests match current executed code",
            "source checkpoint hashes match acquisition provenance",
            "54 ledgers unique/eligible; six policies share initial IDs/metrics",
            "seven reserved targets absent from fit/score records",
        ],
        "scope": "Post-run receipt audit; no new training or evaluation. "
        "Acquisition source-code hashes were not captured before execution; "
        "current source is recorded by the final research branch commit.",
        "artifact_sha256": {str(p): digest(p) for p in artifacts},
    }
    (ROOT / "summary-v1/audit.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"status": "passed", "checks": evidence["checks"]}, indent=2))


if __name__ == "__main__":
    main()
