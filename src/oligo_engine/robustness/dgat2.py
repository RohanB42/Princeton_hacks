"""Declared, evaluation-only transfer replay of original DGAT2 records.

Uses the released HELM as encoded, including its unresolved methylcytosine
annotation discrepancy. Never changes molecules or the production admission gate.
"""

import csv
import hashlib
import importlib.metadata
import json
import pickle
import subprocess
import warnings
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from statistics import fmean

from oligo_engine.provenance import identity
from oligo_engine.robustness.adapters import SourceMetadata, load_asoptimizer
from oligo_engine.robustness.contracts import chemistry, records_hash
from oligo_engine.robustness.evaluate import predictive_metrics, risk_coverage
from oligo_engine.robustness.existing import checked_bytes
from oligo_engine.robustness.existing_study import ReplayCandidate, save
from oligo_engine.robustness.guardrails import GuardrailPolicy
from oligo_engine.robustness.optimization import optimize, verify_seal

ORIGIN_COMMIT = "c7716f223fa432ea4fb99401e680db9dc37d3add"
ORIGIN_SHA = "61db5466ead5c9bf1e34241d89c3a02a3e6b5e03d0930e1062cdd14799a2fa43"
ATLAS_SHA = "77b5334b21a4fb86f99821852e7e83a50488649f887cad52b3d7c29ff8941285"
LOADER_REVISION = "f197d79"
METADATA_FIELDS = (
    "ISIS",
    "Target_gene",
    "Cell_line",
    "ASO_volume(nM)",
    "Treatment_Period(hours)",
    "Transfection",
    "Sequence",
    "Chemical_Pattern",
    "Modification",
    "Linkage",
)


def join_original_metadata(rows: tuple, original: list[dict]) -> list[dict]:
    """Join using sequence, sugar pattern, cell and declared dose correspondence.

    The 1000 correspondence is checked against original metadata, not assumed to
    redefine the reduced release's undocumented concentration unit globally.
    Multiple source rows are allowed only when all recovered assay/chemistry
    annotations agree; retain every original row/compound identifier.
    """
    lookup = defaultdict(list)
    for row in original:
        key = (
            row["Sequence"],
            row["Chemical_Pattern"],
            row["Cell_line"],
            Decimal(row["ASO_volume(nM)"]),
        )
        lookup[key].append(row)
    output = []
    for row in rows:
        parsed = chemistry(row.helm)
        context = dict(row.context)
        pattern = "".join({"MOE": "M", "DNA": "d"}[s] for s in parsed.sugars)
        key = (
            parsed.natural_rna.replace("U", "T"),
            pattern,
            context["cell_line"],
            Decimal(context["concentration"]) * 1000,
        )
        matches = lookup.get(key, [])
        fields = (
            "Cell_line",
            "ASO_volume(nM)",
            "Treatment_Period(hours)",
            "Transfection",
            "Modification",
            "Linkage",
        )
        variants = {tuple(m[k] for k in fields) for m in matches}
        if len(variants) != 1:
            raise ValueError("Incomplete or ambiguous original-metadata crosswalk")
        first = matches[0]
        if first["Modification"] != "MOE/5-methylcytosines/deoxy":
            raise ValueError("Changed source chemistry declaration")
        output.append(
            {
                "sample_id": row.sample_id,
                "raw_helm": row.helm,
                "helm": row.helm[:-4] if row.helm.endswith("}$$$$V2.0") else row.helm,
                "compound_id": row.compound_id,
                "sequence": key[0],
                "sugar_pattern": pattern,
                "target": row.target_id,
                "source_concentration": context["concentration"],
                "cell_line": first["Cell_line"],
                "dosage_nm": float(first["ASO_volume(nM)"]),
                "treatment_period_hrs": float(first["Treatment_Period(hours)"]),
                "transfection_method": first["Transfection"],
                "original_source_rows": sorted(m["source_row"] for m in matches),
                "original_compound_ids": sorted({m["ISIS"] for m in matches}),
                "declared_modification": first["Modification"],
                "chemistry_annotation_conflict": "C_in_HELM_vs_methylcytosines_in_text",
            }
        )
    return output


