"""Preflight and frozen inference for actual owner-local saved predictors.

No fitting or fallback model construction exists in this module. Joblib is used
only after explicit caller trust and pinned hash/runtime checks.
"""

import csv
import gzip
import hashlib
import json
import math
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from random import Random

from oligo_engine.contracts import Observation
from oligo_engine.data.catalog import Catalog
from oligo_engine.provenance import identity
from oligo_engine.robustness.adapters import OutcomeCapability
from oligo_engine.robustness.contracts import chemistry


def checked_bytes(path: Path, expected: str) -> bytes:
    value = path.read_bytes()
    if hashlib.sha256(value).hexdigest() != expected:
        raise ValueError(f"Hash mismatch: {path}")
    return value


def checked_json(path: Path, expected: str) -> dict:
    return json.loads(checked_bytes(path, expected))


def load_existing(
    path: Path, expected: str, sklearn_version: str, trusted: bool
) -> object:
    checked_bytes(path, expected)
    if not trusted:
        raise ValueError(
            "Owner-local checkpoint trust must be explicit before unpickling"
        )
    import joblib
    import sklearn
    from sklearn.exceptions import InconsistentVersionWarning

    if sklearn.__version__ != sklearn_version:
        raise ValueError(
            "Checkpoint runtime mismatch; use its isolated verified runtime"
        )
    with warnings.catch_warnings():
        warnings.simplefilter("error", InconsistentVersionWarning)
        return joblib.load(path)


def validate_membership(rows: list[dict], roles: dict[str, list[str]]) -> dict:
    mapping = {r["sample_id"]: r for r in rows}
    ids = [i for part in roles.values() for i in part]
    if (
        len(mapping) != len(rows)
        or len(ids) != len(set(ids))
        or set(ids) != set(mapping)
    ):
        raise ValueError("Incomplete or overlapping source ID partitions")
    if not all(roles.values()):
        raise ValueError("No evaluable cohort: every declared role must be nonempty")
    seen = {}
    for role, members in roles.items():
        for key in members:
            compound = mapping[key]["compound_id"]
            if compound in seen and seen[compound] != role:
                raise ValueError("Cross-partition chemical overlap")
            seen[compound] = role
    return {
        "counts": {k: len(v) for k, v in roles.items()},
        "chemical_overlap": 0,
        "training_overlap": 0,
    }


@dataclass
class ExistingSource:
    suite: str
    rows: list[dict]
    roles: dict[str, list[str]]
    source_path: Path
    source_hash: str
    receipt: dict

    def outcomes(self, role: str) -> OutcomeCapability:
        allowed = tuple(self.roles[role])

        def read(ids: tuple[str, ...]) -> dict[str, float]:
            checked_bytes(self.source_path, self.source_hash)
            if self.suite in ("atlas", "supported"):
                import pyarrow.parquet as pq

                values = pq.read_table(
                    self.source_path,
                    columns=["source_row_id", "Inhibition_pct"],
                    filters=[("source_row_id", "in", list(ids))],
                ).to_pylist()
                if len(values) != len(ids):
                    raise ValueError("Exact outcome join is not unique/complete")
                return {r["source_row_id"]: float(r["Inhibition_pct"]) for r in values}
            requested = set(ids)
            output = {}
            with gzip.open(self.source_path, "rt", newline="") as handle:
                for index, row in enumerate(csv.DictReader(handle)):
                    key = f"{self.source_hash[:16]}:Ichihara_2007_1:{index}"
                    if key in requested:
                        output[key] = float(row["y"])
            return output

        return OutcomeCapability(allowed, read)


