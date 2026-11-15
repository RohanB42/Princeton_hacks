"""Label-free mapping into a reviewed Atlas predictor's predict(frame) boundary."""

from dataclasses import asdict
from typing import Protocol

from oligo_engine.design.aso_space import TargetContext, candidate_identity
from oligo_engine.design.candidates import DESIGNS, Candidate
from oligo_engine.reward.chemistry import parse_helm
from oligo_engine.reward.scoring import AssayProfile


def atlas_helm(candidate: Candidate, target: TargetContext) -> str:
    """Project only a verified MOE template; original HELM remains in the archive."""
    candidate_identity(candidate, target)
    projected = candidate.helm.replace("[m5C]", "[5meC]")
    parsed = parse_helm(projected)
    design = DESIGNS[candidate.chemistry]
    length, left, right = design["length"], design["wing5"], design["wing3"]
    if (
        parsed.natural_rna != candidate.sequence.replace("T", "U")
        or parsed.sugars
        != ("MOE",) * left + ("DNA",) * (length - left - right) + ("MOE",) * right
        or parsed.links != ("PS",) * (length - 1) + ("END",)
        or parsed.terminal != "none"
    ):
        raise ValueError("Atlas projection lost molecular structure")
    return projected


class AtlasPredictor(Protocol):
    def predict(self, frame: object) -> object: ...


class AtlasInference:
    """Already-fitted predictor; assay scope is checked by FrozenScorer first."""

    def __init__(self, predictor: AtlasPredictor) -> None:
        self._predictor = predictor

    def __call__(
        self, candidate: Candidate, target: TargetContext, assay: AssayProfile
    ) -> float:
        import pandas as pd

        frame = pd.DataFrame(
            [{"HELM Annotation": atlas_helm(candidate, target), **asdict(assay)}]
        )
        values = self._predictor.predict(frame)
        if len(values) != 1:
            raise ValueError("Expected one Atlas inhibition prediction")
        return float(values[0])
