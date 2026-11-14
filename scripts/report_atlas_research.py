"""Aggregate complete development matrices without promoting seeds to targets."""

import json
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path("artifacts/atlas-rnafm")


def areas(rows: list[dict], key: str) -> dict:
    grouped = defaultdict(list)
    for row in rows:
        if row.get("stage", "target") != "target" or row["budget"] == 0:
            continue
        grouped[(row["target"], row["seed"], row[key])].append(row)
    values = {}
    for group, points in grouped.items():
        points = sorted(points, key=lambda r: r["budget"])
        budgets = np.array([p["budget"] for p in points])
        if budgets[0] != 50 or budgets[-1] != 200:
            raise ValueError("Incomplete budget window")
        values[group] = float(
            np.trapz([p["metrics"]["rmse"] for p in points], budgets) / 150.0
        )
    return values


def main() -> None:
    out = ROOT / "summary-v1"
    out.mkdir(exist_ok=True)
    classical = json.loads((ROOT / "classical-development-v1/report.json").read_text())
    fm = json.loads((ROOT / "fm-development-v1/report.json").read_text())
    rows = [r for r in classical["rows"] if r["stage"] == "target"] + fm["rows"]
    a = areas(rows, "model")
    summary = {}
    for model in sorted({k[2] for k in a}):
        differences = defaultdict(list)
        for (target, seed, m), value in a.items():
            if m == model:
                differences[target].append(value - a[(target, seed, "ridge_offset")])
        vals = {k: float(np.mean(v)) for k, v in differences.items()}
        summary[model] = {
            "target_aulc_rmse_differences_vs_ridge_offset": vals,
            "macro_difference": float(np.mean(list(vals.values()))),
            "target_sd": float(np.std(list(vals.values()), ddof=1)),
        }
    models = ["ridge_target_only", "ridge_offset", "frozen_chemistry", "lora_chemistry"]
    targets = ["F7", "STAT3", "NLRP3"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharex=True)
    for ax, target in zip(axes, targets):
        for model in models:
            means = []
            stds = []
            for b in [50, 100, 200]:
                y = [
                    r["metrics"]["rmse"]
                    for r in rows
                    if r["target"] == target
                    and r["model"] == model
                    and r["budget"] == b
                ]
                means.append(np.mean(y))
                stds.append(np.std(y, ddof=1))
            ax.plot([50, 100, 200], means, marker="o", label=model.replace("_", " "))
            ax.fill_between(
                [50, 100, 200],
                np.array(means) - stds,
                np.array(means) + stds,
                alpha=0.10,
            )
        ax.set_title(target)
        ax.set_xlabel("New-target measured labels")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("RMSE (inhibition percentage points)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=8)
    fig.suptitle(
        "ASO development: transfer arms share 1,000 historical labels; "
        "bands = seed SD (n=3)"
    )
    fig.tight_layout(rect=(0, 0.13, 1, 0.92))
    fig.savefig(out / "transfer-curves.png", dpi=180)
    plt.close(fig)
    payload = {
        "transfer": summary,
        "caveat": "Three development target identifiers; "
        "source training seed fixed; no confirmation",
    }
    path = ROOT / "acquisition-development-v1/report.json"
    if path.exists():
        acq = json.loads(path.read_text())
        v = areas(acq["rows"], "policy")
        res = {}
        for policy in sorted({k[2] for k in v}):
            differences = defaultdict(list)
            crossings = []
            for (target, seed, p), value in v.items():
                if p != policy:
                    continue
                differences[target].append(value - v[(target, seed, "random")])
                series = sorted(
                    [
                        r
                        for r in acq["rows"]
                        if r["target"] == target
                        and r["seed"] == seed
                        and r["policy"] == policy
                    ],
                    key=lambda r: r["budget"],
                )
                crossed = [
                    r["budget"]
                    for r in series
                    if r["metrics"]["rmse"] <= 1.1 * acq["references"][target]["rmse"]
                ]
                crossings.append(
                    {
                        "target": target,
                        "seed": seed,
                        "first_crossing": min(crossed) if crossed else None,
                        "censored": not bool(crossed),
                    }
                )
            vals = {k: float(np.mean(x)) for k, x in differences.items()}
            res[policy] = {
                "target_aulc_rmse_differences_vs_random": vals,
                "macro_difference": float(np.mean(list(vals.values()))),
                "crossings": crossings,
                "n_crossed": sum(not c["censored"] for c in crossings),
            }
        payload["acquisition"] = res
        for target in targets:
            for seed in acq["config"]["seeds"]:
                ledgers = [
                    ledger
                    for ledger in acq["ledgers"]
                    if ledger["target"] == target and ledger["seed"] == seed
                ]
                assert len(ledgers) == 6 and all(
                    ledger["initial_ids"] == ledgers[0]["initial_ids"]
                    for ledger in ledgers
                )
                for ledger in ledgers:
                    ids = ledger["initial_ids"] + sum(ledger["batches"], [])
                    assert len(ids) == len(set(ids)) == 200
                initial = [
                    r["metrics"]["rmse"]
                    for r in acq["rows"]
                    if r["target"] == target and r["seed"] == seed and r["budget"] == 50
                ]
                assert max(initial) == min(initial)
        fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharex=True)
        for ax, target in zip(axes, targets):
            for policy in res:
                budgets = list(range(50, 201, 25))
                means = [
                    np.mean(
                        [
                            r["metrics"]["rmse"]
                            for r in acq["rows"]
                            if r["target"] == target
                            and r["policy"] == policy
                            and r["budget"] == b
                        ]
                    )
                    for b in budgets
                ]
                stds = [
                    np.std(
                        [
                            r["metrics"]["rmse"]
                            for r in acq["rows"]
                            if r["target"] == target
                            and r["policy"] == policy
                            and r["budget"] == b
                        ],
                        ddof=1,
                    )
                    for b in budgets
                ]
                ax.plot(budgets, means, label=policy.replace("_", " "), linewidth=1.5)
                ax.fill_between(
                    budgets, np.array(means) - stds, np.array(means) + stds, alpha=0.07
                )
            ax.axhline(
                acq["references"][target]["rmse"],
                color="black",
                linestyle=":",
                label="full-pool reference",
            )
            ax.set_title(target)
            ax.set_xlabel("New-target measured labels")
            ax.grid(alpha=0.2)
        axes[0].set_ylabel("RMSE (inhibition percentage points)")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=7)
        fig.suptitle(
            "Fixed predictor; source-trained acquisition geometry; "
            "bands = seed SD (n=3)"
        )
        fig.tight_layout(rect=(0, 0.13, 1, 0.92))
        fig.savefig(out / "acquisition-curves.png", dpi=180)
        plt.close(fig)
    (out / "summary.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                stage: {k: v["macro_difference"] for k, v in table.items()}
                for stage, table in payload.items()
                if isinstance(table, dict)
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
