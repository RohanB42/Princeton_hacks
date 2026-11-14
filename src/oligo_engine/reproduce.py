"""Rerun one frozen published configuration using the pinned upstream wrappers."""

import argparse
import ast
import csv
import hashlib
import json
import random
import tomllib
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from statistics import fmean, stdev
from time import perf_counter

from oligo_engine.audit_upstream import PINNED_REVISION, audit_checkout
from oligo_engine.data.catalog import Catalog
from oligo_engine.evaluation.metrics import regression_metrics
from oligo_engine.evaluation.runner import environment_identity


def published_reference(checkout: Path, config: dict) -> dict:
    values = []
    model_args = {k: v for k, v in config["model"].items() if k != "name"}
    features = {k: v for k, v in config["featurizer"].items() if k != "name"}
    with (checkout / "benchmarks/oligogym_benchmarks.csv").open() as file:
        for row in csv.DictReader(file):
            if (
                row["dataset"] == config["benchmark_alias"]
                and row["cross_validation"] == config["split"]["strategy"]
                and row["model"] == config["model"]["name"]
                and row["featurizer"] == config["featurizer"]["name"]
                and ast.literal_eval(row["model_args"]) == model_args
                and ast.literal_eval(row["featurizer_args"]) == features
                and row["test_pearson_correlation"]
            ):
                values.append(float(row["test_pearson_correlation"]))
    return {"n": len(values), "mean": fmean(values) if values else None}


