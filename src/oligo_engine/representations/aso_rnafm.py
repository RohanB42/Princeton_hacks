"""Verified single-strand RNA-FM token features; chemistry stays in a separate track."""

import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from oligo_engine.atlas.chemistry import parse_helm
from oligo_engine.representations.rnafm import FrozenRNAFM


class ASORNAFM:
    def __init__(self, checkpoint: Path, cache: Path | None = None):
        loader = FrozenRNAFM(checkpoint, device="cpu")
        self.backbone = loader.model
        self.converter = loader.batch_converter
        self.config = {
            **loader.config,
            "representation_schema": "aso_tokens_v1",
            "strands": ["RNA1"],
            "pooling": "none; per-nucleotide states",
            "n_features": 640,
            "chemical_features": "separate exact monomer tracks",
        }
        self.identity = hashlib.sha256(
            json.dumps(self.config, sort_keys=True).encode()
        ).hexdigest()
        self.cache = cache
        if cache:
            cache.mkdir(parents=True, exist_ok=True)

    def forward(self, sequences: list[str]) -> tuple[torch.Tensor, torch.Tensor]:
        if not sequences or any(not s or set(s) - set("ACGU") for s in sequences):
            raise ValueError("Expected nonempty canonical RNA projections")
        _, _, tokens = self.converter([(str(i), s) for i, s in enumerate(sequences)])
        h = self.backbone(tokens, repr_layers=[12])["representations"][12][:, 1:-1]
        mask = (
            torch.arange(h.shape[1])[None, :]
            < torch.tensor([len(s) for s in sequences])[:, None]
        )
        return h, mask

    def frozen(self, sequences: list[str]) -> list[np.ndarray]:
        output = []
        for s in sequences:
            key = hashlib.sha256((self.identity + s).encode()).hexdigest()
            p = self.cache / f"{key}.npz" if self.cache else None
            if p and p.exists():
                with np.load(p, allow_pickle=False) as archive:
                    a = archive["features"]
                    digest = str(archive["sha256"])
                    if (
                        a.shape != (len(s), 640)
                        or not np.isfinite(a).all()
                        or hashlib.sha256(a.tobytes()).hexdigest() != digest
                    ):
                        raise ValueError("Invalid token cache")
            else:
                with torch.no_grad():
                    h, _ = self.forward([s])
                    a = h[0, : len(s)].cpu().numpy().copy()
                if p:
                    np.savez_compressed(
                        p, features=a, sha256=hashlib.sha256(a.tobytes()).hexdigest()
                    )
            output.append(a)
        return output

    def encode_helms(self, helms: list[str]) -> list[np.ndarray]:
        return self.frozen([parse_helm(h).natural_rna for h in helms])
