"""Source metadata, partition-scoped outcomes, and independent frozen audit models."""

import csv
import gzip
import hashlib
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from typing import Callable

from oligo_engine.data.catalog import Catalog
from oligo_engine.provenance import identity
from oligo_engine.robustness.contracts import (
    AuditObservation,
    AuditPrediction,
    chemistry,
    records_hash,
)


class OutcomeCapability:
    """A fixed permitted-ID set, never passed to predictor or optimizer code."""

    def __init__(
        self, allowed: tuple[str, ...], reader: Callable[[tuple[str, ...]], dict]
    ) -> None:
        if len(set(allowed)) != len(allowed):
            raise ValueError("Duplicate permitted outcome IDs")
        self.__allowed, self.__reader = frozenset(allowed), reader
        self.accessed: list[str] = []

    def read(self, ids: tuple[str, ...]) -> dict[str, float]:
        if len(set(ids)) != len(ids) or not set(ids) <= self.__allowed:
            raise ValueError("Denied outcome access outside partition capability")
        values = self.__reader(ids)
        if set(values) != set(ids) or any(not isfinite(v) for v in values.values()):
            raise ValueError("Missing or nonfinite requested outcomes")
        self.accessed.extend(ids)
        return values


@dataclass(frozen=True)
class SourceMetadata:
    rows: tuple[AuditObservation, ...]
    receipt: dict
    _path: Path
    _prefix: str

    def outcomes(self, allowed: tuple[str, ...]) -> OutcomeCapability:
        def reader(ids: tuple[str, ...]) -> dict[str, float]:
            if (
                hashlib.sha256(self._path.read_bytes()).hexdigest()
                != self.receipt["source_sha256"]
            ):
                raise ValueError("Source bytes changed after metadata freeze")
            requested = set(ids)
            values = {}
            with gzip.open(self._path, "rt", newline="") as handle:
                for index, row in enumerate(csv.DictReader(handle)):
                    key = f"{self._prefix}:{index}"
                    if key in requested:
                        values[key] = float(row["y"])
            return values

        if not set(allowed) <= {r.sample_id for r in self.rows}:
            raise ValueError("Unknown permitted source IDs")
        return OutcomeCapability(allowed, reader)


def load_asoptimizer() -> SourceMetadata:
    """Read no endpoint values while constructing the original matched ASO view.

    CSV decoding sees source columns, but only explicitly selected IDs are parsed
    into numeric outcomes through separate capabilities. No Catalog.load(all-label)
    or OligoGym fitting factory is invoked.
    """
    catalog = Catalog()
    entry = catalog.resolve("Hwang_2024_1")
    path = catalog.verify_file(entry["data_file"])
    digest = catalog.manifest["files"][entry["data_file"]]["sha256"]
    prefix = f"{digest[:16]}:{entry['name']}"
    records, excluded = [], {}
    with gzip.open(path, "rt", newline="") as handle:
        for index, source in enumerate(csv.DictReader(handle)):
            try:
                parsed = chemistry(source["x"])
                if (
                    not 2 <= len(parsed.bases) <= 20
                    or set(parsed.bases) - set("ACGTU")
                    or set(parsed.sugars) - {"DNA", "MOE"}
                    or set(parsed.links) - {"PS", "PO", "END"}
                ):
                    raise ValueError("outside_matched_chemistry")
                records.append(
                    AuditObservation(
                        f"{prefix}:{index}",
                        source["x"],
                        source["targets"].strip(),
                        "asoptimizer_inhibition",
                        "source y percentage inhibition",
                        digest,
                        tuple(
                            (k, source.get(k, ""))
                            for k in ("cell_line", "concentration")
                        ),
                    )
                )
            except ValueError:
                excluded["unsupported_chemistry_or_parse"] = (
                    excluded.get("unsupported_chemistry_or_parse", 0) + 1
                )
    return SourceMetadata(
        tuple(records),
        {
            "dataset": entry["name"],
            "source_revision": catalog.manifest["upstream_revision"],
            "source_sha256": digest,
            "source_rows": entry["rows"],
            "eligible_rows": len(records),
            "excluded": excluded,
            "label_values_read": False,
            "patent_metadata_available": False,
            "prior_exposure": "internal_diagnostic_previously_studied",
            "endpoint_context": "source cell_line/concentration; no invented units",
            "eligibility": "DNA/MOE PS/PO unmodified bases length2-20",
        },
        path,
        prefix,
    )


BASES = ("A", "C", "G", "T", "U", "5meC")
SUGARS = ("DNA", "MOE")
LINKS = ("PS", "PO", "END")


def features(row: AuditObservation) -> list[float]:
    parsed = chemistry(row.helm)
    if (
        not 2 <= len(parsed.bases) <= 20
        or set(parsed.bases) - set(BASES)
        or set(parsed.sugars) - set(SUGARS)
        or set(parsed.links) - set(LINKS)
    ):
        raise ValueError("Unsupported feature scope")
    # Explicit absence indicators, never inferred molecular truncation. Full source
    # identity and lengths remain unchanged; this is a declared feature encoding.
    result = []
    for index in range(20):
        for track, alphabet in (
            (parsed.bases, BASES),
            (parsed.sugars, SUGARS),
            (parsed.links, LINKS),
        ):
            value = track[index] if index < len(track) else "ABSENT"
            result.extend(float(value == token) for token in alphabet + ("ABSENT",))
    result.extend(float(parsed.terminal == token) for token in ("none", "PO", "PS"))
    return result


