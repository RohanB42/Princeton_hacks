"""Frozen source-learning and development-target classical controls."""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from oligo_engine.atlas.baselines import Classical, metrics


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    cfg = json.loads(Path("configs/atlas/development-v1.json").read_text())
    manifest = json.loads(Path(cfg["manifest"]).read_text())
    frame = pd.read_parquet(Path(cfg["manifest"]).parent / "cohort.parquet").set_index(
        "source_row_id", drop=False
    )
    labels = frame.pop("Inhibition_pct")
    rows = []
    t = time.monotonic()
    source_models = {}
    for seed in cfg["source_seeds"]:
        ids = np.random.default_rng(seed).permutation(manifest["source_train_ids"])
        for b in cfg["source_budgets"]:
            chosen = ids[:b].tolist()
            for kind in ["context", "ridge", "xgb"]:
                model = Classical(kind, seed).fit(
                    frame.loc[chosen], labels.loc[chosen].to_numpy()
                )
                val = manifest["source_validation_ids"]
                rows.append(
                    {
                        "stage": "source",
                        "seed": seed,
                        "budget": b,
                        "model": kind,
                        "ids": chosen,
                        "choice": model.choice,
                        "metrics": metrics(
                            labels.loc[val].to_numpy(), model.predict(frame.loc[val])
                        ),
                    }
                )
                if seed == 510 and b == 1000:
                    source_models[kind] = model
                print("source", seed, b, kind, flush=True)
    # All source hyperparameter searches above are acquired-only; metrics are reporting.
    predictions = []
    for campaign in manifest["campaigns"]:
        if campaign["role"] != "development":
            continue
        test = campaign["test_ids"]
        for kind, model in source_models.items():
            source_pred = model.predict(frame.loc[test])
            predictions.append(
                (
                    {
                        "stage": "target",
                        "target": campaign["target"],
                        "seed": None,
                        "budget": 0,
                        "model": kind + "_source",
                    },
                    test,
                    source_pred,
                )
            )
            for seed in cfg["target_seeds"]:
                pool = np.random.default_rng(seed).permutation(campaign["pool_ids"])
                for b in cfg["target_budgets"]:
                    acquired = pool[:b].tolist()
                    y = labels.loc[acquired].to_numpy()
                    offset = float(np.mean(y - model.predict(frame.loc[acquired])))
                    predictions.append(
                        (
                            {
                                "stage": "target",
                                "target": campaign["target"],
                                "seed": seed,
                                "budget": b,
                                "model": kind + "_offset",
                                "ids": acquired,
                                "source_budget": 1000,
                            },
                            test,
                            source_pred + offset,
                        )
                    )
                    if kind != "context":
                        residual = Classical("ridge", seed).fit(
                            frame.loc[acquired], y - model.predict(frame.loc[acquired])
                        )
                        predictions.append(
                            (
                                {
                                    "stage": "target",
                                    "target": campaign["target"],
                                    "seed": seed,
                                    "budget": b,
                                    "model": kind + "_residual",
                                    "ids": acquired,
                                    "source_budget": 1000,
                                },
                                test,
                                source_pred + residual.predict(frame.loc[test]),
                            )
                        )
        for seed in cfg["target_seeds"]:
            pool = np.random.default_rng(seed).permutation(campaign["pool_ids"])
            for b in cfg["target_budgets"]:
                acquired = pool[:b].tolist()
                local = Classical("ridge", seed).fit(
                    frame.loc[acquired], labels.loc[acquired].to_numpy()
                )
                predictions.append(
                    (
                        {
                            "stage": "target",
                            "target": campaign["target"],
                            "seed": seed,
                            "budget": b,
                            "model": "ridge_target_only",
                            "ids": acquired,
                            "source_budget": 0,
                        },
                        test,
                        local.predict(frame.loc[test]),
                    )
                )
        print("target fitted", campaign["target"], flush=True)
    # Final target scoring deferred until all fitting decisions are complete.
    for meta, ids, pred in predictions:
        rows.append(meta | {"metrics": metrics(labels.loc[ids].to_numpy(), pred)})
    report = {
        "config": cfg,
        "rows": rows,
        "elapsed_s": time.monotonic() - t,
        "reserved_targets_scored": False,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("complete", len(rows), report["elapsed_s"], flush=True)


if __name__ == "__main__":
    main()
