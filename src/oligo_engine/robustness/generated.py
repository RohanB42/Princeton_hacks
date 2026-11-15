"""Post-seal audits of real design archives; no invented measured outcomes."""

from dataclasses import asdict

from oligo_engine.design.aso_space import TargetContext, candidate_identity, identity
from oligo_engine.design.candidates import Candidate
from oligo_engine.robustness.contracts import AuditObservation
from oligo_engine.robustness.diagnostics import DomainReference


def audit_generated_archive(
    receipt: dict,
    reference: DomainReference,
    endpoint: str,
    units: str,
    evaluator: object | None = None,
) -> dict:
    """Accept a sealed scorer archive and an optional frozen comparison predictor.

    An evaluator is computational corroboration, not independent measured truth.
    Training history/overlap must be audited separately; this function never grants
    independence merely because a second model exists.
    """
    target = TargetContext(**receipt["target_manifest"])
    if receipt["target_identity"] != target.identity or not receipt.get(
        "scorer_identity"
    ):
        raise ValueError("Pinned target/scorer manifest mismatch")
    context = tuple(
        sorted((key, str(value)) for key, value in receipt["assay"].items())
    )
    rows = []
    for item in receipt["archive"]:
        candidate = Candidate(**item["candidate"])
        candidate_identity(candidate, target)
        key = identity(
            {
                "candidate": asdict(candidate),
                "context": context,
                "target": target.identity,
                "endpoint": endpoint,
            }
        )
        rows.append(
            AuditObservation(
                key,
                candidate.helm,
                target.gene,
                endpoint,
                units,
                target.identity,
                context,
            )
        )
    values = reference.reference_values()
    diagnostics = [reference.diagnose(row, values) for row in rows]
    predicted = evaluator.predict(tuple(rows)) if evaluator else ()
    return {
        "status": "computational_only",
        "archive_hash": identity(receipt),
        "candidate_count": len(rows),
        "domain_diagnostics": diagnostics,
        "comparison_predictions": [asdict(p) for p in predicted],
        "evaluator_identity": evaluator.manifest if evaluator else None,
        "evaluator_independence": "not_established_by_this_function",
        "exact_measured_outcomes": 0,
        "novel_candidate_validation": False,
        "source_score_cost": {
            k: receipt[k] for k in ("requests", "unique_scores", "head_calls")
        },
    }
