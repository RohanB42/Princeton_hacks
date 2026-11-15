"""Ordered, source-only supported-ASO study with delayed measured evaluation."""

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

from oligo_engine.design.aso_space import TargetContext, identity
from oligo_engine.design.candidates import tile
from oligo_engine.reward.portable import (
    CHEMISTRY,
    PortableEfficacy,
    encode_sequence,
    supported_sequence,
)
from oligo_engine.reward.scoring import ScoringSession

CONFIG = Path("configs/research/supported-aso-v1.json")
COHORT_SHA = "bbc3edbef73f2f2b926cd1fcc63946f16d52238f994e99c620be9f756522165d"
META = [
    "source_row_id",
    "HELM Annotation",
    "USPTO ID",
    "target_key",
    "natural_rna",
    "cell_line",
    "cell_line_species",
    "transfection_method",
    "dosage_nm",
    "treatment_period_hrs",
]


def save(path: Path, value: dict) -> None:
    with path.open("x") as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def close_mask(sequence: str, matrix: np.ndarray) -> np.ndarray:
    bases = np.asarray(list(sequence))
    return (
        ((matrix != bases).sum(axis=1) <= 2)
        | (matrix[:, 1:] == bases[:-1]).all(axis=1)
        | (matrix[:, :-1] == bases[1:]).all(axis=1)
    )


def labels(path: Path, ids: list[str]) -> np.ndarray:
    frame = pq.read_table(
        path,
        columns=["source_row_id", "Inhibition_pct"],
        filters=[("source_row_id", "in", ids)],
    ).to_pandas()
    indexed = frame.set_index("source_row_id").Inhibition_pct
    if not indexed.index.is_unique or set(indexed.index) != set(ids):
        raise ValueError("Measured-label IDs disagree")
    values = indexed.loc[ids].to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite measured labels")
    return values


def checked_partition(output: Path) -> dict:
    partition = json.loads((output / "partition.json").read_text())
    cohort = Path(partition["cohort"])
    digest = hashlib.sha256(cohort.read_bytes()).hexdigest()
    if digest != COHORT_SHA or digest != partition["cohort_sha256"]:
        raise ValueError("Cohort changed after partition freeze")
    if partition["config"] != json.loads(CONFIG.read_text()):
        raise ValueError("Protocol changed after partition freeze")
    return partition


