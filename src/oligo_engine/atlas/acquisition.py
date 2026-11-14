"""Batch policies over fixed source-trained geometry, with no label argument."""

import numpy as np


def select_batch(
    kind: str,
    features: np.ndarray,
    labeled: list[int],
    eligible: list[int],
    size: int,
    rng: np.random.Generator,
) -> list[int]:
    if (
        size > len(eligible)
        or set(labeled) & set(eligible)
        or len(set(eligible)) != len(eligible)
    ):
        raise ValueError("Invalid eligible set or batch size")
    if kind == "random":
        return rng.choice(eligible, size, replace=False).tolist()
    x = np.asarray(features, float)
    if not np.isfinite(x).all():
        raise ValueError("Nonfinite features")
    remaining = np.array(eligible, dtype=int)
    if kind == "diversity":
        distances = (
            ((x[remaining, None, :] - x[labeled][None, :, :]) ** 2)
            .sum(axis=-1)
            .min(axis=1)
        )
        chosen = []
        for _ in range(size):
            j = int(np.argmax(distances))
            i = int(remaining[j])
            chosen.append(i)
            distances = np.minimum(distances, ((x[remaining] - x[i]) ** 2).sum(axis=1))
            distances[j] = -np.inf
        return chosen
    covariance = np.linalg.inv(np.eye(x.shape[1]) + x[labeled].T @ x[labeled])
    transformed = x[remaining] @ covariance
    variances = np.einsum("ij,ij->i", transformed, x[remaining])
    if kind == "uncertainty":
        return remaining[np.argsort(-variances, kind="stable")[:size]].tolist()
    if kind != "maxdet":
        raise ValueError(kind)
    chosen = []
    available = np.ones(len(remaining), bool)
    # Conditional rank-one posterior update after each selected point.
    for _ in range(size):
        scores = np.where(available, variances, -np.inf)
        j = int(np.argmax(scores))
        i = int(remaining[j])
        chosen.append(i)
        available[j] = False
        v = covariance @ x[i]
        denominator = 1.0 + float(x[i] @ v)
        covariance -= np.outer(v, v) / denominator
        transformed = x[remaining] @ covariance
        variances = np.maximum(np.einsum("ij,ij->i", transformed, x[remaining]), 0.0)
    return chosen
