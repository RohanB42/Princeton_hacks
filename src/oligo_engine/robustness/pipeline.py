"""Immutable audit stages with outcome capabilities introduced only where required."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from copy import deepcopy
from dataclasses import asdict
from math import isfinite
from pathlib import Path
from random import Random
from statistics import fmean
from time import perf_counter

from oligo_engine.design.aso_space import identity
from oligo_engine.robustness.adapters import fit_model, load_asoptimizer
from oligo_engine.robustness.calibration import ResidualIntervals
from oligo_engine.robustness.contracts import PARTITIONS, SCHEMA, records_hash
from oligo_engine.robustness.diagnostics import DomainReference
from oligo_engine.robustness.evaluate import (
    paired_groups,
    predictive_metrics,
    risk_coverage,
)
from oligo_engine.robustness.fixture import SyntheticAuditModel
from oligo_engine.robustness.fixture import source as fixture_source
from oligo_engine.robustness.guardrails import GuardrailPolicy, select_guardrail
from oligo_engine.robustness.optimization import optimize, verify_seal
from oligo_engine.robustness.perturbations import probe
from oligo_engine.robustness.splits import audit_artifact, make_split

STAGES = (
    "plan",
    "audit",
    "predict",
    "perturb",
    "diagnose",
    "select-guardrail",
    "optimize",
    "evaluate",
    "report",
)


def validate_config(config: dict) -> None:
    required = {
        "schema",
        "source",
        "purpose",
        "split_strategy",
        "seed",
        "model",
        "diagnostic",
        "thresholds",
        "minimum_retention",
        "maximum_mae",
        "reference_cap",
        "perturbation_parents",
        "optimizer_seeds",
        "query_budget",
        "shortlist_k",
        "direction",
        "prior_exposure",
    }
    if set(config) != required or config["schema"] != SCHEMA:
        raise ValueError("Unsupported or incomplete robustness protocol")
    if config["source"] not in ("fixture", "asoptimizer"):
        raise ValueError("Unsupported source adapter")
    if config["direction"] != "higher_is_better":
        raise ValueError("Initial adapters support inhibition-oriented objectives only")
    expected = (
        "fixture_only"
        if config["source"] == "fixture"
        else "complete_measured_diagnostic"
    )
    if config["purpose"] != expected or not config["prior_exposure"]:
        raise ValueError("Explicit diagnostic provenance required")
    if config["model"] not in (
        ("synthetic",) if config["source"] == "fixture" else ("rf", "ridge")
    ):
        raise ValueError("Model/source mismatch")
    if config["diagnostic"] not in ("uncertainty", "distance", "disagreement"):
        raise ValueError("Unknown diagnostic")
    for key in ("reference_cap", "perturbation_parents", "query_budget", "shortlist_k"):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f"Positive integer required: {key}")
    if not config["optimizer_seeds"] or len(set(config["optimizer_seeds"])) != len(
        config["optimizer_seeds"]
    ):
        raise ValueError("Unique optimizer seeds required")
    if type(config["seed"]) is not int or any(
        type(v) is not int for v in config["optimizer_seeds"]
    ):
        raise ValueError("Integer seeds required")
    if (
        not 0 < config["minimum_retention"] <= 1
        or not config["thresholds"]
        or any(not isfinite(v) for v in config["thresholds"])
    ):
        raise ValueError("Invalid guardrail protocol")


class StageStore:
    """Resume only a matching frozen protocol and unmodified dependency chain."""

    def __init__(self, root: Path, input_hash: str) -> None:
        self.root, self.input_hash = root, input_hash
        root.mkdir(parents=True, exist_ok=True)

    def read(self, name: str) -> dict:
        if name not in STAGES:
            raise ValueError("Unknown stage name")
        value = json.loads((self.root / f"{name}.json").read_text())
        if (
            value["input_hash"] != self.input_hash
            or identity(value["payload"]) != value["seal"]
        ):
            raise ValueError("Stage changed or source/config mismatch")
        for dep, seal in value["dependencies"].items():
            if dep not in STAGES or STAGES.index(dep) >= STAGES.index(name):
                raise ValueError("Invalid stage dependency order")
            previous = self.read(dep)
            if identity(previous) != seal:
                raise ValueError("Stage dependency changed")
        return value["payload"]

    def write(
        self, name: str, payload: dict, dependencies: tuple[str, ...] = ()
    ) -> dict:
        path = self.root / f"{name}.json"
        if path.exists():
            existing = self.read(name)
            if identity(existing) != identity(payload):
                raise ValueError("Refusing to overwrite a different immutable stage")
            return existing
        value = {
            "schema": SCHEMA,
            "input_hash": self.input_hash,
            "dependencies": {dep: identity(self.read(dep)) for dep in dependencies},
            "payload": payload,
            "seal": identity(payload),
        }
        with path.open("x") as handle:
            handle.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        return payload


class AuditPipeline:
    """Orchestrator owns outcomes; scorer/search modules never receive this object."""

    def __init__(
        self, config: dict, output: Path, source: object | None = None
    ) -> None:
        validate_config(config)
        self.config = deepcopy(config)
        self.source = source or (
            fixture_source() if config["source"] == "fixture" else load_asoptimizer()
        )
        self.rows = self.source.rows
        if len({(r.endpoint, r.units, r.modality) for r in self.rows}) != 1:
            raise ValueError("An audit cannot pool endpoints, units or modalities")
        self.by_id = {r.sample_id: r for r in self.rows}
        self.split, self.audit = make_split(
            self.rows, config["split_strategy"], config["seed"]
        )
        source_root = Path(__file__).parents[1]
        self.runtime_versions = {}
        for package in ("numpy", "scipy", "scikit-learn"):
            try:
                self.runtime_versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                self.runtime_versions[package] = "not_installed"
        implementation = identity(
            [
                (
                    str(p.relative_to(source_root)),
                    hashlib.sha256(p.read_bytes()).hexdigest(),
                )
                for p in sorted(source_root.rglob("*.py"))
            ]
        )
        self.store = StageStore(
            output,
            identity(
                {
                    "config": config,
                    "rows": records_hash(self.rows),
                    "implementation": implementation,
                    "python": platform.python_version(),
                    "libraries": self.runtime_versions,
                }
            ),
        )
        self._model = self._secondary = None
        self.fit_access: list[str] = []

    def subset(self, name: str) -> tuple:
        return tuple(self.by_id[i] for i in getattr(self.split, name))

    def _models(self) -> tuple[object, object | None]:
        if self._model is None:
            fitting = self.subset("fit")
            if self.config["model"] == "synthetic":
                self._model = SyntheticAuditModel(fitting)
            else:
                capability = self.source.outcomes(self.split.fit)
                labels = capability.read(self.split.fit)
                self.fit_access.extend(capability.accessed)
                self._model = fit_model(
                    fitting, labels, self.config["model"], self.config["seed"]
                )
                other = "ridge" if self.config["model"] == "rf" else "rf"
                self._secondary = fit_model(fitting, labels, other, self.config["seed"])
            audit_artifact(tuple(self._model.manifest["training_ids"]), self.split)
        return self._model, self._secondary

    def plan(self) -> dict:
        code = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        return self.store.write(
            "plan",
            {
                "config": self.config,
                "split": asdict(self.split),
                "split_hash": self.split.identity,
                "source": self.source.receipt,
                "metadata_hash": records_hash(self.rows),
                "code_revision": code,
                "code_dirty": bool(
                    subprocess.check_output(
                        ["git", "status", "--porcelain"], text=True
                    ).strip()
                ),
                "python": platform.python_version(),
                "label_values_read": False,
            },
        )

    def predict(self) -> dict:
        self.store.read("audit")
        model, secondary = self._models()
        partitions = {}
        for name in PARTITIONS:
            rows = self.subset(name)
            predictions = model.predict(rows)
            second = (
                secondary.predict(rows)
                if secondary is not None
                else (None,) * len(rows)
            )
            partitions[name] = [
                {
                    "sample_id": row.sample_id,
                    "assessment_id": row.assessment_id,
                    "compound_id": row.compound_id,
                    "group": row.target_id,
                    "mean": pred.mean,
                    "status": pred.status,
                    "reason": pred.reason,
                    "uncertainty_type": pred.uncertainty_type,
                    "diagnostics": {
                        "uncertainty": pred.uncertainty,
                        "disagreement": abs(pred.mean - other.mean)
                        if other is not None
                        and pred.mean is not None
                        and other.mean is not None
                        else None,
                    },
                }
                for row, pred, other in zip(rows, predictions, second, strict=True)
            ]
        return self.store.write(
            "predict",
            {
                "model_manifest": model.manifest,
                "secondary_manifest": secondary.manifest if secondary else None,
                "partitions": partitions,
                "final_outcomes_read": False,
                "precomputation_cost": {
                    "primary_predictions": sum(len(v) for v in partitions.values()),
                    "secondary_predictions": len(self.rows) - len(self.split.excluded)
                    if secondary
                    else 0,
                    "primary_scored_rows": sum(
                        r["mean"] is not None
                        for part in partitions.values()
                        for r in part
                    ),
                    "primary_prediction_batches": len(PARTITIONS),
                    "secondary_prediction_batches": len(PARTITIONS) if secondary else 0,
                    "primary_inference_batches": sum(
                        any(r["mean"] is not None for r in part)
                        for part in partitions.values()
                    ),
                    "batch_counter_semantics": "requests and scored batches",
                    "note": "table construction charged separately",
                },
            },
            ("audit",),
        )

    def diagnose(self) -> dict:
        prediction = self.store.read("predict")
        fitting = list(self.subset("fit"))
        Random(self.config["seed"]).shuffle(fitting)
        reference = DomainReference(tuple(fitting[: self.config["reference_cap"]]))
        values = reference.reference_values()
        partitions = {}
        for name in PARTITIONS:
            records = []
            for record in prediction["partitions"][name]:
                row = self.by_id[record["sample_id"]]
                distance = reference.diagnose(row, values)
                records.append(
                    {
                        **record,
                        "diagnostics": {
                            **record["diagnostics"],
                            "distance": distance["distance"],
                        },
                        "domain": distance,
                    }
                )
            partitions[name] = records
        return self.store.write(
            "diagnose",
            {
                "partitions": partitions,
                "reference_ids": [r.sample_id for r in reference.rows],
                "reference_hash": reference.identity,
                "reference_distances": values,
                "reference_total_fit_rows": len(fitting),
                "reference_sampled": len(reference.rows) < len(fitting),
                "final_labels_read": False,
            },
            ("predict",),
        )

    def select(self) -> dict:
        diagnosed = self.store.read("diagnose")
        records = diagnosed["partitions"]["development"]
        dev = self.source.outcomes(self.split.development).read(self.split.development)
        guardrail = select_guardrail(
            records,
            dev,
            self.config["diagnostic"],
            tuple(self.config["thresholds"]),
            self.config["minimum_retention"],
            self.config["maximum_mae"],
        )
        calibration = diagnosed["partitions"]["calibration"]
        scored = [r for r in calibration if r["mean"] is not None]
        ids = tuple(r["sample_id"] for r in scored)
        intervals = None
        if ids:
            labels = self.source.outcomes(self.split.calibration).read(ids)
            fitted = ResidualIntervals.fit(
                ids, tuple(r["mean"] for r in scored), tuple(labels[i] for i in ids)
            )
            intervals = asdict(fitted)
        return self.store.write(
            "select-guardrail",
            {
                "guardrail": asdict(guardrail),
                "calibration": intervals,
                "calibration_status": "fitted"
                if intervals
                else "no_supported_calibration_rows",
                "label_budgets": {
                    "fit": len(self.split.fit),
                    "development": len(dev),
                    "calibration": len(ids),
                    "final_used_for_selection": 0,
                    "real_labels": len(self.split.fit) + len(dev) + len(ids)
                    if self.config["source"] != "fixture"
                    else 0,
                },
                "development_metrics": predictive_metrics(records, dev),
            },
            ("diagnose",),
        )

    def optimize(self) -> dict:
        diagnostic = self.store.read("diagnose")
        selected = self.store.read("select-guardrail")
        policy = GuardrailPolicy(
            **{
                **selected["guardrail"],
                "development_ids": tuple(selected["guardrail"]["development_ids"]),
                "receipt": tuple(tuple(v) for v in selected["guardrail"]["receipt"]),
            }
        )
        mapping = {r["sample_id"]: r for r in diagnostic["partitions"]["final"]}

        def score(row):
            return mapping[row.sample_id]

        runs = []
        for group in sorted({r.target_id for r in self.subset("final")}):
            rows = tuple(r for r in self.subset("final") if r.target_id == group)
            for seed in self.config["optimizer_seeds"]:
                for guarded in (False, True):
                    result = optimize(
                        rows,
                        score,
                        "random",
                        seed,
                        self.config["query_budget"],
                        self.config["shortlist_k"],
                        policy if guarded else None,
                    )
                    result["group"] = group
                    result["guarded"] = guarded
                    # Group/arm annotations are part of the final immutable seal.
                    result["seal"] = identity(
                        {
                            k: v
                            for k, v in result.items()
                            if k not in ("seal", "wall_seconds")
                        }
                    )
                    runs.append(result)
            reference = optimize(
                rows, score, "exhaustive", 0, len(rows), self.config["shortlist_k"]
            )
            reference["group"], reference["guarded"] = group, False
            reference["seal"] = identity(
                {
                    k: v
                    for k, v in reference.items()
                    if k not in ("seal", "wall_seconds")
                }
            )
            runs.append(reference)
        return self.store.write(
            "optimize",
            {
                "runs": runs,
                "final_outcomes_read": False,
                "cost_semantics": "table charged; queries simulated",
                "unsupported_methods": {
                    "greedy": "not_applicable_without_source_pool_graph",
                    "genetic": "not_applicable_without_source_pool_graph",
                    "ppo": "requires_real_transcript_space_use_existing_rl_bridge",
                },
            },
            ("select-guardrail", "diagnose"),
        )

    def evaluate(self) -> dict:
        sealed = self.store.read("optimize")
        for run in sealed["runs"]:
            verify_seal(run)
        diagnosed, selected = (
            self.store.read("diagnose"),
            self.store.read("select-guardrail"),
        )
        records = diagnosed["partitions"]["final"]
        # Final outcomes are first accessed after all decisions are sealed.
        labels = self.source.outcomes(self.split.final).read(self.split.final)
        metrics = predictive_metrics(records, labels)
        diagnostics = {
            name: {
                order: risk_coverage(records, labels, name, order)
                for order in ("diagnostic", "random", "oracle")
            }
            for name in ("uncertainty", "distance", "disagreement")
        }
        selection_results = []
        for run in sealed["runs"]:
            ids = run["shortlist"]
            measured = [labels[i] for i in ids]
            representatives = {}
            for r in sorted(records, key=lambda r: r["sample_id"]):
                if r["group"] == run["group"]:
                    representatives.setdefault(r["assessment_id"], r["sample_id"])
            population = [labels[i] for i in representatives.values()]
            selection_results.append(
                {
                    "method": run["method"],
                    "seed": run["seed"],
                    "group": run["group"],
                    "guarded": run["guarded"],
                    "n": len(ids),
                    "requested_k": run["k"],
                    "measured_mean": fmean(measured) if measured else None,
                    "random_population_mean": fmean(population),
                    "selected_positive_residual": fmean(
                        next(r["mean"] for r in records if r["sample_id"] == i)
                        - labels[i]
                        for i in ids
                    )
                    if ids
                    else None,
                    "oracle_mean_at_selected_k": fmean(
                        sorted(population, reverse=True)[: len(ids)]
                    )
                    if ids
                    else None,
                    "requests": run["requests"],
                    "unique_scores": run["unique_scores"],
                    "exact_measurement_coverage": 1.0 if ids else None,
                    "all_candidates_are_recorded_assays": True,
                    "replicate_rule": "first_source_ID_per_recorded_compound_assay",
                    "shortlist_ids": ids,
                }
            )
        paired = {}
        for group in sorted({r["group"] for r in selection_results}):
            differences = []
            for seed in self.config["optimizer_seeds"]:
                arms = [
                    r
                    for r in selection_results
                    if r["group"] == group
                    and r["seed"] == seed
                    and r["method"] == "random"
                ]
                if len(arms) == 2:
                    n = min(r["n"] for r in arms)
                    if n:
                        means = {
                            r["guarded"]: fmean(
                                labels[i] for i in r["shortlist_ids"][:n]
                            )
                            for r in arms
                        }
                        differences.append(means[True] - means[False])
            if differences:
                paired[group] = fmean(differences)
        interval_metrics = {}
        if selected["calibration"]:
            calibration = ResidualIntervals(
                tuple(selected["calibration"]["residuals"]),
                tuple(selected["calibration"]["calibration_ids"]),
            )
            for alpha in (0.1, 0.05):
                intervals = [
                    (r, calibration.interval(r["mean"], alpha))
                    for r in records
                    if r["mean"] is not None
                ]
                valid = [(r, v) for r, v in intervals if v["lower"] is not None]
                interval_metrics[str(alpha)] = {
                    "n": len(valid),
                    "coverage": fmean(
                        v["lower"] <= labels[r["sample_id"]] <= v["upper"]
                        for r, v in valid
                    )
                    if valid
                    else None,
                    "mean_width": fmean(v["upper"] - v["lower"] for _, v in valid)
                    if valid
                    else None,
                    "shift_guarantee": False,
                }
        baseline_mean = self.store.read("predict")["model_manifest"]["training_mean"]
        baseline = [
            {**r, "mean": baseline_mean if r["mean"] is not None else None}
            for r in records
        ]
        return self.store.write(
            "evaluate",
            {
                "status": self.config["purpose"],
                "support_status": "scored"
                if metrics["scored_rows"]
                else "no_eligible_candidates",
                "metrics": metrics,
                "training_mean_baseline": predictive_metrics(baseline, labels),
                "diagnostics": diagnostics,
                "intervals": interval_metrics,
                "selection": selection_results,
                "guarded_minus_unguarded": paired_groups(paired),
                "paired_cardinality": "matched_to_smaller_shortlist_per_seed_group",
                "label_budgets": selected["label_budgets"],
                "final_outcome_count": len(labels),
                "final_outcomes_used_upstream": False,
                "prior_exposure": self.config["prior_exposure"],
                "claims": "internal diagnostic; no biological validation",
            },
            ("optimize", "diagnose", "select-guardrail"),
        )

    def run_stage(self, name: str) -> dict:
        if name not in STAGES:
            raise ValueError("Unknown audit stage")
        path = self.store.root / f"{name}.json"
        if path.exists():
            if name == "report":
                from oligo_engine.reporting.robustness import write_report

                write_report(self.store.root / "report.md", self.store.read("evaluate"))
            return self.store.read(name)
        if name == "plan":
            return self.plan()
        if name == "audit":
            self.store.read("plan")
            return self.store.write("audit", self.audit, ("plan",))
        if name == "predict":
            return self.predict()
        if name == "perturb":
            self.store.read("predict")
            return self.store.write(
                "perturb",
                probe(
                    self._models()[0],
                    self.subset("final"),
                    self.config["perturbation_parents"],
                ),
                ("predict",),
            )
        if name == "diagnose":
            return self.diagnose()
        if name == "select-guardrail":
            return self.select()
        if name == "optimize":
            return self.optimize()
        if name == "evaluate":
            return self.evaluate()
        from oligo_engine.reporting.robustness import write_report

        evaluation = self.store.read("evaluate")
        report = self.store.write(
            "report",
            {"evaluation_hash": identity(evaluation), "status": evaluation["status"]},
            ("evaluate",),
        )
        write_report(self.store.root / "report.md", evaluation)
        return report

    def run(self) -> dict:
        started = perf_counter()
        costs = []
        for stage in STAGES:
            cached = (self.store.root / f"{stage}.json").exists()
            stage_start = perf_counter()
            self.run_stage(stage)
            costs.append(
                {
                    "stage": stage,
                    "wall_seconds": perf_counter() - stage_start,
                    "cached": cached,
                }
            )
        versions = {}
        for name in ("numpy", "scikit-learn", "scipy"):
            try:
                versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                versions[name] = "not_installed"
        receipts = sorted(self.store.root.glob("runtime-*.json"))
        number = max((int(p.stem.split("-")[-1]) for p in receipts), default=-1) + 1
        with (self.store.root / f"runtime-{number}.json").open("x") as handle:
            json.dump(
                {
                    "stages": costs,
                    "versions": versions,
                    "input_hash": self.store.input_hash,
                    "wall_seconds": perf_counter() - started,
                },
                handle,
                indent=2,
            )
        return {
            "status": self.store.read("evaluate")["status"],
            "output": str(self.store.root),
            "wall_seconds": perf_counter() - started,
            "macro_rmse": self.store.read("evaluate")["metrics"]["macro_rmse"],
        }
