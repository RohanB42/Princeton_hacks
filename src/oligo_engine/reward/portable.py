"""Explicit JSON Ridge inference for one evidence-supported ASO assay profile.

No unpickling, model fitting, dynamic imports, or measured-label loading occurs at
inference. Chemistry and context are fixed, so only base-position features vary.
"""

import hashlib
import json
from dataclasses import asdict
from math import isfinite
from pathlib import Path

from oligo_engine.design.aso_space import TargetContext, candidate_identity, identity
from oligo_engine.design.candidates import Candidate, build_helm
from oligo_engine.reward.chemistry import parse_helm
from oligo_engine.reward.scoring import (
    AssayProfile,
    EndpointManifest,
    EndpointPrediction,
    FrozenEndpoint,
    FrozenScorer,
)

CHEMISTRY = "ps_moe_20_gapmer"


def supported_sequence(helm: str) -> str:
    """Validate complete 20-mer chemistry, accepting only the known m5C alias."""
    parsed = parse_helm(helm.replace("[m5C]", "[5meC]"))
    sequence = parsed.natural_rna.replace("U", "T")
    if len(sequence) != 20:
        raise ValueError("This efficacy bundle requires a 20-mer")
    expected = parse_helm(build_helm(sequence, CHEMISTRY).replace("[m5C]", "[5meC]"))
    if parsed.identity != expected.identity:
        raise ValueError("Unsupported sugar/base/linkage/terminal chemistry")
    return sequence


def encode_sequence(sequence: str) -> list[float]:
    if len(sequence) != 20 or set(sequence) - set("ACGT"):
        raise ValueError("Expected 20 ACGT bases")
    return [float(base == letter) for base in sequence for letter in "ACGT"]


class PortableEfficacy:
    """Hash-verified, fitted one-hot Ridge; context is deliberately non-tunable."""

    def __init__(self, path: Path, expected_sha256: str) -> None:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("Efficacy artifact hash mismatch")
        self.artifact_hash = expected_sha256
        self.bundle = json.loads(raw)
        b = self.bundle
        if (
            b.get("schema") != "supported-aso-ridge-v1"
            or b.get("chemistry") != CHEMISTRY
        ):
            raise ValueError("Unsupported efficacy bundle schema/profile")
        self.assay = AssayProfile(**b["assay"])
        self.coefficients = tuple(b["coefficients"])
        self.intercept = b["intercept"]
        if len(self.coefficients) != 80 or not all(
            isfinite(x) for x in (*self.coefficients, self.intercept)
        ):
            raise ValueError("Invalid Ridge parameters")
        self.reference = tuple(b["training_prediction_reference"])
        if not self.reference or not all(isfinite(x) for x in self.reference):
            raise ValueError("Invalid fixed training reference")
        self.training_sequences = tuple(b["training_sequences"])
        for sequence in self.training_sequences:
            encode_sequence(sequence)
        if not self.training_sequences or not b["training_ids"] or not b["split_hash"]:
            raise ValueError("Training provenance required")

    def predict_helm(self, helm: str, assay: AssayProfile) -> float:
        if assay != self.assay:
            raise ValueError("Assay context outside frozen bundle profile")
        features = encode_sequence(supported_sequence(helm))
        return self.intercept + sum(
            x * coefficient for x, coefficient in zip(features, self.coefficients)
        )

    def __call__(
        self, candidate: Candidate, target: TargetContext, assay: AssayProfile
    ) -> EndpointPrediction:
        candidate_identity(candidate, target)
        if candidate.chemistry != CHEMISTRY:
            raise ValueError("Candidate chemistry name does not match bundle")
        value = self.predict_helm(candidate.helm, assay)
        distance = min(
            sum(a != b for a, b in zip(candidate.sequence, seq, strict=True))
            for seq in self.training_sequences
        )
        return EndpointPrediction(
            value,
            diagnostics=(("nearest_training_hamming", float(distance)),),
        )

    def scorer(self) -> FrozenScorer:
        objective = EndpointManifest(
            "atlas_inhibition",
            "supported-aso-ridge-v1",
            "inhibition percentage points",
            CHEMISTRY,
            self.artifact_hash,
            identity(self.bundle["training_ids"]),
            self.bundle["split_hash"],
            "ACGT-position-20-v1",
            self.assay,
            "objective",
            reference=self.reference,
            provenance="measured_source_only_efficacy_no_validated_safety",
        )
        missing = EndpointManifest(
            "neurotoxicity",
            "no_validated_matching_neurotox_bundle",
            "unknown",
            CHEMISTRY,
            "unavailable",
            "unavailable",
            "unavailable",
            "unavailable",
            self.assay,
            "advisory",
            provenance="unknown_not_zero_risk",
        )
        return FrozenScorer(
            (FrozenEndpoint(objective, self), FrozenEndpoint(missing, None)),
            "measured_source_only_efficacy_unvalidated_generated_candidates",
        )

    def context(self) -> dict:
        return asdict(self.assay)
