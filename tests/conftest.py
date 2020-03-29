import sys

import pytest

pytest_plugins = "tox.pytest"


@pytest.fixture(scope="session")
def value_error():
    def _fmt(msg):
        return 'ValueError("{}"{})'.format(msg, "," if sys.version_info < (3, 7) else "")

    return _fmt
