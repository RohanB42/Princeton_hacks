"""Explicit actual-checkpoint and synthetic fixtures. No implicit fitting."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from oligo_engine.provenance import identity
from oligo_engine.reward.portable import PortableEfficacy
from oligo_engine.reward.scoring import AssayProfile

from .contracts import Campaign, Design, Pattern, Profile, Target
from .scoring import FrozenRegistry, Head, HeadManifest, Prediction


def fixture(
    seed: int = 0, requests: int = 12, partition: str = "development"
) -> tuple[Campaign, FrozenRegistry]:
    """Multi-pattern/length construction exercise, never scientific support."""
    import random

    rng = random.Random(seed)
    patterns = tuple(
        Pattern(
            f"fixture-{length}-{sugar}",
            (sugar,) * 2 + ("DNA",) * (length - 4) + (sugar,) * 2,
            ("PS",) * (length - 1),
            (True,) * length,
            2,
            2,
            evidence="synthetic construction fixture, not measured support",
        )
        for length in (8, 10)
        for sugar in ("MOE", "cEt")
    )
    profile = Profile("synthetic-molecular-v1", patterns, "fixture")
    target = Target(
        f"synthetic-{seed}",
        f"synthetic-{seed}.1",
        "".join(rng.choice("ACGT") for _ in range(32)),
        "synthetic",
        "generated fixture",
        ((0, 32),),
    )
    campaign = Campaign(
        f"fixture-{seed}",
        target,
        profile,
        requests,
        requests * 20,
        ((0, patterns[0].name, "none"),),
        partition,
    )
    scope = tuple(p.structure_id for p in patterns)
    efficacy = HeadManifest(
        "fixture-efficacy",
        "synthetic_activity",
        "fixture units",
        "objective",
        "higher",
        (("assay", "synthetic efficacy"),),
        scope,
        ("none",),
        "fixture-v1",
        "fixture-sequence-chemistry-v1",
        (),
        reference=tuple(i / 100 for i in range(101)),
        evidence="synthetic",
    )
    risk = HeadManifest(
        "fixture-risk",
        "synthetic_risk",
        "fixture units",
        "required_screen",
        "lower",
        (("assay", "synthetic risk"),),
        scope,
        ("none",),
        "fixture-risk-v1",
        "fixture-risk-v1",
        (),
        upper=0.7,
        evidence="synthetic",
        property_kind="risk",
    )

    def activity(d: Design, context: tuple) -> Prediction:
        # Repeated motif plus chemistry interaction: no site-index oracle.
        seq = d.sequence
        motif = sum(a == b for a, b in zip(seq, "GACTGACTGA")) / len(seq)
        interaction = 0.15 if d.pattern.endswith("cEt") and seq[0] == "G" else 0
        return Prediction(min(1.0, motif + interaction))

    def safety(d: Design, context: tuple) -> Prediction:
        return Prediction(d.sequence.count("G") / len(d.sequence))

    return campaign, FrozenRegistry(
        profile, (Head(efficacy, activity), Head(risk, safety))
    )


def portable_bundle(path: Path, expected_hash: str) -> tuple[Profile, FrozenRegistry]:
    model = PortableEfficacy(path, expected_hash)
    p = Pattern(
        "moe-20-5-10-5-full-ps-m5c",
        ("MOE",) * 5 + ("DNA",) * 10 + ("MOE",) * 5,
        ("PS",) * 19,
        (True,) * 20,
        5,
        5,
        evidence="supported-aso-v1 exact-profile source-only efficacy anchor",
    )
    profile = Profile("supported-aso-efficacy-ablation-v1", (p,), "efficacy_ablation")
    context = tuple(sorted((k, str(v)) for k, v in model.context().items()))
    manifest = HeadManifest(
        "supported-aso-ridge-v1",
        "atlas_inhibition",
        "inhibition percentage points",
        "objective",
        "higher",
        context,
        (p.structure_id,),
        ("none",),
        expected_hash,
        "ACGT-position-20-v1",
        tuple(model.bundle["training_ids"]),
        model.reference,
        evidence="docs/supported-aso-results-2026-11-14.md; safety unknown",
        provenance="measured",
        diagnostics=("nearest_training_hamming",),
    )

    def predict(d: Design, values: tuple) -> Prediction:
        if values != context:
            raise ValueError("Portable assay changed")
        raw = model.predict_helm(d.helm, AssayProfile(**model.context()))
        distance = min(
            sum(a != b for a, b in zip(d.sequence, seq, strict=True))
            for seq in model.training_sequences
        )
        return Prediction(
            raw, diagnostics=(("nearest_training_hamming", float(distance)),)
        )

    # Direct/package parity on fixed inputs before this entry is admitted.
    checks = []
    for seq in ("ACGT" * 5, "G" * 20, "T" * 20):
        d = Design("parity-only", 0, p.name, "none", seq, p.helm(seq, "none"))
        direct = model.predict_helm(d.helm, model.assay)
        packaged = predict(d, context).mean
        if direct != packaged:
            raise ValueError("Portable inference parity failed")
        checks.append((d.compound_id, direct))
    manifest = replace(manifest, parity_receipt=identity(checks))
    return profile, FrozenRegistry(profile, (Head(manifest, predict),))


def inventory(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_text())
    failures, families = [], {}
    for entry in manifest["checkpoints"]:
        path = root / entry["path"]
        raw = path.read_bytes()
        if (
            len(raw) != entry["bytes"]
            or hashlib.sha256(raw).hexdigest() != entry["sha256"]
        ):
            failures.append(entry["path"])
        families[entry["family"]] = families.get(entry["family"], 0) + 1
    return {
        "checked": len(manifest["checkpoints"]),
        "failures": failures,
        "families": families,
        "full_profile_status": "blocked_pending_qualified_risk_and_chemistry",
        "integrity_is_applicability": False,
    }


def atlas_bundle(
    path: Path,
    expected_hash: str,
    profile: Profile,
    context: dict[str, str],
    evidence: str,
) -> FrozenRegistry:
    """Actual frozen Atlas Ridge; wider use is explicitly an extrapolation stress."""
    from .atlas import AtlasRidge

    model = AtlasRidge(path, expected_hash)
    if (
        profile.purpose != "efficacy_ablation"
        or profile.applicability != "extrapolation_stress"
    ):
        raise ValueError("Expanded Atlas profile lacks independent scope qualification")
    if not evidence:
        raise ValueError("Explicit scope/evidence declaration required")
    bundle = model.bundle
    if bundle.get("reference_ids") != bundle["training_ids"]:
        raise ValueError("Reference must use exact fitted training membership")
    manifest = HeadManifest(
        "atlas-existing-ridge",
        "atlas_inhibition",
        "inhibition percentage points",
        "objective",
        "higher",
        tuple(sorted((k, str(v)) for k, v in context.items())),
        tuple(p.structure_id for p in profile.patterns),
        tuple(sorted({t for p in profile.patterns for t in p.terminals})),
        expected_hash,
        "atlas-ridge-inference-v1",
        tuple(bundle["training_ids"]),
        tuple(bundle["training_prediction_reference"]),
        evidence=evidence,
        parity_receipt=identity(bundle["parity_anchors"]),
        provenance="measured",
        validation_ids=tuple(bundle["validation_ids"]),
    )
    return FrozenRegistry(profile, (Head(manifest, model),))


def attach_development_risk(
    registry: FrozenRegistry,
    profile: Profile,
    model_path: Path,
    model_hash: str,
    protocol_path: Path,
    protocol_seal: str,
) -> FrozenRegistry:
    """Qualified development screen, explicitly not a completed scientific profile."""
    from .artifacts import verify
    from .chemical_model import ChemicalRegressor
    from .contracts import campaign_from_dict

    protocol = json.loads(protocol_path.read_text())
    verify(protocol, protocol_seal)
    model = ChemicalRegressor(model_path, model_hash)
    b = model.bundle
    qualification = b["qualification"]
    original = campaign_from_dict(protocol["config"]["campaigns"][0]).profile
    if (
        profile.purpose != "multi_endpoint_diagnostic"
        or profile.patterns != original.patterns
        or qualification["status"] != "development_qualified"
        or qualification["protocol_seal"] != protocol_seal
    ):
        raise ValueError("Risk qualification does not cover this diagnostic profile")
    for field, part in (
        ("training_ids", "fit"),
        ("validation_ids", "development"),
        ("calibration_ids", "calibration"),
    ):
        allowed = set(protocol["partitions"][part]) - set(
            qualification["missing_outcome_ids"]
        )
        if set(b[field]) != allowed:
            raise ValueError("Risk membership differs from its locked protocol")
    manifest = HeadManifest(
        "mouse-acute-fob-development",
        "mouse_acute_fob_0_7",
        "FOB score 0–7",
        "required_screen",
        "lower",
        tuple(sorted((k, str(v)) for k, v in b["context"].items())),
        tuple(p.structure_id for p in profile.patterns),
        tuple(sorted({t for p in profile.patterns for t in p.terminals})),
        model_hash,
        "positional-chemical-tracks-64-v1",
        tuple(b["training_ids"]),
        lower=0,
        upper=qualification["upper"],
        evidence=(
            "Grouped development screening only; acute mouse endpoint; "
            "final assessment sealed; relative bound is not a safety threshold"
        ),
        parity_receipt=identity(b["parity"]),
        provenance="measured",
        validation_ids=tuple(b["validation_ids"]),
        calibration_ids=tuple(b["calibration_ids"]),
        property_kind="risk",
    )
    return FrozenRegistry(profile, registry.heads + (Head(manifest, model),))
