import os
from typing import Dict

import pytest


@pytest.fixture(scope="session")
def os_env() -> Dict[str, str]:
    return os.environ.copy()
