"""Bounded real-weight efficacy adaptation proof, not an active-learning claim."""

import argparse
import hashlib
import json
import resource
import time
from dataclasses import asdict
from pathlib import Path
from random import Random

import torch

from oligo_engine.data.catalog import Catalog
from oligo_engine.huesken_learning import official_split
from oligo_engine.models.rnafm_lora import RNAFMLoRAPredictor
from oligo_engine.representations.rnafm import FrozenRNAFM, duplex_sequences


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=300)
    parser.add_argument("--labels", type=int, default=50)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier attempts")
    torch.set_num_threads(1)
    if args.device == "mps" and not torch.backends.mps.is_available():
        parser.error("MPS is unavailable")
    args.output.mkdir(parents=True)
    receipt = {
        "status": "running",
        "purpose": "bounded_measured_adaptation_proof",
        "config": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
        "source_sha256": {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ("src/oligo_engine/models/rnafm_lora.py", __file__)
        },
        "caveats": [
            "Single-seed diagnostic; no label efficiency or therapeutic claim.",
            "Fixed-epoch training; no test-derived model selection.",
            "Full official held-out split scored after both training jobs.",
        ],
    }

    def save():
        (args.output / "profile.json").write_text(
            json.dumps(receipt, indent=2, allow_nan=False) + "\n"
        )

    save()
    try:
        loaded = Catalog().load("Huesken")
        split = official_split(loaded.dataset, args.seed, args.checkout.resolve())
        if args.labels > len(split.train_ids):
            raise ValueError("Requested labels exceed eligible pool")
        initial = tuple(Random(args.seed).sample(list(split.train_ids), args.labels))
        oracle, evaluator, _ = loaded.capabilities(split)
        labels = oracle.reveal(initial)
        records = {row.sample_id: row for row in loaded.dataset.observations}
        train = tuple(records[i] for i in initial)
        test_ids = split.test_ids
        test = tuple(records[i] for i in test_ids)
        receipt.update(
            split=asdict(split),
            initial_ids=initial,
            evaluation_ids=test_ids,
            dataset=loaded.public_metadata(),
            results={},
        )
        probe = FrozenRNAFM(args.checkpoint, device=args.device)
        base_identity = probe.config
        # Normalise only identity key; all source provenance is retained.
        if "checkpoint_sha256" not in base_identity:
            raise ValueError("Encoder config must expose verified checkpoint SHA256")
        del probe

        def factory():
            encoder = FrozenRNAFM(args.checkpoint, device=args.device)
            return encoder.model, encoder.alphabet

        pending = {}
        for name, adapt in (("frozen_linear_head", False), ("lora_linear_head", True)):
            started = time.perf_counter()
            model = RNAFMLoRAPredictor(
                factory,
                duplex_sequences,
                base_identity,
                seed=args.seed,
                rank=4,
                alpha=8,
                epochs=args.epochs,
                batch_size=args.batch_size,
                learning_rate=1e-3,
                device=args.device,
                adapt_backbone=adapt,
            )
            model.fit(train, labels)
            fit_seconds = time.perf_counter() - started
            predicted = model.predict(test)
            pending[name] = [p.mean for p in predicted]
            adapter = args.output / f"{name}.pt"
            receipt["results"][name] = {
                "fit_seconds": fit_seconds,
                "total_seconds": time.perf_counter() - started,
                "fit_audit": model.fit_audit,
                "config": model.config,
                "adapter_sha256": model.save_adapter(adapter),
                "peak_process_rss_bytes": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
            }
            save()
            del model
        # Both fixed training jobs finish before held-out labels are scored.
        from oligo_engine.contracts import Prediction

        for name, predictions in pending.items():
            receipt["results"][name]["metrics"] = asdict(
                evaluator.score(tuple(Prediction(p) for p in predictions))
            )
        receipt["status"] = "complete"
    except Exception as error:
        receipt.update(status="failed", error=f"{type(error).__name__}: {error}")
        save()
        raise
    save()


if __name__ == "__main__":
    main()