def recover_original(source: SourceMetadata, path: Path) -> list[dict]:
    """Read only named metadata fields, never the original inhibition column."""
    checked_bytes(path, ORIGIN_SHA)
    selected = []
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        indices = {name: header.index(name) for name in METADATA_FIELDS}
        for index, raw in enumerate(reader):
            if raw[indices["Target_gene"]] != "DGAT2":
                continue
            selected.append(
                {**{k: raw[i] for k, i in indices.items()}, "source_row": index}
            )
    rows = tuple(r for r in source.rows if r.target_id == "DGAT2")
    if len(rows) != 2536 or len(selected) != 2536:
        raise ValueError("Original DGAT2 cohort changed")
    return join_original_metadata(rows, selected)


def pinned_loader(directory: Path) -> dict:
    """Export the actual compatible research code; import no guessed classes."""
    import oligo_engine

    root = directory / "oligo_engine" / "atlas"
    root.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in (
        "__init__.py",
        "baselines.py",
        "chemistry.py",
        "scaling.py",
        "data.py",
    ):
        raw = subprocess.check_output(
            ["git", "show", f"{LOADER_REVISION}:src/oligo_engine/atlas/{name}"]
        )
        path = root / name
        digest = hashlib.sha256(raw).hexdigest()
        if path.exists():
            checked_bytes(path, digest)
        else:
            path.write_bytes(raw)
        hashes[name] = digest
    location = str(root.parent.resolve())
    if location not in oligo_engine.__path__:
        oligo_engine.__path__.append(location)
    return {
        "revision": subprocess.check_output(
            ["git", "rev-parse", LOADER_REVISION], text=True
        ).strip(),
        "files": hashes,
    }


def atlas_metadata(path: Path) -> tuple[object, list[str], dict]:
    """Reproduce source memberships using metadata and endpoint availability only.

    The already prepared finite_endpoint flag denotes availability, not an endpoint
    value. The Inhibition_pct column is never requested. No sequence-group target
    partition needs constructing to recover the original source pool.
    """
    import numpy as np
    import pyarrow.parquet as pq
    from sklearn.model_selection import GroupShuffleSplit

    from oligo_engine.atlas.chemistry import parse_helm
    from oligo_engine.atlas.data import CONTEXT, stable_id

    checked_bytes(path, ATLAS_SHA)
    frame = pq.read_table(
        path,
        columns=[
            "source_row_id",
            "Compound ID",
            "HELM Annotation",
            "finite_endpoint",
            *CONTEXT,
        ],
    ).to_pandas()
    frame = frame[
        frame["HELM Annotation"].notna()
        & frame["USPTO ID"].notna()
        & frame.finite_endpoint
        & np.isfinite(frame.dosage_nm)
        & frame.dosage_nm.gt(0)
    ].copy()
    complete = frame[CONTEXT].notna().all(axis=1)
    for name in ("target_RNA", "cell_line", "cell_line_species", "transfection_method"):
        complete &= frame[name].astype(str).str.strip().ne("")
    frame = frame[complete].copy()
    parsed = {}
    for helm in frame["HELM Annotation"].unique():
        try:
            parsed[helm] = parse_helm(helm)
        except ValueError:
            pass
    frame = frame[frame["HELM Annotation"].isin(parsed)].copy()
    frame["chemistry"] = [parsed[h] for h in frame["HELM Annotation"]]
    frame = frame[
        [
            set(c.sugars) <= {"DNA", "MOE", "cEt"} and "DNA" in c.sugars
            for c in frame.chemistry
        ]
    ].copy()
    frame["target_key"] = frame.target_RNA.astype(str).str.strip().str.upper()
    frame["natural_rna"] = [c.natural_rna for c in frame.chemistry]
    frame["compound_key"] = [c.identity for c in frame.chemistry]
    frame["campaign_id"] = [
        stable_id(list(v)) for v in frame[CONTEXT].itertuples(index=False, name=None)
    ]
    frame["assay_key"] = [
        stable_id([c, k]) for c, k in zip(frame.campaign_id, frame.compound_key)
    ]
    frame = frame.drop_duplicates("assay_key", keep="first").reset_index(drop=True)
    candidates = []
    for cid, group in frame.groupby("campaign_id", sort=True):
        if (
            len(group) >= 400
            and group.cell_line_species.iloc[0].lower() == "human"
            and group.target_key.iloc[0] not in {"HBV", "HCV", "HIV"}
        ):
            candidates.append((group.target_key.iloc[0], -len(group), cid))
    chosen = {}
    for target, _, cid in sorted(candidates):
        chosen.setdefault(target, cid)
    held = frame[frame.target_key.isin(chosen)]
    patents, bases, compounds = (
        set(held["USPTO ID"]),
        set(held.natural_rna),
        set(held.compound_key),
    )
    pool = frame[
        ~frame.target_key.isin(chosen)
        & ~frame["USPTO ID"].isin(patents)
        & ~frame.natural_rna.isin(bases)
        & ~frame.compound_key.isin(compounds)
    ].sort_values("source_row_id")
    train, _ = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=20261114).split(
            pool, groups=pool["USPTO ID"].to_numpy()
        )
    )
    ids = pool.iloc[train].source_row_id.tolist()
    if len(ids) != 95638:
        raise ValueError("Published source denominator was not reproduced")
    return (
        frame.set_index("source_row_id", drop=False),
        ids,
        {
            "source_pool": len(ids),
            "excluded_targets": sorted(chosen),
            "endpoint_values_read": False,
            "eligibility_availability_flag": "preexisting finite_endpoint only",
        },
    )


