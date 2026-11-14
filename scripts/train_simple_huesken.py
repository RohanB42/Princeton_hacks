"""Train simple, separate Huesken diagnostic baselines on frozen local splits."""

import argparse
import csv
import gzip
import hashlib
import json
import platform
from dataclasses import asdict
from pathlib import Path
from statistics import fmean, stdev

import numpy as np
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold, KFold

from oligo_engine.contracts import Prediction
from oligo_engine.data.audit import audit_split
from oligo_engine.data.catalog import Catalog
from oligo_engine.data.splits import make_split
from oligo_engine.evaluation.metrics import regression_metrics
from oligo_engine.evaluation.runner import environment_identity

RIDGE_ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)
MODELS = ("training_mean", "linear", "ridge", "random_forest")
BASE_COLUMNS = {"C": 0, "G": 1, "U": 2}


def position_features(catalog: Catalog) -> dict[str, np.ndarray]:
    """Encode RNA1's 19 bases with A as the reference at each position."""
    entry = catalog.resolve("Huesken")
    path = catalog.verify_file(entry["data_file"])
    prefix = catalog.manifest["files"][entry["data_file"]]["sha256"][:16]
    features = {}
    with gzip.open(path, "rt", newline="") as file:
        for index, row in enumerate(csv.DictReader(file)):
            strands = row["fasta"].split(".")
            if len(strands) != 2 or len(strands[0]) != 19:
                raise ValueError(f"Unexpected Huesken FASTA at row {index}")
            sequence = strands[0]
            if set(sequence) - set("ACGU"):
                raise ValueError(f"Unexpected RNA1 base at row {index}")
            vector = np.zeros(57, dtype=np.float64)
            for position, base in enumerate(sequence):
                if base != "A":
                    vector[position * 3 + BASE_COLUMNS[base]] = 1.0
            sample_id = f"{prefix}:{entry['name']}:{index}"
            features[sample_id] = vector
    if len(features) != entry["rows"]:
        raise ValueError("Huesken feature rows do not match the manifest")
    return features


def inner_folds(
    strategy: str, seed: int, target_ids: tuple[str, ...]
) -> tuple[list[tuple[np.ndarray, np.ndarray]], dict]:
    """Select Ridge alpha from outer-training rows alone."""
    positions = np.arange(len(target_ids))
    if strategy == "target":
        groups = np.asarray(target_ids)
        splitter = GroupKFold(n_splits=5)
        folds = list(splitter.split(positions, groups=groups))
        method = "GroupKFold_5_by_target"
    else:
        splitter = KFold(n_splits=5, shuffle=True, random_state=seed)
        folds = list(splitter.split(positions))
        method = "shuffled_KFold_5_by_row"
    if any(
        set(train) & set(validation) or not len(train) or not len(validation)
        for train, validation in folds
    ):
        raise ValueError("Inner folds must be nonempty and disjoint")
    if strategy == "target" and any(
        set(target_ids[i] for i in train) & set(target_ids[i] for i in validation)
        for train, validation in folds
    ):
        raise ValueError("Inner target groups overlap")
    return folds, {"method": method, "seed": seed, "fold_count": len(folds)}