def prepare(root: Path, output: Path) -> None:
    cfg = json.loads(CONFIG.read_text())
    cohort = root / "cohort.parquet"
    actual_sha = hashlib.sha256(cohort.read_bytes()).hexdigest()
    if actual_sha != COHORT_SHA:
        raise ValueError("Prepared cohort hash changed")
    source = json.loads((root / "manifests.json").read_text())
    train_ids, test_ids = (
        set(source["source_train_ids"]),
        set(source["source_validation_ids"]),
    )
    reserved = {i for c in source["campaigns"] for i in c["pool_ids"] + c["test_ids"]}
    assert not train_ids & test_ids and not (train_ids | test_ids) & reserved
    frame = pq.read_table(
        cohort,
        columns=META,
        filters=[("source_row_id", "in", sorted(train_ids | test_ids))],
    ).to_pandas()
    support = {}
    for raw in frame["HELM Annotation"].unique():
        try:
            support[raw] = supported_sequence(raw)
        except ValueError:
            pass
    keep = frame["HELM Annotation"].isin(support)
    for key, value in cfg["assay"].items():
        keep &= frame[key].eq(value)
    frame = frame[keep].copy()
    before = frame.groupby(frame.source_row_id.isin(train_ids)).size().to_dict()
    frame = frame[
        ~frame.target_key.str.match(cfg["exclude_ambiguous_target_pattern"])
    ].copy()
    frame["sequence"] = frame["HELM Annotation"].map(support)
    train_all = frame[frame.source_row_id.isin(train_ids)].sort_values("source_row_id")
    test_all = frame[frame.source_row_id.isin(test_ids)].sort_values("source_row_id")
    train = train_all.drop_duplicates("sequence", keep="first").reset_index(drop=True)
    test = test_all.drop_duplicates("sequence", keep="first").reset_index(drop=True)
    # Internal groups connect target IDs, patent IDs and nearby source sequences.
    parent = list(range(len(train)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)

    # Keep duplicate-source provenance when assigning patent links.
    by_sequence = dict(zip(train.sequence, train.index))
    groups_seen = {}
    for sequence, target in zip(train_all.sequence, train_all.target_key):
        i = by_sequence[sequence]
        key = ("target", target)
        if key in groups_seen:
            union(i, groups_seen[key])
        else:
            groups_seen[key] = i
    for sequence, patent in zip(train_all.sequence, train_all["USPTO ID"]):
        i = by_sequence[sequence]
        key = ("patent", patent)
        if key in groups_seen:
            union(i, groups_seen[key])
        else:
            groups_seen[key] = i
    matrix = np.asarray([list(s) for s in train.sequence])
    for i, sequence in enumerate(train.sequence):
        for j in np.flatnonzero(close_mask(sequence, matrix)):
            if j > i:
                union(i, int(j))
    train["cv_group"] = [find(i) for i in range(len(train))]
    removed = test[test.sequence.map(lambda s: bool(close_mask(s, matrix).any()))]
    test = test[~test.source_row_id.isin(removed.source_row_id)].reset_index(drop=True)
    if len(train) < 100 or len(test) < 100 or train.cv_group.nunique() < 2:
        raise ValueError("Insufficient source groups or clean held-out records")
    assert set(train["USPTO ID"]).isdisjoint(test["USPTO ID"])
    manifest = {
        "config": cfg,
        "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "cohort": str(cohort.resolve()),
        "cohort_sha256": actual_sha,
        "source_manifest_sha256": hashlib.sha256(
            (root / "manifests.json").read_bytes()
        ).hexdigest(),
        "train": train.to_dict("records"),
        "test": test.to_dict("records"),
        "profile_train_rows_before_filters": int(before.get(True, 0)),
        "profile_test_rows_before_filters": int(before.get(False, 0)),
        "heldout_near_source_exclusions": len(removed),
        "cv_groups": int(train.cv_group.nunique()),
        "labels_read": False,
        "reserved_campaigns_used": False,
    }
    save(output / "partition.json", manifest)
    print(
        {
            "training": len(train),
            "assessment": len(test),
            "cv_groups": manifest["cv_groups"],
            "test_targets": dict(Counter(test.target_key)),
            "near_source_removed": len(removed),
        }
    )


def fit(output: Path) -> None:
    partition_path = output / "partition.json"
    p = checked_partition(output)
    cfg = p["config"]
    rows = p["train"]
    ids = [r["source_row_id"] for r in rows]
    x = np.asarray([encode_sequence(r["sequence"]) for r in rows])
    y = labels(Path(p["cohort"]), ids)
    groups = [r["cv_group"] for r in rows]
    cv = []
    folds = list(GroupKFold(min(3, len(set(groups)))).split(x, groups=groups))
    for alpha in cfg["alpha_grid"]:
        errors = []
        for tr, va in folds:
            model = Ridge(alpha=alpha, solver="lsqr", tol=1e-8).fit(x[tr], y[tr])
            errors.append(float(np.mean((model.predict(x[va]) - y[va]) ** 2)))
        cv.append(
            {"alpha": alpha, "fold_mse": errors, "mean_mse": float(np.mean(errors))}
        )
    chosen = min(cv, key=lambda r: r["mean_mse"])["alpha"]
    model = Ridge(alpha=chosen, solver="lsqr", tol=1e-8).fit(x, y)
    bundle = {
        "schema": "supported-aso-ridge-v1",
        "chemistry": CHEMISTRY,
        "assay": cfg["assay"],
        "coefficients": model.coef_.tolist(),
        "intercept": float(model.intercept_),
        "training_prediction_reference": model.predict(x).tolist(),
        "training_sequences": [r["sequence"] for r in rows],
        "training_ids": ids,
        "split_hash": hashlib.sha256(partition_path.read_bytes()).hexdigest(),
        "cohort_sha256": p["cohort_sha256"],
        "alpha": chosen,
        "cv": cv,
        "training_label_mean": float(y.mean()),
        "no_target_adaptation": True,
        "safety": "unknown",
        "provenance": "existing_source_train_partition_only",
    }
    model_path = output / "efficacy.json"
    save(model_path, bundle)
    sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    portable = PortableEfficacy(model_path, sha)
    probe_rows = rows + p["test"]
    reference = model.predict(
        np.asarray([encode_sequence(r["sequence"]) for r in probe_rows])
    )
    reproduced = np.asarray(
        [
            portable.predict_helm(r["HELM Annotation"], portable.assay)
            for r in probe_rows
        ]
    )
    error = float(np.max(np.abs(reference - reproduced)))
    if error > 1e-9:
        raise AssertionError("Portable model parity failed")
    preds = reproduced[len(rows) :]
    locked = []
    for target in sorted({r["target_key"] for r in p["test"]}):
        indices = [i for i, r in enumerate(p["test"]) if r["target_key"] == target]
        if len(indices) < cfg["minimum_target_rows"]:
            continue
        order = sorted(
            indices, key=lambda i: (-preds[i], p["test"][i]["source_row_id"])
        )
        locked.append(
            {
                "target": target,
                "eligible_indices": indices,
                "selected_indices": order[: cfg["top_k"]],
            }
        )
    save(
        output / "predictions.json",
        {
            "test_ids": [r["source_row_id"] for r in p["test"]],
            "predictions": preds.tolist(),
            "locked_shortlists": locked,
            "labels_read": False,
        },
    )
    save(
        output / "bundle-manifest.json",
        {
            "artifact_sha256": sha,
            "prediction_parity_max_abs": error,
            "training_ids_sha256": identity(ids),
            "split_sha256": bundle["split_hash"],
            "fit_label_count": len(ids),
            "selected_alpha": chosen,
            "cv": cv,
            "independent_measured_evaluation_pending": True,
        },
    )
    print({"fit_labels": len(ids), "alpha": chosen, "parity_max_abs": error})


def evaluate(output: Path) -> None:
    from scipy.stats import pearsonr, spearmanr

    p = checked_partition(output)
    predictions = json.loads((output / "predictions.json").read_text())
    assert predictions["test_ids"] == [r["source_row_id"] for r in p["test"]]
    assert set(predictions["test_ids"]).isdisjoint(
        r["source_row_id"] for r in p["train"]
    )
    pred = np.asarray(predictions["predictions"])
    manifest = json.loads((output / "bundle-manifest.json").read_text())
    portable = PortableEfficacy(output / "efficacy.json", manifest["artifact_sha256"])
    bundle = portable.bundle
    if (
        bundle["split_hash"]
        != hashlib.sha256((output / "partition.json").read_bytes()).hexdigest()
    ):
        raise ValueError("Partition changed after prediction freeze")
    expected = np.asarray(
        [portable.predict_helm(r["HELM Annotation"], portable.assay) for r in p["test"]]
    )
    if not np.array_equal(pred, expected):
        raise ValueError("Saved predictions disagree with frozen model")
    for selection in predictions["locked_shortlists"]:
        indices = [
            i
            for i, row in enumerate(p["test"])
            if row["target_key"] == selection["target"]
        ]
        order = sorted(indices, key=lambda i: (-pred[i], p["test"][i]["source_row_id"]))
        if (
            selection["eligible_indices"] != indices
            or selection["selected_indices"] != order[: p["config"]["top_k"]]
        ):
            raise ValueError("Saved shortlist differs from frozen ranking rule")
    y = labels(Path(p["cohort"]), predictions["test_ids"])
    rows = []
    for selection in predictions["locked_shortlists"]:
        indices = selection["eligible_indices"]
        selected = selection["selected_indices"]
        a, b = y[indices], pred[indices]
        rows.append(
            {
                "target": selection["target"],
                "n": len(indices),
                "k": len(selected),
                "selected_mean": float(y[selected].mean()),
                "random_expected_mean": float(a.mean()),
                "lift_percentage_points": float(y[selected].mean() - a.mean()),
                "rmse": float(np.mean((a - b) ** 2) ** 0.5),
                "pearson": float(pearsonr(a, b).statistic)
                if np.std(a) > 0 and np.std(b) > 0
                else None,
                "spearman": float(spearmanr(a, b).statistic)
                if np.std(a) > 0 and np.std(b) > 0
                else None,
            }
        )
    macro = (
        float(np.mean([r["lift_percentage_points"] for r in rows])) if rows else None
    )
    gate = (
        len(rows) >= 2
        and macro > 0
        and sum(r["lift_percentage_points"] > 0 for r in rows) >= 2
    )
    report = {
        "status": "heldout_patent_development_assessment",
        "rows": rows,
        "n": len(y),
        "rmse": float(np.mean((pred - y) ** 2) ** 0.5),
        "mae": float(np.abs(pred - y).mean()),
        "training_mean_baseline_rmse": float(
            np.mean((y - bundle["training_label_mean"]) ** 2) ** 0.5
        ),
        "macro_lift_percentage_points": macro,
        "provisional_readiness_gate": bool(gate),
        "reserved_campaigns_scored": False,
        "target_adaptation_labels": 0,
        "novel_candidates_validated": False,
        "safety_validated": False,
        "limits": [
            "Patent identifiers, not resolved patent families.",
            "Mostly seen-target patent transfer; not a new-target guarantee.",
            "Grouped source tuning; close assessment sequences excluded.",
            "One assay context; data-derived profile and development evidence only.",
        ],
    }
    save(output / "assessment.json", report)
    print(json.dumps(report, indent=2))


def panel(output: Path, transcript_path: Path) -> None:
    raw = json.loads(transcript_path.read_text())
    # Sequence content is pinned even when the upstream REST ID lacks a version suffix.
    target = TargetContext(
        raw["gene"],
        raw["transcript_id"],
        raw["sequence"],
        raw["species"],
        raw["source"]
        + "; sha256="
        + hashlib.sha256(raw["sequence"].encode()).hexdigest(),
    )
    manifest = json.loads((output / "bundle-manifest.json").read_text())
    model = PortableEfficacy(output / "efficacy.json", manifest["artifact_sha256"])
    candidates = tile(
        target.gene, target.transcript_id, target.sequence, chemistry=CHEMISTRY
    )
    # Fixed evenly-spaced panel; no selection using outcomes or final prediction scores.
    indices = np.linspace(0, len(candidates) - 1, min(64, len(candidates)), dtype=int)
    session = ScoringSession(model.scorer(), target, model.assay, 64, 64)
    for i in indices:
        session.score(candidates[i])
    records = session.receipt()
    records["target_manifest"] = asdict(target)
    records["candidate_status"] = "unmeasured_hypotheses_no_safety_validation"
    save(output / "real-panel.json", records)
    # Verify that the same real candidate receives identical direct and env scores
    # in the isolated optional RL runtime; that check is invoked separately.
    print(
        {
            "target": target.gene,
            "candidates": len(indices),
            "scorer": session.scorer.identity,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "fit", "evaluate", "panel"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepared-root", type=Path)
    parser.add_argument("--transcript", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.phase == "prepare":
        if args.prepared_root is None:
            parser.error("--prepared-root required")
        prepare(args.prepared_root, args.output)
    elif args.phase == "fit":
        fit(args.output)
    elif args.phase == "evaluate":
        evaluate(args.output)
    else:
        if args.transcript is None:
            parser.error("--transcript required")
        panel(args.output, args.transcript)


if __name__ == "__main__":
    main()
