from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def os_env() -> dict[str, str]:
    return os.environ.copy()
