"""Audit paired full-data runs and export descriptive statistics and figures."""

import argparse
import csv
import hashlib
import json
import platform
from collections import defaultdict
from pathlib import Path
from statistics import fmean, stdev


def statistics(values: list[float | None]) -> dict:
    defined = [float(v) for v in values if v is not None]
    return {
        "n": len(defined),
        "mean": fmean(defined) if defined else None,
        "sample_sd": stdev(defined) if len(defined) > 1 else None,
        "values": values,
    }


def validate_pair(random: dict, uncertainty: dict) -> None:
    for key in ("dataset", "split", "config", "model", "initial_ids"):
        if random[key] != uncertainty[key]:
            raise ValueError(f"Policies are not paired on {key}")
    if random["full_pool_metrics"] != uncertainty["full_pool_metrics"]:
        raise ValueError("Paired full-pool references differ")
    for run in (random, uncertainty):
        if run["execution"].get("fit_order") != "sample_id_lexicographic":
            raise ValueError("Acquisition-dependent fit order is not comparable")
        if (
            run["dataset"]["metadata"]["selected_rows"]
            != run["dataset"]["metadata"]["source_rows"]
        ):
            raise ValueError("Expected full data, not a sampled engineering check")
        points = run["checkpoints"]
        if points[0]["acquired_ids"] != run["initial_ids"]:
            raise ValueError("Initial labels do not match the acquisition ledger")
        cumulative = 0
        for point in points:
            cumulative += len(point["acquired_ids"])
            if cumulative != point["labels_used"]:
                raise ValueError("Checkpoint label counts do not match acquired IDs")
        counts = [p["labels_used"] for p in points]
        if counts != sorted(set(counts)):
            raise ValueError("Budgets are not strictly increasing")
        acquired = [i for p in points for i in p["acquired_ids"]]
        if (
            len(acquired) != len(set(acquired))
            or len(acquired) != run["config"]["max_labels"]
            or set(acquired) - set(run["split"]["train_ids"])
        ):
            raise ValueError("Acquisition ledger violates pool/budget invariants")
        if set(acquired) & set(run["split"]["test_ids"]):
            raise ValueError("Held-out rows were acquired")
        if points[-1]["labels_used"] == run["full_pool_labels"]:
            if points[-1]["metrics"] != run["full_pool_metrics"]:
                raise ValueError("Complete pool differs from the same-model reference")
    if [p["labels_used"] for p in random["checkpoints"]] != [
        p["labels_used"] for p in uncertainty["checkpoints"]
    ]:
        raise ValueError("Policies have unmatched budget checkpoints")


def efficiency(run: dict, tolerance: float, fraction: float) -> dict:
    reference = run["full_pool_metrics"]["pearson_r"]
    if reference is None or reference <= 0:
        return {"status": "reference_not_positive", "labels": None}
    threshold = reference - tolerance
    reached = next(
        (
            p["labels_used"]
            for p in run["checkpoints"]
            if p["metrics"]["pearson_r"] is not None
            and p["metrics"]["pearson_r"] >= threshold
        ),
        None,
    )
    return {
        "status": "reached" if reached is not None else "not_reached",
        "threshold_r": threshold,
        "labels": reached,
        "fraction_of_training_pool": reached / run["full_pool_labels"]
        if reached is not None
        else None,
        "meets_fraction_criterion": reached / run["full_pool_labels"] <= fraction
        if reached is not None
        else False,
    }


def aulc_reason(run: dict) -> str | None:
    if run["normalized_pearson_aulc"] is not None:
        return None
    if len(run["checkpoints"]) < 2:
        return "single_checkpoint_no_budget_interval"
    return "undefined_checkpoint_pearson"


def curve(runs: list[dict], metric: str) -> list[dict]:
    by_count = defaultdict(list)
    for run in runs:
        for point in run["checkpoints"]:
            by_count[point["labels_used"]].append(
                (run["config"]["seed"], point["metrics"][metric])
            )
    return [
        {
            "labels": n,
            **statistics([value for _, value in values]),
            "valid_seeds": [seed for seed, value in values if value is not None],
        }
        for n, values in sorted(by_count.items())
    ]


