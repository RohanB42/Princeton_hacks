"""Evaluation-only DGAT2 replay with metadata recovered from pinned ASOptimizer."""

import argparse
import json
from pathlib import Path

from oligo_engine.robustness.dgat2 import run_dgat2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/robustness/dgat2-transfer-v1.json")
    )
    parser.add_argument("--original-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trust-published-checkpoints", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run_dgat2(
                json.loads(args.config.read_text()),
                args.original_source,
                args.output,
                args.trust_published_checkpoints,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
