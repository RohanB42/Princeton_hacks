"""Label-blind grouped partitions and matched holdout-selected classical controls."""

from pathlib import Path

import numpy as np
import pandas as pd

from oligo_engine.atlas.baselines import Classical, Features, metrics


def grouped_validation(
    ids: list[str], groups: list[str], seed: int, fraction: float = 0.2
) -> dict:
    """Random group prefix nearest the desired row fraction, without using labels."""
    if len(ids) != len(groups) or len(set(ids)) != len(ids):
        raise ValueError("Invalid IDs/groups")
    unique, counts = np.unique(groups, return_counts=True)
    if len(unique) < 2 or not 0 < fraction < 1:
        raise ValueError("At least two groups and an interior fraction required")
    order = np.random.default_rng(seed).permutation(len(unique))
    totals = np.cumsum(counts[order])[:-1]
    take = 1 + int(np.argmin(abs(totals - fraction * len(ids))))
    validation_groups = set(unique[order[:take]])
    train = [i for i, g in zip(ids, groups) if g not in validation_groups]
    validation = [i for i, g in zip(ids, groups) if g in validation_groups]
    return {
        "fit_ids": train,
        "validation_ids": validation,
        "fit_groups": sorted(set(groups) - validation_groups),
        "validation_groups": sorted(validation_groups),
        "total_labels": len(ids),
        "fit_labels": len(train),
        "validation_labels": len(validation),
        "validation_fraction": len(validation) / len(ids),
        "seed": seed,
        "method": "random_group_prefix_nearest_20pct_rows",
    }


class HoldoutClassical(Classical):
    """Same candidate set as historical control; fit on explicit inner rows only."""

    def fit_validation(
        self,
        frame: pd.DataFrame,
        y: np.ndarray,
        validation: pd.DataFrame,
        validation_y: np.ndarray,
    ) -> dict:
        if "Inhibition_pct" in frame or "Inhibition_pct" in validation:
            raise ValueError("Labels in predictor records")
        if set(frame.source_row_id) & set(validation.source_row_id):
            raise ValueError("Fitting and validation overlap")
        if not np.isfinite(y).all() or not np.isfinite(validation_y).all():
            raise ValueError("Nonfinite labels")
        self.features = Features().fit(frame)
        x, vx = self.features.transform(frame), self.features.transform(validation)
        candidates = (
            [0.1, 10.0, 100.0] if self.kind != "xgb" else [(100, 3), (200, 3), (100, 6)]
        )
        candidates_metrics, models = [], []
        for choice in candidates:
            model = self._model(choice)
            model.fit(x, y)
            models.append(model)
            candidates_metrics.append(metrics(validation_y, model.predict(vx)))
        selected = int(np.argmin([m["rmse"] for m in candidates_metrics]))
        self.model, self.choice = models[selected], candidates[selected]
        self.fit_ids = frame.source_row_id.tolist()
        return {
            "ids": self.fit_ids,
            "validation_ids": validation.source_row_id.tolist(),
            "n_labels": len(frame),
            "validation_labels": len(validation),
            "total_fit_validation_labels": len(frame) + len(validation),
            "choice": self.choice,
            "candidates": candidates,
            "validation_metrics": candidates_metrics,
            "selected_validation_metrics": candidates_metrics[selected],
        }


def read_label_subset(path: Path, permitted_ids: list[str]) -> pd.Series:
    """Read only caller-authorized endpoint rows, excluding reserved outcomes."""
    if not permitted_ids or len(set(permitted_ids)) != len(permitted_ids):
        raise ValueError("Expected unique nonempty permitted IDs")
    selected = pd.read_parquet(
        path,
        columns=["source_row_id", "Inhibition_pct"],
        filters=[("source_row_id", "in", permitted_ids)],
    ).set_index("source_row_id")["Inhibition_pct"]
    if set(selected.index) != set(permitted_ids) or not selected.index.is_unique:
        raise ValueError("Endpoint selection did not match permitted IDs")
    return selected.loc[permitted_ids]


def validate_scaling_config(config: dict) -> None:
    """Reject settings the fixed-recipe implementation cannot actually honor."""
    fixed = {
        "lora_rank": 4,
        "lora_alpha": 8.0,
        "learning_rate": 0.001,
        "weight_decay": 0.0,
        "batch_size": 8,
        "threads": 1,
        "device": "cpu",
        "validation_fraction": 0.2,
    }
    for name, value in fixed.items():
        if config[name] != value:
            raise ValueError(f"Fixed-recipe runner requires {name}={value!r}")
    expected = [
        int(np.floor(f * config["source_denominator"]))
        for f in config["source_fractions"]
    ]
    if config["source_budgets"] != expected:
        raise ValueError("Source budgets disagree with their declared fractions")
    if len(config["source_seeds"]) != len(config["paired_target_seeds"]):
        raise ValueError("Every source seed needs one paired target seed")
    if config["reserved_targets_scored"] or config["external_source_validation_used"]:
        raise ValueError("This budgeted development study excludes reserved outcomes")
