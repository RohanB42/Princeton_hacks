"""Frozen endpoint inference, archive utility and exact logical request accounting."""

from dataclasses import asdict, dataclass
from math import isfinite
from time import perf_counter
from typing import Callable

from oligo_engine.provenance import identity

from .contracts import Campaign, Design, Profile


@dataclass(frozen=True)
class HeadManifest:
    name: str
    endpoint: str
    units: str
    role: str
    direction: str
    context: tuple[tuple[str, str], ...]
    pattern_ids: tuple[str, ...]
    terminals: tuple[str, ...]
    artifact_hash: str
    feature_schema: str
    training_ids: tuple[str, ...]
    reference: tuple[float, ...] = ()
    lower: float | None = None
    upper: float | None = None
    evidence: str = ""
    parity_receipt: str = ""
    provenance: str = "fixture"
    uncertainty_type: str = "none"
    diagnostics: tuple[str, ...] = ()
    validation_ids: tuple[str, ...] = ()
    calibration_ids: tuple[str, ...] = ()
    adaptation_labels: int = 0
    property_kind: str = "efficacy"

    def __post_init__(self) -> None:
        if self.property_kind not in {"efficacy", "risk", "advisory"}:
            raise ValueError("Explicit scientific property kind required")
        if not all(
            (
                self.name,
                self.endpoint,
                self.units,
                self.artifact_hash,
                self.feature_schema,
                self.evidence,
            )
        ):
            raise ValueError("Complete endpoint provenance required")
        if self.role not in {"objective", "required_screen", "advisory"}:
            raise ValueError("Unknown head role")
        if self.direction not in {"higher", "lower"}:
            raise ValueError("Explicit endpoint direction required")
        if len(dict(self.context)) != len(self.context) or not self.context:
            raise ValueError("Unique endpoint-specific context required")
        if self.provenance not in {"fixture", "measured"}:
            raise ValueError("Explicit model provenance required")
        if self.role == "objective" and not self.reference:
            raise ValueError("Objective requires frozen training-only reference")
        if self.role == "required_screen" and self.lower is None and self.upper is None:
            raise ValueError("Screen requires a qualified bound")
        numbers = self.reference + tuple(
            v for v in (self.lower, self.upper) if v is not None
        )
        if any(not isfinite(v) for v in numbers):
            raise ValueError("Nonfinite reference/bound")
        if (
            self.lower is not None
            and self.upper is not None
            and self.lower > self.upper
        ):
            raise ValueError("Reversed screening interval")
        if self.adaptation_labels < 0 or len(set(self.diagnostics)) != len(
            self.diagnostics
        ):
            raise ValueError("Invalid adaptation budget or diagnostic schema")

    @property
    def key(self) -> str:
        return identity(asdict(self))


@dataclass(frozen=True)
class Prediction:
    mean: float
    uncertainty: float | None = None
    diagnostics: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class Head:
    manifest: HeadManifest
    predict: Callable[[Design, tuple[tuple[str, str], ...]], Prediction] | None


@dataclass(frozen=True)
class EndpointResult:
    name: str
    endpoint: str
    units: str
    context_id: str
    assessment_id: str
    manifest_id: str
    role: str
    status: str
    raw: float | None = None
    utility: float | None = None
    uncertainty: float | None = None
    uncertainty_type: str = "none"
    diagnostics: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class Score:
    design_id: str
    compound_id: str
    eligible: bool
    endpoints: tuple[EndpointResult, ...]
    objectives: tuple[float, ...]


class InferenceFailure(RuntimeError):
    """Infrastructure failure, never a biological penalty."""


