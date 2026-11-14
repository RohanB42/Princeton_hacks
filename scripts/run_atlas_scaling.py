"""Budget-accounted Atlas source/epoch scaling; all test scoring is deferred."""

import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
import pickle
import resource
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch

from oligo_engine.atlas.baselines import metrics
from oligo_engine.atlas.scaling import (
    HoldoutClassical,
    grouped_validation,
    read_label_subset,
)
from oligo_engine.atlas.splits import sequence_groups
from oligo_engine.models.aso_rnafm import ASOPredictor, ChemistryHead

CHECKPOINT = Path(
    "/private/tmp/oligoal-rnafm-20261114/artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth"
)
CONFIG = Path("configs/atlas/scaling-v1.json")


def dump(path: Path, value: dict | list) -> None:
    """Persist atomically, including interrupted-run receipts."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def prepare(output: Path, cfg: dict, frame: pd.DataFrame, manifest: dict) -> dict:
    """Freeze all memberships without accepting any efficacy labels."""
    if "Inhibition_pct" in frame:
        raise ValueError("Labels supplied to split preparation")
    if len(manifest["source_train_ids"]) != cfg["source_denominator"]:
        raise ValueError("Changed source denominator")
    partitions = {"source": [], "target": []}
    for seed in cfg["source_seeds"]:
        order = np.random.default_rng(seed).permutation(manifest["source_train_ids"])
        for budget in cfg["source_budgets"]:
            ids = order[:budget].tolist()
            split = grouped_validation(ids, frame.loc[ids, "USPTO ID"].tolist(), seed)
            partitions["source"].append(
                {"seed": seed, "budget": budget, "selected_ids": ids, **split}
            )
    for campaign in manifest["campaigns"]:
        if campaign["role"] != "development":
            continue
        if campaign["target"] not in cfg["targets"]:
            raise ValueError("Unexpected development target")
        pool = campaign["pool_ids"]
        groups = dict(
            zip(
                pool, map(str, sequence_groups(frame.loc[pool, "natural_rna"].tolist()))
            )
        )
        for seed in cfg["paired_target_seeds"]:
            ids = (
                np.random.default_rng(seed)
                .permutation(pool)[: cfg["target_budget"]]
                .tolist()
            )
            split = grouped_validation(ids, [groups[i] for i in ids], seed)
            partitions["target"].append(
                {
                    "target": campaign["target"],
                    "seed": seed,
                    "acquired_ids": ids,
                    "test_ids": campaign["test_ids"],
                    **split,
                }
            )
    source = set(manifest["source_train_ids"])
    for part in partitions["target"]:
        assert not set(part["acquired_ids"]) & set(part["test_ids"])
        assert not source & set(part["acquired_ids"] + part["test_ids"])
    dump(output / "partitions.json", partitions)
    dump(output / "config.json", cfg)
    return partitions


def run(args: argparse.Namespace) -> None:
    torch.set_num_threads(1)
    cfg = json.loads(CONFIG.read_text())
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(cfg["manifest"])
    manifest = json.loads(manifest_path.read_text())
    cohort_path = manifest_path.parent / "cohort.parquet"
    columns = [n for n in pq.read_schema(cohort_path).names if n != "Inhibition_pct"]
    frame = pd.read_parquet(cohort_path, columns=columns).set_index(
        "source_row_id", drop=False
    )
    # Restrict endpoint reads to explicitly permitted fitting IDs.
    allowed = set(manifest["source_train_ids"])
    for c in manifest["campaigns"]:
        if c["role"] == "development":
            allowed.update(c["pool_ids"])
    fit_labels = read_label_subset(cohort_path, sorted(allowed))
    if (output / "partitions.json").exists():
        if json.loads((output / "config.json").read_text()) != cfg:
            raise ValueError("Frozen configuration mismatch")
        parts = json.loads((output / "partitions.json").read_text())
    else:
        parts = prepare(output, cfg, frame, manifest)
    if args.phase == "prepare":
        print(
            "Frozen",
            len(parts["source"]),
            "source and",
            len(parts["target"]),
            "target partitions",
            flush=True,
        )
        return
    state_path = output / "suite.json"
    state = (
        json.loads(state_path.read_text())
        if state_path.exists()
        else {
            "status": "running",
            "started_unix": time.time(),
            "completed": [],
            "failures": [],
            "config": cfg,
            "reserved_targets_scored": False,
            "code_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "environment": {
                p: importlib.metadata.version(p)
                for p in ["numpy", "pandas", "torch", "scikit-learn", "xgboost"]
            },
            "source_hashes": {
                str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [
                    Path(__file__),
                    CONFIG,
                    Path("src/oligo_engine/models/aso_rnafm.py"),
                    Path("src/oligo_engine/atlas/scaling.py"),
                    manifest_path,
                    output / "partitions.json",
                ]
            },
        }
    )
    state.setdefault("invocations", []).append(
        {
            "pid": os.getpid(),
            "code_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "dirty": bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], text=True
                ).strip()
            ),
            "phase": args.phase,
            "time_unix": time.time(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "model_sha256": hashlib.sha256(
                Path("src/oligo_engine/models/aso_rnafm.py").read_bytes()
            ).hexdigest(),
        }
    )
    state.update(pid=os.getpid(), phase=args.phase, status="running")
    dump(state_path, state)

    def persist():
        state["elapsed_s"] = time.time() - state["started_unix"]
        state["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        dump(state_path, state)

    def check_cap():
        if time.time() - state["started_unix"] > cfg["study_wall_cap_seconds"]:
            raise TimeoutError("Frozen study wall cap reached")

    def neural_fit(model, directory, train_ids, val_ids, source=None, fixed=False):
        directory.mkdir(parents=True, exist_ok=True)
        history = []

        def on_epoch(row):
            history.append(row)
            dump(directory / "history.json", history)
            state["active"] = {
                "fit": str(directory),
                "epoch": row["epoch"],
                "train_rmse": row["train_rmse"],
                "validation_rmse": row.get("validation_rmse"),
            }
            persist()
            print(
                directory.name,
                "epoch",
                row["epoch"],
                "train",
                round(row["train_rmse"], 3),
                "validation",
                round(row.get("validation_rmse", 0), 3),
                flush=True,
            )

        receipt = model.fit(
            frame.loc[train_ids],
            fit_labels.loc[train_ids].to_numpy(),
            epochs=cfg["fixed_target_epochs"] if fixed else cfg["max_epochs"],
            source=source,
            validation=None
            if fixed
            else (frame.loc[val_ids], fit_labels.loc[val_ids].to_numpy()),
            record_history=True,
            min_epochs=cfg["min_epochs"],
            patience=cfg["patience"],
            min_delta=cfg["minimum_rmse_improvement"],
            checkpoint_epochs=tuple(cfg["checkpoint_epochs"]),
            epoch_callback=on_epoch,
        )
        receipt["encoder_identity"] = model.encoder.identity
        receipt["encoder_config"] = model.encoder.config
        torch.save(model.snapshot(), directory / "best.pt")
        for epoch, snapshot in model.checkpoints.items():
            torch.save(snapshot, directory / f"epoch-{epoch}.pt")
        dump(directory / "receipt.json", receipt)
        return receipt

    def pending(directory, meta, test_ids, prediction):
        dump(
            directory / "predictions.json",
            {
                "metadata": meta,
                "test_ids": test_ids,
                "predictions": prediction.tolist(),
            },
        )

    try:
        # Process one source condition and its targets at a time to bound memory.
        for source_part in parts["source"]:
            seed, budget = source_part["seed"], source_part["budget"]
            target_seed = cfg["paired_target_seeds"][cfg["source_seeds"].index(seed)]
            tr, va = source_part["fit_ids"], source_part["validation_ids"]
            for name in cfg["models"]:
                source_dir = output / f"source-{budget}-{seed}-{name}"
                if args.phase == "profile" and (
                    seed != 510 or budget != 2869 or name != "lora_chemistry"
                ):
                    continue
                check_cap()
                neural = name.endswith("chemistry")
                if neural:
                    model = ASOPredictor(
                        CHECKPOINT,
                        output / "token-cache",
                        seed,
                        name.startswith("lora"),
                    )
                    if (source_dir / "receipt.json").exists():
                        source_best = torch.load(
                            source_dir / "best.pt", weights_only=False
                        )
                        model.head = ChemistryHead(
                            source_best["context"].transform(frame.loc[tr[:1]]).shape[1]
                        )
                        model.restore(source_best)
                    else:
                        neural_fit(model, source_dir, tr, va)
                        source_best = model.snapshot()
                        state["completed"].append(str(source_dir))
                        persist()
                    source_three = torch.load(
                        source_dir / "epoch-3.pt", weights_only=False
                    )
                else:
                    if (source_dir / "receipt.json").exists():
                        with (source_dir / "model.pkl").open("rb") as f:
                            model = pickle.load(f)
                    else:
                        source_dir.mkdir(parents=True, exist_ok=True)
                        fit_start = time.monotonic()
                        model = HoldoutClassical(name, seed)
                        receipt = model.fit_validation(
                            frame.loc[tr],
                            fit_labels.loc[tr].to_numpy(),
                            frame.loc[va],
                            fit_labels.loc[va].to_numpy(),
                        )
                        receipt["elapsed_s"] = time.monotonic() - fit_start
                        with (source_dir / "model.pkl").open("wb") as f:
                            pickle.dump(model, f)
                        dump(source_dir / "receipt.json", receipt)
                        state["completed"].append(str(source_dir))
                        persist()
                if args.phase == "profile":
                    state["status"] = "profile_complete"
                    persist()
                    return
                for target_part in parts["target"]:
                    if target_part["seed"] != target_seed:
                        continue
                    acquired = target_part["acquired_ids"]
                    ttr, tva, test = (
                        target_part["fit_ids"],
                        target_part["validation_ids"],
                        target_part["test_ids"],
                    )
                    protocols = (
                        [
                            "source3_target3_all",
                            "sourcebest_target3_all",
                            "sourcebest_targetselected_inner",
                        ]
                        if neural
                        else ["sourcebest_offset_all", "sourcebest_offset_inner"]
                    )
                    for protocol in protocols:
                        key = (
                            f"target-{budget}-{seed}-{name}-"
                            f"{target_part['target']}-{protocol}"
                        )
                        directory = output / key
                        if (directory / "predictions.json").exists():
                            continue
                        check_cap()
                        meta = {
                            "model": name,
                            "source_budget": budget,
                            "source_seed": seed,
                            "source_fit_labels": len(tr),
                            "source_validation_labels": len(va),
                            "target_seed": target_seed,
                            "target": target_part["target"],
                            "target_budget": len(acquired),
                            "protocol": protocol,
                        }
                        if neural:
                            model.seed = target_seed
                            selected = protocol.endswith("inner")
                            chosen_source = (
                                source_three
                                if protocol.startswith("source3_")
                                else source_best
                            )
                            receipt = neural_fit(
                                model,
                                directory,
                                ttr if selected else acquired,
                                tva if selected else [],
                                chosen_source,
                                fixed=not selected,
                            )
                            prediction = model.predict(frame.loc[test])
                            meta.update(
                                target_fit_labels=receipt["n_labels"],
                                target_validation_labels=receipt["validation_labels"],
                                selected_epoch=receipt["selected_epoch"],
                            )
                        else:
                            directory.mkdir(parents=True, exist_ok=True)
                            ids = ttr if protocol.endswith("inner") else acquired
                            offset = float(
                                np.mean(
                                    fit_labels.loc[ids].to_numpy()
                                    - model.predict(frame.loc[ids])
                                )
                            )
                            prediction = model.predict(frame.loc[test]) + offset
                            receipt = {
                                "ids": ids,
                                "n_labels": len(ids),
                                "offset": offset,
                                "validation_ids": tva
                                if protocol.endswith("inner")
                                else [],
                                "validation_used_for_selection": False,
                            }
                            dump(directory / "receipt.json", receipt)
                            meta.update(
                                target_fit_labels=len(ids),
                                target_validation_labels=len(tva)
                                if protocol.endswith("inner")
                                else 0,
                            )
                        pending(directory, meta, test, prediction)
                        state["completed"].append(str(directory))
                        persist()
                del model
                if neural:
                    del source_best, source_three
                gc.collect()
        # Fit target-only controls once per acquired/inner partition, then score.
        for part in parts["target"]:
            for kind in ["ridge", "xgb"]:
                for mode in ["all", "inner"]:
                    directory = (
                        output
                        / f"target-only-{part['target']}-{part['seed']}-{kind}-{mode}"
                    )
                    if (directory / "predictions.json").exists():
                        continue
                    check_cap()
                    directory.mkdir(parents=True, exist_ok=True)
                    # Holdout model selection for inner protocol; historical CV for all.
                    model = HoldoutClassical(kind, part["seed"])
                    if mode == "inner":
                        tr, va = part["fit_ids"], part["validation_ids"]
                        receipt = model.fit_validation(
                            frame.loc[tr],
                            fit_labels.loc[tr].to_numpy(),
                            frame.loc[va],
                            fit_labels.loc[va].to_numpy(),
                        )
                    else:
                        tr, va = part["acquired_ids"], []
                        model.fit(frame.loc[tr], fit_labels.loc[tr].to_numpy())
                        receipt = {
                            "ids": tr,
                            "n_labels": len(tr),
                            "choice": model.choice,
                            "cv_scores": model.cv_scores,
                        }
                    dump(directory / "receipt.json", receipt)
                    pending(
                        directory,
                        {
                            "model": f"target_only_{kind}",
                            "target": part["target"],
                            "target_seed": part["seed"],
                            "source_budget": 0,
                            "protocol": f"target_only_{mode}",
                            "target_budget": len(part["acquired_ids"]),
                            "target_fit_labels": len(tr),
                            "target_validation_labels": len(va),
                        },
                        part["test_ids"],
                        model.predict(frame.loc[part["test_ids"]]),
                    )
                    state["completed"].append(str(directory))
                    persist()
        # Reopen only development test outcomes after all training decisions finish.
        test_ids = sorted({i for p in parts["target"] for i in p["test_ids"]})
        scored = read_label_subset(cohort_path, test_ids)
        rows = []
        for path in sorted(output.glob("target-*/predictions.json")):
            prediction = json.loads(path.read_text())
            rows.append(
                prediction["metadata"]
                | {
                    "metrics": metrics(
                        scored.loc[prediction["test_ids"]].to_numpy(),
                        np.array(prediction["predictions"]),
                    )
                }
            )
        dump(
            output / "report.json",
            {
                "rows": rows,
                "reserved_targets_scored": False,
                "config": cfg,
                "n_completed_fits": len(state["completed"]),
            },
        )
        state["status"] = "complete"
        persist()
        print("COMPLETE", len(rows), "test-score records", flush=True)
    except Exception as error:
        state["status"] = "failed"
        state["failures"].append({"error": repr(error), "active": state.get("active")})
        persist()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/atlas-rnafm/scaling-v1")
    )
    parser.add_argument("--phase", choices=["prepare", "profile", "run"], default="run")
    run(parser.parse_args())
