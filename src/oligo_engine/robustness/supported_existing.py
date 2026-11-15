"""Metadata-first replay of the preserved supported-profile ASO Ridge bundle."""

from collections import Counter
from pathlib import Path
from random import Random

from oligo_engine.provenance import identity
from oligo_engine.reward.portable import (
    PortableEfficacy,
    encode_sequence,
    supported_sequence,
)
from oligo_engine.robustness.existing import (
    ExistingSource,
    checked_bytes,
    validate_membership,
)


def prepare_supported(config: dict) -> ExistingSource:
    """Exclude training compounds, close analogues and patents without labels."""
    import numpy as np
    import pyarrow.parquet as pq

    cfg = config["supported"]
    model = PortableEfficacy(Path(cfg["primary"]), cfg["primary_sha256"])
    path = Path(cfg["source"])
    checked_bytes(path, cfg["source_sha256"])
    assay = model.context()
    raw = pq.read_table(
        path,
        columns=["source_row_id", "HELM Annotation", "USPTO ID", "target_RNA", *assay],
    ).to_pylist()
    training = dict(
        zip(model.bundle["training_ids"], model.training_sequences, strict=True)
    )
    indexed = {r["source_row_id"]: r for r in raw}
    if len(training) != 2000 or not set(training) <= set(indexed):
        raise ValueError("Supported checkpoint training membership is incomplete")
    patents = {indexed[i]["USPTO ID"] for i in training}
    matrix = np.asarray([list(s) for s in training.values()])
    rows, excluded = [], Counter()
    for r in raw:
        key = r["source_row_id"]
        if any(r[k] != v for k, v in assay.items()) or not isinstance(
            r["HELM Annotation"], str
        ):
            continue
        try:
            sequence = supported_sequence(r["HELM Annotation"])
        except ValueError:
            continue
        if key in training and sequence != training[key]:
            raise ValueError("Training ID/sequence provenance mismatch")
        if key not in training:
            if r["USPTO ID"] in patents:
                excluded["training_patent"] += 1
                continue
            bases = np.asarray(list(sequence))
            close = (
                ((matrix != bases).sum(axis=1) <= 2)
                | (matrix[:, 1:] == bases[:-1]).all(axis=1)
                | (matrix[:, :-1] == bases[1:]).all(axis=1)
            )
            if close.any():
                excluded["near_training"] += 1
                continue
        rows.append(
            {
                "sample_id": key,
                "helm": r["HELM Annotation"],
                "sequence": sequence,
                "compound_id": identity(sequence),
                "group": r["target_RNA"],
                "patent": r["USPTO ID"],
                "target": r["target_RNA"],
                "context": assay,
                "modality": "ASO",
            }
        )
    if {r["sample_id"] for r in rows if r["sample_id"] in training} != set(training):
        raise ValueError("Training context/chemistry coverage failure")
    heldout = [r for r in rows if r["sample_id"] not in training]
    # Connect evaluation patents, targets and exact compounds before partitioning.
    parent = list(range(len(heldout)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, row in enumerate(heldout):
        for field in ("patent", "target", "compound_id"):
            key = (field, row[field])
            if key in seen:
                a, b = find(i), find(seen[key])
                parent[max(a, b)] = min(a, b)
            seen[key] = i
    groups = sorted({find(i) for i in range(len(heldout))})
    if len(groups) < config["minimum_supported_components"]:
        raise ValueError("Insufficient independent evaluation components")
    Random(config["seed"]).shuffle(groups)
    # Outcome-free size constraint: consume the same shuffled order, without
    # changing seeds, until the minimum development row count is met.
    sizes = Counter(find(i) for i in range(len(heldout)))
    development = set(groups[: max(1, len(groups) // 3)])
    for group in groups:
        if sum(sizes[g] for g in development) >= config["minimum_development_rows"]:
            break
        development.add(group)
    roles = {"fit": list(training), "development": [], "final": []}
    for i, row in enumerate(heldout):
        row["group"] = str(find(i))
        roles["development" if find(i) in development else "final"].append(
            row["sample_id"]
        )
    audit = validate_membership(rows, roles)
    return ExistingSource(
        "supported",
        rows,
        roles,
        path,
        cfg["source_sha256"],
        {
            **audit,
            "context_coverage": {role: 1.0 for role in roles},
            "assay": assay,
            "excluded": dict(excluded),
            "modality": "ASO",
            "units": "inhibition percentage points",
            "task": "supported_context_historical_patent_replay",
            "component_counts": {
                role: len({r["group"] for r in heldout if r["sample_id"] in ids})
                for role, ids in roles.items()
                if role != "fit"
            },
            "calibration": "not_requested",
            "model_count": 1,
        },
    )


class FrozenSupported:
    """One preserved JSON model; no invented second model or uncertainty."""

    def __init__(self, source: ExistingSource, config: dict) -> None:
        self.source, self.cfg = source, config["supported"]
        self.model = PortableEfficacy(
            Path(self.cfg["primary"]), self.cfg["primary_sha256"]
        )

    def features(self, ids: list[str]) -> object:
        import numpy as np

        indexed = {r["sample_id"]: r for r in self.source.rows}
        return np.asarray([encode_sequence(indexed[i]["sequence"]) for i in ids])

    def predict(self, ids: list[str]) -> tuple[list[float], list[None], list[None]]:
        indexed = {r["sample_id"]: r for r in self.source.rows}
        values = [
            self.model.predict_helm(indexed[i]["helm"], self.model.assay) for i in ids
        ]
        return values, [None] * len(ids), [None] * len(ids)

    def parity(self, ids: list[str]) -> dict:
        import numpy as np

        probe = ids[:16]
        expected = (
            self.features(probe) @ np.asarray(self.model.coefficients)
            + self.model.intercept
        )
        actual = self.predict(probe)[0]
        error = float(np.max(np.abs(expected - actual)))
        order_error = max(
            abs(a - b)
            for a, b in zip(
                actual, reversed(self.predict(list(reversed(probe)))[0]), strict=True
            )
        )
        if max(error, order_error) > 1e-8:
            raise ValueError("Supported-model inference parity failed")
        return {
            "probe_rows": len(probe),
            "direct_wrapper_max_abs": error,
            "row_order_max_abs": order_error,
            "refit_calls": 0,
        }
