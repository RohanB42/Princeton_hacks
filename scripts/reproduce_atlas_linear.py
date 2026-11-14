"""Execute the pinned Atlas native linear efficacy anchor separately from our cohort.

Upstream fits the featurizer globally and aggregates max labels across contexts;
these are reproduced only in this isolated anchor, not adopted in target studies.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import GroupKFold


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--upstream", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    revision = subprocess.check_output(
        ["git", "-C", str(args.upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != "bb90c946013f183379da04678340e193088e5f99":
        raise ValueError(revision)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    sys.path.insert(0, str(args.upstream.resolve()))
    from analyses.utils import oligogym_adapter as adapter

    adapter._data_dir = args.output / "input"
    adapter._data_dir.mkdir()
    (adapter._data_dir / "in_vitro_inhibition_processed.parquet").symlink_to(
        Path("data/aso_atlas_2/release/in_vitro_inhibition.parquet").resolve()
    )
    t = time.monotonic()
    data = adapter.load_in_vitro_inhibition()
    from oligogym.features import OneHotEncoder

    feat = OneHotEncoder(encode_components=["base", "sugar", "phosphate"])
    x = feat.fit_transform(data["x"]).astype(np.float32)
    x = np.column_stack([x.reshape(len(x), -1), data["covariates"]])
    folds = pd.read_csv(
        "data/aso_atlas_2/release/folds/in_vitro_inhibition_folds.csv.gz"
    )
    mapping = folds.set_index("model_input_helm")["fold"].to_dict()
    assert len(mapping) == len(folds)
    declared = np.array([mapping.get(h, -1) for h in data["x"]])
    native = np.zeros(len(x), dtype=int)
    rows = []
    for i, (tr, te) in enumerate(GroupKFold(5).split(x, data["y"], data["groups"]), 1):
        native[te] = i
        model = (
            Ridge()
        )  # native LinearModel(type='ridge') delegates to sklearn defaults
        model.fit(x[tr], data["y"][tr])
        pred = model.predict(x[te])
        y = data["y"][te]
        rows.append(
            {
                "fold": i,
                "train": len(tr),
                "test": len(te),
                "pearson": float(pearsonr(y, pred).statistic),
                "spearman": float(spearmanr(y, pred).statistic),
                "rmse": float(mean_squared_error(y, pred) ** 0.5),
            }
        )
        print(rows[-1], flush=True)
    report = {
        "upstream_revision": revision,
        "samples": len(x),
        "features": x.shape[1],
        "supplied_fold_rows": len(folds),
        "unmatched_rows": int((declared < 0).sum()),
        "native_supplied_fold_disagreements": int((declared != native).sum()),
        "folds": rows,
        "elapsed_s": time.monotonic() - t,
        "caveats": [
            "native global featurizer fit for reproduction only",
            "native max aggregation across assay contexts",
            "published oligogym_benchmark.json missing from pinned checkout; "
            "numerical reproduction unverified",
        ],
        "mean": {
            k: float(np.mean([r[k] for r in rows]))
            for k in ["pearson", "spearman", "rmse"]
        },
        "adapter_sha256": hashlib.sha256(
            Path(adapter.__file__).read_bytes()
        ).hexdigest(),
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["mean"]))


if __name__ == "__main__":
    main()
