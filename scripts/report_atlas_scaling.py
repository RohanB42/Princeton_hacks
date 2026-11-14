"""Render actual epoch histories and paired developmental scaling outcomes."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

COLORS = {"lora_chemistry": "#b35806", "frozen_chemistry": "#2166ac"}


def source_curves(output: Path) -> None:
    """Render completed epochs only; missing fits stay visibly pending."""
    cfg = json.loads((output / "config.json").read_text())
    for axis_key, xlabel, name in [
        ("epoch", "Epoch", "source-loss-epochs.png"),
        ("elapsed_s", "Elapsed minutes (includes validation)", "source-loss-time.png"),
    ]:
        fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharey=True)
        for row, seed in enumerate(cfg["source_seeds"]):
            for col, budget in enumerate(cfg["source_budgets"]):
                ax = axes[row, col]
                found = False
                for model, color in COLORS.items():
                    directory = output / f"source-{budget}-{seed}-{model}"
                    path = directory / "history.json"
                    if not path.exists():
                        continue
                    found = True
                    history = pd.DataFrame(json.loads(path.read_text()))
                    x = history[axis_key] / (60 if axis_key == "elapsed_s" else 1)
                    ax.plot(
                        x,
                        history.train_mse,
                        color=color,
                        marker=".",
                        label=f"{model.split('_')[0]} train",
                    )
                    ax.plot(
                        x,
                        history.validation_mse,
                        color=color,
                        linestyle="--",
                        marker=".",
                        label=f"{model.split('_')[0]} validation",
                    )
                    if (directory / "receipt.json").exists():
                        receipt = json.loads((directory / "receipt.json").read_text())
                        best = history.loc[
                            history.epoch == receipt["selected_epoch"]
                        ].iloc[0]
                        bx = best[axis_key] / (60 if axis_key == "elapsed_s" else 1)
                        ax.scatter(
                            bx,
                            best.validation_mse,
                            color=color,
                            marker="*",
                            s=100,
                            zorder=5,
                        )
                ax.set_title(
                    f"{budget:,} labels ({budget / cfg['source_denominator']:.2%}); "
                    f"seed {seed}"
                )
                ax.set_xlabel(xlabel)
                ax.set_ylabel("MSE (inhibition percentage points²)")
                ax.grid(alpha=0.2)
                if found:
                    ax.legend(fontsize=7)
                else:
                    ax.text(0.5, 0.5, "Pending", ha="center", transform=ax.transAxes)
        fig.suptitle(
            "Atlas source training vs patent-held-out validation\n"
            "Solid=train; dashed=validation; star=selected checkpoint. "
            "Validation labels count in budgets."
        )
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fig.savefig(output / name, dpi=180)
        plt.close(fig)


def report(output: Path) -> None:
    source_curves(output)
    rows = []
    for path in sorted(output.glob("source-*/receipt.json")):
        receipt = json.loads(path.read_text())
        parts = path.parent.name.split("-", 3)
        history = receipt.get("history", [])
        selected = receipt.get("selected_epoch")
        best = next((h for h in history if h["epoch"] == selected), {})
        third = next((h for h in history if h["epoch"] == 3), {})
        rows.append(
            {
                "source_budget": int(parts[1]),
                "seed": int(parts[2]),
                "model": parts[3],
                "fit_labels": receipt["n_labels"],
                "validation_labels": receipt["validation_labels"],
                "epochs_run": receipt.get("epochs"),
                "selected_epoch": selected,
                "selected_validation_rmse": best.get(
                    "validation_rmse",
                    receipt.get("selected_validation_metrics", {}).get("rmse"),
                ),
                "epoch3_validation_rmse": third.get("validation_rmse"),
                "elapsed_s": receipt.get("elapsed_s"),
            }
        )
    pd.DataFrame(rows).to_csv(output / "source-summary.csv", index=False)
    if not (output / "report.json").exists():
        print("Wrote actual source curves; target fitting/scoring still pending")
        return
    result = json.loads((output / "report.json").read_text())
    table = pd.DataFrame(
        [
            r | {f"metric_{k}": v for k, v in r["metrics"].items()}
            for r in result["rows"]
        ]
    ).drop(columns=["metrics"])
    table.to_csv(output / "target-results.csv", index=False)
    summary = (
        table.groupby(["model", "source_budget", "protocol"])
        .agg(
            rmse=("metric_rmse", "mean"),
            pearson=("metric_pearson", "mean"),
            pearson_defined=("metric_pearson", "count"),
            spearman=("metric_spearman", "mean"),
            mae=("metric_mae", "mean"),
            records=("target", "count"),
        )
        .reset_index()
    )
    summary.to_csv(output / "target-summary.csv", index=False)
    comparisons = []
    for (model, budget), frame in table[table.model.isin(COLORS)].groupby(
        ["model", "source_budget"]
    ):
        pivot = frame.pivot(
            index=["target", "target_seed"], columns="protocol", values="metric_rmse"
        )
        for a, b, description in [
            (
                "sourcebest_target3_all",
                "source3_target3_all",
                "source duration: selected minus epoch3; target3 all200 fixed",
            ),
            (
                "sourcebest_targetselected_inner",
                "sourcebest_target3_all",
                "target protocol: selected/inner minus fixed3/all200; "
                "fitting counts differ",
            ),
        ]:
            difference = pivot[a] - pivot[b]
            comparisons.append(
                {
                    "model": model,
                    "source_budget": int(budget),
                    "contrast": description,
                    "mean_paired_rmse_difference": float(difference.mean()),
                    "paired_record_sd": float(difference.std(ddof=1)),
                    "per_target_mean": {
                        str(k): float(v)
                        for k, v in difference.groupby(level=0).mean().items()
                    },
                    "n_pairs": len(difference),
                    "n_independent_target_identifiers": 3,
                }
            )
    (output / "paired-comparisons.json").write_text(
        json.dumps(comparisons, indent=2) + "\n"
    )
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    selected = table[
        table.protocol.isin(["sourcebest_target3_all", "sourcebest_offset_all"])
    ]
    for ax, target in zip(axes, ["F7", "STAT3", "NLRP3"]):
        for model in ["lora_chemistry", "frozen_chemistry", "ridge", "xgb"]:
            subset = selected[(selected.target == target) & (selected.model == model)]
            g = subset.groupby("source_budget").metric_rmse.agg(["mean", "std"])
            ax.errorbar(
                g.index / 95638 * 100,
                g["mean"],
                yerr=g["std"],
                label=model,
                marker="o",
                capsize=3,
            )
        ax.set_title(target)
        ax.set_xlabel("Source-label fraction (%)")
        ax.set_ylabel("Held-out target RMSE")
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=7)
    fig.suptitle(
        "200 new-target labels; source validation selected models\n"
        "Error bars: paired-seed sample SD, not confidence intervals; "
        "three development targets"
    )
    fig.text(
        0.5,
        0.01,
        "Budgets include validation; inner source fitting cohorts "
        "are not strictly nested.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.9))
    fig.savefig(output / "target-scaling-comparison.png", dpi=180)
    plt.close(fig)
    # Each duration-selected target fit uses budget-internal validation.
    for model in COLORS:
        for time_axis in [False, True]:
            fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharey=True)
            for row, target in enumerate(["F7", "STAT3", "NLRP3"]):
                for col, budget in enumerate([2869, 4781]):
                    ax = axes[row, col]
                    for seed in [510, 511, 512]:
                        path = output / (
                            f"target-{budget}-{seed}-{model}-{target}-"
                            "sourcebest_targetselected_inner/history.json"
                        )
                        if not path.exists():
                            continue
                        h = pd.DataFrame(json.loads(path.read_text()))
                        (line,) = ax.plot(
                            (h.elapsed_s / 60 if time_axis else h.epoch),
                            h.train_mse,
                            label=f"seed {seed}",
                        )
                        ax.plot(
                            (h.elapsed_s / 60 if time_axis else h.epoch),
                            h.validation_mse,
                            color=line.get_color(),
                            linestyle="--",
                        )
                    ax.set_title(f"{target}; {budget:,} source labels")
                    ax.set_xlabel(
                        "Elapsed minutes" if time_axis else "Target adaptation epoch"
                    )
                    ax.set_ylabel("MSE (percentage points²)")
                    ax.legend(fontsize=7)
                    ax.grid(alpha=0.2)
            fig.suptitle(
                f"{model}: target training (solid) and grouped validation (dashed)\n"
                "Validation rows are inside the 200-label target budget; "
                "test outcomes never select epochs"
            )
            fig.tight_layout(rect=(0, 0, 1, 0.94))
            suffix = "-time" if time_axis else ""
            fig.savefig(output / f"target-loss-{model}{suffix}.png", dpi=180)
            plt.close(fig)
    print(summary.to_string(index=False))
    print("Paired comparisons", json.dumps(comparisons, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/atlas-rnafm/scaling-v1")
    )
    report(parser.parse_args().output)
