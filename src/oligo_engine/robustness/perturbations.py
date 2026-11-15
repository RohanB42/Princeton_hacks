"""Typed, outcome-free representation and assay-context perturbation probes."""

from dataclasses import asdict, dataclass, replace

from oligo_engine.provenance import identity
from oligo_engine.robustness.contracts import AuditObservation, chemistry


@dataclass(frozen=True)
class PerturbationCase:
    parent_id: str
    variant_id: str
    family: str
    legal: bool
    helm: str
    measurement_status: str = "unmeasured_variant"
    reason: str = ""


def representation_cases(
    row: AuditObservation,
) -> tuple[tuple[PerturbationCase, AuditObservation | None], ...]:
    raw = row.helm[:-4] if row.helm.endswith("}$$$$V2.0") else row.helm
    canonical = raw.replace("[m5C]", "[5meC]")
    if canonical.startswith("RNA1{{"):
        variant_helm = "RNA1{" + canonical[6:-6] + "}$$$$"
    else:
        variant_helm = "RNA1{{" + canonical[5:-5] + "}}$$$$"
    result = []
    for family, helm in (
        ("equivalent_representation", variant_helm),
        ("malformed_input", row.helm + "UNCONSUMED"),
    ):
        variant_id = identity({"parent": row.sample_id, "family": family, "helm": helm})
        try:
            parsed = chemistry(helm)
            if (
                family == "equivalent_representation"
                and parsed.identity != row.compound_id
            ):
                raise ValueError("Projection changed molecular identity")
            variant = replace(row, sample_id=variant_id, helm=helm)
            case = PerturbationCase(row.sample_id, variant_id, family, True, helm)
        except ValueError as exc:
            variant = None
            case = PerturbationCase(
                row.sample_id, variant_id, family, False, helm, reason=str(exc)
            )
        result.append((case, variant))
    return tuple(result)


def context_change(
    row: AuditObservation,
    key: str,
    value: str,
    supported_contexts: frozenset[tuple[tuple[str, str], ...]],
) -> tuple[PerturbationCase, AuditObservation | None]:
    context = dict(row.context)
    if key not in context or not value:
        raise ValueError("An existing context field and explicit value are required")
    context[key] = value
    changed = tuple(sorted(context.items()))
    variant_id = identity({"parent": row.sample_id, "context": changed})
    legal = changed in supported_contexts
    case = PerturbationCase(
        row.sample_id,
        variant_id,
        "single_context_change",
        legal,
        row.helm,
        reason="" if legal else "CONTEXT_UNSUPPORTED",
    )
    return case, replace(row, sample_id=variant_id, context=changed) if legal else None


def probe(
    model: object, parents: tuple[AuditObservation, ...], limit: int = 32
) -> dict:
    if limit < 1:
        raise ValueError("Positive label-blind perturbation limit required")
    records = []
    for parent in sorted(parents, key=lambda r: r.sample_id)[:limit]:
        original = model.predict((parent,))[0]
        for case, variant in representation_cases(parent):
            output = asdict(case)
            output["parent_mean"] = original.mean
            output["variant_mean"] = None
            output["delta"] = None
            if variant is not None:
                prediction = model.predict((variant,))[0]
                output["variant_mean"] = prediction.mean
                if original.mean is not None and prediction.mean is not None:
                    output["delta"] = prediction.mean - original.mean
                    if (
                        case.family == "equivalent_representation"
                        and abs(output["delta"]) > 1e-8
                    ):
                        raise ValueError(
                            "Equivalent molecular representation changed prediction"
                        )
            records.append(output)
    return {
        "records": records,
        "attempted": len(records),
        "rejected_before_inference": sum(not r["legal"] for r in records),
        "biological_error_inferred": False,
        "measured_labels_copied": False,
    }
