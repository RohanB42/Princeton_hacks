"""Verified optional runtime; independent of the retired molecular scaffold."""

from importlib.metadata import version

RUNTIME = {
    "gymnasium": "1.1.1",
    "stable-baselines3": "2.6.0",
    "sb3-contrib": "2.6.0",
    "torch": "2.3.1",
    "numpy": "1.26.4",
    "scipy": "1.15.3",
    "scikit-learn": "1.4.0",
    "pandas": "2.2.3",
    "pyarrow": "21.0.0",
}


def verify_runtime() -> dict[str, str]:
    """Fail before fitting on unverified scientific package versions."""
    actual = {name: version(name) for name in RUNTIME}
    if any(
        actual[name].split("+")[0] != expected for name, expected in RUNTIME.items()
    ):
        raise RuntimeError(f"Unverified experimental-selection runtime: {actual}")
    return actual
