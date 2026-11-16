"""Collection rules: upstream-dependent tests never run by accident, never skip.

``tests/upstream`` needs the pinned OligoGym environment. It is excluded from a plain
``pytest`` so the core suite runs everywhere, and it is collected only when explicitly
selected (``pytest tests/upstream`` or ``pytest -m upstream``). Once selected, a
missing or mismatched environment FAILS (see tests/upstream/conftest.py).
"""


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "upstream: needs the pinned OligoGym environment; fails if absent"
    )
    config.addinivalue_line("markers", "rnafm: requires the RNA-FM research runtime")
    config.addinivalue_line("markers", "robustness: optional science robustness checks")


def pytest_ignore_collect(collection_path, config):
    selected = " ".join(str(arg) for arg in config.invocation_params.args)
    if collection_path.name == "test_molecular_rl_optional.py":
        return "molecular_rl_optional" not in selected
    if collection_path.name == "test_robustness_optional.py":
        return "robustness_optional" not in selected and "-m robustness" not in selected
    if collection_path.name.startswith("test_rnafm"):
        return "rnafm" not in selected
    if collection_path.name == "upstream" and collection_path.is_dir():
        return "upstream" not in selected
    return None


def pytest_collection_modifyitems(items):
    import pytest

    for item in items:
        if "tests/upstream/" in item.nodeid:
            item.add_marker(pytest.mark.upstream)
        if "test_rnafm" in item.nodeid:
            item.add_marker(pytest.mark.rnafm)
        if "test_robustness_optional" in item.nodeid:
            item.add_marker(pytest.mark.robustness)
