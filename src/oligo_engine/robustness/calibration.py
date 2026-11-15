"""Separate split-conformal residual calibration; no shifted-domain guarantee."""

from dataclasses import dataclass
from math import ceil, isfinite


@dataclass(frozen=True)
class ResidualIntervals:
    residuals: tuple[float, ...]
    calibration_ids: tuple[str, ...]

    @classmethod
    def fit(
        cls,
        ids: tuple[str, ...],
        means: tuple[float, ...],
        outcomes: tuple[float, ...],
    ) -> "ResidualIntervals":
        if (
            not ids
            or len(set(ids)) != len(ids)
            or not len(ids) == len(means) == len(outcomes)
        ):
            raise ValueError("Unique aligned calibration rows required")
        if any(not isfinite(x) for x in means + outcomes):
            raise ValueError("Nonfinite calibration input")
        return cls(
            tuple(sorted(abs(a - b) for a, b in zip(means, outcomes, strict=True))), ids
        )

    def interval(self, mean: float, alpha: float) -> dict:
        if not 0 < alpha < 1 or not isfinite(mean):
            raise ValueError("Invalid interval arguments")
        index = ceil((len(self.residuals) + 1) * (1 - alpha))
        if index > len(self.residuals):
            return {"status": "insufficient_calibration", "lower": None, "upper": None}
        q = self.residuals[index - 1]
        return {
            "status": "empirical_shift_diagnostic",
            "lower": mean - q,
            "upper": mean + q,
            "alpha": alpha,
            "guarantee_under_group_shift": False,
        }