def analyze(root: Path) -> dict:
    suite = json.loads((root / "suite.json").read_text())
    if suite["status"] not in ("complete", "incomplete"):
        raise ValueError("The suite is running, interrupted, or superseded")
    if suite["config"].get("max_rows") is not None:
        raise ValueError("Full-data analysis does not accept a row cap")
    if len(suite["config"]["seeds"]) < 5:
        raise ValueError("At least five seeds are required")
    if set(suite["config"]["policies"]) != {"random", "uncertainty"}:
        raise ValueError("Expected the predefined random/uncertainty comparison")
    settings = suite["config"]["analysis"]
    report = {
        "status": "complete",
        "split": suite["config"]["split"],
        "config": suite["config"],
        "source_revision": suite["source_revision"],
        "source_sha256": suite["environment"]["source_sha256"],
        "config_sha256": suite["config_sha256"],
        "dispersion": "sample SD across five seeds; not a confidence interval",
        "primary": "paired normalized Pearson AULC: uncertainty minus random",
        "caveats": [
            "Diagnostic HELM-hash RF; not published benchmark reproduction.",
            "Local exact-sequence/target group holdout; overlapping seeded test sets.",
            "Uncalibrated tree spread; endpoint scales are not pooled.",
            "Five seeds provide limited precision; no significance or clinical claim.",
            "Tolerance/fraction thresholds are reporting only, never policy feedback.",
        ],
        "datasets": [],
        "input_files_sha256": {},
    }
    for dataset in suite["datasets"]:
        if dataset["status"] == "unsupported_split":
            report["datasets"].append(
                {
                    "key": dataset["key"],
                    "name": dataset["name"],
                    "status": "unsupported_split",
                    "reason": dataset["reason"],
                }
            )
            continue
        if dataset["status"] != "complete":
            raise ValueError(f"Incomplete dataset: {dataset['key']}")
        policies = {}
        for policy in ("random", "uncertainty"):
            runs = []
            for seed in suite["config"]["seeds"]:
                relative = Path(dataset["name"]) / policy / f"run-seed-{seed}.json"
                path = root / relative
                content = path.read_bytes()
                run = json.loads(content)
                if run["policy"]["name"] != policy or run["config"]["seed"] != seed:
                    raise ValueError(
                        "Artifact policy/seed does not match its directory"
                    )
                if run["dataset"]["name"] != dataset["name"]:
                    raise ValueError("Artifact belongs to a different dataset")
                if run["environment"]["source_sha256"] != report["source_sha256"]:
                    raise ValueError("Experiment source changed during this suite")
                report["input_files_sha256"][str(relative)] = hashlib.sha256(
                    content
                ).hexdigest()
                runs.append(run)
            policies[policy] = runs
        random, uncertainty = policies["random"], policies["uncertainty"]
        pairs = []
        for r, u in zip(random, uncertainty, strict=True):
            validate_pair(r, u)
            ra, ua = r["normalized_pearson_aulc"], u["normalized_pearson_aulc"]
            rf, uf = (
                r["checkpoints"][-1]["metrics"]["pearson_r"],
                u["checkpoints"][-1]["metrics"]["pearson_r"],
            )
            pairs.append(
                {
                    "seed": r["config"]["seed"],
                    "max_labels": r["config"]["max_labels"],
                    "train_rows": r["full_pool_labels"],
                    "test_rows": len(r["split"]["test_ids"]),
                    "delta_aulc": ua - ra
                    if ra is not None and ua is not None
                    else None,
                    "random_aulc_undefined_reason": aulc_reason(r),
                    "uncertainty_aulc_undefined_reason": aulc_reason(u),
                    "delta_final_r": uf - rf
                    if rf is not None and uf is not None
                    else None,
                    "random_efficiency": efficiency(
                        r,
                        settings["full_reference_absolute_r_tolerance"],
                        settings["label_fraction_criterion"],
                    ),
                    "uncertainty_efficiency": efficiency(
                        u,
                        settings["full_reference_absolute_r_tolerance"],
                        settings["label_fraction_criterion"],
                    ),
                }
            )
        entry = {
            "key": dataset["key"],
            "name": dataset["name"],
            "status": "complete",
            "source_rows": random[0]["dataset"]["metadata"]["source_rows"],
            "pairs": pairs,
            "paired_delta_aulc": statistics([p["delta_aulc"] for p in pairs]),
            "paired_delta_final_r": statistics([p["delta_final_r"] for p in pairs]),
            "full_reference_r": statistics(
                [r["full_pool_metrics"]["pearson_r"] for r in random]
            ),
            "policies": {},
        }
        for policy, runs in policies.items():
            entry["policies"][policy] = {
                "pearson_curve": curve(runs, "pearson_r"),
                "aulc": statistics([r["normalized_pearson_aulc"] for r in runs]),
                "final_r": statistics(
                    [r["checkpoints"][-1]["metrics"]["pearson_r"] for r in runs]
                ),
                "final_rmse": statistics(
                    [r["checkpoints"][-1]["metrics"]["rmse"] for r in runs]
                ),
                "final_mae": statistics(
                    [r["checkpoints"][-1]["metrics"]["mae"] for r in runs]
                ),
            }
        report["datasets"].append(entry)
    report["completed_datasets"] = sum(
        d["status"] == "complete" for d in report["datasets"]
    )
    report["unsupported_datasets"] = sum(
        d["status"] == "unsupported_split" for d in report["datasets"]
    )
    report["source_suite_status"] = suite["status"]
    if report["unsupported_datasets"]:
        report["status"] = "complete_with_unsupported_splits"
    report["completed_campaigns"] = (
        len(suite["config"]["seeds"]) * 2 * report["completed_datasets"]
    )
    return report


