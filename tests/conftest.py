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


def pytest_ignore_collect(collection_path, config):
    if collection_path.name == "upstream" and collection_path.is_dir():
        selected = " ".join(str(arg) for arg in config.invocation_params.args)
        return "upstream" not in selected
    return None


def pytest_collection_modifyitems(items):
    import pytest

    for item in items:
        if "tests/upstream/" in item.nodeid:
            item.add_marker(pytest.mark.upstream)
