"""Acquired-only classical controls and chemistry/context encoding."""

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import pearsonr, spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

from .chemistry import parse_helm

CATEGORIES = ["cell_line", "cell_line_species", "transfection_method"]
BASES = ["A", "C", "G", "T", "U", "5meC"]
SUGARS = ["DNA", "MOE", "cEt", "RNA", "OMe"]
LINKS = ["PO", "PS", "END"]


def chemistry_matrix(frame: pd.DataFrame) -> sparse.csr_matrix:
    row, col = [], []
    width = len(BASES) + len(SUGARS) + len(LINKS)
    for i, raw in enumerate(frame["HELM Annotation"]):
        c = parse_helm(raw)
        for j, (b, s, linkage) in enumerate(zip(c.bases, c.sugars, c.links)):
            row.extend([i] * 3)
            col.extend(
                [
                    j * width + BASES.index(b),
                    j * width + len(BASES) + SUGARS.index(s),
                    j * width + len(BASES) + len(SUGARS) + LINKS.index(linkage),
                ]
            )
        row.append(i)
        col.append(64 * width + ["none", "PO", "PS"].index(c.terminal))
    return sparse.csr_matrix(
        (np.ones(len(row)), (row, col)),
        shape=(len(frame), 64 * width + 3),
        dtype=np.float32,
    )


def context_frame(frame: pd.DataFrame) -> pd.DataFrame:
    x = frame[CATEGORIES].copy()
    x["log_dose"] = np.log1p(frame.dosage_nm.to_numpy())
    x["log_hours"] = np.log1p(frame.treatment_period_hrs.to_numpy())
    return x


class Features:
    def __init__(self, chemistry: bool = True):
        self.chemistry = chemistry
        self.context = ColumnTransformer(
            [
                ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORIES),
                ("num", StandardScaler(), ["log_dose", "log_hours"]),
            ],
            sparse_threshold=1.0,
        )

    def fit(self, frame: pd.DataFrame) -> "Features":
        self.context.fit(context_frame(frame))
        return self

    def transform(self, frame: pd.DataFrame) -> sparse.csr_matrix:
        c = sparse.csr_matrix(self.context.transform(context_frame(frame)))
        return (
            sparse.hstack([chemistry_matrix(frame), c], format="csr")
            if self.chemistry
            else c
        )


class Classical:
    def __init__(self, kind: str, seed: int = 0):
        self.kind, self.seed = kind, seed

    def fit(self, frame: pd.DataFrame, labels: np.ndarray) -> "Classical":
        if "Inhibition_pct" in frame:
            raise ValueError("Predictor input must not contain labels")
        labels = np.asarray(labels, float)
        if len(frame) != len(labels) or not np.isfinite(labels).all():
            raise ValueError("Invalid fit labels")
        groups = frame["USPTO ID"].to_numpy()
        if len(set(groups)) < 3:
            groups = frame["natural_rna"].to_numpy()
        n = min(3, len(set(groups)))
        if n < 2:
            raise ValueError("Insufficient internal-validation groups")
        candidates = (
            [0.1, 10.0, 100.0] if self.kind != "xgb" else [(100, 3), (200, 3), (100, 6)]
        )
        scores = []
        for choice in candidates:
            errors = []
            for tr, va in GroupKFold(n).split(frame, groups=groups):
                feat = Features(self.kind != "context").fit(frame.iloc[tr])
                model = self._model(choice)
                model.fit(feat.transform(frame.iloc[tr]), labels[tr])
                errors.append(
                    mean_squared_error(
                        labels[va], model.predict(feat.transform(frame.iloc[va]))
                    )
                )
            scores.append(float(np.mean(errors)))
        self.choice = candidates[int(np.argmin(scores))]
        self.features = Features(self.kind != "context").fit(frame)
        self.model = self._model(self.choice)
        self.model.fit(self.features.transform(frame), labels)
        self.fit_ids = frame.source_row_id.tolist()
        self.cv_scores = scores
        return self

    def _model(self, choice):
        if self.kind == "xgb":
            return XGBRegressor(
                n_estimators=choice[0],
                max_depth=choice[1],
                learning_rate=0.05,
                tree_method="hist",
                n_jobs=1,
                random_state=self.seed,
                objective="reg:squarederror",
            )
        return Ridge(alpha=choice, solver="lsqr", tol=1e-6)

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        if "Inhibition_pct" in frame:
            raise ValueError("Predictor input must not contain labels")
        return self.model.predict(self.features.transform(frame))


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y, p = np.asarray(y), np.asarray(p)
    if len(y) != len(p) or not np.isfinite(p).all():
        raise ValueError("Invalid predictions")
    valid = len(y) > 1 and np.std(y) > 0 and np.std(p) > 0
    return {
        "n": len(y),
        "rmse": float(np.mean((y - p) ** 2) ** 0.5),
        "mae": float(np.mean(abs(y - p))),
        "pearson": float(pearsonr(y, p).statistic) if valid else None,
        "spearman": float(spearmanr(y, p).statistic) if valid else None,
    }