class FrozenAuditModel:
    """Already-fitted classical model, no fit method or outcome capability."""

    def __init__(self, model: object, manifest: dict, contexts: frozenset) -> None:
        self.__model, self.manifest, self.__contexts = model, manifest, contexts

    def predict(
        self, rows: tuple[AuditObservation, ...]
    ) -> tuple[AuditPrediction, ...]:
        import numpy as np

        output = {}
        supported, matrix = [], []
        for row in rows:
            reason = None
            if (
                row.endpoint != self.manifest["endpoint"]
                or row.units != self.manifest["units"]
                or row.context not in self.__contexts
            ):
                reason = "CONTEXT_UNSUPPORTED"
            try:
                vector = features(row)
            except ValueError:
                reason = "CHEMISTRY_UNSUPPORTED"
            if reason:
                output[row.sample_id] = AuditPrediction(
                    row.sample_id,
                    self.manifest["model_id"],
                    None,
                    "out_of_domain",
                    reason,
                )
            else:
                supported.append(row)
                matrix.append(vector)
        if supported:
            x = np.asarray(matrix)
            means = self.__model.predict(x)
            spreads = (
                np.std([tree.predict(x) for tree in self.__model.estimators_], axis=0)
                if hasattr(self.__model, "estimators_")
                else [None] * len(supported)
            )
            for row, mean, spread in zip(supported, means, spreads, strict=True):
                output[row.sample_id] = AuditPrediction(
                    row.sample_id,
                    self.manifest["model_id"],
                    float(mean),
                    uncertainty=float(spread) if spread is not None else None,
                    uncertainty_type="rf_tree_sd_uncalibrated"
                    if spread is not None
                    else "none",
                )
        return tuple(output[r.sample_id] for r in rows)


def fit_model(
    rows: tuple[AuditObservation, ...],
    labels: dict[str, float],
    kind: str,
    seed: int,
) -> FrozenAuditModel:
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge

    if (
        not rows
        or set(labels) != {r.sample_id for r in rows}
        or len(labels) != len(rows)
        or any(not isfinite(v) for v in labels.values())
    ):
        raise ValueError("Fitting labels must align exactly with permitted rows")
    if len({(r.endpoint, r.units) for r in rows}) != 1:
        raise ValueError("Never pool endpoints or units")
    constructors = {
        "ridge": lambda: Ridge(alpha=10.0, solver="lsqr", tol=1e-8),
        "rf": lambda: RandomForestRegressor(
            n_estimators=64, max_depth=12, random_state=seed, n_jobs=1
        ),
    }
    if kind not in constructors:
        raise ValueError("Unsupported audit model")
    rows = tuple(sorted(rows, key=lambda r: r.sample_id))
    model = constructors[kind]()
    model.fit(
        np.asarray([features(r) for r in rows]), [labels[r.sample_id] for r in rows]
    )
    state = (
        [
            {
                "feature": tree.tree_.feature.tolist(),
                "threshold": tree.tree_.threshold.tolist(),
                "left": tree.tree_.children_left.tolist(),
                "right": tree.tree_.children_right.tolist(),
                "values": tree.tree_.value.tolist(),
            }
            for tree in model.estimators_
        ]
        if hasattr(model, "estimators_")
        else {
            "coefficients": model.coef_.tolist(),
            "intercept": float(model.intercept_),
        }
    )
    manifest = {
        "model_id": f"audit-{kind}-v1",
        "artifact_hash": identity(state),
        "endpoint": rows[0].endpoint,
        "units": rows[0].units,
        "direction": "higher_is_better",
        "seed": seed,
        "feature_schema": "source-chemistry-onehot20-absence-v1",
        "training_ids": [r.sample_id for r in rows],
        "training_hash": records_hash(rows),
        "training_mean": float(np.mean(list(labels.values()))),
        "hyperparameters": {
            k: v
            for k, v in model.get_params().items()
            if isinstance(v, (str, int, float, bool, type(None)))
        },
        "uses_assay_covariates": False,
        "context_gate": "exact fitting-supported context; no extrapolation",
        "fit_only": True,
        "historical_reproduction": False,
    }
    return FrozenAuditModel(model, manifest, frozenset(r.context for r in rows))


def portable_adapter(
    path: Path, sha256: str, allowed_fit_ids: tuple[str, ...]
) -> object:
    """Latest-main 20-mer bundle bridge; audit its true training membership first."""
    from oligo_engine.reward.portable import PortableEfficacy

    portable = PortableEfficacy(path, sha256)
    if not portable.bundle["training_ids"] or not set(
        portable.bundle["training_ids"]
    ) <= set(allowed_fit_ids):
        raise ValueError("blocked_artifact_overlap")

    class Adapter:
        manifest = {
            "model_id": "portable-supported-aso-ridge",
            "endpoint": "atlas_inhibition",
            "units": "inhibition percentage points",
            "artifact_sha256": sha256,
            "training_ids": portable.bundle["training_ids"],
            "context": asdict(portable.assay),
        }

        def predict(
            self, rows: tuple[AuditObservation, ...]
        ) -> tuple[AuditPrediction, ...]:
            output = []
            for row in rows:
                if (
                    row.endpoint != self.manifest["endpoint"]
                    or row.units != self.manifest["units"]
                    or dict(row.context)
                    != {k: str(v) for k, v in asdict(portable.assay).items()}
                ):
                    output.append(
                        AuditPrediction(
                            row.sample_id,
                            self.manifest["model_id"],
                            None,
                            "out_of_domain",
                            "CONTEXT_UNSUPPORTED",
                        )
                    )
                    continue
                try:
                    mean = portable.predict_helm(row.helm, portable.assay)
                except ValueError:
                    output.append(
                        AuditPrediction(
                            row.sample_id,
                            self.manifest["model_id"],
                            None,
                            "not_applicable",
                            "CHEMISTRY_UNSUPPORTED",
                        )
                    )
                    continue
                output.append(
                    AuditPrediction(row.sample_id, self.manifest["model_id"], mean)
                )
            return tuple(output)

    return Adapter()
