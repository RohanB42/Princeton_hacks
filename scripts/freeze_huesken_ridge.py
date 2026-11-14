"""Freeze a training-only Huesken Ridge model as an RL-safe JSON bundle."""

import argparse
import csv
import gzip
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import sklearn
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV
from train_simple_huesken import RIDGE_ALPHAS, inner_folds, position_features

from oligo_engine.data.audit import audit_split
from oligo_engine.data.catalog import Catalog
from oligo_engine.data.splits import make_split
from oligo_engine.design.huesken_bundle import HueskenRidgeBundle, encode_rna1
from oligo_engine.evaluation.runner import environment_identity


def freeze(output: Path, strategy: str, seed: int) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    catalog = Catalog()
    loaded = catalog.load("Huesken")
    dataset = loaded.dataset
    split = make_split(dataset, strategy, seed, test_size=0.2)
    old_features = position_features(catalog)
    entry = catalog.resolve("Huesken")
    source = catalog.verify_file(entry["data_file"])
    prefix = dataset.content_sha256[:16]
    sequences = {}
    with gzip.open(source, "rt", newline="") as file:
        for index, row in enumerate(csv.DictReader(file)):
            identity = f"{prefix}:{entry['name']}:{index}"
            rna1 = row["fasta"].split(".")[0]
            encoded = encode_rna1(rna1)
            if not np.array_equal(encoded, old_features[identity]):
                raise ValueError(f"Feature encoding changed at source row {index}")
            sequences[identity] = rna1
    if len(sequences) != len(dataset.observations):
        raise ValueError("Feature encoder did not cover every source row")
    oracle, _, _ = loaded.capabilities(split)
    row_by_id = {row.sample_id: row for row in dataset.observations}
    train = tuple(sorted(split.train_ids))
    x_train = np.stack([encode_rna1(sequences[i]) for i in train])
    y_train = np.asarray(oracle.reveal(train), dtype=np.float64)
    targets = tuple(row_by_id[i].target_id for i in train)
    folds, inner = inner_folds(strategy, seed, targets)
    model = GridSearchCV(
        Ridge(),
        {"alpha": list(RIDGE_ALPHAS)},
        cv=folds,
        scoring="neg_root_mean_squared_error",
        refit=True,
        n_jobs=1,
    )
    model.fit(x_train, y_train)
    fitted = model.best_estimator_
    bundle = HueskenRidgeBundle(
        coefficients=tuple(float(x) for x in fitted.coef_),
        intercept=float(fitted.intercept_),
        alpha=float(model.best_params_["alpha"]),
        training_mean=float(y_train.mean()),
        training_sd=float(y_train.std(ddof=1)),
        training_sequences=tuple(sequences[i] for i in train),
        training_ids_sha256=hashlib.sha256("\n".join(train).encode()).hexdigest(),
        source_sha256=dataset.content_sha256,
        source_revision=dataset.source_revision,
        split_strategy=strategy,
        split_seed=seed,
        label_description=dataset.endpoint,
        sklearn_version=sklearn.__version__,
        numpy_version=np.__version__,
    )
    path = output / "ridge_bundle.json"
    bundle.save(path)
    reloaded = HueskenRidgeBundle.load(path)
    if reloaded.identity() != bundle.identity():
        raise ValueError("Reloaded bundle identity changed")
    golden = tuple(sequences[i] for i in split.test_ids[:10])
    expected = model.predict(np.stack([encode_rna1(s) for s in golden]))
    observed = reloaded.predict(golden)
    max_error = float(np.max(np.abs(expected - observed)))
    if max_error > 1e-10:
        raise ValueError("Reloaded predictor changed numerical predictions")
    audit = {
        "purpose": "frozen_Huesken_Ridge_surrogate_for_restricted_sequence_design",
        "source_sha256": dataset.content_sha256,
        "source_revision": dataset.source_revision,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "bundle_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bundle_identity": bundle.identity(),
        "training_rows": len(train),
        "training_ids_sha256": bundle.training_ids_sha256,
        "split": asdict(split),
        "split_audit": audit_split(dataset, split),
        "inner_validation": {
            **inner,
            "validation_ids_by_fold": [
                [train[i] for i in validation] for _, validation in folds
            ],
        },
        "alpha_candidates": RIDGE_ALPHAS,
        "selected_alpha": bundle.alpha,
        "inner_cv_rmse": float(-model.best_score_),
        "features_verified_on_all_source_rows": len(sequences),
        "golden_reload_max_absolute_prediction_error": max_error,
        "test_labels_used": False,
        "target_context_supported": False,
        "chemistry_edits_supported": False,
        "environment": environment_identity(),
    }
    (output / "fit_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--strategy", choices=("sequence_group", "target"), default="sequence_group"
    )
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    result = freeze(args.output, args.strategy, args.seed)
    print(
        f"Frozen {result['training_rows']} training rows; "
        f"alpha={result['selected_alpha']}; "
        f"reload error={result['golden_reload_max_absolute_prediction_error']:.2e}"
    )


if __name__ == "__main__":
    main()
