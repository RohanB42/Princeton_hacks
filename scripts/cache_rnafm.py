"""Verify and cache actual RNA-FM embeddings with timing and provenance."""

import argparse
import json
import resource
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from oligo_engine.data.catalog import Catalog
from oligo_engine.representations.rnafm import FrozenRNAFM


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--random-seed", type=int)
    args = parser.parse_args()
    if args.output.exists() or args.limit < 1:
        parser.error("Use a new output directory and positive limit")
    torch.set_num_threads(2)
    loaded = Catalog().load("Huesken")
    records = loaded.dataset.observations[: args.limit]
    start = perf_counter()
    if args.random_seed is None:
        representation = FrozenRNAFM(args.checkpoint, args.device, args.cache)
    else:
        representation = FrozenRNAFM.random_initialized(
            args.checkpoint, args.random_seed, args.device, args.cache
        )
    load_seconds = perf_counter() - start
    start = perf_counter()
    vectors = representation.encode(records)
    encode_seconds = perf_counter() - start
    start = perf_counter()
    repeated = representation.encode(records)
    cache_seconds = perf_counter() - start
    if not np.array_equal(vectors, repeated):
        raise ValueError("Cache hit representations differ from original extraction")
    args.output.mkdir(parents=True)
    np.save(args.output / "embeddings.npy", vectors, allow_pickle=False)
    result = {
        "status": "complete",
        "config": representation.config,
        "dataset_sha256": loaded.dataset.content_sha256,
        "sample_ids": [row.sample_id for row in records],
        "shape": list(vectors.shape),
        "load_seconds": load_seconds,
        "encode_seconds": encode_seconds,
        "cache_seconds": cache_seconds,
        "cache_exact_equal": True,
        "peak_rss_native_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "rss_units": "bytes on macOS; KiB on Linux",
        "torch_threads": 2,
        "trainable_parameters": sum(
            p.numel() for p in representation.model.parameters() if p.requires_grad
        ),
        "total_parameters": sum(p.numel() for p in representation.model.parameters()),
        "measurement_labels_accessed": False,
    }
    (args.output / "profile.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "config"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
