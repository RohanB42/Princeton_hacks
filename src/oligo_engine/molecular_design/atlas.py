"""Exact portable inference for a verified export of the actual Atlas Ridge."""

import hashlib
import json
from math import isclose, isfinite, log1p
from pathlib import Path

from oligo_engine.reward.chemistry import parse_helm

from .contracts import Design
from .scoring import Prediction


class AtlasRidge:
    def __init__(self, path: Path, expected_sha256: str) -> None:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("Atlas exported artifact hash mismatch")
        self.bundle = json.loads(raw)
        if self.bundle["schema"] != "atlas-ridge-inference-v1":
            raise ValueError("Unknown Atlas export schema")
        if not self.bundle["chemistry"]:
            raise ValueError("Context-only model is not a chemistry-aware design head")
        self.features = self.bundle["features"]
        self.coef = self.bundle["coefficients"]
        self.intercept = self.bundle["intercept"]
        width = sum(len(self.features[k]) for k in ("bases", "sugars", "links"))
        expected = (
            64 * width
            + 3
            + sum(len(v) for v in self.features["categories"].values())
            + 2
        )
        if len(self.coef) != expected or not all(
            isfinite(v) for v in self.coef + [self.intercept]
        ):
            raise ValueError("Invalid Atlas coefficients/schema")
        for anchor in self.bundle["parity_anchors"]:
            inputs = dict(anchor["input"])
            helm = inputs.pop("HELM Annotation")
            if not isclose(
                self.predict_helm(helm, inputs),
                anchor["mean"],
                abs_tol=1e-5,
                rel_tol=1e-7,
            ):
                raise ValueError("Atlas owner/export parity failed")

    def predict_helm(self, helm: str, context: dict) -> float:
        c, f = parse_helm(helm.replace("[m5C]", "[5meC]")), self.features
        width = sum(len(f[k]) for k in ("bases", "sugars", "links"))
        value = float(self.intercept)
        for i, (base, sugar, link) in enumerate(
            zip(c.bases, c.sugars, c.links, strict=True)
        ):
            offset = i * width
            for vocabulary, token in (
                (f["bases"], base),
                (f["sugars"], sugar),
                (f["links"], link),
            ):
                value += self.coef[offset + vocabulary.index(token)]
                offset += len(vocabulary)
        value += self.coef[64 * width + ["none", "PO", "PS"].index(c.terminal)]
        offset = 64 * width + 3
        for name, categories in f["categories"].items():
            # Unknown categories require explicit scientific admission.
            if context[name] not in categories:
                raise ValueError(f"Unseen Atlas categorical context: {name}")
            value += self.coef[offset + categories.index(context[name])]
            offset += len(categories)
        for i, name in enumerate(("dosage_nm", "treatment_period_hrs")):
            raw = float(context[name])
            if not isfinite(raw) or raw <= 0:
                raise ValueError("Positive finite Atlas dose/time required")
            transformed = (log1p(raw) - f["numeric_mean"][i]) / f["numeric_scale"][i]
            value += self.coef[offset + i] * transformed
        return value

    def __call__(
        self, design: Design, context: tuple[tuple[str, str], ...]
    ) -> Prediction:
        return Prediction(self.predict_helm(design.helm, dict(context)))