class FrozenRegistry:
    def __init__(self, profile: Profile, heads: tuple[Head, ...]) -> None:
        self.profile, self.heads = profile, heads
        if len({h.manifest.name for h in heads}) != len(heads):
            raise ValueError("Head names must be unique")
        objectives = sum(h.manifest.role == "objective" for h in heads)
        if objectives < 1 or (
            profile.objective == "constrained_efficacy" and objectives != 1
        ):
            raise ValueError("Constrained efficacy requires exactly one objective")
        if profile.objective == "hypervolume" and objectives != len(
            profile.hypervolume_reference
        ):
            raise ValueError("Hypervolume dimensionality mismatch")
        if any(h.predict is None and h.manifest.role != "advisory" for h in heads):
            raise ValueError("Required checkpoint unavailable")
        if profile.purpose != "fixture" and any(
            h.manifest.provenance != "measured"
            for h in heads
            if h.manifest.role != "advisory"
        ):
            raise ValueError("Fixture head cannot satisfy a real profile")
        if profile.purpose == "full":
            if len({p.structure_id for p in profile.patterns}) < 2:
                raise ValueError("Full profile requires meaningful chemical choices")
            if not any(
                h.manifest.role == "required_screen"
                and h.manifest.property_kind == "risk"
                for h in heads
            ):
                raise ValueError("Full profile requires an evaluated risk screen")
            if any(
                not h.manifest.parity_receipt or not h.manifest.training_ids
                for h in heads
                if h.manifest.role != "advisory"
            ):
                raise ValueError(
                    "Full profile requires inference and membership evidence"
                )
        self.key = self.current_identity()

    def current_identity(self) -> str:
        return identity(
            {
                "profile": self.profile.key,
                "heads": [(h.manifest.key, h.predict is not None) for h in self.heads],
            }
        )

    def applicable(self, design: Design, head: Head) -> bool:
        p = next(p for p in self.profile.patterns if p.name == design.pattern)
        return (
            p.structure_id in head.manifest.pattern_ids
            and design.terminal in head.manifest.terminals
        )

    def score(self, design: Design, on_call: Callable[[str], None]) -> Score:
        results, objectives = [], []
        eligible = True
        for h in self.heads:
            m = h.manifest
            context_id = identity(m.context)
            assessment = identity(
                {
                    "compound": design.compound_id,
                    "endpoint": m.endpoint,
                    "target": design.target_id,
                    "context": context_id,
                }
            )
            status, raw, utility, uncertainty, diagnostics = (
                "scored",
                None,
                None,
                None,
                (),
            )
            if not self.applicable(design, h):
                status = "chemistry_unsupported"
            elif h.predict is None:
                status = "model_unavailable"
            else:
                on_call(m.name)
                try:
                    prediction = h.predict(design, m.context)
                    raw = float(prediction.mean)
                    uncertainty = prediction.uncertainty
                    diagnostics = prediction.diagnostics
                    if not isfinite(raw):
                        raise ValueError("Nonfinite prediction")
                    if (uncertainty is None) != (m.uncertainty_type == "none"):
                        raise ValueError("Uncertainty availability/type mismatch")
                    if uncertainty is not None and (
                        not isfinite(uncertainty) or uncertainty < 0
                    ):
                        raise ValueError("Invalid uncertainty")
                    if len(dict(diagnostics)) != len(diagnostics) or set(
                        dict(diagnostics)
                    ) != set(m.diagnostics):
                        raise ValueError("Diagnostic schema mismatch")
                    if any(not isfinite(v) for _, v in diagnostics):
                        raise ValueError("Nonfinite diagnostic")
                except Exception as exc:
                    raise InferenceFailure(
                        f"Inference failed for {m.name}: {exc}"
                    ) from exc
                if m.role == "objective":
                    utility = (
                        sum(v < raw for v in m.reference)
                        + 0.5 * sum(v == raw for v in m.reference)
                    ) / len(m.reference)
                    if m.direction == "lower":
                        utility = 1 - utility
                    objectives.append(utility)
                if m.role == "required_screen" and (
                    (m.lower is not None and raw < m.lower)
                    or (m.upper is not None and raw > m.upper)
                ):
                    status = "screen_failed"
            if status != "scored" and m.role != "advisory":
                eligible = False
            results.append(
                EndpointResult(
                    m.name,
                    m.endpoint,
                    m.units,
                    context_id,
                    assessment,
                    m.key,
                    m.role,
                    status,
                    raw,
                    utility,
                    uncertainty,
                    m.uncertainty_type if uncertainty is not None else "none",
                    diagnostics,
                )
            )
        return Score(
            design.key, design.compound_id, eligible, tuple(results), tuple(objectives)
        )


