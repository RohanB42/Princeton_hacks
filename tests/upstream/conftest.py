"""Every test here fails loudly if the pinned OligoGym environment is unavailable."""

import pytest

from oligo_engine.features.upstream import (
    UpstreamEnvironmentError,
    verify_upstream_environment,
)


@pytest.fixture(autouse=True, scope="session")
def upstream_environment():
    try:
        return verify_upstream_environment()
    except UpstreamEnvironmentError as error:
        pytest.fail(f"Pinned upstream environment required: {error}", pytrace=False)
