"""Separate, frozen-protocol endpoint qualification; final outcomes stay sealed.

Prepare reads chemistry/context only. Fit may read fit/development/calibration
outcomes through explicit source-row filters; never the final partition.
"""

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from oligo_engine.molecular_design.artifacts import seal, verify, write_new
from oligo_engine.molecular_design.cli import load_study
from oligo_engine.reward.chemistry import parse_helm

RISK_CONTEXT = {
    "species": "Mouse",
    "species_strain": "C57BL/6 mice",
    "dosage_ug": 700.0,
    "latency_time_hours": 3.0,
    "administration_method": "ICV",
    "tolerability_score_type": "Behavioral",
}


def prepare(config_path: Path, root: Path, output: Path) -> dict:
    import pandas as pd

    config, campaigns, _ = load_study(config_path)
    profile = campaigns[0].profile
    audit = json.loads((root / "cleaned/audit.json").read_text())
    path = root / "release/neurotoxicity.parquet"
    if (
        hashlib.sha256(path.read_bytes()).hexdigest()
        != audit["endpoints"]["neurotoxicity"]["source_sha256"]
    ):
        raise ValueError("Risk source integrity failure")
    columns = ["HELM Annotation", "USPTO ID", "target_RNA", *RISK_CONTEXT]
    frame = pd.read_parquet(path, columns=columns)
    frame["source_row_id"] = [f"neurotoxicity:{i}" for i in range(len(frame))]
    for key, value in RISK_CONTEXT.items():
        frame = frame[frame[key] == value]
    records = []
    for row in frame.to_dict("records"):
        try:
            chem = parse_helm(row["HELM Annotation"])
        except (ValueError, TypeError):
            continue
        sequence = chem.natural_rna.replace("U", "T")
        for p in profile.patterns:
            if p.length == len(sequence) and chem.terminal in p.terminals:
                expected = parse_helm(p.helm(sequence, chem.terminal))
                if chem.identity == expected.identity:
                    records.append(
                        {
                            "id": row["source_row_id"],
                            "helm": row["HELM Annotation"],
                            "sequence": sequence,
                            "compound": chem.identity,
                            "patent": str(row["USPTO ID"]),
                            "target": str(row["target_RNA"]),
                            "pattern": p.name,
                        }
                    )
                    break
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a, b):
        parent[find(a)] = find(b)

    families = {}
    for row in records:
        patent, sequence = "patent:" + row["patent"], row["sequence"]
        union(patent, "seq:" + sequence)
        # Hamming <=2 and exact one-base shifts are connected before splitting.
        for i, j in combinations(range(len(sequence)), 2):
            key = sequence[:i] + "*" + sequence[i + 1 : j] + "*" + sequence[j + 1 :]
            if key in families:
                union(patent, families[key])
            else:
                families[key] = patent
        for key in ("shift:" + sequence[1:], "shift:" + sequence[:-1]):
            if key in families:
                union(patent, families[key])
            else:
                families[key] = patent
    groups = defaultdict(list)
    for row in records:
        groups[find("patent:" + row["patent"])].append(row)
    names, rng = sorted(groups), random.Random(1729)
    best = None
    for _ in range(2000 if len(names) >= 13 else 0):
        shuffled = rng.sample(names, len(names))
        allocation = {
            "final": shuffled[:5],
            "calibration": shuffled[5:7],
            "development": shuffled[7:9],
            "fit": shuffled[9:],
        }
        parts = {
            k: [r for g in values for r in groups[g]]
            for k, values in allocation.items()
        }
        counts = {
            k: Counter(r["pattern"] for r in values) for k, values in parts.items()
        }
        if any(
            counts[k][p.name] < (20 if k == "fit" else 5)
            for k in parts
            for p in profile.patterns
        ):
            continue
        discrepancy = sum(
            abs(len(parts[k]) / len(records) - fraction)
            for k, fraction in (
                ("fit", 0.5),
                ("development", 0.15),
                ("calibration", 0.15),
                ("final", 0.2),
            )
        )
        if best is None or discrepancy < best[0]:
            best = discrepancy, parts, allocation
    result = {
        "schema": "molecular-head-qualification-v1",
        "config": config,
        "risk_context": RISK_CONTEXT,
        "risk_source_sha256": audit["endpoints"]["neurotoxicity"]["source_sha256"],
        "risk_cleaned_sha256": audit["endpoints"]["neurotoxicity"]["cleaned_sha256"],
        "metadata_rows": len(records),
        "connected_groups": len(groups),
        "group_sizes": sorted(map(len, groups.values()), reverse=True),
        "patterns": dict(Counter(r["pattern"] for r in records)),
        "split_rule": (
            "fixed metadata-only 2000-allocation balance search; "
            "5 final, 2 calibration, 2 development, >=4 fit groups"
        ),
        "minimum_per_pattern": {
            "fit": 20,
            "development": 5,
            "calibration": 5,
            "final": 5,
        },
        "models": {
            "ridge_alpha": 10.0,
            "rf_trees": 256,
            "rf_max_depth": 12,
            "seed": 1729,
        },
        "selection": "lowest development RMSE, Ridge on ties",
        "screen": "0 <= prediction <= median fitted-training predictions",
        "screen_meaning": (
            "relative low predicted acute mouse FOB; not a clinical threshold"
        ),
        "development_gate": (
            "RMSE below fit-mean baseline and retained measured mean below pool mean; "
            "10%-90% retention and >=20 retained"
        ),
        "replicates": (
            "arithmetic mean of finite 0-7 FOB values per exact source row; "
            "no copied labels"
        ),
        "final_outcomes_access": "forbidden in prepare and fit",
        "status": "metadata_ready"
        if best
        else "blocked_insufficient_grouped_pattern_coverage",
    }
    if best:
        result["partitions"] = {
            k: [r["id"] for r in values] for k, values in best[1].items()
        }
        result["groups"] = best[2]
        result["records"] = records
    write_new(output / "protocol.json", seal(result))
    return result


