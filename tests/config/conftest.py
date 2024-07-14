from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.conftest import ToxIniCreator, ToxTomlCreator
    from tox.config.main import Config


@pytest.fixture
def empty_config(tox_ini_conf: ToxIniCreator) -> Config:
    """Make and return an empty INI config file."""
    return tox_ini_conf("")


@pytest.fixture()
def empty_toml_config(tox_toml_conf: ToxTomlCreator) -> Config:
    """Make and return an empty TOML config file."""
    return tox_toml_conf("")
