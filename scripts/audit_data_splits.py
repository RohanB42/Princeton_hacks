"""Save label-free integrity and local split audits without training models."""

import argparse
import json
from pathlib import Path

from oligo_engine.data.audit import audit_split
from oligo_engine.data.catalog import DEFAULT_DATA_ROOT, Catalog
from oligo_engine.data.splits import UnsupportedSplit, make_split


def build_report(catalog: Catalog, seeds: tuple[int, ...]) -> dict:
    validation = catalog.validate_all()
    report = {
        "source_revision": catalog.manifest["upstream_revision"],
        "source_manifest": "data/oligogym/manifest.json",
        "seeds": list(seeds),
        "split_test_size": 0.2,
        "validation": validation,
        "split_audits": [],
    }
    for entry in catalog.entries:
        dataset = catalog.load(entry["key"]).dataset
        for strategy in ("sequence_group", "target"):
            for seed in seeds:
                record = {
                    "dataset": entry["key"],
                    "source_name": entry["name"],
                    "source_sha256": dataset.content_sha256,
                    "strategy": strategy,
                    "seed": seed,
                }
                try:
                    split = make_split(dataset, strategy, seed, test_size=0.2)
                    record.update(
                        status="supported",
                        split_parameters=dict(split.parameters),
                        audit=audit_split(dataset, split),
                    )
                except UnsupportedSplit as error:
                    record.update(status="unsupported", reason=str(error))
                report["split_audits"].append(record)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(5)))
    args = parser.parse_args()
    if not args.seeds or len(set(args.seeds)) != len(args.seeds):
        parser.error("Seeds must be nonempty and distinct")
    report = build_report(Catalog(args.data_root), tuple(args.seeds))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        json.dump(report, file, indent=2, allow_nan=False)
        file.write("\n")
    print(
        f"Saved {len(report['split_audits'])} audits to {args.output} "
        f"from {report['validation']['total_rows']} source rows"
    )


if __name__ == "__main__":
    main()
