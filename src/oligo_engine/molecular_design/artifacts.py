"""Immutable run receipts, reproducible seals and deterministic scientist panels."""

import csv
import json
import os
import platform
import subprocess
import tempfile
from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from oligo_engine.provenance import identity

from .contracts import Campaign, Design


def seal(payload: dict) -> dict:
    if "seal" in payload:
        raise ValueError("Payload already sealed")
    return {**payload, "seal": identity(payload)}


def verify(payload: dict, expected: str | None = None) -> None:
    recorded = payload.get("seal")
    if not recorded or recorded != identity(
        {k: v for k, v in payload.items() if k != "seal"}
    ):
        raise ValueError("Artifact seal invalid")
    if expected is not None and recorded != expected:
        raise ValueError("Artifact differs from independently locked selection")


def write_new(path: Path, payload: dict) -> None:
    """Atomic, refuses overwrite; disallow JSON NaN and infinity."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


class QueryJournal:
    """Durable hash-chained responses, including failures during initial queries."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=False)
        self.path, self.previous = path, ""

    def __call__(self, event: dict) -> None:
        record = seal({"previous": self.previous, "event": event})
        with self.path.open("a") as stream:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.previous = record["seal"]


def environment_receipt() -> dict:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        ).stdout.strip()

    packages = {}
    for name in (
        "numpy",
        "torch",
        "gymnasium",
        "stable-baselines3",
        "sb3-contrib",
        "scikit-learn",
    ):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "packages": packages,
    }


def panel(receipt: dict, size: int, diversity: float = 0.0) -> list[dict]:
    """Pareto tiers, then deterministic utility/diversity; never changes reward."""
    if size < 1 or not 0 <= diversity <= 1:
        raise ValueError("Invalid panel preferences")
    unique = {}
    for event in receipt["trace"]:
        if event["status"] == "scored" and event["score"]["eligible"]:
            unique.setdefault(event["compound_id"], event)
    remaining, selected = list(unique.values()), []
    tiers = {}
    unranked = remaining.copy()
    level = 0
    while unranked:
        front = [
            e
            for e in unranked
            if not any(
                all(
                    a >= b
                    for a, b in zip(
                        other["score"]["objectives"],
                        e["score"]["objectives"],
                        strict=True,
                    )
                )
                and any(
                    a > b
                    for a, b in zip(
                        other["score"]["objectives"],
                        e["score"]["objectives"],
                        strict=True,
                    )
                )
                for other in unranked
            )
        ]
        for e in front:
            tiers[e["compound_id"]] = level
            unranked.remove(e)
        level += 1
    while remaining and len(selected) < size:

        def rank(e: dict) -> tuple:
            seq = e["design"]["sequence"]
            distance = (
                min(
                    (
                        sum(a != b for a, b in zip(seq, x["design"]["sequence"]))
                        + abs(len(seq) - len(x["design"]["sequence"]))
                    )
                    / max(len(seq), len(x["design"]["sequence"]))
                    for x in selected
                )
                if selected
                else 1.0
            )
            value = sum(e["score"]["objectives"]) / len(e["score"]["objectives"])
            return (
                tiers[e["compound_id"]],
                -(1 - diversity) * value - diversity * distance,
                e["compound_id"],
            )

        chosen = min(remaining, key=rank)
        remaining.remove(chosen)
        selected.append(chosen)
    return [
        {
            "design": e["design"],
            "compound_id": e["compound_id"],
            "predictions": e["score"]["endpoints"],
            "pareto_tier": tiers[e["compound_id"]],
            "claim": "unvalidated computational hypothesis",
        }
        for e in selected
    ]


def run_artifact(
    campaign: Campaign, receipt: dict, size: int = 10, diversity: float = 0.0
) -> dict:
    return seal(
        {
            "schema": "molecular-design-run-v1",
            "campaign": asdict(campaign),
            "environment": environment_receipt(),
            "run": receipt,
            "panel": panel(receipt, size, diversity),
            "requested_panel_size": size,
            "panel_diversity_weight": diversity,
            "risk_status": "model_based_endpoint_predictions"
            if any(h["property_kind"] == "risk" for h in receipt["heads"])
            else "unknown_no_applicable_risk_head",
            "evidence": "synthetic_engineering"
            if campaign.profile.purpose == "fixture"
            else "computational_prediction_only",
            "gate1": "unchanged",
        }
    )


def export_csv(artifact: dict, path: Path) -> None:
    verify(artifact)
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "compound_id",
                "sequence",
                "helm",
                "start",
                "end",
                "pattern",
                "terminal",
                "predictions_json",
                "claim",
            ],
        )
        writer.writeheader()
        for row in artifact["panel"]:
            d = Design(**row["design"])
            writer.writerow(
                {
                    "compound_id": d.compound_id,
                    "sequence": d.sequence,
                    "helm": d.helm,
                    "start": d.start,
                    "end": d.start + len(d.sequence),
                    "pattern": d.pattern,
                    "terminal": d.terminal,
                    "predictions_json": json.dumps(row["predictions"]),
                    "claim": row["claim"],
                }
            )
