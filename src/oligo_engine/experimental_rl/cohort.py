"""Label-blind Atlas cohort preparation and targeted reads of measured outcomes."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from oligo_engine.provenance import identity
from oligo_engine.reward.chemistry import parse_helm

CONTEXT = [
    "USPTO ID",
    "Table Number",
    "target_RNA",
    "cell_line",
    "cell_line_species",
    "transfection_method",
    "treatment_period_hrs",
    "dosage_nm",
]
ID = "source_row_id"
LABEL = "Inhibition_pct"
HISTORICAL_DEVELOPMENT = {"F7", "STAT3", "NLRP3"}
PRIMARY_FILE = "in_vitro_inhibition.parquet"


@dataclass(frozen=True)
class Atlas:
    root: Path

    @property
    def path(self) -> Path:
        return self.root / "cleaned" / PRIMARY_FILE

    def verify(self) -> dict:
        audit = json.loads((self.root / "cleaned/audit.json").read_text())
        spec = audit["endpoints"]["in_vitro_inhibition"]
        expected = {
            f"release/{PRIMARY_FILE}": spec["source_sha256"],
            f"cleaned/{PRIMARY_FILE}": spec["cleaned_sha256"],
            **{f"release/folds/{p}": f["sha256"] for p, f in audit["folds"].items()},
        }
        for name, digest in expected.items():
            with (self.root / name).open("rb") as file:
                if hashlib.file_digest(file, "sha256").hexdigest() != digest:
                    raise ValueError(f"Atlas hash mismatch: {name}")
        return {
            "release": audit["release_tag"],
            "revision": audit["source_code_revision"],
            "hashes": expected,
        }

    def labels(self, ids: list[str] | tuple[str, ...]) -> dict[str, float]:
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("Unique, nonempty assay IDs required")
        rows = pd.read_parquet(
            self.path, columns=[ID, LABEL], filters=[(ID, "in", list(ids))]
        )
        labels = dict(zip(rows[ID], rows[LABEL], strict=True))
        if (
            len(rows) != len(ids)
            or set(labels) != set(ids)
            or not all(np.isfinite(value) for value in labels.values())
        ):
            raise ValueError("Missing, duplicate, or nonfinite recorded outcomes")
        return labels

    def metadata(self) -> tuple[pd.DataFrame, dict]:
        columns = [ID, "Compound ID", "HELM Annotation", *CONTEXT, "finite_endpoint"]
        rows = pd.read_parquet(self.path, columns=columns)
        counts = {"released": len(rows)}
        mask = rows[columns].notna().all(axis=1) & rows.finite_endpoint.eq(True)
        for name in (
            "target_RNA",
            "cell_line",
            "cell_line_species",
            "transfection_method",
        ):
            rows[name] = rows[name].str.strip()
            mask &= rows[name].str.len().gt(0)
        for name in ("dosage_nm", "treatment_period_hrs"):
            mask &= np.isfinite(rows[name]) & rows[name].gt(0)
        rows = rows.loc[mask].copy()
        counts["complete_positive_context"] = len(rows)
        compounds = {}
        for helm in rows["HELM Annotation"].unique():
            try:
                chemistry = parse_helm(helm)
            except ValueError:
                continue
            if "DNA" in chemistry.sugars and set(chemistry.sugars) <= {
                "DNA",
                "MOE",
                "cEt",
            }:
                compounds[helm] = chemistry
        rows = rows.loc[rows["HELM Annotation"].isin(compounds)].copy()
        counts["supported_chemistry"] = len(rows)
        molecules = [compounds[h] for h in rows["HELM Annotation"]]
        rows["base"] = [c.natural_rna for c in molecules]
        rows["compound"] = [c.identity for c in molecules]
        rows["scoped_compound"] = (
            rows["USPTO ID"] + ":" + rows["Compound ID"].astype(str)
        )
        rows["gene"] = rows.target_RNA.str.upper()
        contexts = rows[CONTEXT].copy()
        contexts["target_RNA"] = rows.gene
        contexts["cell_line_species"] = rows.cell_line_species.str.lower()
        rows["campaign"] = [
            identity(list(values))
            for values in contexts.itertuples(index=False, name=None)
        ]
        group_sizes = rows.groupby(["campaign", "compound"]).size()
        counts["duplicate_same_table_context_groups"] = int(group_sizes.gt(1).sum())
        counts["replicate_batch_identity_verified"] = False
        rows = rows.drop_duplicates(["campaign", "compound"]).set_index(ID, drop=False)
        counts["first_record_per_compound_context"] = len(rows)
        return rows, counts


def sequence_groups(sequences: list[str]) -> np.ndarray:
    """Port the Atlas development split's same-length <=2 edits / one-shift rule."""
    parent = list(range(len(sequences)))

    def root(i: int) -> int:
        while i != parent[i]:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for length in sorted({len(s) for s in sequences}):
        ids = [i for i, s in enumerate(sequences) if len(s) == length]
        x = np.array([list(sequences[i]) for i in ids])
        for i, current in enumerate(x):
            right = x[i + 1 :]
            close = (right != current).sum(axis=1) <= 2
            if length > 1:
                close |= (right[:, 1:] == current[:-1]).all(axis=1)
                close |= (right[:, :-1] == current[1:]).all(axis=1)
            for j in np.flatnonzero(close) + i + 1:
                a, b = root(ids[i]), root(ids[j])
                parent[max(a, b)] = min(a, b)
    return np.array([root(i) for i in range(len(sequences))])


