"""Seal, verify and analyze existing molecular PPO receipts without model queries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from oligo_engine.molecular_design.artifacts import seal, verify, write_new

TARGETS = ("DGAT2", "CFB", "FGFR4", "F9", "F12", "TTR")
DEVELOPMENT = TARGETS[2:]
METHODS = (
    "full",
    "warm_start",
    "pretrained_prior_ranking",
    "random",
    "greedy",
    "architecture",
)
SEEDS = tuple(range(800, 805))
BUDGETS = (8, 32)


def sha(path: Path) -> str:
    """Hash raw bytes, including model archives without deserializing them."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path, expected: str | None = None) -> dict[str, Any]:
    """Load an existing receipt and require its content seal."""
    result = json.loads(path.read_text())
    verify(result, expected)
    return result


def freeze(source: Path, output: Path) -> None:
    """Lock inputs and descriptive methods before the new analysis executes."""
    names = [
        "protocol.json",
        "config.json",
        "results.json",
        "prior-control-protocol.json",
        "prior-control-results.json",
    ]
    paths = [source / name for name in names]
    for pattern in (
        "runs/*",
        "prior-runs/*",
        "full-*/training.json",
        "full-*/pretraining.json",
        "full-*/*.zip",
        "full-*/validation-*.json",
        "full-*/*-queries.jsonl",
    ):
        paths.extend(p for p in source.glob(pattern) if p.is_file())
    paths.append(Path(__file__))
    write_new(
        output / "protocol.json",
        seal(
            {
                "schema": "molecular-ppo-attribution-v1",
                "source": str(source),
                "status": "post_hoc_development_diagnostic",
                "previous_outcomes_inspected": True,
                "new_queries": 0,
                "measured_labels_accessed": 0,
                "targets": TARGETS,
                "development_targets": DEVELOPMENT,
                "methods": METHODS,
                "seeds": SEEDS,
                "budgets": BUDGETS,
                "outcome": "best eligible archive utility at every actual request",
                "contrasts": [
                    "full-minus-warm_start",
                    "full-minus-pretrained_prior_ranking",
                ],
                "auc": "trapezoidal quality requests 1..B divided by B-1; no padding",
                "statistics": "paired seed differences; crossed target/seed bootstrap "
                "descriptive sensitivity only, not confirmatory confidence or p values",
                "bootstrap": {
                    "replicates": 10000,
                    "seed": 20261115,
                    "targets": DEVELOPMENT,
                    "quantiles": [0.025, 0.975],
                },
                "checkpoint_limit": "existing validation receipts only; no inference",
                "inputs": {str(p): sha(p) for p in sorted(set(paths))},
            }
        ),
    )


def trajectory(run: dict[str, Any], budget: int) -> np.ndarray:
    """Require complete, distinct, monotonically improving scored trajectories."""
    events = run["trace"]
    if run.get("failed") or run["requests"] != budget or len(events) != budget:
        raise ValueError("Incomplete or failed evaluation; no implicit padding")
    if [e["request"] for e in events] != list(range(1, budget + 1)):
        raise ValueError("Request positions are not consecutive")
    if any(e["status"] != "scored" or e["cache_hit"] for e in events):
        raise ValueError("Expected successful unique scoring requests")
    if len({e["design_id"] for e in events}) != budget:
        raise ValueError("Duplicate proposals")
    values = np.asarray([e["quality"] for e in events], dtype=float)
    if (
        not np.all(np.isfinite(values))
        or np.any(values < 0)
        or np.any(values > 1)
        or np.any(np.diff(values) < -1e-12)
    ):
        raise ValueError("Invalid archive quality trajectory")
    initial = [e for e in events if e["initial"]]
    if not initial or events[: len(initial)] != initial:
        raise ValueError("Initial archive must be a prefix")
    if not np.isclose(initial[-1]["quality"], run["initial_quality"], atol=1e-12):
        raise ValueError("Initial quality differs")
    if not np.isclose(values[-1], run["final_quality"], atol=1e-12):
        raise ValueError("Final quality differs")
    return values


