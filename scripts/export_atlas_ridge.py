"""Export one trusted published Atlas Ridge in its pinned owner runtime.

Run with the pinned research checkout on PYTHONPATH. Verifies code and artifact
before trusted pickle loading; never calls fit or reads measurement outcomes.
"""

import argparse
import hashlib
import json
import pickle
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--owner-checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repository / "model_checkpoints"
    inventory = json.loads((root / "manifest.json").read_text())
    entries = [e for e in inventory["checkpoints"] if e["path"] == args.checkpoint]
    if len(entries) != 1 or not args.checkpoint.endswith("ridge/model.pkl"):
        raise ValueError("Select exactly one published Ridge artifact")
    entry = entries[0]
    revision = subprocess.check_output(
        ["git", "-C", str(args.owner_checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if not revision.startswith(entry["loader_code_commit"]):
        raise ValueError("Owner code revision mismatch")
    if subprocess.check_output(
        ["git", "-C", str(args.owner_checkout), "diff", "HEAD", "--", "src"]
    ):
        raise ValueError("Owner inference source has uncommitted changes")
    import numpy as np
    import pandas as pd

    import oligo_engine.atlas.baselines as owner

    if not Path(owner.__file__).resolve().is_relative_to(args.owner_checkout.resolve()):
        raise ValueError("Imported owner classes from the wrong checkout")
    raw = (root / entry["path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ValueError("Checkpoint integrity failure")
    model = pickle.loads(raw)  # Only the manifest-verified trusted project artifact.
    transformer = model.features.context
    categories = transformer.named_transformers_["cat"].categories_
    scaler = transformer.named_transformers_["num"]
    bundle = {
        "schema": "atlas-ridge-inference-v1",
        "source_artifact": entry,
        "owner_revision": revision,
        "features": {
            "bases": owner.BASES,
            "sugars": owner.SUGARS,
            "links": owner.LINKS,
            "categories": {k: list(v) for k, v in zip(owner.CATEGORIES, categories)},
            "numeric_mean": scaler.mean_.tolist(),
            "numeric_scale": scaler.scale_.tolist(),
        },
        "coefficients": model.model.coef_.tolist(),
        "intercept": float(model.model.intercept_),
        "training_ids": model.fit_ids,
        "chemistry": model.features.chemistry,
        "runtime": {"numpy": np.__version__, "pandas": pd.__version__},
        "scope": "inference parity only; scientific support not inferred",
    }
    # Direct owner predictions are label-free parity anchors, not normalization data.
    anchors = []
    context = {k: str(v[0]) for k, v in zip(owner.CATEGORIES, categories)}
    context.update(dosage_nm=4500.0, treatment_period_hrs=24.0)
    for n in (18, 20):
        for sugar in ("moe", "cet"):
            seq = ("ACGT" * 5)[:n]
            units = [
                (f"[{sugar}]" if i < 4 or i >= n - 4 else "d")
                + f"({b})"
                + ("[sp]" if i < n - 1 else "")
                for i, b in enumerate(seq)
            ]
            helm = "RNA1{" + ".".join(units) + "}$$$$"
            anchors.append({"HELM Annotation": helm, **context})
    frame = pd.DataFrame(anchors)
    expected = model.predict(frame)
    bundle["parity_anchors"] = [
        {"input": x, "mean": float(y)} for x, y in zip(anchors, expected)
    ]
    bundle["batch_reverse_parity"] = bool(
        np.allclose(
            model.predict(frame.iloc[::-1]), expected[::-1], rtol=1e-10, atol=1e-10
        )
    )
    if not bundle["batch_reverse_parity"]:
        raise ValueError("Owner batch parity failed")
    # Restore training-only prediction references, without reading any label column.
    from oligo_engine.atlas.data import SOURCE_SHA

    source = args.repository / "data/aso_atlas_2/release/in_vitro_inhibition.parquet"
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("Pinned Atlas source hash mismatch")
    columns = [
        "HELM Annotation",
        *owner.CATEGORIES,
        "dosage_nm",
        "treatment_period_hrs",
    ]
    metadata = pd.read_parquet(source, columns=columns)
    indices = [int(i.split(":")[1]) for i in model.fit_ids]
    if any(i.split(":")[0] != "in_vitro_inhibition" for i in model.fit_ids):
        raise ValueError("Unexpected source row identity")
    training = metadata.iloc[indices]
    bundle["training_prediction_reference"] = model.predict(training).tolist()
    bundle["reference_ids"] = list(model.fit_ids)
    bundle["source_hash"] = SOURCE_SHA
    bundle["metadata_columns_read"] = columns
    receipt_path = (
        args.owner_checkout
        / "artifacts/atlas-rnafm/scaling-v1"
        / Path(entry["path"]).parent.name
        / "receipt.json"
    )
    receipt_raw = receipt_path.read_bytes()
    if hashlib.sha256(receipt_raw).hexdigest() != entry["source_receipt_sha256"]:
        raise ValueError("Source selection receipt hash mismatch")
    selection_receipt = json.loads(receipt_raw)
    bundle["validation_ids"] = selection_receipt["validation_ids"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(bundle, stream, indent=2, allow_nan=False)
    print(
        json.dumps(
            {
                "export": str(args.output),
                "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                "anchors": len(anchors),
                "training_ids": len(model.fit_ids),
            }
        )
    )


if __name__ == "__main__":
    main()
