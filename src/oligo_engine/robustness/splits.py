"""Metadata-only connected-component splits with no label dependency."""

from random import Random

from oligo_engine.robustness.contracts import (
    AuditObservation,
    RobustnessSplit,
    records_hash,
)


def make_split(
    rows: tuple[AuditObservation, ...],
    strategy: str = "target_id",
    seed: int = 1729,
) -> tuple[RobustnessSplit, dict]:
    if strategy not in ("target_id", "patent_id") or type(seed) is not int:
        raise ValueError("Unsupported split strategy or seed")
    if len({r.sample_id for r in rows}) != len(rows):
        raise ValueError("Duplicate observation IDs")
    eligible = [r for r in rows if getattr(r, strategy)]
    excluded = tuple(sorted(r.sample_id for r in rows if not getattr(r, strategy)))
    parent = {r.sample_id: r.sample_id for r in eligible}

    def find(i: str) -> str:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen: dict[tuple[str, str], str] = {}
    for row in sorted(eligible, key=lambda r: r.sample_id):
        for field in (strategy, "compound_id", "sequence"):
            key = (field, getattr(row, field))
            if key in seen:
                a, b = find(row.sample_id), find(seen[key])
                parent[max(a, b)] = min(a, b)
            seen[key] = row.sample_id
    components: dict[str, list[str]] = {}
    for row in eligible:
        components.setdefault(find(row.sample_id), []).append(row.sample_id)
    groups = sorted(components)
    if len(groups) < 4:
        raise ValueError(
            f"infeasible_split: {len(groups)} independent connected groups; need four"
        )
    Random(seed).shuffle(groups)
    parts = {
        "final": tuple(sorted(components[groups[0]])),
        "calibration": tuple(sorted(components[groups[1]])),
        "development": tuple(sorted(components[groups[2]])),
        "fit": tuple(sorted(i for g in groups[3:] for i in components[g])),
    }
    split = RobustnessSplit(
        **parts,
        strategy=strategy,
        seed=seed,
        metadata_hash=records_hash(rows),
        excluded=excluded,
    )
    split.validate(rows)
    return split, {
        "strategy": strategy,
        "independent_components": len(groups),
        "component_ids": {g: sorted(v) for g, v in sorted(components.items())},
        "excluded_missing_group_ids": list(excluded),
        "overlap": "none_under_target_or_patent_plus_compound_and_natural_sequence",
        "patent_families_resolved": False,
    }


def audit_artifact(training_ids: tuple[str, ...], split: RobustnessSplit) -> None:
    if (
        not training_ids
        or len(set(training_ids)) != len(training_ids)
        or not set(training_ids) <= set(split.fit)
    ):
        raise ValueError(
            "blocked_artifact_overlap: artifact fit IDs outside fitting set"
        )
