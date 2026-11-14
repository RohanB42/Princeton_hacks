"""Audit full-data best-model reruns and report numerical agreement per dataset."""

import argparse
import hashlib
import json
import math
import tomllib
from pathlib import Path
from statistics import fmean, stdev


def validate_baseline(result: dict, entry: dict, config: dict) -> dict:
    if result["config"] != config or result["dataset"] != entry:
        raise ValueError("Baseline config or dataset identity differs")
    seeds = config["seeds"]
    if seeds != [0, 1, 2, 3, 4] or [r["seed"] for r in result["runs"]] != seeds:
        raise ValueError("Expected all five declared baseline seeds")
    source = result["source_audit"]["files_sha256"][
        f"oligogym/resources/pkg_dataset/{entry['data_file']}"
    ]
    prefix = f"{source[:16]}:{entry['name']}:"
    expected_rows = entry["rows"]
    for run in result["runs"]:
        train, test = run["train_ids"], run["test_ids"]
        combined = train + test
        if (
            len(train) != run["train_rows"]
            or len(test) != run["test_rows"]
            or len(combined) != expected_rows
            or len(set(combined)) != expected_rows
        ):
            raise ValueError("Incomplete, overlapping or capped baseline split")
        if any(not sample.startswith(prefix) for sample in combined):
            raise ValueError("Unexpected source-qualified observation ID")
        indices = {int(sample[len(prefix) :]) for sample in combined}
        if indices != set(range(expected_rows)):
            raise ValueError("Baseline does not cover the complete released dataset")
        trace = run["model_execution"]
        if trace["execution_mode"] != "benchmark_helpers" or trace[
            "requested_model_args"
        ] != {key: value for key, value in config["model"].items() if key != "name"}:
            raise ValueError("Baseline did not execute the frozen upstream model")
        if len(run["prediction_sha256"]) != 64:
            raise ValueError("Missing prediction identity")
    values = [run["metrics"]["pearson_r"] for run in result["runs"]]
    valid = [value for value in values if value is not None]
    if any(not math.isfinite(value) for value in valid):
        raise ValueError("Nonfinite Pearson must be represented as undefined")
    mean = fmean(valid) if valid else None
    sd = stdev(valid) if len(valid) > 1 else None
    if result["mean_pearson_r"] != mean or result["sample_sd_pearson_r"] != sd:
        raise ValueError("Aggregate statistics differ from actual per-seed scores")
    reference = result["published_configuration_reference"]
    if reference != {"n": 5, "mean": config["reference_mean_pearson"]}:
        raise ValueError("Published configuration reference differs")
    delta = mean - reference["mean"] if mean is not None else None
    return {
        "dataset": entry["key"],
        "modality": entry["modality"],
        "rows": expected_rows,
        "model": config["model"]["name"],
        "local_mean_pearson": mean,
        "local_sample_sd": sd,
        "reference_mean_pearson": reference["mean"],
        "delta": delta,
        "tolerance": config["tolerance"],
        "n_defined_seeds": len(valid),
        "per_seed_pearson": values,
        "within_tolerance": (
            len(valid) == 5 and delta is not None and abs(delta) <= config["tolerance"]
        ),
    }


def report(suite_path: Path, configs: Path) -> dict:
    suite = json.loads((suite_path / "suite.json").read_text())
    if suite["status"] != "complete":
        raise ValueError("Suite is not fully executed; do not report a partial success")
    manifest = json.loads((configs / "manifest.json").read_text())
    if suite["manifest"] != manifest or len(manifest["datasets"]) != 7:
        raise ValueError("Suite and frozen seven-dataset manifest differ")
    outcomes = []
    source_identity = None
    environment = None
    for row in manifest["datasets"]:
        path = configs / row["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Frozen configuration changed after execution")
        key = row["dataset"]["key"]
        if suite["datasets"][key]["status"] != "complete":
            raise ValueError("A baseline execution failed")
        artifact = suite_path / f"{path.stem}.json"
        result = json.loads(artifact.read_text())
        identity = result["environment"]["source_sha256"]
        versions = result["installed_distribution_versions"]
        if source_identity is None:
            source_identity, environment = identity, versions
        elif source_identity != identity or environment != versions:
            raise ValueError(
                "Model comparisons used different source or package versions"
            )
        outcomes.append(
            validate_baseline(result, row["dataset"], tomllib.loads(path.read_text()))
        )
    matches = sum(row["within_tolerance"] for row in outcomes)
    return {
        "status": "complete_best_efficacy_baseline_comparison",
        "datasets_executed": len(outcomes),
        "fits_executed": sum(len(row["per_seed_pearson"]) for row in outcomes),
        "datasets_within_tolerance": matches,
        "all_numerically_reproduced": matches == 7,
        "exact_historical_reproduction": False,
        "datasets": outcomes,
        "caveats": [
            "Original split/RNG states and runtime hardware are unavailable.",
            "Local and published repeats are not paired historical folds.",
            "Sample SD is not a confidence interval.",
            "Report each assay separately; there is no pooled efficacy score.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--configs", type=Path, default=Path("configs/gate1-efficacy"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Report output exists; preserve previous results")
    result = report(args.suite, args.configs)
    args.output.mkdir(parents=True)
    (args.output / "report.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    lines = [
        "| Dataset | Model | Published r | Local mean r | Local sample SD "
        "| Difference | Within 0.03? |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in result["datasets"]:

        def number(value):
            return f"{value:.6f}" if value is not None else "undefined"

        lines.append(
            f"| {row['dataset']} | {row['model']} "
            f"| {number(row['reference_mean_pearson'])} "
            f"| {number(row['local_mean_pearson'])} | {number(row['local_sample_sd'])} "
            f"| {number(row['delta'])} | {'Yes' if row['within_tolerance'] else 'No'} |"
        )
    table = "\n".join(lines) + "\n"
    (args.output / "comparison.md").write_text(table)
    print(table)
    print(
        f"{result['datasets_within_tolerance']}/7 datasets within the frozen tolerance"
    )


if __name__ == "__main__":
    main()
