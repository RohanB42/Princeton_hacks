"""Check exact within-environment repeatability, not historical reproduction."""

import argparse
import json
from pathlib import Path


def compare(first: dict, repeated: dict) -> dict:
    for field in (
        "config",
        "config_sha256",
        "dataset",
        "source_audit",
        "published_configuration_reference",
        "versions",
        "installed_distribution_versions",
        "mean_pearson_r",
        "sample_sd_pearson_r",
        "n_defined_seeds",
        "delta_from_published_configuration",
        "within_numeric_tolerance",
    ):
        if field not in first or first[field] != repeated.get(field):
            raise ValueError(f"Baseline repeats differ or lack {field}")
    for field in ("python", "platform", "code_revision", "source_sha256"):
        if field not in first["environment"] or first["environment"][field] != repeated[
            "environment"
        ].get(field):
            raise ValueError(f"Baseline repeat environment differs or lacks {field}")
    seeds = first["config"]["seeds"]
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Expected a nonempty unique seed schedule")
    for artifact in (first, repeated):
        if [run["seed"] for run in artifact["runs"]] != seeds:
            raise ValueError("Incomplete or reordered repeated baseline seeds")
    for run, other in zip(first["runs"], repeated["runs"], strict=True):
        for field in (
            "train_ids",
            "test_ids",
            "train_rows",
            "test_rows",
            "metrics",
            "model_execution",
            "feature_shape_train",
            "feature_shape_test",
            "prediction_sha256",
        ):
            if field not in run or run[field] != other.get(field):
                raise ValueError(f"Seed {run['seed']} differs or lacks {field}")
    return {
        "status": "exact_within_environment_repeat",
        "seeds": seeds,
        "n_defined_seeds": first["n_defined_seeds"],
        "mean_pearson_r": first["mean_pearson_r"],
        "sample_sd_pearson_r": first["sample_sd_pearson_r"],
        "delta_from_published_configuration": first[
            "delta_from_published_configuration"
        ],
        "within_numeric_tolerance": first["within_numeric_tolerance"],
        "gate_1_exact_reproduction": False,
        "caveat": "Historical RNG states and original environment remain unknown.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--repeat", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous checks")
    result = compare(
        json.loads(args.first.read_text()), json.loads(args.repeat.read_text())
    )
    result["inputs"] = {"first": str(args.first), "repeat": str(args.repeat)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        file.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
