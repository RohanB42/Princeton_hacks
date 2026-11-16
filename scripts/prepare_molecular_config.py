"""Create explicit fixture or cached-transcript real diagnostic configurations."""

import argparse
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

from oligo_engine.molecular_design.artifacts import write_new
from oligo_engine.molecular_design.bundles import fixture, portable_bundle
from oligo_engine.molecular_design.contracts import Campaign, Pattern, Profile, Target


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--kind", choices=("fixture", "portable", "atlas-stress"), required=True
    )
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--atlas-export", type=Path)
    p.add_argument("--metadata-audit", type=Path)
    p.add_argument("--risk-qualification", type=Path)
    p.add_argument("--transcripts", type=Path, default=Path("artifacts/transcripts"))
    args = p.parse_args()
    if args.kind == "fixture":
        campaigns = [
            fixture(
                1000 + i,
                requests=12,
                partition="training" if i < 4 else "validation" if i < 6 else "final",
            )[0]
            for i in range(11)
        ]
        bundle = {"kind": "fixture"}
    else:
        if args.kind == "portable":
            path = Path("model_checkpoints/supported-aso-v1/efficacy.json")
            sha = "44f975ae47c1a073ec52bde1e3403baa21de8a1b0b733e4bcac1a9b236252a84"
            profile, _ = portable_bundle(path, sha)
            bundle = {"kind": "portable_efficacy", "path": str(path), "sha256": sha}
        else:
            if args.atlas_export is None or args.metadata_audit is None:
                raise ValueError(
                    "Atlas stress requires actual export and metadata audit"
                )
            audit = json.loads(args.metadata_audit.read_text())
            patterns = []
            # Frozen metadata-only rule: two largest shared structures at each length.
            for length in (18, 20):
                candidates = [
                    v
                    for v in audit["shared_efficacy_neuro_structural_patterns"]
                    if v["length"] == length
                    and v["terminal"] == "none"
                    and set(v["sugars"]) <= {"DNA", "MOE"}
                ]
                for index, value in enumerate(candidates[:2]):
                    sugars = tuple(value["sugars"])
                    wing5 = sugars.index("DNA")
                    wing3 = sugars[::-1].index("DNA")
                    patterns.append(
                        Pattern(
                            f"atlas-stress-{length}-{index}",
                            sugars,
                            tuple(value["links"][:-1]),
                            (True,) * length,
                            wing5,
                            wing3,
                            evidence=(
                                "metadata structural overlap only; methylation "
                                "and prediction support unvalidated"
                            ),
                        )
                    )
            profile = Profile(
                "atlas-multi-chemistry-stress-v1",
                tuple(patterns),
                "efficacy_ablation",
                applicability="extrapolation_stress",
            )
            bundle = {
                "kind": "atlas_ridge",
                "path": str(args.atlas_export),
                "sha256": hashlib.sha256(args.atlas_export.read_bytes()).hexdigest(),
                "context": {
                    "cell_line": "HepG2",
                    "cell_line_species": "human",
                    "transfection_method": "Electroporation",
                    "dosage_nm": "4500.0",
                    "treatment_period_hrs": "24.0",
                },
                "evidence": (
                    "Actual source Ridge; expanded chemistry stress test. Risk unknown."
                ),
            }
        campaigns = []
        for gene, partition in (
            ("DGAT2", "training"),
            ("CFB", "validation"),
            ("FGFR4", "development"),
        ):
            raw = json.loads(
                (args.transcripts / f"homo_sapiens.{gene}.json").read_text()
            )
            sequence = raw["sequence"].upper().replace("U", "T")
            midpoint = len(sequence) // 2
            target = Target(
                gene,
                raw["transcript_id"],
                sequence,
                raw["species"],
                raw["source"],
                ((midpoint, min(len(sequence), midpoint + 48)),),
            )
            first = profile.patterns[0]
            campaigns.append(
                Campaign(
                    f"{gene}-{args.kind}-development",
                    target,
                    profile,
                    8,
                    160,
                    ((midpoint, first.name, "none"),),
                    partition,
                )
            )
    if args.risk_qualification is not None:
        if args.kind != "atlas-stress":
            raise ValueError(
                "Development risk attachment requires Atlas stress profile"
            )
        from oligo_engine.molecular_design.artifacts import verify
        from oligo_engine.molecular_design.bundles import (
            atlas_bundle,
            attach_development_risk,
        )

        directory = args.risk_qualification
        protocol = json.loads((directory / "protocol.json").read_text())
        verify(protocol)
        model = directory / "model.json"
        profile = replace(
            campaigns[0].profile,
            name="atlas-multi-endpoint-diagnostic-v1",
            purpose="multi_endpoint_diagnostic",
        )
        digest = hashlib.sha256(model.read_bytes()).hexdigest()
        base = atlas_bundle(
            args.atlas_export,
            bundle["sha256"],
            campaigns[0].profile,
            bundle["context"],
            bundle["evidence"],
        )
        attach_development_risk(
            base, profile, model, digest, directory / "protocol.json", protocol["seal"]
        )
        campaigns = [replace(c, profile=profile) for c in campaigns]
        bundle["kind"] = "atlas_ridge_development_risk"
        bundle["risk"] = {
            "path": str(model),
            "sha256": digest,
            "protocol_path": str(directory / "protocol.json"),
            "protocol_seal": protocol["seal"],
        }
        bundle["evidence"] = (
            "Efficacy extrapolation with grouped development mouse acute-risk screen; "
            "full scope and independent evidence blocked"
        )
    config = {
        "schema": "molecular-study-v1",
        "bundle": bundle,
        "campaigns": [asdict(c) for c in campaigns],
        "seeds": [700, 701, 702, 703, 704],
        "methods": ["initial", "random", "greedy", "genetic", "sweep"],
        "panel_size": 10,
        "training": {
            "decoder": "transactional-v2",
            "seed": 700,
            "total_tokens": 2048,
            "rollout_tokens": 256,
            "batch_size": 64,
            "epochs": 4,
            "validation_interval": 1024,
        },
        "qualification": "Synthetic engineering"
        if args.kind == "fixture"
        else (
            "Previously used targets; development diagnostic, "
            "not independent confirmation"
        ),
    }
    write_new(args.output, config)
    print(args.output)


if __name__ == "__main__":
    main()
