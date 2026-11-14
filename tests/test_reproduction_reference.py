"""A dataset override must not inherit another task's published reference."""

import csv

from oligo_engine.reproduce import published_reference


def test_reference_matches_dataset_model_feature_arguments(tmp_path):
    directory = tmp_path / "benchmarks"
    directory.mkdir()
    fields = [
        "dataset",
        "cross_validation",
        "model",
        "model_args",
        "featurizer",
        "featurizer_args",
        "test_pearson_correlation",
    ]
    template = {
        "dataset": "siRNA1",
        "cross_validation": "nucleobase",
        "model": "RandomForestModel",
        "model_args": "{'n_estimators': 100}",
        "featurizer": "OneHotEncoder",
        "featurizer_args": "{'encode_components': ['base']}",
        "test_pearson_correlation": "0.7",
    }
    with (directory / "oligogym_benchmarks.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            [
                template,
                {**template, "dataset": "openASO", "test_pearson_correlation": "0.2"},
                {**template, "dataset": "openASO", "test_pearson_correlation": "0.4"},
                {
                    **template,
                    "dataset": "openASO",
                    "model_args": "{'n_estimators': 200}",
                    "test_pearson_correlation": "0.9",
                },
            ]
        )
    config = {
        "benchmark_alias": "openASO",
        "split": {"strategy": "nucleobase"},
        "model": {"name": "RandomForestModel", "n_estimators": 100},
        "featurizer": {"name": "OneHotEncoder", "encode_components": ["base"]},
    }
    result = published_reference(tmp_path, config)
    assert result == {"n": 2, "mean": 0.30000000000000004}
    config["benchmark_alias"] = "absent"
    assert published_reference(tmp_path, config) == {"n": 0, "mean": None}
