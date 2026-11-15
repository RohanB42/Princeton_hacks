"""Prepare or run a versioned candidate-pool, three-layer PPO diagnostic."""

import argparse
import json
import tomllib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "run", "plot"))
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/experimental_rl/atlas_600_3layer.toml"),
    )
    parser.add_argument("--atlas", type=Path, default=Path("data/aso_atlas_2"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.stage == "plot":
        from oligo_engine.experimental_rl.report import figures

        figures(args.output)
        return
    from oligo_engine.experimental_rl.cohort import Atlas, CampaignCapacityError
    from oligo_engine.experimental_rl.study import prepare_study, run_study

    config = tomllib.loads(args.config.read_text())
    try:
        if args.stage == "prepare":
            manifest = prepare_study(Atlas(args.atlas), config, args.output)
            print(json.dumps(manifest["counts"], indent=2))
        else:
            report = run_study(Atlas(args.atlas), config, args.output)
            print(json.dumps(report["summary"], indent=2))
    except CampaignCapacityError as error:
        receipt = error.receipt | {"config": config}
        path = args.output
        if args.stage == "run":
            path.mkdir(exist_ok=False)
            path = path / "preflight-failure.json"
        with path.open("x") as stream:
            json.dump(receipt, stream, indent=2, allow_nan=False)
        print(json.dumps(receipt, indent=2))
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
