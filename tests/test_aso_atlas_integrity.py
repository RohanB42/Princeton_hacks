"""Protect the authorized Atlas snapshot without optional Parquet dependencies."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "data" / "aso_atlas_2"
AUDIT = json.loads((ROOT / "cleaned" / "audit.json").read_text())


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@pytest.mark.parametrize("name", sorted(AUDIT["endpoints"]))
def test_atlas_source_and_prepared_bytes(name: str) -> None:
    entry = AUDIT["endpoints"][name]
    assert digest(ROOT / "release" / entry["source_file"]) == entry["source_sha256"]
    assert digest(ROOT / "cleaned" / f"{name}.parquet") == entry["cleaned_sha256"]


@pytest.mark.parametrize("name", sorted(AUDIT["folds"]))
def test_atlas_supplied_fold_bytes(name: str) -> None:
    assert digest(ROOT / "release" / "folds" / name) == AUDIT["folds"][name]["sha256"]


def test_atlas_manifest_and_audit_agree() -> None:
    manifest = json.loads((ROOT / "release" / "upstream_manifest.json").read_text())
    assert set(AUDIT["endpoints"]) == {
        "in_vitro_inhibition",
        "dose_response",
        "hepatotoxicity",
        "neurotoxicity",
    }
    assert len(AUDIT["folds"]) == 7
    assert AUDIT["source_code_revision"] == "bb90c946013f183379da04678340e193088e5f99"
    assert AUDIT["release_tag"] == manifest["release_tag"] == "neurips-rebuttal"
    assert sum(e["rows_source"] for e in AUDIT["endpoints"].values()) == 283521
    for name, entry in AUDIT["endpoints"].items():
        assert entry["rows_source"] == entry["rows_cleaned"]
        assert entry["rows_source"] == manifest["configs"][name]["rows"]
        assert (
            entry["upstream_model_eligible"]
            == manifest["configs"][name]["model_eligible_rows"]
        )
