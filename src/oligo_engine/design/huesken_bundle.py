"""Frozen, reloadable Huesken RNA1 Ridge surrogate for restricted design."""

import hashlib
import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import numpy as np

BASES = "ACGU"
BASE_COLUMNS = {"C": 0, "G": 1, "U": 2}
FEATURE_VERSION = "huesken_rna1_19_position_onehot_A_reference_v1"
BUNDLE_VERSION = "huesken_ridge_surrogate_v1"


def encode_rna1(sequence: str) -> np.ndarray:
    """Encode precisely the RNA1 columns used by the existing Ridge baseline."""
    if len(sequence) != 19 or set(sequence) - set(BASES):
        raise ValueError("RNA1 proposal must contain exactly 19 A/C/G/U bases")
    vector = np.zeros(57, dtype=np.float64)
    for position, base in enumerate(sequence):
        if base != "A":
            vector[position * 3 + BASE_COLUMNS[base]] = 1.0
    return vector


@dataclass(frozen=True)
class HueskenRidgeBundle:
    """JSON-only numerical bundle; no Python object deserialization."""

    coefficients: tuple[float, ...]
    intercept: float
    alpha: float
    training_mean: float
    training_sd: float
    training_sequences: tuple[str, ...]
    training_ids_sha256: str
    source_sha256: str
    source_revision: str
    split_strategy: str
    split_seed: int
    label_description: str
    sklearn_version: str
    numpy_version: str

    def __post_init__(self) -> None:
        if len(self.coefficients) != 57:
            raise ValueError("Ridge bundle must have 57 feature coefficients")
        if not all(isfinite(value) for value in self.coefficients):
            raise ValueError("Nonfinite Ridge coefficients")
        if (
            not all(
                isfinite(value)
                for value in (
                    self.intercept,
                    self.alpha,
                    self.training_mean,
                    self.training_sd,
                )
            )
            or self.alpha <= 0
            or self.training_sd <= 0
        ):
            raise ValueError("Invalid Ridge numeric metadata")
        if not self.training_sequences or any(
            len(sequence) != 19 or set(sequence) - set(BASES)
            for sequence in self.training_sequences
        ):
            raise ValueError("Invalid training-domain RNA1 sequences")
        if self.split_strategy not in {"sequence_group", "target"}:
            raise ValueError("Unsupported bundle split strategy")
        if len(self.source_sha256) != 64 or len(self.training_ids_sha256) != 64:
            raise ValueError("Invalid source or training ID SHA256")

    def predict(self, sequences: tuple[str, ...]) -> np.ndarray:
        if not sequences:
            raise ValueError("At least one sequence is required")
        features = np.stack([encode_rna1(sequence) for sequence in sequences])
        values = features @ np.asarray(self.coefficients) + self.intercept
        if not np.isfinite(values).all():
            raise ValueError("Nonfinite frozen predictions")
        return values

    def nearest_training_distance(self, sequence: str) -> int:
        encode_rna1(sequence)
        return min(
            sum(a != b for a, b in zip(sequence, example, strict=True))
            for example in self.training_sequences
        )

    def identity(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()

    def to_bytes(self) -> bytes:
        data = {
            "bundle_version": BUNDLE_VERSION,
            "feature_version": FEATURE_VERSION,
            "modality": "unmodified_siRNA_sequence_proposal",
            "endpoint": "Huesken_reporter_inhibition",
            "target_context_supported": False,
            "chemistry_edits_supported": False,
            "uncertainty": "unavailable",
            **vars(self),
        }
        return (
            json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode()

    def save(self, path: Path) -> None:
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_bytes())

    @classmethod
    def load(cls, path: Path) -> "HueskenRidgeBundle":
        data = json.loads(path.read_text())
        expected = {
            "bundle_version": BUNDLE_VERSION,
            "feature_version": FEATURE_VERSION,
            "modality": "unmodified_siRNA_sequence_proposal",
            "endpoint": "Huesken_reporter_inhibition",
            "target_context_supported": False,
            "chemistry_edits_supported": False,
            "uncertainty": "unavailable",
        }
        if any(data.get(key) != value for key, value in expected.items()):
            raise ValueError("Bundle schema or scientific scope is incompatible")
        if set(data) != set(expected) | set(cls.__dataclass_fields__):
            raise ValueError("Bundle fields differ from the supported version")
        for key in expected:
            del data[key]
        data["coefficients"] = tuple(data["coefficients"])
        data["training_sequences"] = tuple(data["training_sequences"])
        return cls(**data)