def render(report: dict, output: Path) -> None:
    import os
    import tempfile

    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "oligoal-mpl-report")
    )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    report["renderer"] = {
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
    }
    fig, axes = plt.subplots(4, 3, figsize=(16, 15))
    colors = {"random": "#2878B5", "uncertainty": "#D55E00"}
    import textwrap

    for axis, dataset in zip(axes.flat, report["datasets"]):
        axis.set_title(dataset["key"], loc="left", fontsize=12, fontweight="bold")
        if dataset["status"] != "complete":
            axis.text(
                0.05,
                0.6,
                "Target holdout unsupported\n\n" + textwrap.fill(dataset["reason"], 44),
                transform=axis.transAxes,
                fontsize=9,
                va="top",
            )
            axis.set_axis_off()
            continue
        for policy in ("random", "uncertainty"):
            values = dataset["policies"][policy]["pearson_curve"]
            x = [p["labels"] for p in values]
            means = [
                p["mean"] if p["mean"] is not None else float("nan") for p in values
            ]
            lower = [
                p["mean"] - p["sample_sd"]
                if p["mean"] is not None and p["sample_sd"] is not None
                else float("nan")
                for p in values
            ]
            upper = [
                p["mean"] + p["sample_sd"]
                if p["mean"] is not None and p["sample_sd"] is not None
                else float("nan")
                for p in values
            ]
            # Do not connect means calculated from different contributing seeds.
            start = 0
            for stop in range(1, len(values) + 1):
                if (
                    stop == len(values)
                    or values[stop]["valid_seeds"] != values[start]["valid_seeds"]
                ):
                    axis.plot(
                        x[start:stop],
                        means[start:stop],
                        "o-",
                        color=colors[policy],
                        markersize=3,
                        label=policy if start == 0 else None,
                    )
                    axis.fill_between(
                        x[start:stop],
                        lower[start:stop],
                        upper[start:stop],
                        color=colors[policy],
                        alpha=0.15,
                    )
                    start = stop
            for point in values:
                if point["mean"] is not None and point["n"] < len(
                    report["config"]["seeds"]
                ):
                    axis.annotate(
                        f"n={point['n']}",
                        (point["labels"], point["mean"]),
                        xytext=(0, 5),
                        textcoords="offset points",
                        fontsize=6,
                        color=colors[policy],
                        ha="center",
                    )
        reference = dataset["full_reference_r"]
        if reference["mean"] is not None:
            axis.axhline(
                reference["mean"],
                color="#333333",
                linestyle="--",
                linewidth=1.2,
                label="full training pool",
            )
            if reference["sample_sd"] is not None:
                axis.axhspan(
                    reference["mean"] - reference["sample_sd"],
                    reference["mean"] + reference["sample_sd"],
                    color="#777777",
                    alpha=0.10,
                )
        axis.set_xlabel("Measured training labels", fontsize=9)
        axis.set_ylabel("Test Pearson r", fontsize=9)
        axis.grid(alpha=0.18)
        axis.tick_params(labelsize=8)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=3,
        bbox_to_anchor=(0.5, 0.96),
        frameon=False,
    )
    fig.suptitle(
        "Full-data random vs uncertainty acquisition — "
        f"{report['split']['strategy']} holdout",
        fontsize=17,
        y=0.99,
    )
    fig.text(
        0.5,
        0.015,
        "Five seeds; defined counts in JSON. Bands: sample SD, not CI. "
        "Diagnostic HELM-hash RF; not official benchmark reproduction.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.94))
    for suffix in ("png", "svg"):
        fig.savefig(output / f"learning-curves.{suffix}", dpi=180, bbox_inches="tight")
    plt.close(fig)
    complete = [d for d in report["datasets"] if d["status"] == "complete"]
    fig, axis = plt.subplots(figsize=(10, max(4, 0.45 * len(complete))))
    for index, dataset in enumerate(complete):
        stat = dataset["paired_delta_aulc"]
        if stat["mean"] is not None:
            axis.errorbar(
                stat["mean"],
                index,
                xerr=stat["sample_sd"],
                fmt="o",
                capsize=4,
                color="#D55E00" if stat["mean"] >= 0 else "#2878B5",
            )
    axis.set_yticks(
        range(len(complete)),
        [
            d["key"]
            + (
                f" (n={d['paired_delta_aulc']['n']})"
                if d["paired_delta_aulc"]["n"] < len(report["config"]["seeds"])
                else ""
            )
            for d in complete
        ],
    )
    axis.invert_yaxis()
    axis.axvline(0, color="#777777", linewidth=1)
    axis.set_xlabel(
        "Paired normalized Pearson AULC: uncertainty minus random\n"
        "Mean ± sample SD across five seeds"
    )
    axis.set_title(
        "Acquisition effect over the full label-budget interval "
        f"({report['split']['strategy']})"
    )
    axis.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output / "paired-aulc.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_report(report: dict, output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Report output must be empty")
    output.mkdir(parents=True, exist_ok=True)
    fields = [
        "dataset",
        "status",
        "source_rows",
        "label_budget_min",
        "label_budget_max",
        "paired_seeds",
        "defined_aulc_pairs",
        "defined_final_r_pairs",
        "random_final_r",
        "random_final_r_sd",
        "uncertainty_final_r",
        "uncertainty_final_r_sd",
        "full_reference_r",
        "full_reference_r_sd",
        "paired_delta_aulc",
        "paired_delta_aulc_sd",
        "reason",
    ]
    with (output / "summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for d in report["datasets"]:
            row = {"dataset": d["key"], "status": d["status"]}
            if d["status"] == "complete":
                row.update(source_rows=d["source_rows"], paired_seeds=len(d["pairs"]))
                row.update(
                    label_budget_min=min(p["max_labels"] for p in d["pairs"]),
                    label_budget_max=max(p["max_labels"] for p in d["pairs"]),
                )
                row.update(
                    defined_aulc_pairs=d["paired_delta_aulc"]["n"],
                    defined_final_r_pairs=d["paired_delta_final_r"]["n"],
                )
                for policy in ("random", "uncertainty"):
                    row[f"{policy}_final_r"] = d["policies"][policy]["final_r"]["mean"]
                    row[f"{policy}_final_r_sd"] = d["policies"][policy]["final_r"][
                        "sample_sd"
                    ]
                row.update(
                    full_reference_r=d["full_reference_r"]["mean"],
                    full_reference_r_sd=d["full_reference_r"]["sample_sd"],
                    paired_delta_aulc=d["paired_delta_aulc"]["mean"],
                    paired_delta_aulc_sd=d["paired_delta_aulc"]["sample_sd"],
                )
            else:
                row["reason"] = d["reason"]
            writer.writerow(row)
    render(report, output)
    report["analysis_script_sha256"] = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    (output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.suite)
    write_report(report, args.output)
    print(
        f"Analyzed {report['completed_campaigns']} campaigns; "
        f"{report['unsupported_datasets']} unsupported datasets"
    )


if __name__ == "__main__":
    main()
