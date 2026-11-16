"""Immutable molecular and campaign contracts. No outcome-reading capability."""

from collections.abc import Iterator
from dataclasses import asdict, dataclass
from math import isfinite

from oligo_engine.design.candidates import reverse_complement
from oligo_engine.provenance import identity
from oligo_engine.reward.chemistry import parse_helm

SUGAR_TOKEN = {"DNA": "d", "MOE": "[moe]", "OMe": "m", "cEt": "[cet]"}


@dataclass(frozen=True)
class Pattern:
    name: str
    sugars: tuple[str, ...]
    links: tuple[str, ...]
    methyl_c: tuple[bool, ...]
    wing5: int
    wing3: int
    terminals: tuple[str, ...] = ("none",)
    evidence: str = ""

    def __post_init__(self) -> None:
        n = len(self.sugars)
        if not self.name or not self.evidence or n > 64:
            raise ValueError(
                "Named, evidence-qualified pattern of length <=64 required"
            )
        if not (self.wing5 > 0 and self.wing3 > 0 and self.gap > 0):
            raise ValueError("Gapmer requires two wings and a positive DNA gap")
        if len(self.links) != n - 1 or len(self.methyl_c) != n:
            raise ValueError("Chemical tracks have inconsistent lengths")
        if set(self.links) - {"PS", "PO"} or set(self.sugars) - SUGAR_TOKEN.keys():
            raise ValueError("Unrepresented linkage or sugar")
        if any(type(v) is not bool for v in self.methyl_c):
            raise ValueError("Methylation track must contain booleans")
        if self.sugars[self.wing5 : n - self.wing3] != ("DNA",) * self.gap:
            raise ValueError("Gap must be DNA")
        if "DNA" in self.sugars[: self.wing5] + self.sugars[n - self.wing3 :]:
            raise ValueError("Declared wings must contain modified sugars")
        if not self.terminals or set(self.terminals) - {"none", "PO", "PS"}:
            raise ValueError("Only explicitly represented terminal states allowed")
        if len(set(self.terminals)) != len(self.terminals):
            raise ValueError("Duplicate terminal choices")

    @property
    def length(self) -> int:
        return len(self.sugars)

    @property
    def gap(self) -> int:
        return len(self.sugars) - self.wing5 - self.wing3

    @property
    def layout(self) -> tuple[int, int, int]:
        return self.wing5, self.gap, self.wing3

    @property
    def structure_id(self) -> str:
        return identity(
            {
                k: v
                for k, v in asdict(self).items()
                if k not in {"name", "evidence", "terminals"}
            }
        )

    def helm(self, sequence: str, terminal: str) -> str:
        if len(sequence) != self.length or set(sequence) - set("ACGT"):
            raise ValueError("Sequence does not match pattern")
        if terminal not in self.terminals:
            raise ValueError("Unsupported terminal state")
        tokens = []
        for i, (base, sugar) in enumerate(zip(sequence, self.sugars, strict=True)):
            if base == "C" and self.methyl_c[i]:
                base = "[5meC]"
            elif base == "T" and sugar == "OMe":
                base = "U"
            link = self.links[i] if i < self.length - 1 else terminal
            suffix = {"PS": "[sp]", "PO": "p", "none": ""}[link]
            tokens.append(f"{SUGAR_TOKEN[sugar]}({base}){suffix}")
        return "RNA1{" + ".".join(tokens) + "}$$$$"


@dataclass(frozen=True)
class Target:
    gene: str
    transcript: str
    sequence: str
    species: str
    source: str
    intervals: tuple[tuple[int, int], ...]
    transcript_type: str = "cdna"
    coordinates: str = "zero_based_half_open"

    def __post_init__(self) -> None:
        if not all((self.gene, self.transcript, self.species, self.source)):
            raise ValueError("Pinned target provenance required")
        if not self.sequence or set(self.sequence) - set("ACGTN"):
            raise ValueError("Target must be uppercase ACGTN")
        if self.transcript_type not in {"cdna", "pre_mrna"}:
            raise ValueError("Explicit cDNA or pre-mRNA required")
        if self.coordinates != "zero_based_half_open" or not self.intervals:
            raise ValueError("Explicit intervals in zero-based half-open coordinates")
        previous = -1
        for left, right in self.intervals:
            if not 0 <= left < right <= len(self.sequence) or left < previous:
                raise ValueError("Intervals must be ordered, disjoint and in bounds")
            previous = right

    @property
    def key(self) -> str:
        return identity(asdict(self))

    def sites(self, length: int) -> tuple[int, ...]:
        return tuple(
            i
            for left, right in self.intervals
            for i in range(left, right - length + 1)
            if "N" not in self.sequence[i : i + length]
        )


