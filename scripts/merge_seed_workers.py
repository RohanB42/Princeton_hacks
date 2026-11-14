"""Join completed independent seeds with identical science settings and source."""

import argparse
import json
import shutil
from pathlib import Path

from oligo_engine.contracts import (
    Checkpoint,
    Metrics,
    RunArtifact,
    RunConfig,
    SplitManifest,
)
from oligo_engine.reporting.artifacts import write_artifacts


def read_run(path: Path) -> RunArtifact:
    data = json.loads(path.read_text())
    split = data["split"]
    split["train_ids"] = tuple(split["train_ids"])
    split["test_ids"] = tuple(split["test_ids"])
    split["parameters"] = tuple(tuple(p) for p in split["parameters"])
    data["split"] = SplitManifest(**split)
    data["config"] = RunConfig(**data["config"])
    data["checkpoints"] = tuple(
        Checkpoint(p["labels_used"], tuple(p["acquired_ids"]), Metrics(**p["metrics"]))
        for p in data["checkpoints"]
    )
    data["full_pool_metrics"] = Metrics(**data["full_pool_metrics"])
    data["initial_ids"] = tuple(data["initial_ids"])
    data["caveats"] = tuple(data["caveats"])
    return RunArtifact(**data)


def merge(parent: Path, workers: Path, dataset_name: str) -> None:
    suite_path = parent / "suite.json"
    suite = json.loads(suite_path.read_text())
    record = next(d for d in suite["datasets"] if d["name"] == dataset_name)
    expected = suite["config"]
    worker_suites = []
    pending = []
    records = []
    for seed in expected["seeds"]:
        child_root = workers / f"seed-{seed}"
        child = json.loads((child_root / "suite.json").read_text())
        if child["status"] != "complete" or child["config"]["seeds"] != [seed]:
            raise ValueError("Worker is incomplete or has the wrong seed")
        for key in (
            "purpose",
            "split",
            "budget",
            "model",
            "analysis",
            "cache_features",
            "reuse_full_reference",
        ):
            if child["config"].get(key) != expected.get(key):
                raise ValueError(f"Worker science settings differ: {key}")
        if (
            child["environment"]["source_sha256"]
            != suite["environment"]["source_sha256"]
        ):
            raise ValueError("Worker source differs from the parent experiment")
        if len(child["datasets"]) != 1 or child["datasets"][0]["name"] != dataset_name:
            raise ValueError("Worker has the wrong dataset")
        worker_suites.append(str(child_root / "suite.json"))
        records.extend(child["datasets"][0]["runs"])
        for policy in expected["policies"]:
            source = child_root / dataset_name / policy / f"run-seed-{seed}.json"
            run = json.loads(source.read_text())
            if (
                run["config"]["seed"] != seed
                or run["policy"]["name"] != policy
                or run["execution"]["fit_order"] != "sample_id_lexicographic"
            ):
                raise ValueError("Worker artifact identity/order mismatch")
            target = parent / dataset_name / policy / source.name
            if target.exists():
                old = json.loads(target.read_text())
                for key in (
                    "dataset",
                    "split",
                    "config",
                    "model",
                    "policy",
                    "initial_ids",
                    "checkpoints",
                    "full_pool_labels",
                    "full_pool_metrics",
                ):
                    if old[key] != run[key]:
                        raise ValueError(
                            f"Existing run has different scientific contents: {key}"
                        )
            pending.append((source, target))
    # All workers are validated before making any changes to the parent output.
    for source, target in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(source, target)
    for policy in expected["policies"]:
        directory = parent / dataset_name / policy
        runs = tuple(
            read_run(directory / f"run-seed-{seed}.json") for seed in expected["seeds"]
        )
        write_artifacts(runs, directory, allow_completed_runs=True)
    record.update(status="complete", runs=records, worker_suites=worker_suites)
    record.pop("current", None)
    suite["status"] = (
        "complete"
        if all(d["status"] == "complete" for d in suite["datasets"])
        else "incomplete"
    )
    suite.setdefault("execution_notes", []).append(
        "Independent Sherwood seed jobs ran in parallel with unchanged data, "
        "model/acquisition settings and source hashes; source workers are retained."
    )
    temporary = parent / "suite.json.merge-tmp"
    temporary.write_text(json.dumps(suite, indent=2, allow_nan=False) + "\n")
    temporary.replace(suite_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--workers", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args()
    merge(args.parent, args.workers, args.dataset)


if __name__ == "__main__":
    main()
