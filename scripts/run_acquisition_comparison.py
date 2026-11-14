"""Run the frozen four-arm Huesken comparison (docs/acquisition-comparison.md).

Official OligoGym ``nucleobase`` split per seed; unchanged ``run_campaign``. Seeds are
processed in parallel worker processes (one seed per task, all arms and predictors in
sequence so the full-pool reference is shared only between matched arms). Each run is
written as soon as it finishes; failures are recorded, never dropped. Requires the
pinned upstream environment.

    PYTHONPATH=src python scripts/run_acquisition_comparison.py \
        --output artifacts/acquisition-huesken --workers 5
"""

import argparse
import json
import multiprocessing as mp
import os
import traceback
from dataclasses import asdict
from pathlib import Path

ARMS = ("random", "uncertainty", "diversity", "uncertainty_then_diversity")
PREDICTORS = ("gp", "rf")
SEEDS = tuple(range(100, 110))
INITIAL, BATCH, MAXIMUM = 50, 50, 1000


def make_policy(name: str, featurizer):
    from oligo_engine.acquisition.diversity import (
        DiversityAcquisition,
        UncertaintyDiversityAcquisition,
    )
    from oligo_engine.acquisition.random import RandomAcquisition
    from oligo_engine.acquisition.uncertainty import UncertaintyAcquisition

    return {
        "random": RandomAcquisition,
        "uncertainty": UncertaintyAcquisition,
        "diversity": lambda: DiversityAcquisition(featurizer),
        "uncertainty_then_diversity": lambda: UncertaintyDiversityAcquisition(
            featurizer, pool_multiplier=4
        ),
    }[name]()


def run_seed(task):
    seed, train_ids, test_ids, output = task
    from oligo_engine.contracts import RunConfig, SplitManifest
    from oligo_engine.data.catalog import Catalog
    from oligo_engine.evaluation.runner import run_campaign
    from oligo_engine.features.upstream import OneHotBaseFeaturizer
    from oligo_engine.models.baseline import OneHotGaussianProcess, OneHotRandomForest

    loaded = Catalog().load("Huesken")
    split = SplitManifest(
        "nucleobase",
        seed,
        tuple(train_ids),
        tuple(test_ids),
        (
            ("n_clusters", "8"),
            ("kmer", "True"),
            ("kmer_max", "3"),
            ("test_size", "0.2"),
        ),
    )
    config = RunConfig(seed, INITIAL, BATCH, MAXIMUM, 0.60, "diagnostic")
    featurizer = OneHotBaseFeaturizer()
    factories = {
        "gp": lambda: OneHotGaussianProcess(seed),
        "rf": lambda: OneHotRandomForest(seed, n_jobs=2),
    }
    done = []
    for predictor in PREDICTORS:
        cache: dict = {}
        for arm in ARMS:
            path = output / predictor / arm / f"run-seed-{seed}.json"
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                oracle, evaluator, reference = loaded.capabilities(split)
                run = run_campaign(
                    loaded.dataset,
                    split,
                    oracle,
                    evaluator,
                    factories[predictor],
                    make_policy(arm, featurizer),
                    config,
                    reference,
                    cache,
                )
                path.write_text(
                    json.dumps(asdict(run), indent=2, allow_nan=False) + "\n"
                )
                done.append((predictor, arm, "ok"))
            except Exception:
                path.with_suffix(".FAILED.txt").write_text(traceback.format_exc())
                done.append((predictor, arm, "FAILED"))
            print(seed, predictor, arm, done[-1][2], flush=True)
    return seed, done


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()) and not args.resume:
        parser.error("Output exists; pass --resume to add missing runs only")

    from _huesken import load, split

    data, observations, _labels = load()
    del _labels
    tasks, sizes = [], {}
    for seed in SEEDS:
        train, test = split(data, seed)
        if len(train) < MAXIMUM:
            raise ValueError(f"seed {seed}: pool {len(train)} below {MAXIMUM}")
        sizes[seed] = {"train": len(train), "test": len(test)}
        tasks.append(
            (
                seed,
                [observations[i].sample_id for i in train],
                [observations[i].sample_id for i in test],
                args.output,
            )
        )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "protocol.json").write_text(
        json.dumps(
            {
                "doc": "docs/acquisition-comparison.md",
                "seeds": list(SEEDS),
                "arms": list(ARMS),
                "predictors": list(PREDICTORS),
                "initial": INITIAL,
                "batch": BATCH,
                "maximum": MAXIMUM,
                "split": "official nucleobase",
                "partition_sizes": sizes,
            },
            indent=2,
        )
        + "\n"
    )
    os.environ.update(OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
    with mp.get_context("spawn").Pool(args.workers) as pool:
        for seed, done in pool.imap_unordered(run_seed, tasks):
            print("seed finished", seed, done, flush=True)


if __name__ == "__main__":
    main()
