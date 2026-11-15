"""Static candidate/model doubles for inference tests; no search environment."""

from types import SimpleNamespace

from oligo_engine.design.candidates import tile
from oligo_engine.design.context import TargetContext
from oligo_engine.reward.scoring import (
    AssayProfile,
    EndpointManifest,
    FrozenEndpoint,
    FrozenScorer,
    ScoringSession,
)

ASSAY = AssayProfile("fixture", "fixture", "fixture", 10.0, 24.0)


def candidate_panel(chemistry="ps_moe_gapmer"):
    target = TargetContext("TEST", "TEST.1", "ACGT" * 7, "synthetic", "unit-test")
    candidates = tile(
        target.gene, target.transcript_id, target.sequence, chemistry=chemistry
    )
    return SimpleNamespace(target=target, start=1, candidate=candidates.__getitem__)


def constant_scorer():
    def manifest(endpoint, role, chemistry="ps_moe_gapmer"):
        return EndpointManifest(
            endpoint,
            f"test-{endpoint}",
            "fixture units",
            chemistry,
            "test-artifact",
            "test-training",
            "test-split",
            "constant-test-v1",
            ASSAY,
            role,
            reference=tuple(float(i) for i in range(10)),
        )

    return FrozenScorer(
        (
            FrozenEndpoint(manifest("potency", "objective"), lambda c, t, a: 1.0),
            FrozenEndpoint(manifest("neurotox", "advisory"), lambda c, t, a: 2.0),
            FrozenEndpoint(manifest("tlr7", "advisory", "ps_2ome_gapmer"), None),
            FrozenEndpoint(manifest("hepatic", "advisory"), None),
        ),
        "constant_unit_test_no_measured_labels",
    )


def scoring_session(panel, max_unique=10, max_requests=100):
    return ScoringSession(
        constant_scorer(), panel.target, ASSAY, max_unique, max_requests
    )