def scope_audit(rows: list[dict], atlas: object, exposed: set[str]) -> dict:
    """Declare scope separately from deployment admission and known-label exposure."""
    from oligo_engine.reward.portable import supported_sequence

    portable = Counter()
    for row in rows:
        try:
            supported_sequence(row["helm"])
            portable["compatible"] += 1
        except ValueError as exc:
            portable[str(exc)] += 1
    species = set(atlas[atlas.cell_line == "HepG2"].cell_line_species)
    if species != {"human"}:
        raise ValueError("Ambiguous released HepG2 species mapping")
    for row in rows:
        row["cell_line_species"] = "human"
        row["group"] = identity(
            [
                row["cell_line"],
                row["dosage_nm"],
                row["treatment_period_hrs"],
                row["transfection_method"],
            ]
        )[:16]
    exposed_bases = set(atlas.loc[sorted(exposed), "natural_rna"])
    eligible = [
        r["sample_id"]
        for r in rows
        if r["sequence"].replace("T", "U") not in exposed_bases
    ]
    return {
        "original_rows": len(rows),
        "eligible_ids": eligible,
        "eligible_rows": len(eligible),
        "excluded_exposed_sequence_rows": len(rows) - len(eligible),
        "exposure_includes": "union of fitting and hyperparameter-validation sequences",
        "portable_aso_encoded_chemistry": dict(portable),
        "portable_deployment_context_compatible": 0,
        "huesken_gp_rf_lora": "incompatible_siRNA_modality",
        "atlas_pilot_ridge_hgb": "incompatible_fixed_methylcytosine_profile",
        "atlas_scaling_classical": "encoded_input_supported_evaluation_only_transfer",
        "atlas_neural": "same_input_vocabulary_but_inference_not_executed",
        "source_metadata_recovered_rows": len(rows),
        "methylation_conflict_rows": len(rows),
        "species_mapping": "unique HepG2=human in pinned Atlas metadata",
        "transfection_mapping": "original reagent string retained; no alias imputation",
        "chemical_view": "released_HELM_encoded_C_not_silently_changed_to_5meC",
        "prior_exposure": "previously_studied_development_evidence",
        "target_shift": "DGAT2_is_seen_in_Atlas_source_training",
    }


