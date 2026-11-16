"""Source-only Ridge and model-conditional residual Gaussian posteriors."""

from dataclasses import dataclass
from itertools import pairwise

import numpy as np
import pandas as pd
from scipy.linalg import cho_factor, cho_solve
from scipy.sparse import csr_matrix
from scipy.special import ndtr
from scipy.stats import norm, rankdata, spearmanr
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import Ridge
from sklearn.preprocessing import normalize

from oligo_engine.reward.chemistry import parse_helm


def encode(
    rows: pd.DataFrame, dimensions: int
) -> tuple[csr_matrix, np.ndarray, tuple[str, ...]]:
    """Fixed feature dictionaries, no fitting or labels at the encoding boundary."""
    records = []
    for helm, cell, species, transfection, dose, hours in rows[
        [
            "HELM Annotation",
            "cell_line",
            "cell_line_species",
            "transfection_method",
            "dosage_nm",
            "treatment_period_hrs",
        ]
    ].itertuples(index=False, name=None):
        c = parse_helm(helm)
        chemistry = [
            (f"{kind}:{i}:{v}", 1.0)
            for kind, values in (("b", c.bases), ("s", c.sugars), ("l", c.links))
            for i, v in enumerate(values)
        ]
        chemistry += [
            (f"k:{left}{right}", 1.0) for left, right in pairwise(c.natural_rna)
        ]
        chemistry.append((f"terminal:{c.terminal}", 1.0))
        assay = [
            (f"cell:{cell}", 1.0),
            (f"species:{species}", 1.0),
            (f"method:{transfection}", 1.0),
            ("log_dose", np.log1p(dose) / 4),
            ("log_time", np.log1p(hours) / 4),
        ]
        records.append((chemistry, assay))
    source = FeatureHasher(n_features=4096, input_type="pair").transform(
        chemistry + assay for chemistry, assay in records
    )
    molecular = normalize(
        FeatureHasher(n_features=dimensions, input_type="pair").transform(
            chemistry for chemistry, _ in records
        )
    ).toarray()
    seq = tuple(parse_helm(h).natural_rna for h in rows["HELM Annotation"])
    return source, molecular, seq


def source_model(x: csr_matrix, y: np.ndarray, alpha: float) -> Ridge:
    return Ridge(alpha=alpha, solver="lsqr", tol=1e-6).fit(x, y)


@dataclass(frozen=True)
class UncertaintyPrediction:
    mean: np.ndarray
    latent_std: np.ndarray | None
    noise_assumption_std: float | None
    predictive_std: np.ndarray | None
    fit_label_count: int
    model_version: str
    unit: str = "inhibition percentage points"
    aleatoric_std: None = None  # Batch identities are unverified.
    calibration_status: str = "model_conditional_empirical_audit"


class FrozenBelief:
    def __init__(self, prior: np.ndarray, noise: float) -> None:
        self.prior, self.noise = prior, noise

    def update(self, index: int, outcome: float) -> None:
        pass

    def predict(self) -> UncertaintyPrediction:
        return UncertaintyPrediction(
            self.prior,
            None,
            self.noise,
            np.full_like(self.prior, self.noise),
            0,
            "source-ridge-v1",
            calibration_status="constant_source_cal_residual_scale",
        )


class LinearBelief(FrozenBelief):
    """Bayesian linear correction with an intercept and fixed Gaussian noise."""

    def __init__(self, prior: np.ndarray, x: np.ndarray, noise: float) -> None:
        super().__init__(prior, noise)
        self.x = np.column_stack((np.ones(len(x)), x))
        self.cov = np.eye(self.x.shape[1]) * noise**2
        self.weights = np.zeros(self.x.shape[1])
        self.count = 0

    def update(self, index: int, outcome: float) -> None:
        x = self.x[index]
        gain = self.cov @ x
        total = self.noise**2 + x @ gain
        self.weights += gain * (outcome - self.prior[index] - x @ self.weights) / total
        self.cov -= np.outer(gain, gain) / total
        self.count += 1

    def predict(self) -> UncertaintyPrediction:
        latent = np.maximum(np.sum((self.x @ self.cov) * self.x, axis=1), 0)
        return UncertaintyPrediction(
            self.prior + self.x @ self.weights,
            np.sqrt(latent),
            self.noise,
            np.sqrt(latent + self.noise**2),
            self.count,
            "bayes-linear-residual-v1",
        )


class GPBelief(FrozenBelief):
    """Fixed RBF + offset residual reference, exact conditioning at small budgets."""

    def __init__(self, prior: np.ndarray, x: np.ndarray, noise: float) -> None:
        super().__init__(prior, noise)
        self.x, self.indices, self.residuals = x, [], []

    def update(self, index: int, outcome: float) -> None:
        self.indices.append(index)
        self.residuals.append(outcome - self.prior[index])

    def _kernel(self, left: np.ndarray, right: np.ndarray) -> np.ndarray:
        distances = (left**2).sum(1)[:, None] + (right**2).sum(1) - 2 * left @ right.T
        return self.noise**2 * (1 + np.exp(-np.maximum(distances, 0) / 2))

    def predict(self) -> UncertaintyPrediction:
        latent = np.full(len(self.x), 2 * self.noise**2)
        mean = self.prior
        if self.indices:
            observed = self.x[self.indices]
            cross = self._kernel(self.x, observed)
            covariance = self._kernel(observed, observed)
            covariance.flat[:: len(observed) + 1] += self.noise**2
            factor = cho_factor(covariance)
            mean = mean + cross @ cho_solve(factor, self.residuals)
            latent -= (cross * cho_solve(factor, cross.T).T).sum(axis=1)
        latent = np.maximum(latent, 0)
        return UncertaintyPrediction(
            mean,
            np.sqrt(latent),
            self.noise,
            np.sqrt(latent + self.noise**2),
            len(self.indices),
            "fixed-rbf-gp-residual-v1",
        )


def uncertainty_metrics(y: np.ndarray, pred: UncertaintyPrediction) -> dict:
    error = y - pred.mean
    sigma = pred.predictive_std
    if sigma is None or not np.isfinite(sigma).all() or (sigma <= 0).any():
        raise ValueError("A positive predictive scale is required")
    absolute = np.abs(error)
    z = error / sigma
    rho = (
        None
        if np.ptp(sigma) == 0 or np.ptp(absolute) == 0
        else float(spearmanr(rankdata(sigma), rankdata(absolute)).statistic)
    )
    return {
        "rows": len(y),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "mae": float(absolute.mean()),
        "nll": float(np.mean(np.log(sigma * np.sqrt(2 * np.pi)) + z**2 / 2)),
        "crps": float(
            np.mean(
                sigma * (z * (2 * ndtr(z) - 1) + 2 * norm.pdf(z) - 1 / np.sqrt(np.pi))
            )
        ),
        "scale_error_spearman": rho,
        "intervals": {
            str(level): {
                "coverage": float(np.mean(np.abs(z) <= norm.ppf((1 + level) / 2))),
                "mean_width": float(2 * norm.ppf((1 + level) / 2) * sigma.mean()),
            }
            for level in (0.5, 0.8, 0.9)
        },
    }
