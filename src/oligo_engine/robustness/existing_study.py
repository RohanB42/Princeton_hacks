"""Existing-checkpoint diagnostics: freeze predictions/decisions before outcomes."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from time import perf_counter

from oligo_engine.provenance import identity
from oligo_engine.robustness.evaluate import (
    paired_groups,
    predictive_metrics,
    risk_coverage,
)
from oligo_engine.robustness.existing import (
    ExistingSource,
    FrozenExistingPair,
    checked_bytes,
    prepare_atlas,
    prepare_huesken,
)
from oligo_engine.robustness.guardrails import select_guardrail
from oligo_engine.robustness.optimization import optimize, verify_seal
from oligo_engine.robustness.supported_existing import (
    FrozenSupported,
    prepare_supported,
)


@dataclass(frozen=True)
class ReplayCandidate:
    sample_id: str
    compound_id: str
    group: str
    helm: str
    context: tuple[tuple[str, object], ...]

    @property
    def assessment_id(self) -> str:
        return identity([self.compound_id, self.group, self.context])


def save(path: Path, payload: dict) -> None:
    with path.open("x") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")


def preflight(source: ExistingSource, config: dict) -> dict:
    for role, minimum in (
        ("development", config["minimum_development_rows"]),
        ("final", config["minimum_final_rows"]),
    ):
        if len(source.roles[role]) < minimum:
            raise ValueError(f"Preflight: insufficient {role} rows")
        if source.receipt["context_coverage"][role] < config["required_coverage"]:
            raise ValueError(f"Preflight: no evaluable {role} context")
        members = set(source.roles[role])
        groups = {r["group"] for r in source.rows if r["sample_id"] in members}
        minimum_groups = config[source.suite].get(f"minimum_{role}_groups", 1)
        if len(groups) < minimum_groups:
            raise ValueError(f"Preflight: insufficient {role} groups")
    return {
        "status": "eligible_internal_replay",
        "outcomes_read": False,
        "source_sha256": source.source_hash,
        "roles": source.roles,
        "metadata_audit": source.receipt,
        "config": config,
        "fit_calls_allowed": 0,
        "prior_exposure": "previously_evaluated_internal_replay",
    }


def frozen_predictions(source: ExistingSource, pair: object) -> dict:
    import numpy as np
    from sklearn.metrics import pairwise_distances

    mapping = {r["sample_id"]: r for r in source.rows}
    train_x = pair.features(source.roles["fit"])
    partitions = {}
    near_training = {}
    for role in ("development", "final"):
        ids = source.roles[role]
        primary, secondary, uncertainty = pair.predict(ids)
        x = pair.features(ids)
        # Euclidean one-hot distance: fixed chemistry for Atlas, native duplex
        # features for Huesken. For Atlas, squared distance / 40 is Hamming fraction.
        distance = pairwise_distances(x, train_x, metric="euclidean").min(axis=1)
        if source.suite in ("atlas", "supported"):
            # Recover the integer mismatch count before normalizing. Sqrt then
            # squaring can otherwise put an exact threshold tie just above it.
            distance = np.rint(distance**2 / 2) / 20
        near_training[role] = int(
            np.count_nonzero(
                distance <= (0.1 if source.suite in ("atlas", "supported") else 0)
            )
        )
        records = []
        for i, first, other, warning, nearest in zip(
            ids, primary, secondary, uncertainty, distance, strict=True
        ):
            row = mapping[i]
            records.append(
                {
                    "sample_id": i,
                    "assessment_id": identity(
                        [row["compound_id"], row["context"], row["group"]]
                    ),
                    "compound_id": row["compound_id"],
                    "group": row["group"],
                    "mean": first,
                    "secondary_mean": other,
                    "diagnostics": {
                        "uncertainty": warning,
                        "distance": float(nearest),
                        "disagreement": abs(first - other)
                        if other is not None
                        else None,
                    },
                    "uncertainty_type": "gp_latent_sd_uncalibrated"
                    if warning is not None
                    else "none",
                }
            )
        partitions[role] = records
    return {
        "partitions": partitions,
        "parity": pair.parity(source.roles["final"]),
        "model_identities": {
            "primary": pair.cfg["primary_sha256"],
            "secondary": pair.cfg.get("secondary_sha256"),
        },
        "refit_calls": 0,
        "final_outcomes_read": False,
        "distance_representation": "base_hamming20_fixed_chemistry"
        if source.suite in ("atlas", "supported")
        else "native_onehot210_euclidean",
        "near_training_rows": near_training,
        "precomputation_cost": {
            "primary_rows": sum(len(v) for v in partitions.values()),
            "secondary_rows": (
                0
                if source.suite == "supported"
                else sum(len(v) for v in partitions.values())
            ),
            "parity_probe_rows": 16,
            "distance_reference_rows": len(train_x),
            "heads_per_query": 1 if source.suite == "supported" else 2,
            "query_cost_note": (
                "Predictor-vector queries; table construction charged separately"
            ),
        },
    }


def select_and_seal(
    source: ExistingSource,
    predictions: dict,
    config: dict,
) -> tuple[dict, list[dict]]:
    from dataclasses import asdict

    cfg = config[source.suite]
    development = predictions["partitions"]["development"]
    labels = source.outcomes("development").read(tuple(source.roles["development"]))
    policy = select_guardrail(
        development,
        labels,
        cfg["diagnostic"],
        tuple(cfg["thresholds"]),
        config["minimum_retention"],
    )
    mapping = {r["sample_id"]: r for r in predictions["partitions"]["final"]}

    def score(row: ReplayCandidate) -> dict:
        return mapping[row.sample_id]

    rows = [
        ReplayCandidate(
            r["sample_id"],
            r["compound_id"],
            r["group"],
            r["helm"],
            tuple(sorted(r["context"].items())),
        )
        for r in source.rows
        if r["sample_id"] in mapping
    ]
    runs = []
    for group in sorted({r.group for r in rows}):
        candidates = tuple(r for r in rows if r.group == group)
        for seed in config["optimizer_seeds"]:
            for guarded in (False, True):
                receipt = optimize(
                    candidates,
                    score,
                    "random",
                    seed,
                    config["query_budget"],
                    config["shortlist_k"],
                    policy if guarded else None,
                )
                receipt.update(group=group, guarded=guarded)
                receipt["seal"] = identity(
                    {
                        k: v
                        for k, v in receipt.items()
                        if k not in ("seal", "wall_seconds")
                    }
                )
                runs.append(receipt)
        reference = optimize(
            candidates, score, "exhaustive", 0, len(candidates), config["shortlist_k"]
        )
        reference.update(group=group, guarded=False)
        reference["seal"] = identity(
            {k: v for k, v in reference.items() if k not in ("seal", "wall_seconds")}
        )
        runs.append(reference)
    return {
        "guardrail": asdict(policy),
        "guardrail_hash": policy.identity,
        "development_metrics": predictive_metrics(development, labels),
        "development_outcome_count": len(labels),
        "final_outcomes_read": False,
        "calibration": "not_requested_no_new_interval_claim",
    }, runs


def deferred_evaluation(
    source: ExistingSource, predictions: dict, policy: dict, runs: list[dict]
) -> dict:
    for run in runs:
        verify_seal(run)
    labels = source.outcomes("final").read(tuple(source.roles["final"]))
    records = predictions["partitions"]["final"]
    secondary = [{**r, "mean": r["secondary_mean"]} for r in records]
    from oligo_engine.robustness.guardrails import GuardrailPolicy

    guardrail = GuardrailPolicy(**policy["guardrail"])
    guarded_records = [
        {**r, "mean": r["mean"] if guardrail.accepts(r) else None} for r in records
    ]
    diagnostics = {
        name: {
            kind: risk_coverage(records, labels, name, kind)
            for kind in ("diagnostic", "random", "oracle")
        }
        for name in ("uncertainty", "distance", "disagreement")
    }
    # Recorded replicate measurements are averaged within compound/context group;
    # selecting an arbitrary representative ID must not select its assay replicate.
    replicate_labels = {}
    for record in records:
        key = (record["compound_id"], record["group"])
        replicate_labels.setdefault(key, []).append(labels[record["sample_id"]])
    selection_labels = {
        r["sample_id"]: fmean(replicate_labels[(r["compound_id"], r["group"])])
        for r in records
    }
    outcomes = []
    source_by_id = {r["sample_id"]: r for r in source.rows}
    for run in runs:
        ids = run["shortlist"]
        values = [selection_labels[i] for i in ids]
        outcomes.append(
            {
                "group": run["group"],
                "seed": run["seed"],
                "method": run["method"],
                "guarded": run["guarded"],
                "n": len(ids),
                "requested_k": run["k"],
                "measured_mean": fmean(values) if values else None,
                "prediction_mean": fmean(
                    next(r["mean"] for r in records if r["sample_id"] == i) for i in ids
                )
                if ids
                else None,
                "query_count": run["requests"],
                "model_vector_heads": 1 if source.suite == "supported" else 2,
                "shortlist_ids": ids,
                "accepted_fraction": sum(r["accepted"] for r in run["archive"])
                / len(run["archive"])
                if run["archive"]
                else 0,
            }
        )
    group_differences = {}
    for group in sorted({r["group"] for r in records}):
        differences = []
        for seed in sorted({r["seed"] for r in runs if r["method"] == "random"}):
            arms = [
                r
                for r in outcomes
                if r["group"] == group and r["seed"] == seed and r["method"] == "random"
            ]
            if len(arms) == 2:
                n = min(r["n"] for r in arms)
                if n:
                    means = {
                        r["guarded"]: fmean(
                            selection_labels[i] for i in r["shortlist_ids"][:n]
                        )
                        for r in arms
                    }
                    differences.append(means[True] - means[False])
        if differences:
            group_differences[group] = fmean(differences)
    return {
        "status": "previously_evaluated_internal_replay",
        "suite": source.suite,
        "metrics": predictive_metrics(records, labels),
        "selected_guardrail_metrics": predictive_metrics(guarded_records, labels),
        "secondary_metrics": predictive_metrics(secondary, labels)
        if source.suite != "supported"
        else None,
        "diagnostics": diagnostics,
        "selection": outcomes,
        "guarded_minus_unguarded": paired_groups(group_differences),
        "guardrail": policy["guardrail"],
        "final_outcome_count": len(labels),
        "final_outcomes_used_upstream": False,
        "selection_measurement_weighting": "mean_replicates_per_compound_context_group",
        "targets": dict(
            Counter(
                source_by_id[i].get("target", source_by_id[i]["group"]) for i in labels
            )
        ),
        "claims": (
            "Frozen checkpoint historical replay. "
            "No clinical validation or unseen-target guarantee."
        ),
    }


def run_existing(
    suite: str,
    config: dict,
    output: Path,
    trusted: bool,
) -> dict:
    if config.get("schema") != "existing-predictor-replay-v1" or suite not in (
        "huesken",
        "atlas",
        "supported",
    ):
        raise ValueError("Unsupported existing-predictor protocol")
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = perf_counter()
    try:
        source = {
            "huesken": prepare_huesken,
            "atlas": prepare_atlas,
            "supported": prepare_supported,
        }[suite](config)
        save(
            output / "metadata-audit.json",
            {"audit": source.receipt, "roles": source.roles, "outcomes_read": False},
        )
        metadata = preflight(source, config)
        save(output / "preflight.json", metadata)
        pair = (
            FrozenSupported(source, config)
            if suite == "supported"
            else FrozenExistingPair(source, config, trusted)
        )
        predictions = frozen_predictions(source, pair)
        save(output / "predictions.json", predictions)
        policy, runs = select_and_seal(source, predictions, config)
        save(output / "guardrail.json", policy)
        save(
            output / "sealed-search.json", {"runs": runs, "final_outcomes_read": False}
        )
        frozen_hashes = {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in (
                "preflight.json",
                "predictions.json",
                "guardrail.json",
                "sealed-search.json",
            )
        }
        result = deferred_evaluation(source, predictions, policy, runs)
        for name, expected in frozen_hashes.items():
            checked_bytes(output / name, expected)
        for key in ("primary",) if suite == "supported" else ("primary", "secondary"):
            checked_bytes(Path(config[suite][key]), config[suite][key + "_sha256"])
        result["frozen_stage_hashes"] = frozen_hashes
        result["model_hashes_unchanged"] = True
        result["refit_calls"] = 0
        result["parity"] = predictions["parity"]
        result["preflight"] = source.receipt
        result["code_revision"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        result["code_dirty"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        )
        result["python"] = platform.python_version()
        result["runtime"] = {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "scikit-learn", "joblib")
        }
        result["wall_seconds"] = perf_counter() - started
        save(output / "report.json", result)
        from oligo_engine.reporting.robustness import write_report

        report_view = {
            **result,
            "prior_exposure": "Previously examined outcomes; development evidence only",
        }
        for row in report_view["selection"]:
            row["requests"] = row["query_count"]
        write_report(output / "report.md", report_view)
        return {
            "suite": suite,
            "output": str(output),
            "primary_rmse": result["metrics"]["macro_rmse"],
            "secondary_rmse": result["secondary_metrics"]["macro_rmse"]
            if result["secondary_metrics"]
            else None,
            "coverage": result["metrics"]["coverage"],
            "guarded_minus_unguarded": result["guarded_minus_unguarded"],
            "refit_calls": 0,
        }
    except Exception as exc:
        save(
            output / "failure.json",
            {
                "status": "blocked_existing_predictor_replay",
                "reason": str(exc),
                "exception": type(exc).__name__,
                "completed_stages": [p.name for p in output.glob("*.json")],
                "no_fallback_model_fitted": True,
            },
        )
        raise