ISOLATION = ("gene", "USPTO ID", "compound", "base", "scoped_compound")


def remove_overlap(
    rows: pd.DataFrame, other: pd.DataFrame, keys=ISOLATION
) -> pd.DataFrame:
    mask = np.ones(len(rows), dtype=bool)
    for key in keys:
        mask &= ~rows[key].isin(set(other[key]))
    return rows.loc[mask]


def _sample(rows: pd.DataFrame, n: int, salt: str) -> list[str]:
    if len(rows) < n:
        raise ValueError(f"Insufficient rows for {salt}: {len(rows)} < {n}")
    return sorted(rows.index, key=lambda row: identity([salt, row]))[:n]


def disjoint(rows: pd.DataFrame, groups: dict[str, list[str]]) -> None:
    seen = set()
    keys = []
    for part, ids in groups.items():
        if len(set(ids)) != len(ids) or seen.intersection(ids):
            raise ValueError(f"Duplicate row IDs in {part}")
        seen.update(ids)
        memberships = {key: set(rows.loc[ids, key]) for key in ISOLATION}
        for previous, prior in keys:
            overlap = {
                key: len(prior[key] & members) for key, members in memberships.items()
            }
            if any(overlap.values()):
                raise ValueError(f"{previous}/{part} leakage: {overlap}")
        keys.append((part, memberships))


class CampaignCapacityError(ValueError):
    """Metadata-only preflight failure, before any outcome access or fitting."""

    def __init__(self, receipt: dict) -> None:
        self.receipt = receipt
        super().__init__(
            f"Insufficient campaigns for {receipt['requested_candidate_count']} "
            f"candidates each: {receipt['role_counts']}; need two per role"
        )


def restrict_pools(
    campaigns: list[dict], config: dict
) -> tuple[list[dict], list[dict]]:
    """Uniform label-blind caps, preserving original roles and sentinel membership.

    Development/evaluation campaigns must supply the exact requested capacity.
    Training campaigns retain their original membership, capped at that capacity.
    No outcomes or alternate split seeds are used to rescue an undersized campaign.
    """
    capacity = config.get("candidate_pool_size")
    if capacity is None:
        return campaigns, []
    if type(capacity) is not int or capacity < config["total_assays"]:
        raise ValueError("Candidate capacity must cover the full assay budget")
    overrides = config.get("evaluation_pool_sizes")
    if overrides is not None and (
        not isinstance(overrides, dict)
        or not overrides
        or any(
            type(size) is not int or size < config["total_assays"]
            for size in overrides.values()
        )
    ):
        raise ValueError("Explicit evaluation capacities must cover the assay budget")
    kept, excluded = [], []
    for entry in campaigns:
        original = entry["pool"]
        limit = capacity
        if entry["role"] == "test" and overrides is not None:
            if entry["name"] not in overrides:
                excluded.append(
                    {
                        "name": entry["name"],
                        "role": entry["role"],
                        "available": len(original),
                        "reason": "outside_explicit_evaluation_targets",
                    }
                )
                continue
            limit = overrides[entry["name"]]
        if len(original) < limit and entry["role"] != "train":
            excluded.append(
                {
                    "name": entry["name"],
                    "role": entry["role"],
                    "available": len(original),
                    "required": limit,
                    "reason": "insufficient_label_blind_pool_capacity",
                }
            )
            continue
        rng = np.random.default_rng(
            int(identity([config["partition_seed"], entry["key"], "pool-cap"])[:16], 16)
        )
        pool = sorted(rng.choice(original, min(limit, len(original)), replace=False))
        initial = {}
        for seed in config["evaluation_seeds"]:
            rng = np.random.default_rng(seed)
            initial[str(seed)] = sorted(
                rng.choice(pool, config["initial_assays"], replace=False)
            )
        kept.append(
            entry
            | {"pool": pool, "initial": initial, "uncapped_pool_count": len(original)}
        )
    role_counts = {
        role: sum(c["role"] == role for c in kept) for role in ("train", "dev", "test")
    }
    if overrides is not None:
        observed = {c["name"] for c in kept if c["role"] == "test"}
        if observed != set(overrides):
            raise ValueError("An explicit evaluation target is missing or undersized")
    if min(role_counts.values()) < 2:
        raise CampaignCapacityError(
            {
                "status": "preflight_failed",
                "reason": "insufficient_campaign_capacity",
                "requested_candidate_count": capacity,
                "role_counts": role_counts,
                "capacity_exclusions": excluded,
                "outcomes_read": False,
                "predictors_fitted": False,
                "policies_trained": False,
            }
        )
    return kept, excluded


