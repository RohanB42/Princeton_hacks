"""Fixed-predictor acquisition geometry; hidden labels restricted to pool oracle."""

import argparse
import gc
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler, normalize

from oligo_engine.atlas.acquisition import select_batch
from oligo_engine.atlas.baselines import Classical, metrics
from oligo_engine.atlas.chemistry import parse_helm
from oligo_engine.models.aso_rnafm import ASOPredictor, ChemistryHead

CHECKPOINT = Path(
    "/private/tmp/oligoal-rnafm-20261114/artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth"
)


class PoolOracle:
    def __init__(self, labels: dict):
        self._labels = labels
        self.revealed = {}

    def reveal(self, ids: list[str]) -> None:
        if (
            len(set(ids)) != len(ids)
            or set(ids) & self.revealed.keys()
            or not set(ids) <= self._labels.keys()
        ):
            raise ValueError("Invalid or duplicate reveal")
        self.revealed.update({i: self._labels[i] for i in ids})

    def labels(self, ids: list[str]) -> np.ndarray:
        if not set(ids) <= self.revealed.keys():
            raise ValueError("Unrevealed labels requested")
        return np.array([self.revealed[i] for i in ids])


def fm_geometry(frame, source, adapt):
    name = "lora_chemistry" if adapt else "frozen_chemistry"
    path = Path("artifacts/atlas-rnafm/fm-development-v1") / f"{name}-source.pt"
    with torch.serialization.safe_globals([torch.torch_version.TorchVersion]):
        saved = torch.load(path, weights_only=True)
    if saved["source_ids"] != source.source_row_id.tolist():
        raise ValueError("Source label set mismatch")
    model = ASOPredictor(
        CHECKPOINT, Path("artifacts/atlas-rnafm/token-cache"), 510, adapt
    )
    model.context.fit(source)
    model.head = ChemistryHead(model.context.transform(source.iloc[:1]).shape[1])
    model.head.load_state_dict(saved["head"])
    with torch.no_grad():
        for key, value in model.encoder.backbone.named_parameters():
            if value.requires_grad:
                value.copy_(saved["adapters"][key])
    model.mean = saved["mean"]
    model.scale = saved["scale"]
    model.source_ids = saved["source_ids"]
    lengths = [len(parse_helm(h).bases) for h in frame["HELM Annotation"]]
    vectors = []

    def capture(module, inputs, output):
        start = len(vectors)
        vectors.extend(
            [
                z[: lengths[start + i]].mean(0).detach().numpy()
                for i, z in enumerate(output)
            ]
        )

    hook = model.head.fusion.register_forward_hook(capture)
    model.predict(frame)
    hook.remove()
    vectors = np.stack(vectors)
    del model
    gc.collect()
    return vectors, hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    torch.set_num_threads(1)
    cfg = json.loads(Path("configs/atlas/acquisition-development-v1.json").read_text())
    manifest = json.loads(
        Path("artifacts/atlas-rnafm/preparation-v1/manifests.json").read_text()
    )
    frame = pd.read_parquet(
        "artifacts/atlas-rnafm/preparation-v1/cohort.parquet"
    ).set_index("source_row_id", drop=False)
    labels = frame.pop("Inhibition_pct")
    source_ids = (
        np.random.default_rng(cfg["source_seed"])
        .permutation(manifest["source_train_ids"])[: cfg["source_labels"]]
        .tolist()
    )
    campaigns = [c for c in manifest["campaigns"] if c["role"] == "development"]
    source = frame.loc[source_ids]
    prior = Classical("ridge", 510).fit(source, labels.loc[source_ids].to_numpy())
    pool_ids = [i for c in campaigns for i in c["pool_ids"]]
    geometry_ids = source_ids + pool_ids
    assert len(set(geometry_ids)) == len(geometry_ids)
    assert not set(geometry_ids) & {i for c in campaigns for i in c["test_ids"]}
    geometry_frame = frame.loc[geometry_ids]
    classical = prior.features.transform(geometry_frame)
    projection = (
        np.random.default_rng(cfg["projection_seed"]).normal(
            size=(classical.shape[1], 64)
        )
        / 8
    )
    geometries = {"classical": np.asarray(classical @ projection)}
    checkpoint_hashes = {}
    for name, adapt in [("frozen", False), ("lora", True)]:
        geometries[name], checkpoint_hashes[name] = fm_geometry(
            geometry_frame, source, adapt
        )
        print("geometry complete", name, flush=True)
    for name, x in geometries.items():
        scaler = StandardScaler().fit(x[: len(source_ids)])
        geometries[name] = normalize(scaler.transform(x))
    lookup = {sid: i for i, sid in enumerate(geometry_ids)}
    t = time.monotonic()
    pending = []
    ledgers = []
    refs = []
    for campaign in campaigns:
        pool = campaign["pool_ids"]
        test = campaign["test_ids"]
        testframe = frame.loc[test]
        source_prediction = prior.predict(testframe)
        for seed in cfg["seeds"]:
            initial = (
                np.random.default_rng(seed).permutation(pool)[: cfg["initial"]].tolist()
            )
            for policy in cfg["policies"]:
                oracle = PoolOracle(labels.loc[pool].to_dict())
                oracle.reveal(initial)
                acquired = list(initial)
                batches = []
                rng = np.random.default_rng(seed + 10000)
                while True:
                    if time.monotonic() - t > cfg["wall_cap_seconds"]:
                        raise TimeoutError("Frozen cap reached")
                    residual = Classical("ridge", seed).fit(
                        frame.loc[acquired],
                        oracle.labels(acquired) - prior.predict(frame.loc[acquired]),
                    )
                    pred = source_prediction + residual.predict(testframe)
                    pending.append(
                        (
                            {
                                "target": campaign["target"],
                                "seed": seed,
                                "policy": policy,
                                "budget": len(acquired),
                            },
                            test,
                            pred,
                        )
                    )
                    if len(acquired) == cfg["max_labels"]:
                        break
                    kind = "random" if policy == "random" else policy.split("_")[0]
                    space = "classical" if policy == "random" else policy.split("_")[1]
                    allowed = [lookup[i] for i in pool if i not in oracle.revealed]
                    selected = select_batch(
                        kind,
                        geometries[space],
                        [lookup[i] for i in acquired],
                        allowed,
                        cfg["batch"],
                        rng,
                    )
                    batch = [geometry_ids[i] for i in selected]
                    oracle.reveal(batch)
                    acquired.extend(batch)
                    batches.append(batch)
                ledgers.append(
                    {
                        "target": campaign["target"],
                        "seed": seed,
                        "policy": policy,
                        "initial_ids": initial,
                        "batches": batches,
                        "source_ids": source_ids,
                    }
                )
                print("campaign complete", campaign["target"], seed, policy, flush=True)
        # Separate full-pool reference is reporting only, never exposed to acquisition.
        reference = Classical("ridge", 0).fit(
            frame.loc[pool],
            labels.loc[pool].to_numpy() - prior.predict(frame.loc[pool]),
        )
        refs.append(
            (campaign["target"], test, source_prediction + reference.predict(testframe))
        )
    rows = [
        meta | {"metrics": metrics(labels.loc[ids].to_numpy(), pred)}
        for meta, ids, pred in pending
    ]
    references = {
        target: metrics(labels.loc[ids].to_numpy(), pred) for target, ids, pred in refs
    }
    report = {
        "config": cfg,
        "rows": rows,
        "references": references,
        "ledgers": ledgers,
        "source_checkpoint_hashes": checkpoint_hashes,
        "elapsed_selection_s": time.monotonic() - t,
        "reserved_targets_scored": False,
        "n_campaigns": len(ledgers),
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("complete", len(rows), "checkpoints", flush=True)


if __name__ == "__main__":
    main()