def paired_difference(left: dict[str, Any], right: dict[str, Any]) -> np.ndarray:
    """Pair identical campaign/start/model identities, not arbitrary seed rows."""
    for key in ("campaign_id", "registry_id"):
        if left[key] != right[key]:
            raise ValueError(f"Pair has different {key}")

    def starts(run: dict) -> list[tuple[str, float]]:
        return [(e["design_id"], e["quality"]) for e in run["trace"] if e["initial"]]

    if starts(left) != starts(right):
        raise ValueError("Pair has different starting archive")
    budget = left["requests"]
    return trajectory(left, budget) - trajectory(right, budget)


def crossed_resample(matrix: np.ndarray, replicates: int, seed: int) -> dict:
    """Resample targets and whole seed columns, retaining crossed dependence."""
    if matrix.ndim != 2 or min(matrix.shape) < 2 or not np.isfinite(matrix).all():
        raise ValueError("Need a finite target-by-seed matrix")
    rng = np.random.default_rng(seed)
    nt, ns = matrix.shape
    samples = np.empty(replicates)
    for i in range(replicates):
        targets = rng.integers(nt, size=nt)
        seeds = rng.integers(ns, size=ns)
        samples[i] = matrix[np.ix_(targets, seeds)].mean()
    return {
        "mean": float(matrix.mean()),
        "seed_aggregate_sd": float(matrix.mean(axis=0).std(ddof=1)),
        "target_aggregate_sd": float(matrix.mean(axis=1).std(ddof=1)),
        "crossed_resampling_95_percent_range": np.quantile(
            samples, [0.025, 0.975]
        ).tolist(),
        "interpretation": "descriptive sensitivity; four inspected targets, "
        "five shared policy seeds; not a confirmatory confidence interval",
    }


def journal_matches(path: Path, trace: list[dict]) -> None:
    """Verify every link of the durable query journal against the run trace."""
    if journal_events(path) != trace:
        raise ValueError("Journal events differ from receipt")


def journal_events(path: Path) -> list[dict]:
    """Read all query events after verifying the durable chain."""
    previous, events = "", []
    for line in path.read_text().splitlines():
        record = json.loads(line)
        verify(record)
        if record["previous"] != previous:
            raise ValueError("Journal chain broken")
        previous = record["seal"]
        events.append(record["event"])
    return events


def journal_head_calls(events: list[dict]) -> int:
    """Sum cumulative per-episode counters once, including the partial episode."""
    total, previous_request, previous_calls = 0, 0, 0
    for event in events:
        request = event["request"]
        calls = sum(event["head_calls"].values())
        if request == 1:
            total += previous_calls
            previous_request, previous_calls = 0, 0
        if request != previous_request + 1 or calls < previous_calls:
            raise ValueError("Nonmonotone episode counters")
        previous_request, previous_calls = request, calls
    return total + previous_calls


