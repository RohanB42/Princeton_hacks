"""Test identified existing frozen checkpoints with metadata-first preflight."""

import argparse
import json
from pathlib import Path

from oligo_engine.robustness.existing_study import run_existing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite", choices=("huesken", "atlas", "supported"), required=True
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/robustness/existing-predictors-v1.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trust-owner-local-artifacts", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    result = run_existing(
        args.suite, config, args.output, args.trust_owner_local_artifacts
    )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