def fit(root: Path, output: Path) -> dict:
    if (output / "model.json").exists() or (output / "development.json").exists():
        raise FileExistsError("Qualification outputs already exist")
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge

    from oligo_engine.molecular_design.chemical_model import chemical_features

    protocol = json.loads((output / "protocol.json").read_text())
    verify(protocol)
    if protocol["status"] != "metadata_ready":
        raise ValueError("Qualification blocked before any outcome access")
    path = root / "cleaned/neurotoxicity.parquet"
    if hashlib.sha256(path.read_bytes()).hexdigest() != protocol["risk_cleaned_sha256"]:
        raise ValueError("Risk prepared source integrity failure")
    parts = protocol["partitions"]
    allowed = parts["fit"] + parts["development"] + parts["calibration"]
    if set(allowed) & set(parts["final"]):
        raise ValueError("Outcome capability overlaps final partition")
    labels = pd.read_parquet(
        path,
        columns=["source_row_id", "FOB_score"],
        filters=[("source_row_id", "in", allowed)],
    )
    ymap, missing = {}, []
    for row in labels.to_dict("records"):
        values = np.asarray(row["FOB_score"], dtype=float)
        if values.ndim == 0 or values.size == 0:
            if values.size and np.isfinite(values).any():
                raise ValueError("Unexpected scalar outcome encoding")
            missing.append(row["source_row_id"])
            continue
        if not np.isfinite(values).all() or np.any(values < 0) or np.any(values > 7):
            raise ValueError("Invalid FOB measurement; protocol requires revision")
        ymap[row["source_row_id"]] = float(values.mean())
    amendment = output / "input-schema-amendment.json"
    if missing:
        if not amendment.is_file():
            raise ValueError("Missing labels require an explicit schema amendment")
        receipt = json.loads(amendment.read_text())
        verify(receipt)
        if receipt.get("protocol_seal") != protocol["seal"] or set(
            receipt.get("missing_ids", [])
        ) != set(missing):
            raise ValueError("Missing-label amendment does not match this input")
        parts = {k: [i for i in ids if i not in missing] for k, ids in parts.items()}
    records = {r["id"]: r for r in protocol["records"]}
    for name in ("fit", "development", "calibration"):
        counts = Counter(records[i]["pattern"] for i in parts[name])
        if any(
            counts[pattern] < protocol["minimum_per_pattern"][name]
            for pattern in protocol["patterns"]
        ):
            raise ValueError("Observed-outcome coverage falls below locked minimum")
    x = {
        k: np.asarray([chemical_features(records[i]["helm"]) for i in ids])
        for k, ids in parts.items()
        if k != "final"
    }
    y = {
        k: np.asarray([ymap[i] for i in ids])
        for k, ids in parts.items()
        if k != "final"
    }
    models = [
        Ridge(alpha=10, solver="lsqr", tol=1e-8),
        RandomForestRegressor(
            n_estimators=256, max_depth=12, random_state=1729, n_jobs=1
        ),
    ]
    errors = []
    for model in models:
        model.fit(x["fit"], y["fit"])
        errors.append(
            float(
                np.mean((model.predict(x["development"]) - y["development"]) ** 2)
                ** 0.5
            )
        )
    selected = int(np.argmin(errors))
    model = models[selected]
    train_predictions, dev = model.predict(x["fit"]), model.predict(x["development"])
    upper = float(np.median(train_predictions))
    retained = (dev >= 0) & (dev <= upper)
    baseline = float(np.mean((y["development"] - y["fit"].mean()) ** 2) ** 0.5)
    selected_mean = float(y["development"][retained].mean()) if retained.any() else None
    passed = (
        errors[selected] < baseline
        and retained.sum() >= 20
        and 0.1 <= retained.mean() <= 0.9
        and selected_mean < float(y["development"].mean())
    )
    result = {
        "status": "development_qualified" if passed else "development_gate_failed",
        "model": "ridge" if selected == 0 else "random_forest",
        "development_rmse": errors,
        "baseline_rmse": baseline,
        "upper": upper,
        "retained": int(retained.sum()),
        "retention": float(retained.mean()),
        "retained_mean": selected_mean,
        "pool_mean": float(y["development"].mean()),
        "protocol_seal": protocol["seal"],
        "outcome_ids_read": allowed,
        "missing_outcome_ids": missing,
        "input_schema_amendment": json.loads(amendment.read_text())
        if amendment.is_file()
        else None,
        "final_outcomes_read": False,
        "calibration_residuals": sorted(
            abs(model.predict(x["calibration"]) - y["calibration"]).tolist()
        ),
    }
    parameters = (
        {"coefficients": model.coef_.tolist(), "intercept": float(model.intercept_)}
        if selected == 0
        else {
            "trees": [
                {
                    "left": t.tree_.children_left.tolist(),
                    "right": t.tree_.children_right.tolist(),
                    "feature": t.tree_.feature.tolist(),
                    "threshold": t.tree_.threshold.tolist(),
                    "value": t.tree_.value[:, 0, 0].tolist(),
                }
                for t in model.estimators_
            ]
        }
    )
    bundle = {
        "schema": "frozen-chemical-regressor-v1",
        "model": result["model"],
        "parameters": parameters,
        "training_ids": parts["fit"],
        "validation_ids": parts["development"],
        "calibration_ids": parts["calibration"],
        "context": protocol["risk_context"],
        "training_prediction_reference": train_predictions.tolist(),
        "qualification": result,
        "parity": [
            {"helm": records[i]["helm"], "mean": float(v)}
            for i, v in zip(
                parts["development"][:10], model.predict(x["development"][:10])
            )
        ],
    }
    write_new(output / "model.json", bundle)
    write_new(output / "development.json", seal(result))
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=("prepare", "fit"))
    p.add_argument("--config", type=Path)
    p.add_argument("--root", type=Path, default=Path("data/aso_atlas_2"))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = (
        prepare(args.config, args.root, args.output)
        if args.phase == "prepare"
        else fit(args.root, args.output)
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("status", "metadata_rows", "connected_groups")
                if k in result
            }
        )
    )


if __name__ == "__main__":
    main()
