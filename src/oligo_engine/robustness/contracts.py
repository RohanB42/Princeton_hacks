"""Outcome-free immutable audit records and independent partition contracts."""

from dataclasses import asdict, dataclass
from functools import cached_property
from math import isfinite
from typing import Protocol

from oligo_engine.provenance import identity
from oligo_engine.reward.chemistry import ASOChemistry, parse_helm

SCHEMA = "predictor-robustness-v1"
PARTITIONS = ("fit", "development", "calibration", "final")


def chemistry(helm: str) -> ASOChemistry:
    """Known methylcytosine alias only; never remove chemical modifications."""
    projected = helm[:-4] if helm.endswith("}$$$$V2.0") else helm
    return parse_helm(projected.replace("[m5C]", "[5meC]"))


@dataclass(frozen=True)
class AuditObservation:
    sample_id: str
    helm: str
    target_id: str
    endpoint: str
    units: str
    source_hash: str
    context: tuple[tuple[str, str], ...] = ()
    patent_id: str = ""
    modality: str = "ASO"

    def __post_init__(self) -> None:
        if not all(
            (self.sample_id, self.helm, self.endpoint, self.units, self.source_hash)
        ):
            raise ValueError("Complete source and endpoint identity required")
        if len(dict(self.context)) != len(self.context):
            raise ValueError("Duplicate assay context keys")
        if self.modality != "ASO":
            raise ValueError("This audit adapter is ASO-specific")
        chemistry(self.helm)

    @cached_property
    def compound_id(self) -> str:
        return chemistry(self.helm).identity

    @cached_property
    def sequence(self) -> str:
        return chemistry(self.helm).natural_rna

    @cached_property
    def assessment_id(self) -> str:
        return identity(
            {
                "compound": self.compound_id,
                "context": self.context,
                "endpoint": self.endpoint,
                "target": self.target_id,
            }
        )

    @classmethod
    def from_dict(cls, value: dict) -> "AuditObservation":
        value = dict(value)
        value["context"] = tuple(tuple(v) for v in value.get("context", ()))
        return cls(**value)


@dataclass(frozen=True)
class RobustnessSplit:
    fit: tuple[str, ...]
    development: tuple[str, ...]
    calibration: tuple[str, ...]
    final: tuple[str, ...]
    strategy: str
    seed: int
    metadata_hash: str
    excluded: tuple[str, ...] = ()

    @property
    def identity(self) -> str:
        return identity(asdict(self))

    def validate(self, rows: tuple[AuditObservation, ...]) -> None:
        if self.metadata_hash != records_hash(rows):
            raise ValueError("Split metadata changed")
        mapping = {r.sample_id: r for r in rows}
        ids = [i for part in PARTITIONS for i in getattr(self, part)] + list(
            self.excluded
        )
        if (
            len(mapping) != len(rows)
            or len(ids) != len(set(ids))
            or set(ids) != set(mapping)
        ):
            raise ValueError("Split must be a complete unique partition")
        if any(not getattr(self, part) for part in PARTITIONS):
            raise ValueError("infeasible_split: four nonempty partitions required")
        for key in ("compound_id", "sequence", self.strategy):
            seen: dict[str, str] = {}
            for part in PARTITIONS:
                for i in getattr(self, part):
                    value = getattr(mapping[i], key)
                    if not value:
                        raise ValueError("Missing required group identity")
                    if value in seen and seen[value] != part:
                        raise ValueError(f"Cross-partition {key} overlap")
                    seen[value] = part


@dataclass(frozen=True)
class AuditPrediction:
    sample_id: str
    model_id: str
    mean: float | None
    status: str = "scored"
    reason: str = ""
    uncertainty: float | None = None
    uncertainty_type: str = "none"

    def __post_init__(self) -> None:
        if self.status == "scored" and (self.mean is None or not isfinite(self.mean)):
            raise ValueError("Scored predictions require a finite mean")
        if self.status != "scored" and self.mean is not None:
            raise ValueError("Unscored prediction must remain null")
        if (self.uncertainty is None) != (self.uncertainty_type == "none"):
            raise ValueError("Named uncertainty and availability disagree")
        if self.uncertainty is not None and (
            not isfinite(self.uncertainty) or self.uncertainty < 0
        ):
            raise ValueError("Invalid uncertainty")


def records_hash(rows: tuple[AuditObservation, ...]) -> str:
    return identity([asdict(r) for r in sorted(rows, key=lambda r: r.sample_id)])


class AuditPredictor(Protocol):
    manifest: dict

    def predict(
        self, rows: tuple[AuditObservation, ...]
    ) -> tuple[AuditPrediction, ...]: ...