def frozen_models(
    config: dict, atlas: object, source_ids: list[str], trusted: bool
) -> tuple[dict, dict, set[str]]:
    """Restore all predeclared classical sources and reconstruct selection exposure."""
    import numpy as np
    import sklearn
    from sklearn.exceptions import InconsistentVersionWarning

    from oligo_engine.atlas.scaling import grouped_validation

    if not trusted:
        raise ValueError(
            "Explicit trust required before loading published pickle files"
        )
    for name, expected in config["runtime"].items():
        if importlib.metadata.version(name) != expected:
            raise ValueError(f"Use the isolated pinned runtime for {name}")
    inventory = json.loads(Path("model_checkpoints/manifest.json").read_text())
    entries = {e["path"]: e for e in inventory["checkpoints"]}
    models, receipts, exposed = {}, {}, set()
    for seed in config["source_seeds"]:
        order = np.random.default_rng(seed).permutation(source_ids)
        for budget in config["source_budgets"]:
            ids = order[:budget].tolist()
            split = grouped_validation(
                ids, atlas.loc[ids, "USPTO ID"].tolist(), seed, 0.2
            )
            exposed.update(ids)
            key = f"{budget}-{seed}"
            models[key] = {}
            for family in ("ridge", "xgb"):
                relative = f"atlas-scaling-v1/source-{key}-{family}/model.pkl"
                entry = entries[relative]
                raw = checked_bytes(
                    Path("model_checkpoints") / relative, entry["sha256"]
                )
                with warnings.catch_warnings():
                    warnings.simplefilter("error", InconsistentVersionWarning)
                    model = pickle.loads(raw)
                if model.fit_ids != split["fit_ids"]:
                    raise ValueError(
                        "Checkpoint training IDs differ from recovered split"
                    )
                models[key][family] = model
            receipts[key] = {
                **split,
                "fitting_ids_match_both_checkpoints": True,
                "training_DGAT2_rows": int(
                    (atlas.loc[split["fit_ids"], "target_key"] == "DGAT2").sum()
                ),
                "sklearn": sklearn.__version__,
                "checkpoint_hashes": {
                    family: entries[
                        f"atlas-scaling-v1/source-{key}-{family}/model.pkl"
                    ]["sha256"]
                    for family in ("ridge", "xgb")
                },
            }
    return models, receipts, exposed


def predict_transfer(
    rows: list[dict], models: dict, atlas: object, receipts: dict
) -> dict:
    """Run frozen transforms; never fit context or inspect endpoint values."""
    import numpy as np
    import pandas as pd
    from sklearn.metrics import pairwise_distances

    frame = pd.DataFrame(rows).rename(columns={"helm": "HELM Annotation"})
    output = {}
    for key, pair in models.items():
        means = {name: model.predict(frame).tolist() for name, model in pair.items()}
        reference_ids = receipts[key]["fit_ids"]
        frozen_features = pair["ridge"].features
        distance = pairwise_distances(
            frozen_features.transform(frame),
            frozen_features.transform(atlas.loc[reference_ids]),
            metric="euclidean",
        ).min(axis=1)
        records = []
        for i, row in enumerate(rows):
            records.append(
                {
                    "sample_id": row["sample_id"],
                    "compound_id": row["compound_id"],
                    "group": row["group"],
                    "mean": means["ridge"][i],
                    "secondary_mean": means["xgb"][i],
                    "diagnostics": {
                        "disagreement": abs(means["ridge"][i] - means["xgb"][i]),
                        "distance": float(distance[i]),
                    },
                }
            )
        parity = {}
        for name, model in pair.items():
            probe = frame.iloc[:16]
            forward = np.asarray(means[name][: len(probe)])
            direct = np.asarray(model.model.predict(model.features.transform(probe)))
            reversed_means = model.predict(probe.iloc[::-1])[::-1]
            delta = max(
                float(np.max(abs(forward - direct))),
                float(np.max(abs(forward - reversed_means))),
            )
            if delta > 1e-6:
                raise ValueError("Frozen transfer inference parity failed")
            parity[name] = delta
        cats = pair["ridge"].features.context.named_transformers_["cat"].categories_
        context_status = {
            name: sorted(set(frame[name]) - set(values))
            for name, values in zip(
                ("cell_line", "cell_line_species", "transfection_method"),
                cats,
                strict=True,
            )
        }
        output[key] = {
            "records": records,
            "parity_max_abs": parity,
            "unknown_context_categories": context_status,
            "training_DGAT2_rows": receipts[key]["training_DGAT2_rows"],
            "distance_representation": "frozen_chemistry_context_feature_euclidean",
            "distance_reference_ids_hash": identity(reference_ids),
        }
    return output


