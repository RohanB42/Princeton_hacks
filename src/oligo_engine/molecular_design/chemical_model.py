"""Portable frozen endpoint regressors; fitted in a separate qualification runner."""

import hashlib
import json
from math import isclose
from pathlib import Path

from oligo_engine.reward.chemistry import parse_helm

from .contracts import Design
from .scoring import Prediction

BASES = ("A", "C", "G", "T", "U", "5meC")
SUGARS = ("DNA", "MOE", "cEt", "RNA", "OMe")
LINKS = ("PO", "PS", "END")


def chemical_features(helm: str) -> list[float]:
    c = parse_helm(helm.replace("[m5C]", "[5meC]"))
    if len(c.bases) > 64:
        raise ValueError("Chemical feature capacity is 64 nucleotides")
    features = [0.0] * (64 * 15 + 3)
    for i, (base, sugar, link) in enumerate(
        zip(c.bases, c.sugars, c.links, strict=True)
    ):
        offset = i * 15
        features[offset + BASES.index(base)] = 1
        features[offset + 6 + SUGARS.index(sugar)] = 1
        features[offset + 11 + LINKS.index(link)] = 1
        features[offset + 14] = 1  # Explicit presence: padding is not a nucleotide.
    features[64 * 15 + ("none", "PO", "PS").index(c.terminal)] = 1
    return features


class ChemicalRegressor:
    def __init__(self, path: Path, expected_sha256: str) -> None:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("Chemical regressor hash mismatch")
        self.bundle = json.loads(raw)
        if self.bundle["schema"] != "frozen-chemical-regressor-v1":
            raise ValueError("Unknown chemical regressor schema")
        for anchor in self.bundle["parity"]:
            if not isclose(
                self.predict_helm(anchor["helm"]),
                anchor["mean"],
                abs_tol=1e-8,
                rel_tol=1e-8,
            ):
                raise ValueError("Frozen chemical regressor parity failed")

    def predict_helm(self, helm: str) -> float:
        features = chemical_features(helm)
        p = self.bundle["parameters"]
        if self.bundle["model"] == "ridge":
            return p["intercept"] + sum(
                x * v for x, v in zip(features, p["coefficients"], strict=True)
            )
        if self.bundle["model"] != "random_forest":
            raise ValueError("Unknown frozen regressor")
        values = []
        for tree in p["trees"]:
            node = 0
            while tree["left"][node] != -1:
                node = (
                    tree["left"][node]
                    if features[tree["feature"][node]] <= tree["threshold"][node]
                    else tree["right"][node]
                )
            values.append(tree["value"][node])
        return sum(values) / len(values)

    def __call__(
        self, design: Design, context: tuple[tuple[str, str], ...]
    ) -> Prediction:
        expected = {k: str(v) for k, v in self.bundle["context"].items()}
        if dict(context) != expected:
            raise ValueError("Risk assay context mismatch")
        return Prediction(self.predict_helm(design.helm))
