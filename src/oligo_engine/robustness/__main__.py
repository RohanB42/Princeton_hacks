"""Immutable robustness stages; only evaluate reads final outcomes."""

import argparse
import json
from pathlib import Path

from oligo_engine.robustness.pipeline import STAGES, AuditPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES + ("run",))
    parser.add_argument(
        "--config", type=Path, default=Path("configs/robustness/fixture-v1.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plots", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    try:
        pipeline = AuditPipeline(config, args.output)
    except ValueError as exc:
        if "infeasible_split" not in str(exc):
            raise
        failure = {
            "status": "infeasible_split",
            "reason": str(exc),
            "config": config,
            "outcomes_read": False,
        }
        args.output.mkdir(parents=True, exist_ok=True)
        with (args.output / "failure.json").open("x") as handle:
            json.dump(failure, handle, indent=2)
        print(json.dumps(failure))
        raise SystemExit(2) from exc
    result = pipeline.run() if args.stage == "run" else pipeline.run_stage(args.stage)
    if args.plots:
        from oligo_engine.reporting.robustness import plot_report

        plot_report(args.output, pipeline.store.read("evaluate"))
    if args.stage in ("run", "report"):
        print(json.dumps(result, indent=2, allow_nan=False))
    else:
        print(
            json.dumps(
                {"stage": args.stage, "output": str(args.output), "status": "complete"}
            )
        )


if __name__ == "__main__":
    main()