def prepare(atlas: Atlas, config: dict) -> tuple[pd.DataFrame, dict]:
    provenance = atlas.verify()
    rows, counts = atlas.metadata()
    choices = []
    for key, group in rows.groupby("campaign", sort=True):
        row = group.iloc[0]
        if len(group) >= config["min_campaign_size"] and (
            row.cell_line_species.lower() == "human"
            and row.gene not in {"HBV", "HCV", "HIV"}
        ):
            choices.append((row.gene, -len(group), key, row["USPTO ID"]))
    chosen: dict[str, str] = {}
    patents = set()
    for gene, _, key, patent in sorted(choices):
        if gene not in chosen and patent not in patents:
            chosen[gene] = key
            patents.add(patent)
    seed = config["partition_seed"]
    new = sorted(
        set(chosen) - HISTORICAL_DEVELOPMENT, key=lambda k: identity([seed, k])
    )
    if len(new) < 5 or len(set(chosen) & HISTORICAL_DEVELOPMENT) < 2:
        raise ValueError("Insufficient independent campaign roles")
    dev = set(new[:2])
    test = set(new[2:])
    candidates = rows.loc[rows.campaign.isin(chosen.values())]
    # Remove shared compound/base controls entirely from campaign roles.
    shared = {}
    for key in ("compound", "base", "scoped_compound"):
        levels = candidates.groupby(key).campaign.nunique()
        shared[key] = set(levels[levels.gt(1)].index)
    eligible = candidates.loc[
        ~np.logical_or.reduce(
            [candidates[key].isin(vals) for key, vals in shared.items()]
        )
    ]
    campaigns = []
    for gene, key in chosen.items():
        group = eligible.loc[eligible.campaign.eq(key)].sort_index()
        if len(group) < 100:
            raise ValueError(f"Not enough exclusive assay rows in {gene}")
        groups = sequence_groups(group.base.tolist())
        pool, sentinel = next(
            GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(
                group, groups=groups
            )
        )
        if len(pool) < config["total_assays"] or len(sentinel) < 20:
            raise ValueError(f"Pool or sentinel too small in {gene}")
        row = group.iloc[0]
        pool_ids = group.iloc[pool][ID].tolist()
        initial = config["initial_assays"]
        campaigns.append(
            {
                "name": gene,
                "key": key,
                "role": ("test" if gene in test else "dev" if gene in dev else "train"),
                "context": {
                    k: row[k].item() if hasattr(row[k], "item") else row[k]
                    for k in CONTEXT
                },
                "pool": pool_ids,
                "sentinel": group.iloc[sentinel][ID].tolist(),
                "initial": {
                    str(s): sorted(pool_ids, key=lambda i: identity([s, key, i]))[
                        :initial
                    ]
                    for s in config["evaluation_seeds"]
                },
                "sequence_groups": int(len(set(groups))),
            }
        )
    # Exclude every known row for policy targets, then split the source by patent.
    source = remove_overlap(rows, rows.loc[rows.gene.isin(chosen)])
    fit_idx, cal_idx = next(
        GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed).split(
            source, groups=source["USPTO ID"]
        )
    )
    raw_cal = source.iloc[cal_idx]
    raw_fit = remove_overlap(source.iloc[fit_idx], raw_cal)
    fit = _sample(raw_fit, config["source_fit_count"], f"fit-{seed}")
    cal = _sample(raw_cal, config["source_cal_count"], f"cal-{seed}")
    disjoint(
        rows,
        {
            "source_fit": fit,
            "source_cal": cal,
            **{c["name"]: c["pool"] + c["sentinel"] for c in campaigns},
        },
    )
    campaigns, excluded = restrict_pools(campaigns, config)
    counts |= {
        "campaigns": len(campaigns),
        "shared_campaign_rows_dropped": len(candidates) - len(eligible),
        "source_after_all_target_exclusions": len(source),
        "source_fit_eligible": len(raw_fit),
        "source_cal_eligible": len(raw_cal),
        "capacity_exclusions": excluded,
    }
    manifest = {
        "schema": 1,
        "config": config,
        "atlas": provenance,
        "counts": counts,
        "source_fit": fit,
        "source_cal": cal,
        "campaigns": campaigns,
    }
    manifest["identity"] = identity(manifest)
    return rows, manifest