def prepare_huesken(config: dict) -> ExistingSource:
    cfg = config["huesken"]
    protocol = checked_json(Path(cfg["protocol"]), cfg["protocol_sha256"])
    catalog = Catalog()
    entry = catalog.resolve("Huesken")
    path = catalog.verify_file(entry["data_file"])
    digest = catalog.manifest["files"][entry["data_file"]]["sha256"]
    training = protocol["training_ids"]
    rows = []
    with gzip.open(path, "rt", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            rows.append(
                {
                    "sample_id": f"{digest[:16]}:Ichihara_2007_1:{index}",
                    "helm": row["x"],
                    "group": row["targets"],
                    "compound_id": identity(row["x"]),
                    "context": {},
                    "modality": "siRNA",
                    "endpoint": "Huesken_inhibition",
                }
            )
    mapping = {r["sample_id"]: r for r in rows}
    if (
        len(training) != 1944
        or len(set(training)) != len(training)
        or not set(training) <= set(mapping)
    ):
        raise ValueError("Existing GP/RF training manifest does not match source")
    holdout = [r for r in rows if r["sample_id"] not in set(training)]
    # Same-source historical holdout, not a new-target benchmark.
    parent = {r["group"]: r["group"] for r in holdout}
    if "" in parent:
        raise ValueError("Missing source target IDs")

    def find(group: str) -> str:
        while parent[group] != group:
            group = parent[group]
        return group

    compounds = {}
    for row in holdout:
        group = row["group"]
        if row["compound_id"] in compounds:
            a, b = find(group), find(compounds[row["compound_id"]])
            parent[max(a, b)] = min(a, b)
        compounds[row["compound_id"]] = group
    components = sorted({find(r["group"]) for r in holdout})
    Random(config["seed"]).shuffle(components)
    development = set(components[: math.ceil(len(components) / 3)])
    roles = {
        "fit": training,
        "development": [
            r["sample_id"] for r in holdout if find(r["group"]) in development
        ],
        "final": [
            r["sample_id"] for r in holdout if find(r["group"]) not in development
        ],
    }
    audit = validate_membership(rows, roles)
    return ExistingSource(
        "huesken",
        rows,
        roles,
        path,
        digest,
        {
            **audit,
            "source_revision": catalog.manifest["upstream_revision"],
            "context_coverage": {k: 1.0 for k in roles},
            "modality": "siRNA",
            "endpoint": "Huesken_inhibition",
            "units": "source inhibition percentage",
            "task": "historical_sequence_holdout_not_unseen_target",
            "protocol_sha256": cfg["protocol_sha256"],
            "calibration": "not_requested",
            "target_counts": {
                k: dict(Counter(mapping[i]["group"] for i in v))
                for k, v in roles.items()
            },
        },
    )


def prepare_atlas(config: dict) -> ExistingSource:
    import pyarrow.parquet as pq

    cfg = config["atlas"]
    protocol = checked_json(Path(cfg["protocol"]), cfg["protocol_sha256"])
    manifest = checked_json(Path(cfg["manifest"]), cfg["manifest_sha256"])
    path = Path(cfg["source"])
    checked_bytes(path, cfg["source_sha256"])
    if (
        protocol["source_sha256"] != cfg["source_sha256"]
        or manifest["source_sha256"] != cfg["source_sha256"]
    ):
        raise ValueError("Existing artifact/source identities disagree")
    roles = {
        "fit": protocol["split_ids"]["train"],
        "development": protocol["split_ids"]["validation"],
        "final": protocol["split_ids"]["final"],
    }
    if (
        hashlib.sha256("\n".join(roles["fit"]).encode()).hexdigest()
        != manifest["training_ids_sha256"]
    ):
        raise ValueError("Original training-ID hash mismatch")
    ids = sum(roles.values(), [])
    columns = ["source_row_id", "HELM Annotation", "USPTO ID", "target_RNA"] + list(
        cfg["assay"]
    )
    values = pq.read_table(
        path, columns=columns, filters=[("source_row_id", "in", ids)]
    ).to_pylist()
    rows = []
    for raw in values:
        parsed = chemistry(raw["HELM Annotation"])
        if (
            len(parsed.bases) != 20
            or parsed.sugars != ("MOE",) * 5 + ("DNA",) * 10 + ("MOE",) * 5
            or parsed.links != ("PS",) * 19 + ("END",)
            or parsed.terminal != "none"
            or any(b == "C" for b in parsed.bases)
        ):
            raise ValueError("Checkpoint chemistry coverage failure")
        if any(raw[k] != v for k, v in cfg["assay"].items()):
            raise ValueError("No evaluable cohort: unsupported fixed assay context")
        rows.append(
            {
                "sample_id": raw["source_row_id"],
                "helm": raw["HELM Annotation"],
                "compound_id": parsed.identity,
                "group": raw["USPTO ID"],
                "target": raw["target_RNA"],
                "patent": raw["USPTO ID"],
                "sequence": parsed.natural_rna.replace("U", "T"),
                "context": dict(cfg["assay"]),
                "modality": "ASO",
                "endpoint": "Atlas_pilot_inhibition",
            }
        )
    audit = validate_membership(rows, roles)
    mapping = {r["sample_id"]: r for r in rows}
    patents = {
        role: {mapping[i]["patent"] for i in members} for role, members in roles.items()
    }
    if any(
        patents[a] & patents[b]
        for a, b in (("fit", "development"), ("fit", "final"), ("development", "final"))
    ):
        raise ValueError("Existing patent groups cross evaluation roles")
    # Use the historical connected-component membership, not nominal patent counts.
    components = protocol["patent_components"]
    for row in rows:
        row["group"] = next(
            str(i) for i, c in enumerate(components) if row["patent"] in c
        )
    return ExistingSource(
        "atlas",
        rows,
        roles,
        path,
        cfg["source_sha256"],
        {
            **audit,
            "context_coverage": {k: 1.0 for k in roles},
            "modality": "ASO",
            "endpoint": "Atlas_pilot_inhibition",
            "units": "inhibition percentage points",
            "assay": cfg["assay"],
            "calibration": "not_requested_insufficient_groups",
            "task": "existing_patent_component_holdout_internal_replay",
            "target_counts": {
                k: dict(Counter(mapping[i]["target"] for i in v))
                for k, v in roles.items()
            },
            "component_counts": {
                k: len({mapping[i]["group"] for i in v}) for k, v in roles.items()
            },
        },
    )


class FrozenExistingPair:
    def __init__(self, source: ExistingSource, config: dict, trusted: bool):
        import numpy as np

        cfg = config[source.suite]
        self.source, self.suite = source, source.suite
        self.models = tuple(
            load_existing(Path(cfg[k]), cfg[k + "_sha256"], cfg["sklearn"], trusted)
            for k in ("primary", "secondary")
        )
        self.cfg = cfg
        if self.suite == "huesken":
            for model in self.models:
                if (
                    model.environment["oligogym_revision"]
                    != "97f5b9f58d9e445a8ecb0218037af7465c3708c0"
                ):
                    raise ValueError("Unsupported frozen OligoGym revision")
            fitting = self.features(source.roles["fit"])
            gp_fit = np.asarray(self.models[0].model.model.X_train_)
            if Counter(row.tobytes() for row in fitting) != Counter(
                row.tobytes() for row in gp_fit
            ):
                raise ValueError(
                    "Embedded GP training features disagree with training IDs"
                )
        elif any(model.n_features_in_ != 80 for model in self.models):
            raise ValueError("Atlas artifact feature schema mismatch")

    def observations(self, ids: list[str]) -> tuple[Observation, ...]:
        mapping = {r["sample_id"]: r for r in self.source.rows}
        return tuple(
            Observation(
                i,
                mapping[i]["helm"],
                mapping[i]["group"],
                "siRNA",
                "source_HELM",
                "Huesken_reporter",
            )
            for i in ids
        )

    def features(self, ids: list[str]) -> object:
        import numpy as np

        if self.suite == "huesken":
            return np.asarray(
                self.models[0].featurizer.transform(self.observations(ids))
            )
        mapping = {r["sample_id"]: r for r in self.source.rows}
        return np.asarray(
            [
                [float(base == b) for base in mapping[i]["sequence"] for b in "ACGT"]
                for i in ids
            ],
            dtype=float,
        )

    def predict(
        self, ids: list[str]
    ) -> tuple[list[float], list[float], list[float | None]]:
        import numpy as np

        x = self.features(ids)
        if self.suite == "huesken":
            outputs = [m.predict(self.observations(ids)) for m in self.models]
            means = [[float(p.mean) for p in output] for output in outputs]
            warning = [float(p.uncertainty) for p in outputs[0]]
        else:
            means = [m.predict(x).tolist() for m in self.models]
            warning = [None] * len(ids)
        if not all(np.isfinite(v) for mean in means for v in mean):
            raise ValueError("Existing model produced nonfinite predictions")
        return means[0], means[1], warning

    def parity(self, ids: list[str]) -> dict:
        import numpy as np

        probe = ids[:16]
        means = self.predict(probe)
        reverse = self.predict(list(reversed(probe)))
        error = max(
            abs(a - b)
            for left, right in zip(means[:2], reverse[:2], strict=True)
            for a, b in zip(left, reversed(right), strict=True)
        )
        x = self.features(probe)
        direct = (
            [
                self.models[0].model.model.predict(x),
                self.models[1].model.model.predict(x),
            ]
            if self.suite == "huesken"
            else [
                x @ self.models[0].coef_ + self.models[0].intercept_,
                self.models[1].predict(x),
            ]
        )
        direct_error = max(
            float(np.max(np.abs(np.asarray(a) - b)))
            for a, b in zip(means[:2], direct, strict=True)
        )
        if max(error, direct_error) > 1e-8:
            raise ValueError("Frozen predictor parity failed")
        return {
            "probe_rows": len(probe),
            "row_order_max_abs": error,
            "direct_wrapper_max_abs": direct_error,
            "refit_calls": 0,
        }
