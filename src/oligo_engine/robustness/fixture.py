"""Known distribution-shift and exploitation fixture, explicitly synthetic."""

from dataclasses import dataclass
from random import Random

from oligo_engine.design.candidates import build_helm
from oligo_engine.robustness.adapters import OutcomeCapability
from oligo_engine.robustness.contracts import AuditObservation, AuditPrediction


@dataclass(frozen=True)
class FixtureSource:
    rows: tuple[AuditObservation, ...]
    receipt: dict

    def outcomes(self, allowed: tuple[str, ...]) -> OutcomeCapability:
        mapping = {r.sample_id: r for r in self.rows}

        def read(ids: tuple[str, ...]) -> dict:
            return {i: synthetic_truth(mapping[i]) for i in ids}

        return OutcomeCapability(allowed, read)


def synthetic_truth(row: AuditObservation) -> float:
    return 30.0 + 2 * row.sequence.count("C") - (30 if "GGG" in row.sequence else 0)


def source() -> FixtureSource:
    rng = Random(810)
    rows = []
    for group in range(8):
        for index in range(40):
            prefix = "GGG" if index % 2 == 0 else "AAA"
            sequence = prefix + "".join(rng.choices("ACT", k=17))
            rows.append(
                AuditObservation(
                    f"fixture-{group}-{index:03d}",
                    build_helm(sequence, "ps_moe_20_gapmer"),
                    f"target-{group}",
                    "synthetic_potency",
                    "fixture units",
                    "synthetic-source-v1",
                    (("assay", "synthetic"),),
                    patent_id=f"synthetic-patent-{group}",
                )
            )
    return FixtureSource(
        tuple(rows),
        {
            "provenance": "synthetic_fixture_no_measured_data",
            "eligible_rows": len(rows),
            "label_values_read": False,
        },
    )


class SyntheticAuditModel:
    """Deliberately overestimates the GGG region; its truth is a separate capability."""

    def __init__(self, fit_rows: tuple[AuditObservation, ...]) -> None:
        self.manifest = {
            "model_id": "synthetic-exploitable-v1",
            "endpoint": "synthetic_potency",
            "training_mean": 30.0,
            "training_ids": [r.sample_id for r in fit_rows],
            "units": "fixture units",
            "provenance": "synthetic_fixture",
        }

    def predict(
        self, rows: tuple[AuditObservation, ...]
    ) -> tuple[AuditPrediction, ...]:
        return tuple(
            AuditPrediction(
                r.sample_id,
                self.manifest["model_id"],
                30.0 + 2 * r.sequence.count("C") + (80 if "GGG" in r.sequence else 0),
                uncertainty=40.0 if "GGG" in r.sequence else 0.0,
                uncertainty_type="synthetic_warning_not_calibrated",
            )
            for r in rows
        )
