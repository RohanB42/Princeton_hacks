"""Bounded source-adaptation and development-target comparison, deferred scoring."""

import argparse
import gc
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from oligo_engine.atlas.baselines import metrics
from oligo_engine.models.aso_rnafm import ASOPredictor

CHECKPOINT = Path(
    "/private/tmp/oligoal-rnafm-20261114/artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth"
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    torch.set_num_threads(1)
    cfg = json.loads(Path("configs/atlas/development-v1.json").read_text())
    manifest = json.loads(Path(cfg["manifest"]).read_text())
    frame = pd.read_parquet(Path(cfg["manifest"]).parent / "cohort.parquet").set_index(
        "source_row_id", drop=False
    )
    labels = frame.pop("Inhibition_pct")
    source_ids = (
        np.random.default_rng(cfg["source_fm_seed"])
        .permutation(manifest["source_train_ids"])[: cfg["source_fm_budget"]]
        .tolist()
    )
    t = time.monotonic()
    receipts = []
    predictions = []
    suite = {
        "status": "running",
        "config": cfg,
        "source_ids": source_ids,
        "receipts": receipts,
        "code_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_hashes": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                Path(__file__),
                *Path("src/oligo_engine/atlas").glob("*.py"),
                Path("src/oligo_engine/models/aso_rnafm.py"),
                Path("src/oligo_engine/representations/aso_rnafm.py"),
            ]
        },
    }

    def persist():
        suite["elapsed_s"] = time.monotonic() - t
        (args.output / "suite.json").write_text(json.dumps(suite, indent=2) + "\n")

    persist()
    try:
        for adapt in [False, True]:
            name = "lora_chemistry" if adapt else "frozen_chemistry"
            model = ASOPredictor(
                CHECKPOINT,
                Path("artifacts/atlas-rnafm/token-cache"),
                cfg["source_fm_seed"],
                adapt,
            )
            receipt = model.fit(
                frame.loc[source_ids],
                labels.loc[source_ids].to_numpy(),
                epochs=cfg["source_epochs"],
            )
            source = model.snapshot()
            torch.save(
                {
                    "head": source["head"],
                    "adapters": source["adapters"],
                    "mean": source["mean"],
                    "scale": source["scale"],
                    "source_ids": source_ids,
                    "encoder": model.encoder.config,
                },
                args.output / f"{name}-source.pt",
            )
            receipts.append({"stage": "source", "model": name, **receipt})
            persist()
            print("source complete", name, receipt["elapsed_s"], flush=True)
            for campaign in manifest["campaigns"]:
                if campaign["role"] != "development":
                    continue
                assert campaign["target"] in cfg["targets"]
                test = campaign["test_ids"]
                model.restore(source)
                predictions.append(
                    (
                        {
                            "model": name,
                            "target": campaign["target"],
                            "seed": None,
                            "budget": 0,
                            "source_budget": len(source_ids),
                        },
                        test,
                        model.predict(frame.loc[test]),
                    )
                )
                for seed in cfg["target_seeds"]:
                    pool = np.random.default_rng(seed).permutation(campaign["pool_ids"])
                    for b in cfg["target_budgets"]:
                        if time.monotonic() - t > cfg["development_wall_cap_seconds"]:
                            raise TimeoutError("Frozen wall cap reached")
                        acquired = pool[:b].tolist()
                        assert not set(acquired) & set(test)
                        assert not set(source_ids) & set(test + acquired)
                        model.seed = seed
                        receipt = model.fit(
                            frame.loc[acquired],
                            labels.loc[acquired].to_numpy(),
                            epochs=cfg["target_epochs"],
                            source=source,
                        )
                        metadata = {
                            "model": name,
                            "target": campaign["target"],
                            "seed": seed,
                            "budget": b,
                            "source_budget": len(source_ids),
                            "ids": acquired,
                        }
                        predictions.append(
                            (metadata, test, model.predict(frame.loc[test]))
                        )
                        receipts.append({"stage": "target", **metadata, **receipt})
                        persist()
                        print(
                            "target complete",
                            name,
                            campaign["target"],
                            seed,
                            b,
                            flush=True,
                        )
            del model, source
            gc.collect()
        # Neither outcome nor metrics are available to any fitting decision above.
        rows = [
            meta | {"metrics": metrics(labels.loc[ids].to_numpy(), pred)}
            for meta, ids, pred in predictions
        ]
        report = {
            "config": cfg,
            "rows": rows,
            "elapsed_s": time.monotonic() - t,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "reserved_targets_scored": False,
            "source_budgets_tested": [len(source_ids)],
        }
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        suite["status"] = "complete"
        persist()
        print("complete", len(rows), report["elapsed_s"], flush=True)
    except Exception as error:
        suite["status"] = "failed"
        suite["error"] = repr(error)
        persist()
        raise


if __name__ == "__main__":
    main()
