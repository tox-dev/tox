from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.conftest import ToxIniCreator
    from tox.config.main import Config


@pytest.fixture
def empty_config(tox_ini_conf: ToxIniCreator) -> Config:
    return tox_ini_conf("")
