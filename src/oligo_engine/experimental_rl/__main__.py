"""Audit and run V1 or V2 experimental-selection replay."""

import argparse
import json
import tomllib
from pathlib import Path

from oligo_engine.experimental_rl.cohort import Atlas, prepare


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "v1", "v2", "plot", "linkage"))
    parser.add_argument(
        "--config", type=Path, default=Path("configs/experimental_rl/atlas_v1_v2.toml")
    )
    parser.add_argument("--atlas", type=Path, default=Path("data/aso_atlas_2"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--v1-report", type=Path)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text())
    atlas = Atlas(args.atlas)
    if args.stage == "prepare":
        _, manifest = prepare(atlas, config)
        with args.output.open("x") as out:
            json.dump(manifest, out, indent=2, allow_nan=False)
        print(json.dumps(manifest["counts"], indent=2))
    elif args.stage == "linkage":
        from oligo_engine.experimental_rl.linkage import linkage_audit

        result = linkage_audit(atlas)
        with args.output.open("x") as out:
            json.dump(result, out, indent=2, allow_nan=False)
        print(
            json.dumps(
                {key: count for key, count in result.items() if key != "groups"},
                indent=2,
            )
        )
    elif args.stage == "plot":
        from oligo_engine.experimental_rl.report import figures

        figures(args.output)
    else:
        from oligo_engine.experimental_rl.run import run

        result = run(atlas, config, args.output, args.stage, args.v1_report)
        print(
            json.dumps(
                {
                    "version": result["version"],
                    "episodes": result["episodes"],
                    "mean_hits": {
                        k: v["mean_hits"] for k, v in result["summary"].items()
                    },
                    "wall_seconds": result["wall_seconds"],
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