def analyze(source: Path, output: Path) -> None:
    """Generate fully costed descriptive comparisons from locked run receipts."""
    protocol = read(output / "protocol.json")
    if protocol["source"] != str(source):
        raise ValueError("Source differs from frozen protocol")
    amendment = None
    if (output / "code-amendment.json").exists():
        amendment = read(output / "code-amendment.json")
        if amendment["protocol_seal"] != protocol["seal"]:
            raise ValueError("Code amendment names another protocol")
    for name, expected in protocol["inputs"].items():
        if amendment and Path(name).resolve() == Path(__file__).resolve():
            expected = amendment["new_driver_sha256"]
        if sha(Path(name)) != expected:
            raise ValueError(f"Frozen input changed: {name}")
    parent = read(source / "protocol.json")
    result = read(source / "results.json")
    supplement = read(source / "prior-control-protocol.json")
    prior = read(source / "prior-control-results.json")
    if (
        result["protocol_seal"] != parent["seal"]
        or supplement["parent_protocol_seal"] != parent["seal"]
        or prior["protocol_seal"] != supplement["seal"]
        or sha(source / "config.json") != parent["config_sha256"]
    ):
        raise ValueError("Parent protocol provenance differs")
    rows = result["rows"] + [
        dict(row, method="pretrained_prior_ranking") for row in prior["rows"]
    ]
    runs, roles = {}, {}
    for row in rows:
        key = (row["target"], row["method"], row["budget"], row["seed"])
        if key in runs:
            raise ValueError("Duplicate target/method/budget/seed")
        path = Path(row["artifact"])
        artifact = read(path, row["seal"])
        run = artifact["run"]
        trajectory(run, row["budget"])
        journal_matches(path.with_suffix(".jsonl"), run["trace"])
        if run["seed"] != row["seed"] or not np.isclose(
            run["final_quality"], row["quality"], atol=1e-12
        ):
            raise ValueError("Result index differs from run")
        runs[key] = run
        roles[row["target"]] = artifact["campaign"]["partition"]
    expected_keys = {
        (t, m, b, s) for t in TARGETS for m in METHODS for b in BUDGETS for s in SEEDS
    }
    if set(runs) != expected_keys:
        raise ValueError("Incomplete or unexpected evaluation matrix")
    summaries, contrasts, aggregates, costs, prefixes = [], [], [], [], []
    for target in TARGETS:
        for budget in BUDGETS:
            for method in METHODS:
                group = [runs[target, method, budget, s] for s in SEEDS]
                curves = np.stack([trajectory(r, budget) for r in group])
                summaries.append(
                    {
                        "target": target,
                        "role": roles[target],
                        "method": method,
                        "budget": budget,
                        "n_seeds": len(SEEDS),
                        "quality_by_seed": curves.tolist(),
                        "mean_quality_by_request": curves.mean(axis=0).tolist(),
                        "sd_quality_by_request": curves.std(axis=0, ddof=1).tolist(),
                        "initial_quality": [r["initial_quality"] for r in group],
                        "mean_final_gain": float(
                            np.mean(
                                [
                                    r["final_quality"] - r["initial_quality"]
                                    for r in group
                                ]
                            )
                        ),
                        "mean_auc": float(
                            np.trapz(curves, axis=1).mean() / (budget - 1)
                        ),
                    }
                )
            for control in ("warm_start", "pretrained_prior_ranking"):
                differences = np.stack(
                    [
                        paired_difference(
                            runs[target, "full", budget, s],
                            runs[target, control, budget, s],
                        )
                        for s in SEEDS
                    ]
                )
                final = differences[:, -1]
                contrasts.append(
                    {
                        "target": target,
                        "role": roles[target],
                        "budget": budget,
                        "control": control,
                        "paired_final_differences": final.tolist(),
                        "mean": float(final.mean()),
                        "sd": float(final.std(ddof=1)),
                        "wins": int((final > 1e-12).sum()),
                        "ties": int((abs(final) <= 1e-12).sum()),
                        "losses": int((final < -1e-12).sum()),
                        "mean_difference_by_request": differences.mean(axis=0).tolist(),
                        "mean_auc_difference": float(
                            np.trapz(differences, axis=1).mean() / (budget - 1)
                        ),
                    }
                )
        for method in METHODS:
            prefixes.append(
                {
                    "target": target,
                    "method": method,
                    "identical_first_eight_designs": [
                        [e["design_id"] for e in runs[target, method, 8, s]["trace"]]
                        == [
                            e["design_id"]
                            for e in runs[target, method, 32, s]["trace"][:8]
                        ]
                        for s in SEEDS
                    ],
                }
            )
    for budget in BUDGETS:
        for control in ("warm_start", "pretrained_prior_ranking"):
            matrix = np.asarray(
                [
                    next(
                        c["paired_final_differences"]
                        for c in contrasts
                        if c["target"] == t
                        and c["budget"] == budget
                        and c["control"] == control
                    )
                    for t in DEVELOPMENT
                ]
            )
            aggregates.append(
                {
                    "budget": budget,
                    "control": control,
                    "targets": DEVELOPMENT,
                    **crossed_resample(matrix, 10000, 20261115),
                }
            )
    for seed in SEEDS:
        directory = source / f"full-{seed}"
        receipt = read(directory / "training.json")
        pretraining = read(directory / "pretraining.json", receipt["pretraining_seal"])
        if (
            sha(directory / "warm-start-policy.zip") != receipt["warm_start_sha256"]
            or sha(directory / "selected-policy.zip") != receipt["policy_sha256"]
        ):
            raise ValueError("Model bytes differ from training receipt")
        if any(
            x["campaign_id"] not in receipt["protocol"]["training"]
            for x in pretraining["identities"]
        ):
            raise ValueError("Non-training pretraining example")
        for phase in ("training", "validation"):
            events = journal_events(directory / f"{phase}-queries.jsonl")
            if len(events) != receipt[f"{phase}_requests"]:
                raise ValueError("Training/validation query count differs from journal")
            if (
                phase == "training"
                and journal_head_calls(events) != receipt["training_head_calls"]
            ):
                raise ValueError("Training head-call count differs")
        if pretraining["requests"] != receipt["pretraining_requests"]:
            raise ValueError("Pretraining query count differs")
        history = receipt["validation_history"]
        for v in history:
            if read(directory / f"validation-{v['tokens']}.json") != seal(v):
                raise ValueError("Validation history differs from checkpoint receipt")
        best = max(history, key=lambda v: v["mean_final_quality"])
        if best["tokens"] != receipt["selected_tokens"]:
            raise ValueError("Selection does not choose earliest best validation")
        costs.append(
            {
                "seed": seed,
                **{
                    k: receipt[k]
                    for k in (
                        "training_requests",
                        "training_head_calls",
                        "pretraining_requests",
                        "pretraining_head_calls",
                        "validation_requests",
                        "training_seconds",
                        "selected_tokens",
                        "warm_start_sha256",
                        "policy_sha256",
                    )
                },
                "validation_curve": [
                    {"decisions": v["tokens"], "mean_quality": v["mean_final_quality"]}
                    for v in history
                ],
                "zero_step_selectable": any(v["tokens"] == 0 for v in history),
                "available_model_files": sorted(
                    p.name for p in directory.glob("*.zip")
                ),
                "available_prefix_weight_claim": "selected and last only; intermediate "
                "validation scores cannot reconstruct intermediate model weights",
            }
        )
    payload = seal(
        {
            "protocol_seal": protocol["seal"],
            "code_amendment_seal": amendment["seal"] if amendment else None,
            "verified_runs": len(runs),
            "summaries": summaries,
            "contrasts": contrasts,
            "development_aggregates": aggregates,
            "training": costs,
            "cross_budget_prefix_audit": prefixes,
            "new_queries": 0,
        }
    )
    write_new(output / "analysis.json", payload)
    render(payload, output)


