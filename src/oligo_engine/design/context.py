"""Pinned transcript context and molecular identity, without optimizer actions."""

from dataclasses import asdict, dataclass

from oligo_engine.design.candidates import (
    DESIGNS,
    Candidate,
    build_helm,
    reverse_complement,
)
from oligo_engine.provenance import identity


@dataclass(frozen=True)
class TargetContext:
    gene: str
    transcript_id: str
    sequence: str
    species: str
    source: str
    transcript_type: str = "cdna"
    coordinates: str = "zero_based_half_open"

    def __post_init__(self) -> None:
        if not all((self.gene, self.transcript_id, self.species, self.source)):
            raise ValueError("Versioned transcript, gene, species and source required")
        if not self.sequence or set(self.sequence) - set("ACGTN"):
            raise ValueError("Pinned transcript must be uppercase A/C/G/T/N")
        if self.coordinates != "zero_based_half_open" or not self.transcript_type:
            raise ValueError("Unsupported coordinate convention or transcript type")

    @property
    def identity(self) -> str:
        return identity(asdict(self))


def candidate_identity(candidate: Candidate, target: TargetContext) -> str:
    """Chemical/site identity is separate from the existing display identifier."""
    window = target.sequence[candidate.start : candidate.end]
    if candidate.chemistry not in {"ps_moe_gapmer", "ps_moe_20_gapmer"}:
        raise ValueError("Candidate does not match pinned transcript/template")
    length = DESIGNS[candidate.chemistry]["length"]
    if (
        candidate.gene != target.gene
        or candidate.transcript_id != target.transcript_id
        or candidate.start < 0
        or candidate.end > len(target.sequence)
        or candidate.end - candidate.start != length
        or len(window) != length
        or set(window) - set("ACGT")
        or candidate.target_window != window
        or candidate.sequence != reverse_complement(window)
        or candidate.helm != build_helm(candidate.sequence, candidate.chemistry)
    ):
        raise ValueError("Candidate does not match pinned transcript/template")
    return identity(
        {"candidate": asdict(candidate), "target_identity": target.identity}
    )