def hypervolume(
    points: tuple[tuple[float, ...], ...], reference: tuple[float, ...]
) -> float:
    """Exact union of maximization boxes. Small objective counts, no Monte Carlo."""
    points = tuple(
        set(p for p in points if all(x > r for x, r in zip(p, reference, strict=True)))
    )
    if not points:
        return 0.0
    if len(reference) == 1:
        return max(p[0] for p in points) - reference[0]
    coordinates = sorted({reference[0]} | {p[0] for p in points})
    return sum(
        (right - left)
        * hypervolume(tuple(p[1:] for p in points if p[0] >= right), reference[1:])
        for left, right in zip(coordinates, coordinates[1:])
    )


class Session:
    """One arm's request ledger/cache/archive. No hidden unique-query cap."""

    def __init__(
        self,
        campaign: Campaign,
        registry: FrozenRegistry,
        on_receipt: Callable[[dict], None] | None = None,
    ) -> None:
        if campaign.profile.key != registry.profile.key:
            raise ValueError("Campaign/scorer profile mismatch")
        self.campaign, self.registry = campaign, registry
        self.registry_id = registry.key
        self.on_receipt = on_receipt
        self.archive: dict[str, tuple[Design, Score]] = {}
        self.trace: list[dict] = []
        self.calls: dict[str, int] = {}
        self.requests = 0
        self.failed = False
        self.initial_quality = 0.0
        for start, pattern, terminal in campaign.starts:
            self.query(campaign.construct(start, pattern, terminal), initial=True)
        self.initial_quality = self.quality

    @property
    def quality(self) -> float:
        points = tuple(s.objectives for _, s in self.archive.values() if s.eligible)
        if self.campaign.profile.objective == "constrained_efficacy":
            return max((p[0] for p in points), default=0.0)
        ref = self.campaign.profile.hypervolume_reference
        normalizer = 1.0
        for r in ref:
            normalizer *= 1 - r
        return hypervolume(points, ref) / normalizer

    @property
    def remaining(self) -> int:
        return self.campaign.requests - self.requests

    @property
    def parents(self) -> tuple[Design, ...]:
        return tuple(d for d, _ in self.archive.values())

    def _called(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1

    def query(self, design: Design, initial: bool = False) -> tuple[Score, float]:
        if self.failed or self.remaining <= 0:
            raise RuntimeError("Session failed or request budget exhausted")
        if self.registry.current_identity() != self.registry_id:
            raise RuntimeError("Frozen registry identity changed")
        self.campaign.validate(design)
        before, started = self.quality, perf_counter()
        self.requests += 1
        hit = design.key in self.archive
        receipt = {
            "campaign_id": self.campaign.key,
            "registry_id": self.registry_id,
            "request": self.requests,
            "design": asdict(design),
            "design_id": design.key,
            "compound_id": design.compound_id,
            "cache_hit": hit,
            "initial": initial,
            "input_hash": identity(
                {"design": asdict(design), "registry": self.registry_id}
            ),
        }
        try:
            score = (
                self.archive[design.key][1]
                if hit
                else self.registry.score(design, self._called)
            )
            self.archive.setdefault(design.key, (design, score))
            gain = self.quality - before
            if gain < -1e-12:
                raise RuntimeError("Archive quality is not monotone")
            receipt.update(
                status="scored",
                score=asdict(score),
                quality=self.quality,
                gain=max(0.0, gain),
            )
        except Exception as exc:
            self.failed = True
            receipt.update(
                status="execution_failed", error=str(exc), quality=before, gain=None
            )
            raise
        finally:
            receipt["elapsed_seconds"] = perf_counter() - started
            receipt["head_calls"] = dict(self.calls)
            self.trace.append(receipt)
            if self.on_receipt:
                self.on_receipt(receipt)
        return score, max(0.0, gain)

    def receipt(self) -> dict:
        return {
            "campaign_id": self.campaign.key,
            "registry_id": self.registry_id,
            "requests": self.requests,
            "unique_designs": len(self.archive),
            "unique_compounds": len({s.compound_id for _, s in self.archive.values()}),
            "per_head_calls": dict(self.calls),
            "inference_batches": sum(self.calls.values()),
            "initial_quality": self.initial_quality,
            "final_quality": self.quality,
            "failed": self.failed,
            "trace": self.trace,
            "heads": [asdict(h.manifest) for h in self.registry.heads],
            "claim": "unvalidated computational hypotheses",
        }