def render(analysis: dict, output: Path) -> None:
    """Write all eight request positions and a standalone scientific plot."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = {
        "full": "PPO",
        "warm_start": "Staged pretrained",
        "pretrained_prior_ranking": "Prior ranking",
        "random": "Random",
        "greedy": "Greedy",
        "architecture": "Architecture control",
    }
    lines = [
        "# Post-hoc PPO attribution: all eight charged requests",
        "",
        "Frozen-predictor development diagnostic; means over five seeds. "
        "Request 1 includes the common start. No new queries or measured labels.",
        "",
        "| Target | Role | Method | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True, sharey=True)
    for target, ax in zip(TARGETS, axes.flat, strict=True):
        for method in METHODS:
            row = next(
                r
                for r in analysis["summaries"]
                if r["target"] == target and r["method"] == method and r["budget"] == 8
            )
            values = row["mean_quality_by_request"]
            lines.append(
                f"| {target} | {row['role']} | {labels[method]} | "
                + " | ".join(f"{v:.4f}" for v in values)
                + " |"
            )
            if method != "architecture":
                ax.plot(
                    range(1, 9), values, marker="o", markersize=3, label=labels[method]
                )
        ax.set(
            title=target,
            xticks=range(1, 9),
            ylim=(-0.02, 1.02),
            xlabel="Charged scoring requests (start included)",
        )
        ax.grid(alpha=0.2)
    for ax in axes[:, 0]:
        ax.set_ylabel("Best eligible frozen-predictor utility")
    handles, legend = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend, loc="lower center", ncol=5)
    fig.suptitle(
        "Existing six-target diagnostic: mean over five paired policy seeds\n"
        "All eight request positions; predictions are not measured efficacy"
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(output / "eight-request-trajectories.png", dpi=180)
    fig.savefig(output / "eight-request-trajectories.pdf")
    plt.close(fig)
    (output / "eight-request-trajectories.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "analyze"))
    parser.add_argument(
        "--source", type=Path, default=Path("artifacts/molecular-policy-repair-v3")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/molecular-ppo-attribution-v1")
    )
    args = parser.parse_args()
    (freeze if args.mode == "freeze" else analyze)(args.source, args.output)
