"""Stateless, label-free adapters over the pinned OligoGym featurizers.

OligoGym is imported lazily and verified loudly: a missing or mismatched upstream
environment raises ``UpstreamEnvironmentError`` rather than degrading silently.
Nothing here is fitted, so no featurizer state can depend on revealed, unrevealed or
held-out labels, or on which rows a predictor was fitted with.
"""

import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from oligo_engine.audit_upstream import PINNED_REVISION
from oligo_engine.contracts import Observation

REQUIRED_SKLEARN = "1.4.0"
# Canonical nucleobase alphabet: a data-independent constant, so the encoding does not
# depend on which rows are visible when a model is fitted.
BASE_ALPHABET = ("A", "C", "G", "T", "U")
# Huesken siRNAs are two 21-monomer strands (RNA1 + RNA2).
HUESKEN_MAX_SEQUENCE_LENGTH = 42


class UpstreamEnvironmentError(RuntimeError):
    """The pinned OligoGym environment is absent or does not match the audit."""


def verify_upstream_environment() -> dict:
    """Return identity of the upstream environment or raise; never skip silently."""
    try:
        import oligogym
    except ImportError as error:
        raise UpstreamEnvironmentError(
            "OligoGym is not importable. Install the pinned upstream environment "
            "(docs/upstream-verification.md, docs/gate1-resolution.md)."
        ) from error
    try:
        sklearn_version = version("scikit-learn")
    except PackageNotFoundError as error:
        raise UpstreamEnvironmentError("scikit-learn is not installed") from error
    if sklearn_version != REQUIRED_SKLEARN:
        raise UpstreamEnvironmentError(
            f"scikit-learn {REQUIRED_SKLEARN} is required, found {sklearn_version}"
        )
    package_dir = Path(oligogym.__file__).resolve().parent
    result = subprocess.run(
        ["git", "-C", str(package_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    head = result.stdout.strip() if result.returncode == 0 else None
    if head != PINNED_REVISION:
        raise UpstreamEnvironmentError(
            f"OligoGym must be a git checkout at {PINNED_REVISION}; found {head}"
        )
    return {
        "oligogym_revision": head,
        "scikit_learn": sklearn_version,
        "oligogym_path": str(package_dir),
    }


class OneHotBaseFeaturizer:
    """OligoGym ``OneHotEncoder`` over nucleobases with a fixed map and padding."""

    def __init__(
        self,
        max_sequence_length: int = HUESKEN_MAX_SEQUENCE_LENGTH,
        alphabet: tuple[str, ...] = BASE_ALPHABET,
    ):
        verify_upstream_environment()
        from oligogym.features import OneHotEncoder

        if max_sequence_length < 1 or len(set(alphabet)) != len(alphabet):
            raise ValueError("Positive length and unique alphabet are required")
        self.max_sequence_length = max_sequence_length
        self.alphabet = tuple(alphabet)
        maps = {
            "base": {
                base: [1 if i == j else 0 for j in range(len(alphabet))]
                for i, base in enumerate(alphabet)
            }
        }
        self._encoder = OneHotEncoder(
            encode_components=["base"],
            encoding_maps=maps,
            max_sequence_length=max_sequence_length,
        )

    @property
    def n_features(self) -> int:
        return self.max_sequence_length * len(self.alphabet)

    @property
    def config(self) -> dict:
        return {
            "featurizer": "oligogym.OneHotEncoder",
            "encode_components": ["base"],
            "alphabet": list(self.alphabet),
            "max_sequence_length": self.max_sequence_length,
            "n_features": self.n_features,
            "fitted": False,
        }

    def transform(self, observations: tuple[Observation, ...]):
        """Return an (n, n_features) float array; reject anything not representable."""
        import numpy as np
        from oligogym.features import _extract_monomers

        if not observations:
            raise ValueError("At least one observation is required")
        for row in observations:
            bases = _extract_monomers(row.sequence)["base"]
            if len(bases) > self.max_sequence_length:
                raise ValueError(
                    f"{row.sample_id}: {len(bases)} monomers exceed the fixed length "
                    f"{self.max_sequence_length}"
                )
            unknown = set(bases) - set(self.alphabet) - {"NA", "EMPTY"}
            if unknown or {"NA", "EMPTY"} & set(bases):
                raise ValueError(
                    f"{row.sample_id}: unsupported bases {sorted(unknown)}"
                )
        features = self._encoder.transform([row.sequence for row in observations])
        features = np.asarray(features, dtype=np.float64)
        return features.reshape(len(observations), -1)