def fit_and_score(
    catalog: Catalog, features: dict[str, np.ndarray], strategy: str, seed: int
) -> dict:
    loaded = catalog.load("Huesken")
    dataset = loaded.dataset
    split = make_split(dataset, strategy, seed=seed, test_size=0.2)
    oracle, evaluator, _ = loaded.capabilities(split)
    row_by_id = {row.sample_id: row for row in dataset.observations}
    x_train = np.stack([features[i] for i in split.train_ids])
    x_test = np.stack([features[i] for i in split.test_ids])
    y_train = np.asarray(oracle.reveal(split.train_ids), dtype=np.float64)
    train_targets = tuple(row_by_id[i].target_id for i in split.train_ids)
    folds, inner = inner_folds(strategy, seed, train_targets)

    estimators = {
        "training_mean": DummyRegressor(strategy="mean"),
        "linear": LinearRegression(),
        "ridge": GridSearchCV(
            Ridge(),
            {"alpha": list(RIDGE_ALPHAS)},
            cv=folds,
            scoring="neg_root_mean_squared_error",
            refit=True,
            n_jobs=1,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=3,
            random_state=seed,
            n_jobs=2,
        ),
    }
    results = {}
    for name in MODELS:
        model = estimators[name]
        model.fit(x_train, y_train)
        values = model.predict(x_test)
        if not np.isfinite(values).all():
            raise ValueError(f"Nonfinite predictions from {name}")
        metrics = evaluator.score(tuple(Prediction(float(v)) for v in values))
        training_values = model.predict(x_train)
        record = {
            "metrics": asdict(metrics),
            "training_metrics": asdict(
                regression_metrics(
                    tuple(float(v) for v in y_train),
                    tuple(float(v) for v in training_values),
                )
            ),
            "settings": {},
        }
        if name == "ridge":
            record["settings"] = {
                "alpha": float(model.best_params_["alpha"]),
                "alpha_candidates": list(RIDGE_ALPHAS),
                "selection_metric": "mean_inner_validation_RMSE",
                "best_inner_validation_rmse": float(-model.best_score_),
                "candidate_mean_rmse": {
                    str(params["alpha"]): float(-score)
                    for params, score in zip(
                        model.cv_results_["params"],
                        model.cv_results_["mean_test_score"],
                        strict=True,
                    )
                },
            }
        elif name == "random_forest":
            record["settings"] = {
                "n_estimators": 200,
                "max_depth": 12,
                "min_samples_leaf": 3,
                "random_state": seed,
            }
        results[name] = record
    return {
        "strategy": strategy,
        "seed": seed,
        "source_revision": dataset.source_revision,
        "source_sha256": dataset.content_sha256,
        "split": asdict(split),
        "data_audit": audit_split(dataset, split),
        "inner_validation": {
            **inner,
            "validation_ids_by_fold": [
                [split.train_ids[i] for i in validation] for _, validation in folds
            ],
        },
        "models": results,
    }


def summarize(runs: list[dict]) -> list[dict]:
    output = []
    for strategy in ("sequence_group", "target"):
        selected = [run for run in runs if run["strategy"] == strategy]
        for model in MODELS:
            metrics = {}
            for key in ("pearson_r", "rmse", "mae"):
                values = [
                    run["models"][model]["metrics"][key]
                    for run in selected
                    if run["models"][model]["metrics"][key] is not None
                ]
                metrics[key] = {
                    "n": len(values),
                    "mean": fmean(values) if values else None,
                    "sample_sd": stdev(values) if len(values) > 1 else None,
                }
            output.append({"strategy": strategy, "model": model, "metrics": metrics})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(5)))
    args = parser.parse_args()
    if not args.seeds or len(set(args.seeds)) != len(args.seeds):
        parser.error("Seeds must be nonempty and distinct")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output directory must be empty")
    catalog = Catalog()
    features = position_features(catalog)
    protocol = {
        "purpose": "measured_diagnostic_only",
        "dataset": "Huesken",
        "outer_strategies": ["sequence_group", "target"],
        "outer_test_size_groups": 0.2,
        "seeds": args.seeds,
        "feature": "RNA1_19_position_onehot_A_reference_57_columns",
        "feature_source": "pinned_Huesken_FASTA_RNA1",
        "source_rows": 2431,
        "label": "upstream_y_unchanged",
        "models": list(MODELS),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "ridge_alpha_candidates": list(RIDGE_ALPHAS),
        "inner_validation": "5_fold_training_only; by_target_for_target_holdout",
        "environment": environment_identity(),
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "numpy": np.__version__,
        "benchmark_comparable": False,
        "gate_1_reproduced": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    runs = []
    for strategy in protocol["outer_strategies"]:
        for seed in args.seeds:
            run = fit_and_score(catalog, features, strategy, seed)
            (args.output / f"{strategy}-seed-{seed}.json").write_text(
                json.dumps(run, indent=2, allow_nan=False) + "\n"
            )
            runs.append(run)
            print(
                strategy,
                seed,
                "rows",
                run["data_audit"]["partitions"]["test"]["rows"],
                "ridge_alpha",
                run["models"]["ridge"]["settings"]["alpha"],
                flush=True,
            )
    summary = summarize(runs)
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n"
    )
    with (args.output / "scores.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "strategy",
                "seed",
                "model",
                "train_rows",
                "test_rows",
                "pearson_r",
                "rmse",
                "mae",
                "ridge_alpha",
            ]
        )
        for run in runs:
            for model in MODELS:
                metrics = run["models"][model]["metrics"]
                writer.writerow(
                    [
                        run["strategy"],
                        run["seed"],
                        model,
                        run["data_audit"]["partitions"]["train"]["rows"],
                        run["data_audit"]["partitions"]["test"]["rows"],
                        metrics["pearson_r"],
                        metrics["rmse"],
                        metrics["mae"],
                        run["models"][model]["settings"].get("alpha"),
                    ]
                )
    print(f"Saved {len(runs)} outer runs and {len(summary)} summaries to {args.output}")


if __name__ == "__main__":
    main()
