"""Real-checkpoint single-strand chemistry/adapter profile using source labels only."""

import gc
import json
import resource
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from oligo_engine.models.aso_rnafm import ASOPredictor

CHECKPOINT = Path(
    "/private/tmp/oligoal-rnafm-20261114/artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth"
)


def main() -> None:
    torch.set_num_threads(1)
    out = Path("artifacts/atlas-rnafm/fm-profile-v1")
    out.mkdir(exist_ok=False)
    m = json.loads(
        Path("artifacts/atlas-rnafm/preparation-v1/manifests.json").read_text()
    )
    f = pd.read_parquet(
        "artifacts/atlas-rnafm/preparation-v1/cohort.parquet"
    ).set_index("source_row_id", drop=False)
    y = f.pop("Inhibition_pct")
    ids = np.random.default_rng(510).permutation(m["source_train_ids"])[:50].tolist()
    receipts = []
    for adapt in [False, True]:
        t = time.monotonic()
        model = ASOPredictor(
            CHECKPOINT, Path("artifacts/atlas-rnafm/token-cache"), 510, adapt
        )
        if not adapt:
            sample = f.loc[ids[:8]]
            seq = [
                __import__("oligo_engine.atlas.chemistry", fromlist=["parse_helm"])
                .parse_helm(h)
                .natural_rna
                for h in sample["HELM Annotation"]
            ]
            cached = model.encoder.frozen(seq)
            with torch.no_grad():
                h, mask = model.encoder.forward(seq)
            parity = max(
                float(np.max(abs(a - h[i, : len(a)].numpy())))
                for i, a in enumerate(cached)
            )
        fit = model.fit(f.loc[ids], y.loc[ids].to_numpy(), epochs=1)
        source = model.snapshot()
        before = model.predict(f.loc[ids[:8]])
        model.fit(f.loc[ids[:25]], y.loc[ids[:25]].to_numpy(), epochs=1, source=source)
        model.restore(source)
        after = model.predict(f.loc[ids[:8]])
        assert np.array_equal(before, after)
        receipts.append(
            {
                "adapt": adapt,
                "fit": fit,
                "source_restore_exact": True,
                "total_s": time.monotonic() - t,
            }
        )
        del model, source
        gc.collect()
    report = {
        "receipts": receipts,
        "frozen_cached_batched_max_abs": parity,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "mps_available": torch.backends.mps.is_available(),
        "device": "cpu",
        "test_labels_accessed": False,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
