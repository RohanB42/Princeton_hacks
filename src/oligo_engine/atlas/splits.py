"""Metadata-only development allocation and target/source isolation."""

import hashlib

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from .data import stable_id


def sequence_groups(sequences: list[str]) -> np.ndarray:
    """Connect same-length sequences within two substitutions or one-base shift.

    A one-base shift costs two end edits; remaining aligned bases must match.
    This conservative declared rule is not a complete homology search.
    """
    parent = list(range(len(sequences)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)

    lengths = {}
    for i, s in enumerate(sequences):
        lengths.setdefault(len(s), []).append(i)
    for indices in lengths.values():
        x = np.array([list(sequences[i]) for i in indices])
        for i in range(len(indices)):
            other = x[i + 1 :]
            close = (other != x[i]).sum(axis=1) <= 2
            if x.shape[1] > 1:
                close |= (other[:, 1:] == x[i, :-1]).all(axis=1)
                close |= (other[:, :-1] == x[i, 1:]).all(axis=1)
            for j in np.flatnonzero(close) + i + 1:
                union(indices[i], indices[j])
    return np.array([find(i) for i in range(len(sequences))])


def build_manifests(frame: pd.DataFrame, seed: int = 20261114) -> dict:
    # One largest eligible campaign per named target. No efficacy-based selection.
    candidates = []
    for cid, g in frame.groupby("campaign_id", sort=True):
        if len(g) < 400 or g["cell_line_species"].iloc[0].lower() != "human":
            continue
        target = g.target_key.iloc[0]
        if target in {"HBV", "HCV", "HIV"}:
            continue
        candidates.append((target, -len(g), cid))
    chosen = {}
    for target, _, cid in sorted(candidates):
        chosen.setdefault(target, cid)
    targets = sorted(
        chosen, key=lambda t: hashlib.sha256(f"{seed}:{t}".encode()).hexdigest()
    )
    dev = set(targets[:3])
    campaigns = []
    for target in targets:
        g = frame[frame.campaign_id == chosen[target]].sort_values("source_row_id")
        groups = sequence_groups(g.natural_rna.tolist())
        tr, te = next(
            GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(
                g, groups=groups
            )
        )
        campaigns.append(
            {
                "target": target,
                "campaign_id": chosen[target],
                "role": "development" if target in dev else "reserved",
                "patent": g["USPTO ID"].iloc[0],
                "rows": len(g),
                "pool_ids": g.iloc[tr].source_row_id.tolist(),
                "test_ids": g.iloc[te].source_row_id.tolist(),
                "sequence_groups": len(set(groups)),
                "eligible_200": len(tr) >= 200 and len(te) >= 80,
            }
        )
    held_targets = set(targets)
    held = frame[frame.target_key.isin(held_targets)]
    patents = set(held["USPTO ID"])
    bases = set(held.natural_rna)
    compounds = set(held.compound_key)
    source = frame[
        ~frame.target_key.isin(held_targets)
        & ~frame["USPTO ID"].isin(patents)
        & ~frame.natural_rna.isin(bases)
        & ~frame.compound_key.isin(compounds)
    ]
    assert not (set(source.target_key) & held_targets)
    assert not (set(source["USPTO ID"]) & patents)
    source = source.sort_values("source_row_id")
    groups = source["USPTO ID"].to_numpy()
    tr, va = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(
            source, groups=groups
        )
    )
    return {
        "schema": 1,
        "seed": seed,
        "target_mapping": "strip/uppercase; aliases unverified",
        "source_train_ids": source.iloc[tr].source_row_id.tolist(),
        "source_validation_ids": source.iloc[va].source_row_id.tolist(),
        "source_id": stable_id(source.source_row_id.tolist()),
        "excluded_targets": sorted(held_targets),
        "excluded_patents": sorted(patents),
        "campaigns": campaigns,
        "sequence_rule": "same length, Hamming <=2 or exact one-base shift",
        "purpose": "development_diagnostic; reserved targets not evaluated",
    }
