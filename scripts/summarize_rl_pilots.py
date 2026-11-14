"""Verify and summarize bounded Huesken RL runs without reading assay labels."""

import argparse
import json
from pathlib import Path
from statistics import mean, stdev


def summarize(paths: list[Path]) -> dict:
    reports = [json.loads(path.read_text()) for path in paths]
    if len(reports) < 2:
        raise ValueError("At least two complete runs are required")
    reference = reports[0]
    for report in reports:
        if report["status"] != "complete" or report["mode"] != "huesken":
            raise ValueError("All runs must be complete restricted Huesken runs")
        for field in ("bundle_identity", "scorer_identity", "environment", "algorithm"):
            if report[field] != reference[field]:
                raise ValueError(f"Run mismatch: {field}")
        if (
            not report["checkpoint_reload_equal"]
            or not report["policy_parameters_changed"]
        ):
            raise ValueError("Checkpoint or learning check failed")
        budget = report["training_unique_scores"]
        if not report["training_trace"] or len(report["training_trace"]) != budget:
            raise ValueError("Training trace and budget disagree")
        for method in ("random", "evolutionary"):
            comparison = report["comparators"][method]
            if (
                comparison["unique_budget"] != budget
                or comparison["unique_scores"] != budget
            ):
                raise ValueError(f"Unmatched {method} score budget")
    if len({report["seed"] for report in reports}) != len(reports):
        raise ValueError("Repeated seed")
    rows = []
    for report in sorted(reports, key=lambda item: item["seed"]):
        scores = {
            "ppo": report["training_trace"][-1]["best_reward"],
            "random": report["comparators"]["random"]["best_reward"],
            "evolutionary": report["comparators"]["evolutionary"]["best_reward"],
        }
        rows.append(
            {
                "seed": report["seed"],
                "unique_score_budget": report["training_unique_scores"],
                "training_score_requests": report["training_score_requests"],
                **{f"{method}_best_reward": value for method, value in scores.items()},
                "ppo_minus_random": scores["ppo"] - scores["random"],
                "ppo_minus_evolutionary": scores["ppo"] - scores["evolutionary"],
                "validation_mean_reward": report["best_validation_mean_reward"],
                "final_heldout_start_mean_reward": report[
                    "final_heldout_start_evaluation"
                ]["mean_reward"],
                "runtime_seconds": report["runtime_seconds"],
            }
        )
    fields = [key for key in rows[0] if key != "seed"]
    return {
        "status": "complete",
        "scope": "unvalidated_frozen_Huesken_Ridge_surrogate_only",
        "bundle_identity": reference["bundle_identity"],
        "scorer_identity": reference["scorer_identity"],
        "algorithm": reference["algorithm"],
        "run_count": len(rows),
        "rows": rows,
        "aggregate": {
            field: {
                "mean": mean(row[field] for row in rows),
                "sample_sd": stdev(row[field] for row in rows),
            }
            for field in fields
        },
        "ppo_wins_over_random": sum(row["ppo_minus_random"] > 0 for row in rows),
        "ppo_wins_over_evolutionary": sum(
            row["ppo_minus_evolutionary"] > 0 for row in rows
        ),
    }


def plot_runs(paths: list[Path], output: Path) -> None:
    """Plot mean and sample SD at each shared unique-score count."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    reports = [json.loads(path.read_text()) for path in paths]
    shared_budget = min(report["training_unique_scores"] for report in reports)
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, key, color in (
        ("MaskablePPO", "training_trace", "#7B5AA6"),
        ("Random search", "random", "#2574A9"),
        ("Evolutionary search", "evolutionary", "#D67D22"),
    ):
        traces = [
            report[key]
            if key == "training_trace"
            else report["comparators"][key]["trace"]
            for report in reports
        ]
        values = np.array(
            [
                [point["best_reward"] for point in trace[:shared_budget]]
                for trace in traces
            ]
        )
        x = np.arange(1, shared_budget + 1)
        averages = values.mean(axis=0)
        spread = values.std(axis=0, ddof=1)
        ax.plot(x, averages, label=label, color=color, linewidth=2)
        ax.fill_between(
            x, averages - spread, averages + spread, color=color, alpha=0.16
        )
    ax.set(
        xlabel="Unique frozen-scorer evaluations",
        ylabel="Best predictor-based reward seen",
    )
    ax.set_title(f"Restricted Huesken search, {len(reports)} optimization seeds")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.text(
        0.5,
        0.01,
        "Shading: between-seed SD. Rewards are unvalidated predictions.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plot", type=Path)
    args = parser.parse_args()
    result = summarize(args.reports)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.plot:
        if args.plot.exists():
            raise FileExistsError(args.plot)
        args.plot.parent.mkdir(parents=True, exist_ok=True)
        plot_runs(args.reports, args.plot)
    print(json.dumps(result["aggregate"], indent=2))


if __name__ == "__main__":
    main()