def reproduce(checkout: Path, config: dict, catalog: Catalog | None = None) -> dict:
    audit = audit_checkout(checkout)
    catalog = catalog or Catalog()
    entry = catalog.resolve(config["loader_key"])
    if entry["benchmark_alias"] != config["benchmark_alias"]:
        raise ValueError("Configured dataset and historical benchmark alias differ")
    source_data = catalog.verify_file(entry["data_file"])
    source_meta = catalog.verify_file(entry["metadata_file"])
    digest = catalog.manifest["files"][entry["data_file"]]["sha256"]
    if (
        audit["files_sha256"][f"oligogym/resources/pkg_dataset/{entry['data_file']}"]
        != digest
    ):
        raise ValueError("Vendored data differ from the audited upstream release")
    if config["upstream_revision"] != PINNED_REVISION:
        raise ValueError("Config and audited source revision differ")
    # Imports must resolve to the source that was audited, not another installation.
    import numpy as np
    import oligogym.data.dataset_downloader as downloader_module
    import pandas as pd
    from oligogym.data import Dataset as UpstreamDataset
    from oligogym.features import KMersCounts, OneHotEncoder
    from oligogym.models import LinearModel, RandomForestModel

    expected = (checkout / "oligogym/data/dataset_downloader.py").resolve()
    if Path(downloader_module.__file__).resolve() != expected:
        raise ValueError("Installed OligoGym differs from audited checkout")
    if version("scikit-learn") != "1.4.0":
        raise ValueError("Baseline requires pinned upstream scikit-learn 1.4.0")
    linear = config["model"]["name"] == "LinearModel"
    if config["model"]["name"] not in {"LinearModel", "RandomForestModel"}:
        raise ValueError("Supported upstream models: LinearModel, RandomForestModel")
    feature_classes = {"KMersCounts": KMersCounts, "OneHotEncoder": OneHotEncoder}
    if config["featurizer"]["name"] not in feature_classes:
        raise ValueError("Supported upstream features: KMersCounts, OneHotEncoder")
    reference = published_reference(checkout, config)
    if (
        "reference_mean_pearson" in config
        and config["reference_mean_pearson"] != reference["mean"]
    ):
        raise ValueError("Configured reference does not match the upstream CSV")
    data = UpstreamDataset(json.loads(source_meta.read_text()))
    data.build(dataframe=pd.read_csv(source_data, compression="gzip"))
    if config["split"]["strategy"] == "target" and (
        pd.isna(data.targets).any() or len(set(data.targets)) < 2
    ):
        raise ValueError("Target split requires known targets and at least two groups")
    ids = [f"{digest[:16]}:{entry['name']}:{i}" for i in range(len(data.x))]
    results = []
    for seed in config["seeds"]:
        started = perf_counter()
        random.seed(seed)
        np.random.seed(seed)
        args = dict(config["split"])
        strategy = args.pop("strategy")
        xtrain, xtest, ytrain, ytest, train_idx, test_idx = data.split(
            strategy, random_state=seed, return_index=True, **args
        )
        if set(xtrain) & set(xtest):
            raise ValueError("Exact sequence overlap across official split")
        feature_args = dict(config["featurizer"])
        feature_args.pop("name")
        featurizer = feature_classes[config["featurizer"]["name"]](**feature_args)
        features_train = featurizer.fit_transform(xtrain)
        features_test = featurizer.transform(xtest)
        if len(features_train.shape) == 3:
            features_train = features_train.reshape(len(xtrain), -1)
            features_test = features_test.reshape(len(xtest), -1)
        model_args = {k: v for k, v in config["model"].items() if k != "name"}
        model = (
            LinearModel(**model_args)
            if linear
            else RandomForestModel(**model_args, random_state=seed, n_jobs=2)
        )
        model.fit(features_train, ytrain)
        predictions = np.asarray(model.predict(features_test)).reshape(-1)
        metrics = regression_metrics(tuple(ytest), tuple(predictions))
        results.append(
            {
                "seed": seed,
                "train_ids": [ids[i] for i in train_idx],
                "test_ids": [ids[i] for i in test_idx],
                "train_rows": len(train_idx),
                "test_rows": len(test_idx),
                "metrics": asdict(metrics),
                "linear_diagnostics": {
                    "feature_count": features_train.shape[1],
                    "rank": int(model.model.rank_),
                    "smallest_singular_value": float(model.model.singular_[-1]),
                    "largest_singular_value": float(model.model.singular_[0]),
                    "max_abs_coefficient": float(np.max(np.abs(model.model.coef_))),
                }
                if linear and hasattr(model.model, "rank_")
                else None,
                "runtime_seconds": perf_counter() - started,
            }
        )
        print(
            f"seed={seed} test_rows={len(test_idx)} Pearson={metrics.pearson_r}",
            flush=True,
        )
    values = [r["metrics"]["pearson_r"] for r in results]
    defined = [v for v in values if v is not None]
    mean = fmean(defined) if defined else None
    delta = (
        mean - reference["mean"]
        if mean is not None and reference["mean"] is not None
        else None
    )
    return {
        "status": "measured_baseline_rerun_with_historical_discrepancies",
        "source_audit": audit,
        "config": config,
        "dataset": entry,
        "published_configuration_reference": reference,
        "config_sha256": hashlib.sha256(
            json.dumps(config, sort_keys=True).encode()
        ).hexdigest(),
        "environment": environment_identity(),
        "versions": {
            name: version(name)
            for name in (
                "numpy",
                "pandas",
                "scikit-learn",
                "scipy",
                "torch",
                "catboost",
                "torch-geometric",
                "torchinfo",
            )
        },
        "runs": results,
        "mean_pearson_r": mean,
        "sample_sd_pearson_r": stdev(defined) if len(defined) > 1 else None,
        "n_defined_seeds": len(defined),
        "delta_from_published_configuration": delta,
        "within_numeric_tolerance": (
            abs(delta) <= config["tolerance"] if delta is not None else None
        ),
        "gate_1_exact_reproduction": False,
        "caveats": [
            "Dataset-specific alias verified from the pinned catalog/Analysis.ipynb.",
            "Upstream benchmark script does not record deterministic split seeds.",
            "Three missing imports were installed separately; see versions.",
            "This is the configured published baseline, not the winning CNN.",
            "No active-learning comparison has been performed by this command.",
            *entry["caveats"],
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/reproduce-linear.toml")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--dataset", help="Any catalog key/name/alias; derives its own reference"
    )
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous results")
    config = tomllib.loads(args.config.read_text())
    catalog = Catalog(args.data_root) if args.data_root else Catalog()
    if args.dataset:
        entry = catalog.resolve(args.dataset)
        config.update(loader_key=entry["key"], benchmark_alias=entry["benchmark_alias"])
        config.pop("reference_mean_pearson", None)
    result = reproduce(args.checkout, config, catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        file.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Mean Pearson={result['mean_pearson_r']}; exact Gate 1 remains open.")


if __name__ == "__main__":
    main()
