"""Trusted pinned-owner Atlas inference process. Inputs contain no outcomes."""

import argparse
import contextlib
import hashlib
import json
import pickle
import subprocess
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repository", type=Path, required=True)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--owner-checkout", type=Path, required=True)
    p.add_argument("--backbone", type=Path)
    p.add_argument("--cache", type=Path)
    p.add_argument("--adapt", action="store_true")
    args = p.parse_args()
    root = args.repository / "model_checkpoints"
    manifest = json.loads((root / "manifest.json").read_text())
    matches = [e for e in manifest["checkpoints"] if e["path"] == args.checkpoint]
    if len(matches) != 1 or not matches[0]["family"].startswith("atlas-"):
        raise ValueError("Exactly one inventoried Atlas checkpoint required")
    entry = matches[0]
    revision = subprocess.check_output(
        ["git", "-C", str(args.owner_checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if not revision.startswith(entry["loader_code_commit"]):
        raise ValueError("Owner revision mismatch")
    if subprocess.check_output(
        ["git", "-C", str(args.owner_checkout), "diff", "HEAD", "--", "src"]
    ):
        raise ValueError("Owner source is modified")
    path = root / entry["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise ValueError("Checkpoint hash mismatch")
    with contextlib.redirect_stdout(sys.stderr):
        import pandas as pd

        import oligo_engine.atlas.baselines as owner

        if (
            not Path(owner.__file__)
            .resolve()
            .is_relative_to(args.owner_checkout.resolve())
        ):
            raise ValueError("Wrong imported owner checkout")
        if path.suffix == ".pkl":
            model = pickle.loads(path.read_bytes())
        else:
            if args.backbone is None or args.cache is None:
                raise ValueError(
                    "Neural inference requires verified backbone and local cache"
                )
            import torch

            from oligo_engine.models.aso_rnafm import ASOPredictor, ChemistryHead

            torch.set_num_threads(1)
            if (
                hashlib.sha256(args.backbone.read_bytes()).hexdigest()
                != manifest["external_backbone"]["sha256"]
            ):
                raise ValueError("External backbone hash mismatch")
            state = torch.load(path, map_location="cpu", weights_only=False)
            model = ASOPredictor(args.backbone, args.cache, 0, args.adapt)
            context_dim = state["head"]["output.0.weight"].shape[1] - 64
            model.head = ChemistryHead(context_dim)
            model.restore(state)
    print(
        json.dumps(
            {
                "ready": True,
                "artifact_hash": entry["sha256"],
                "owner_revision": revision,
            }
        ),
        flush=True,
    )
    for line in sys.stdin:
        try:
            inputs = json.loads(line)
            if not isinstance(inputs, list) or not inputs:
                raise ValueError("Nonempty label-free batch required")
            allowed = {
                "HELM Annotation",
                "cell_line",
                "cell_line_species",
                "transfection_method",
                "dosage_nm",
                "treatment_period_hrs",
            }
            if any(set(row) != allowed for row in inputs):
                raise ValueError("Unexpected fields at frozen inference boundary")
            frame = pd.DataFrame(inputs)
            for field in ("dosage_nm", "treatment_period_hrs"):
                frame[field] = frame[field].astype(float)
            with contextlib.redirect_stdout(sys.stderr):
                means = model.predict(frame)
            print(
                json.dumps({"means": [float(v) for v in means]}, allow_nan=False),
                flush=True,
            )
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), flush=True)


if __name__ == "__main__":
    main()
