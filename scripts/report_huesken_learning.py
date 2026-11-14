"""Audit paired Huesken learning curves and plot actual measured-label results."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean, stdev


def statistics(values: list[float | None]) -> dict:
    valid = [value for value in values if value is not None]
    return {
        "n": len(valid),
        "mean": fmean(valid) if valid else None,
        "sample_sd": stdev(valid) if len(valid) > 1 else None,
    }


def validate_pair(random: dict, diversity: dict, budgets: list[int]) -> None:
    for field in ("dataset", "split", "config", "model", "initial_ids"):
        if random[field] != diversity[field]:
            raise ValueError(f"Policy pair differs on {field}")
    if (
        random["policy"]["name"] != "random"
        or diversity["policy"]["name"] != "diversity"
    ):
        raise ValueError("Expected a random/diversity policy pair")
    if random["full_pool_metrics"] != diversity["full_pool_metrics"]:
        raise ValueError("Paired policies have different full-reference metrics")
    if random["full_pool_labels"] != diversity["full_pool_labels"]:
        raise ValueError("Paired policies have different full-reference label counts")
    for run in (random, diversity):
        if run["config"]["purpose"] != "diagnostic" or run["provenance"] != "measured":
            raise ValueError("Study must preserve measured diagnostic provenance")
        if run["model"]["name"] != "upstream_one_hot_cnn":
            raise ValueError("Unexpected predictor in frozen Huesken study")
        if run["execution"]["fit_order"] != "sample_id_lexicographic":
            raise ValueError("Expected canonical fitting order")
        train, test = run["split"]["train_ids"], run["split"]["test_ids"]
        if len(train + test) != 2431 or len(set(train + test)) != 2431:
            raise ValueError("Split must cover all 2431 Huesken observations")
        if run["split"]["strategy"] != "nucleobase":
            raise ValueError("Expected official nucleobase holdout")
        if run["full_pool_labels"] != len(train):
            raise ValueError("Full reference must use the eligible training pool")
        if [point["labels_used"] for point in run["checkpoints"]] != budgets:
            raise ValueError("Missing or changed label-budget checkpoints")
        selected = []
        for point in run["checkpoints"]:
            selected.extend(point["acquired_ids"])
            if len(selected) != point["labels_used"] or len(set(selected)) != len(
                selected
            ):
                raise ValueError("Duplicate reveals or incorrect label accounting")
            if not set(selected) <= set(train):
                raise ValueError("Acquisition contains held-out or unknown IDs")
        if run["checkpoints"][0]["acquired_ids"] != run["initial_ids"]:
            raise ValueError("Initial label IDs do not match the first checkpoint")
        points = run["checkpoints"]
        area = None
        if len(points) > 1 and all(
            point["metrics"]["pearson_r"] is not None for point in points
        ):
            area = sum(
                (b["labels_used"] - a["labels_used"])
                * (a["metrics"]["pearson_r"] + b["metrics"]["pearson_r"])
                / 2
                for a, b in zip(points, points[1:])
            ) / (points[-1]["labels_used"] - points[0]["labels_used"])
        recorded = run["normalized_pearson_aulc"]
        if (area is None) != (recorded is None) or (
            area is not None and not math.isclose(area, recorded, abs_tol=1e-12)
        ):
            raise ValueError("Recorded AULC differs from actual learning checkpoints")
    if random["execution"]["full_reference_reused"] is not False:
        raise ValueError("Random campaign must fit a fresh full reference")
    if diversity["execution"]["full_reference_reused"] is not True:
        raise ValueError("Diversity must reuse only the matching freshly fit reference")


def efficiency(run: dict, tolerance: float, fraction: float) -> dict:
    reference = run["full_pool_metrics"]["pearson_r"]
    if reference is None or reference <= 0:
        return {"status": "undefined_or_nonpositive_reference", "labels": None}
    threshold = reference - tolerance
    count = next(
        (
            point["labels_used"]
            for point in run["checkpoints"]
            if point["metrics"]["pearson_r"] is not None
            and point["metrics"]["pearson_r"] >= threshold
        ),
        None,
    )
    return {
        "status": "reached" if count is not None else "not_reached",
        "threshold_r": threshold,
        "labels": count,
        "fraction_of_training_pool": count / run["full_pool_labels"]
        if count is not None
        else None,
        "meets_fraction_criterion": count / run["full_pool_labels"] <= fraction
        if count is not None
        else False,
    }


def analyze(root: Path) -> dict:
    suite = json.loads((root / "suite.json").read_text())
    if suite["status"] != "complete" or suite["mode"] != "full":
        raise ValueError("Full-study reporting requires a completed full suite")
    config = suite["config"]
    seeds = config["seeds"]
    if seeds != [0, 1, 2, 3, 4] or len(suite["runs"]) != 10:
        raise ValueError("Expected all ten frozen five-seed campaigns")
    budgets = list(range(50, 501, 50))
    matched = {policy: [] for policy in config["policies"]}
    primary = []
    inputs = {}
    expected_source = suite["environment"]["source_sha256"]
    for seed in seeds:
        pair = {}
        for policy in config["policies"]:
            path = root / policy / f"run-seed-{seed}.json"
            run = json.loads(path.read_text())
            if run["environment"]["source_sha256"] != expected_source:
                raise ValueError("Executed source changed between study runs")
            if run["config"]["seed"] != seed:
                raise ValueError("Run seed differs from its ledger entry")
            if run["model"]["seed"] != seed:
                raise ValueError("Model and campaign seeds differ")
            baseline_path = root / "source" / config["upstream"]["baseline_config"]
            if (
                hashlib.sha256(baseline_path.read_bytes()).hexdigest()
                != config["upstream"]["baseline_config_sha256"]
            ):
                raise ValueError("Archived model configuration hash differs")
            import tomllib

            baseline = tomllib.loads(baseline_path.read_text())
            if any(
                run["model"][field] != baseline[field]
                for field in ("featurizer", "model", "training", "trainer")
            ):
                raise ValueError(
                    "Run model settings differ from frozen native baseline"
                )
            inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            matched[policy].append(run)
            pair[policy] = run
        validate_pair(pair["random"], pair["diversity"], budgets)
        left = pair["random"]["normalized_pearson_aulc"]
        right = pair["diversity"]["normalized_pearson_aulc"]
        primary.append(
            {
                "seed": seed,
                "random_aulc": left,
                "diversity_aulc": right,
                "difference": right - left
                if left is not None and right is not None
                else None,
                "undefined_reason": None
                if left is not None and right is not None
                else "undefined_checkpoint_pearson",
                "random_efficiency": efficiency(pair["random"], 0.03, 0.5),
                "diversity_efficiency": efficiency(pair["diversity"], 0.03, 0.5),
            }
        )
    curves = {}
    for policy, runs in matched.items():
        curves[policy] = [
            {
                "labels": labels,
                **{
                    metric: statistics(
                        [run["checkpoints"][index]["metrics"][metric] for run in runs]
                    )
                    for metric in ("pearson_r", "rmse", "mae")
                },
            }
            for index, labels in enumerate(budgets)
        ]
    references = {
        metric: statistics(
            [run["full_pool_metrics"][metric] for run in matched["random"]]
        )
        for metric in ("pearson_r", "rmse", "mae")
    }
    return {
        "status": "complete_huesken_cnn_pilot",
        "purpose": "diagnostic",
        "config": config,
        "source_sha256": expected_source,
        "input_files_sha256": inputs,
        "campaigns": 10,
        "checkpoint_model_fits": 100,
        "independent_full_reference_fits": 5,
        "primary": "paired normalized Pearson AULC, diversity minus random",
        "primary_difference": statistics([item["difference"] for item in primary]),
        "paired_seeds": primary,
        "curves": curves,
        "full_references": references,
        "full_reference_per_seed": [
            {
                "seed": run["config"]["seed"],
                "labels": run["full_pool_labels"],
                "metrics": run["full_pool_metrics"],
            }
            for run in matched["random"]
        ],
        "caveats": suite["caveats"],
        "dispersion": "sample standard deviation; not a confidence interval",
        "selection_information": (
            "label-blind coverage, not efficacy-feedback adaptation"
        ),
        "gate_1_all_dataset_or_exact_historical_reproduction": False,
    }


def plot(report: dict, destination: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.7), constrained_layout=True)
    for axis, metric, title in zip(
        axes,
        ("pearson_r", "rmse", "mae"),
        ("Held-out Pearson r", "Held-out RMSE", "Held-out MAE"),
        strict=True,
    ):
        for policy, color in (("random", "#2878B5"), ("diversity", "#E07A24")):
            points = report["curves"][policy]
            x = [point["labels"] for point in points]
            mean = np.asarray([point[metric]["mean"] for point in points], dtype=float)
            sd = np.asarray(
                [point[metric]["sample_sd"] for point in points], dtype=float
            )
            axis.plot(x, mean, label=policy, color=color, marker="o", markersize=3)
            axis.fill_between(x, mean - sd, mean + sd, color=color, alpha=0.16)
            for point, value in zip(points, mean, strict=True):
                if point[metric]["n"] < 5 and math.isfinite(value):
                    axis.annotate(
                        f"n={point[metric]['n']}",
                        (point["labels"], value),
                        fontsize=7,
                    )
        reference = report["full_references"][metric]
        mean, sd = reference["mean"], reference["sample_sd"]
        if mean is not None:
            axis.axhline(mean, color="#222222", linestyle="--", label="full-pool mean")
            if sd is not None:
                axis.axhspan(mean - sd, mean + sd, color="gray", alpha=0.1)
        for row in report["full_reference_per_seed"]:
            value = row["metrics"][metric]
            if value is not None:
                axis.axhline(value, color="gray", alpha=0.22, linewidth=0.7)
        axis.set(xlabel="Measured labels revealed", ylabel=title)
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
    fig.suptitle(
        "Huesken CNN pilot · five paired nucleobase holdouts · bands = sample SD"
    )
    fig.savefig(destination / "learning-curves.png", dpi=180)
    fig.savefig(destination / "learning-curves.svg")
    plt.close(fig)
    fig, axis = plt.subplots(figsize=(7, 4), constrained_layout=True)
    valid = [item for item in report["paired_seeds"] if item["difference"] is not None]
    axis.bar([item["seed"] for item in valid], [item["difference"] for item in valid])
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set(
        xlabel="Paired seed",
        ylabel="Normalized Pearson AULC: diversity − random",
        title="Per-seed acquisition differences; positive favors diversity",
    )
    fig.savefig(destination / "paired-aulc.png", dpi=180)
    fig.savefig(destination / "paired-aulc.svg")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Report output exists; preserve previous reports")
    report = analyze(args.suite)
    args.output.mkdir(parents=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    plot(report, args.output)
    result = report["primary_difference"]
    print(
        json.dumps({"primary_difference": result, "output": str(args.output)}, indent=2)
    )


if __name__ == "__main__":
    main()
