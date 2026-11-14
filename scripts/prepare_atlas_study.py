"""Build audited cohort and label-blind source/target manifests."""

import argparse
import json
from pathlib import Path

from oligo_engine.atlas.data import prepare
from oligo_engine.atlas.splits import build_manifests


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    frame, audit = prepare(Path("data/aso_atlas_2"))
    manifest = build_manifests(frame)
    frame.drop(columns="chemistry").to_parquet(
        args.output / "cohort.parquet", index=False
    )
    (args.output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (args.output / "manifests.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "steps": audit["steps"],
                "source_train": len(manifest["source_train_ids"]),
                "source_validation": len(manifest["source_validation_ids"]),
                "campaigns": [
                    {k: v for k, v in c.items() if k not in {"pool_ids", "test_ids"}}
                    | {"pool": len(c["pool_ids"]), "test": len(c["test_ids"])}
                    for c in manifest["campaigns"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