def seal_transfer(rows: list[dict], predictions: dict, config: dict) -> list[dict]:
    """Freeze all primary and sensitivity arms; never choose using final outcomes."""
    candidates = tuple(
        ReplayCandidate(
            r["sample_id"],
            r["compound_id"],
            r["group"],
            r["helm"],
            tuple(
                (name, r[name])
                for name in (
                    "cell_line",
                    "dosage_nm",
                    "treatment_period_hrs",
                    "transfection_method",
                )
            ),
        )
        for r in rows
    )
    runs = []
    for key, result in predictions.items():
        mapping = {r["sample_id"]: r for r in result["records"]}
        for group in sorted({r.group for r in candidates}):
            pool = tuple(r for r in candidates if r.group == group)
            for seed in config["query_seeds"]:
                for threshold in (None, *config["disagreement_thresholds"]):
                    policy = (
                        None
                        if threshold is None
                        else GuardrailPolicy(
                            "disagreement", threshold, "selected", (), 0.0
                        )
                    )
                    run = optimize(
                        pool,
                        lambda row: mapping[row.sample_id],
                        "random",
                        seed,
                        config["query_budget"],
                        config["shortlist_k"],
                        policy,
                    )
                    run.update(checkpoint_pair=key, group=group, threshold=threshold)
                    # Uniform selection uses the same query archive, before outcomes.
                    run["uniform_shortlist"] = [
                        r["sample_id"] for r in run["archive"][: config["shortlist_k"]]
                    ]
                    run["seal"] = identity(
                        {
                            k: v
                            for k, v in run.items()
                            if k not in ("seal", "wall_seconds")
                        }
                    )
                    runs.append(run)
    return runs


def evaluate_transfer(predictions: dict, runs: list[dict], labels: dict) -> dict:
    """Evaluate once after all model/threshold/shortlist decisions are persisted."""
    for run in runs:
        verify_seal(run)
    result = {}
    for key, predicted in predictions.items():
        records = predicted["records"]
        replicates = defaultdict(list)
        for row in records:
            replicates[(row["compound_id"], row["group"])].append(
                labels[row["sample_id"]]
            )
        values = {
            r["sample_id"]: fmean(replicates[(r["compound_id"], r["group"])])
            for r in records
        }
        selections = []
        for run in runs:
            if run["checkpoint_pair"] != key:
                continue
            ids, uniform = run["shortlist"], run["uniform_shortlist"]
            selections.append(
                {
                    "group": run["group"],
                    "seed": run["seed"],
                    "threshold": run["threshold"],
                    "n": len(ids),
                    "requested_k": run["k"],
                    "query_count": run["requests"],
                    "shortlist": ids,
                    "measured_mean": fmean(values[i] for i in ids) if ids else None,
                    "uniform_mean": fmean(values[i] for i in uniform)
                    if uniform
                    else None,
                    "retained_query_fraction": sum(
                        r["accepted"] for r in run["archive"]
                    )
                    / run["requests"],
                }
            )
        result[key] = {
            "ridge": predictive_metrics(records, labels),
            "xgb": predictive_metrics(
                [{**r, "mean": r["secondary_mean"]} for r in records], labels
            ),
            "disagreement": {
                order: risk_coverage(records, labels, "disagreement", order)
                for order in ("diagnostic", "random", "oracle")
            },
            "distance": {
                order: risk_coverage(records, labels, "distance", order)
                for order in ("diagnostic", "random", "oracle")
            },
            "guardrail_metrics": {
                str(threshold): predictive_metrics(
                    [
                        {
                            **r,
                            "mean": r["mean"]
                            if r["diagnostics"]["disagreement"] <= threshold
                            else None,
                        }
                        for r in records
                    ],
                    labels,
                )
                for threshold in sorted(
                    {r["threshold"] for r in runs if r["threshold"] is not None}
                )
            },
            "selection": selections,
            "parity_max_abs": predicted["parity_max_abs"],
            "unknown_context_categories": predicted["unknown_context_categories"],
            "training_DGAT2_rows": predicted["training_DGAT2_rows"],
        }
    return result