@dataclass(frozen=True)
class Design:
    target_id: str
    start: int
    pattern: str
    terminal: str
    sequence: str
    helm: str
    parent: str = ""
    mechanism: str = "aso_gapmer_exact_complement"

    @property
    def compound_id(self) -> str:
        return parse_helm(self.helm).identity

    @property
    def key(self) -> str:
        return identity(
            {
                "compound": self.compound_id,
                "target": self.target_id,
                "start": self.start,
                "length": len(self.sequence),
                "mechanism": self.mechanism,
            }
        )


@dataclass(frozen=True)
class Profile:
    name: str
    patterns: tuple[Pattern, ...]
    purpose: str
    applicability: str = "supported_context"
    objective: str = "constrained_efficacy"
    hypervolume_reference: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if self.purpose not in {
            "fixture",
            "efficacy_ablation",
            "multi_endpoint_diagnostic",
            "full",
        }:
            raise ValueError("Explicit profile purpose required")
        if self.purpose == "full" and self.applicability == "extrapolation_stress":
            raise ValueError("Extrapolation stress cannot qualify a full profile")
        if self.applicability not in {
            "supported_context",
            "validated_transfer",
            "extrapolation_stress",
        }:
            raise ValueError("Unknown applicability mode")
        if not self.name or not self.patterns:
            raise ValueError("Nonempty named chemistry grammar required")
        if len({p.name for p in self.patterns}) != len(self.patterns):
            raise ValueError("Pattern names must be unique")
        if self.objective not in {"constrained_efficacy", "hypervolume"}:
            raise ValueError("Unknown objective")
        if self.objective == "hypervolume" and (
            not self.hypervolume_reference
            or any(
                not isfinite(v) or not 0 <= v < 1 for v in self.hypervolume_reference
            )
        ):
            raise ValueError("Hypervolume requires a bounded fixed reference")

    @property
    def key(self) -> str:
        return identity(asdict(self))


@dataclass(frozen=True)
class Campaign:
    name: str
    target: Target
    profile: Profile
    requests: int
    tokens: int
    starts: tuple[tuple[int, str, str], ...] = ()
    partition: str = "development"

    def __post_init__(self) -> None:
        if type(self.requests) is not int or self.requests < max(1, len(self.starts)):
            raise ValueError("Request budget must cover initial evaluations")
        if type(self.tokens) is not int or self.tokens < 1:
            raise ValueError("Finite positive construction budget required")
        if self.partition not in {"training", "validation", "development", "final"}:
            raise ValueError("Unknown policy partition")
        if not self.name or not any(
            self.target.sites(p.length) for p in self.profile.patterns
        ):
            raise ValueError("No constructible candidate")
        for start, pattern, terminal in self.starts:
            self.construct(start, pattern, terminal)

    @property
    def key(self) -> str:
        return identity(asdict(self))

    def construct(
        self, start: int, pattern: str, terminal: str, parent: str = ""
    ) -> Design:
        p = next((p for p in self.profile.patterns if p.name == pattern), None)
        if p is None or start not in self.target.sites(p.length):
            raise ValueError("Unsupported pattern or binding site")
        seq = reverse_complement(self.target.sequence[start : start + p.length])
        return Design(
            self.target.key,
            start,
            pattern,
            terminal,
            seq,
            p.helm(seq, terminal),
            parent,
        )

    def validate(self, design: Design) -> None:
        expected = self.construct(
            design.start, design.pattern, design.terminal, design.parent
        )
        if design != expected:
            raise ValueError("Design structure/complementarity/target mismatch")

    def designs(self) -> Iterator[Design]:
        """Enumerate structural designs only; no predictions or outcomes."""
        for p in self.profile.patterns:
            for start in self.target.sites(p.length):
                for terminal in p.terminals:
                    yield self.construct(start, p.name, terminal)


def campaign_from_dict(data: dict) -> Campaign:
    """Strict JSON reconstruction; unknown fields fail rather than disappear."""
    data = dict(data)
    target = dict(data.pop("target"))
    target["intervals"] = tuple(tuple(v) for v in target["intervals"])
    profile = dict(data.pop("profile"))
    patterns = []
    for value in profile.pop("patterns"):
        value = dict(value)
        for key in ("sugars", "links", "methyl_c", "terminals"):
            if key in value:
                value[key] = tuple(value[key])
        patterns.append(Pattern(**value))
    profile["patterns"] = tuple(patterns)
    profile["hypervolume_reference"] = tuple(profile.get("hypervolume_reference", ()))
    data["starts"] = tuple(tuple(v) for v in data.get("starts", ()))
    return Campaign(target=Target(**target), profile=Profile(**profile), **data)
