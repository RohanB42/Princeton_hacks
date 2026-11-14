"""Check the installable scaffold and parseable package configuration."""

import importlib
import tomllib
from pathlib import Path


def test_package_import_and_metadata() -> None:
    package = importlib.import_module("oligo_engine")
    assert package.__doc__
    metadata = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    assert metadata["tool"]["poetry"]["packages"][0]["include"] == "oligo_engine"