def write_transfer_report(path: Path, result: dict, config: dict) -> None:
    """Summarize every checkpoint pair without selecting a winning model."""
    threshold = config["primary_disagreement_threshold"]
    scope = result["scope"]
    lines = [
        "# DGAT2 existing-checkpoint transfer diagnostic",
        "",
        f"Scored {scope['eligible_rows']}/{scope['original_rows']} original records.",
        (
            f"Excluded {scope['excluded_exposed_sequence_rows']} "
            "known-exposed sequence rows."
        ),
        "No fitting. Previously studied development data; one seen target.",
        "",
        "Chemistry metadata conflicts remain unresolved. Released HELM is unchanged.",
        "Original reagent categories are retained and flagged when unknown.",
        "",
        "Errors: equal assay stratum, then equal compound. Units: inhibition points.",
        f"Fixed primary disagreement threshold: {threshold} points.",
        "Shortlist contrasts use complete matched panels only, equal strata/seeds.",
        ("No confidence interval: strata and checkpoints are not independent targets."),
        "",
        (
            "| Source budget-seed | Ridge RMSE | XGB RMSE | Warning/error rho | "
            "Retained | Guarded minus ordinary | Full panel pairs |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, item in result["results"].items():
        selections = item["selection"]
        contrasts = []
        for guarded in selections:
            if guarded["threshold"] != threshold:
                continue
            ordinary = next(
                r
                for r in selections
                if r["threshold"] is None
                and r["group"] == guarded["group"]
                and r["seed"] == guarded["seed"]
            )
            if guarded["n"] == ordinary["n"] == config["shortlist_k"]:
                contrasts.append(guarded["measured_mean"] - ordinary["measured_mean"])
        difference = fmean(contrasts) if contrasts else None
        retained = item["guardrail_metrics"][str(threshold)]["coverage"]
        rho = item["disagreement"]["diagnostic"]["spearman_error"]
        lines.append(
            f"| {key} | {item['ridge']['macro_rmse']:.3f} | "
            f"{item['xgb']['macro_rmse']:.3f} | {rho} | {retained:.3f} | "
            f"{difference} | {len(contrasts)} |"
        )
    lines.extend(
        [
            "",
            "Detailed diagnostics, threshold sensitivity, uniform shortlists,",
            "Context strata, parity and provenance: report.json and preflight.json.",
            (
                "LoRA inference was not executed. "
                "No siRNA or fixed-profile model substitution."
            ),
            "",
        ]
    )
    with path.open("x") as handle:
        handle.write("\n".join(lines))


@contextmanager
def inference_guard() -> Iterator[dict]:
    """Count and reject any estimator or preprocessing fitting during replay."""
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from xgboost import XGBRegressor

    from oligo_engine.atlas.baselines import Classical, Features
    from oligo_engine.atlas.scaling import HoldoutClassical

    interfaces = [
        (Classical, "fit"),
        (Features, "fit"),
        (HoldoutClassical, "fit_validation"),
        (Ridge, "fit"),
        (XGBRegressor, "fit"),
        (ColumnTransformer, "fit"),
        (OneHotEncoder, "fit"),
        (StandardScaler, "fit"),
    ]
    originals = [(owner, name, getattr(owner, name)) for owner, name in interfaces]
    receipt = {
        "fit_attempts": 0,
        "protected_interfaces": [
            f"{owner.__name__}.{name}" for owner, name in interfaces
        ],
    }

    def denied(*args, **kwargs):
        receipt["fit_attempts"] += 1
        raise RuntimeError(
            "Fitting is forbidden in an existing-checkpoint transfer replay"
        )

    try:
        for owner, name in interfaces:
            setattr(owner, name, denied)
        yield receipt
    finally:
        for owner, name, original in originals:
            setattr(owner, name, original)


def run_dgat2(config: dict, original: Path, output: Path, trusted: bool) -> dict:
    """Execute the declared source/representation-transfer development diagnostic."""
    if config["schema"] != "dgat2-existing-transfer-v1":
        raise ValueError("Unsupported transfer protocol")
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    try:
        save(output / "protocol.json", config)
        source = load_asoptimizer()
        rows = recover_original(source, original)
        loader = pinned_loader(output / "pinned-loader")
        with inference_guard() as fit_guard:
            atlas, ids, source_audit = atlas_metadata(Path(config["atlas_source"]))
            models, memberships, exposed = frozen_models(config, atlas, ids, trusted)
            scope = scope_audit(rows, atlas, exposed)
            save(
                output / "preflight.json",
                {
                    "scope": scope,
                    "source": source.receipt,
                    "source_membership": source_audit,
                    "loader": loader,
                    "checkpoint_memberships": memberships,
                    "recovered_metadata": rows,
                    "endpoint_values_read": False,
                },
            )
            eligible = set(scope["eligible_ids"])
            selected = [r for r in rows if r["sample_id"] in eligible]
            if len(selected) < config["minimum_eligible_rows"]:
                raise ValueError("Insufficient leakage-free transfer records")
            predictions = predict_transfer(selected, models, atlas, memberships)
            save(output / "predictions.json", predictions)
            runs = seal_transfer(selected, predictions, config)
            save(
                output / "sealed-search.json",
                {"runs": runs, "endpoint_values_read": False},
            )
            hashes = {
                name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                for name in (
                    "protocol.json",
                    "preflight.json",
                    "predictions.json",
                    "sealed-search.json",
                )
            }
            # First numeric endpoint read occurs only after all model predictions and
            # shortlists (including every sensitivity threshold) have been sealed.
            labels = source.outcomes(tuple(sorted(eligible))).read(
                tuple(sorted(eligible))
            )
            results = evaluate_transfer(predictions, runs, labels)
            for name, digest in hashes.items():
                checked_bytes(output / name, digest)
            for key, receipt in memberships.items():
                for name, digest in receipt["checkpoint_hashes"].items():
                    checked_bytes(
                        Path("model_checkpoints")
                        / f"atlas-scaling-v1/source-{key}-{name}/model.pkl",
                        digest,
                    )
            result = {
                "status": "complete_development_representation_assay_transfer",
                "scope": scope,
                "results": results,
                "frozen_stage_hashes": hashes,
                "fit_calls": fit_guard["fit_attempts"],
                "inference_guard": fit_guard,
                "test_labels_used_upstream": False,
                "original_metadata_revision": ORIGIN_COMMIT,
                "original_metadata_sha256": ORIGIN_SHA,
                "original_dgat2_metadata_hash": records_hash(
                    tuple(r for r in source.rows if r.target_id == "DGAT2")
                ),
                "code_revision": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True
                ).strip(),
                "code_dirty": bool(
                    subprocess.check_output(
                        ["git", "status", "--porcelain"], text=True
                    ).strip()
                ),
                "runtime": {
                    n: importlib.metadata.version(n) for n in config["runtime"]
                },
                "independent_targets": 1,
                "limits": (
                    "Seen DGAT2 target; correlated assay strata; "
                    "unresolved chemistry annotation. No prospective robustness, "
                    "calibrated uncertainty, RL or safety claim."
                ),
            }
            save(output / "report.json", result)
            write_transfer_report(output / "report.md", result, config)
            return {
                "output": str(output),
                "original_rows": len(rows),
                "scored_rows": len(selected),
                "checkpoint_pairs": len(models),
                "refit_calls": 0,
            }
    except Exception as exc:
        save(
            output / "failure.json",
            {"reason": str(exc), "type": type(exc).__name__, "no_fallback_fit": True},
        )
        raise
