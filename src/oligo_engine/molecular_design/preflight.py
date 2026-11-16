"""Outcome-free campaign and split audits. Evidence is never inferred from success."""

from .contracts import Campaign
from .scoring import FrozenRegistry


def preflight(campaign: Campaign, registry: FrozenRegistry) -> dict:
    counts = {h.manifest.name: 0 for h in registry.heads}
    capacity = joint = 0
    patterns = {}
    for d in campaign.designs():
        capacity += 1
        admitted = True
        for h in registry.heads:
            applicable = registry.applicable(d, h) and h.predict is not None
            counts[h.manifest.name] += applicable
            if h.manifest.role != "advisory":
                admitted &= applicable
        joint += admitted
        patterns[d.pattern] = patterns.get(d.pattern, 0) + 1
    reasons = []
    if joint == 0:
        reasons.append("ZERO_REQUIRED_HEAD_INTERSECTION")
    if campaign.profile.purpose == "full" and joint != capacity:
        reasons.append("PRODUCTION_GRAMMAR_EXCEEDS_REQUIRED_HEAD_SUPPORT")
    return {
        "campaign": campaign.name,
        "campaign_id": campaign.key,
        "purpose": campaign.profile.purpose,
        "partition": campaign.partition,
        "capacity": capacity,
        "patterns": patterns,
        "per_head": counts,
        "joint": joint,
        "admitted_fraction": joint / capacity,
        "status": "blocked" if reasons else "metadata_ready",
        "reasons": reasons,
        "screen_retention": None,
        "independent_evidence": "not_assessed",
    }


def audit_partitions(
    campaigns: tuple[Campaign, ...], minimum_final_groups: int = 5
) -> dict:
    seen, groups = {}, {}
    for c in campaigns:
        groups.setdefault(c.partition, set()).add(c.target.gene)
        for token in (c.target.gene, c.target.transcript, c.target.sequence):
            if token in seen and seen[token] != c.partition:
                raise ValueError("Policy target/transcript crosses partitions")
            seen[token] = c.partition
    return {
        "groups": {k: len(v) for k, v in groups.items()},
        "cross_target_claim_ready": len(groups.get("final", ()))
        >= minimum_final_groups,
        "minimum_final_groups": minimum_final_groups,
    }


def audit_membership(registry: FrozenRegistry, final_ids: tuple[str, ...]) -> None:
    """Final assessment cannot overlap fit, selection or calibration exposure."""
    for head in registry.heads:
        m = head.manifest
        exposed = set(m.training_ids + m.validation_ids + m.calibration_ids)
        if exposed.intersection(final_ids):
            raise ValueError(f"Final outcomes overlap artifact exposure: {m.name}")
