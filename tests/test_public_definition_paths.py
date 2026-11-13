from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.config.loader.ini import IniLoader
from tox.config.loader.toml import TomlLoader
from tox.execute.local_sub_process import (
    LocalSubprocessExecuteFailedStatus,
    LocalSubProcessExecuteInstance,
    LocalSubprocessExecuteStatus,
    LocalSubProcessExecutor,
)
from tox.journal import write_journal
from tox.session.cmd.show_config import show_config, tox_add_option

if TYPE_CHECKING:
    from types import FunctionType


@pytest.mark.parametrize(
    ("value", "module"),
    [
        pytest.param(IniLoader, "tox.config.loader.ini", id="ini-loader"),
        pytest.param(TomlLoader, "tox.config.loader.toml", id="toml-loader"),
        pytest.param(LocalSubProcessExecutor, "tox.execute.local_sub_process", id="executor"),
        pytest.param(LocalSubProcessExecuteInstance, "tox.execute.local_sub_process", id="execute-instance"),
        pytest.param(LocalSubprocessExecuteStatus, "tox.execute.local_sub_process", id="execute-status"),
        pytest.param(LocalSubprocessExecuteFailedStatus, "tox.execute.local_sub_process", id="failed-status"),
        pytest.param(write_journal, "tox.journal", id="journal-writer"),
        pytest.param(show_config, "tox.session.cmd.show_config", id="show-config"),
        pytest.param(tox_add_option, "tox.session.cmd.show_config", id="config-hook"),
    ],
)
def test_public_definition_path(value: type | FunctionType, module: str) -> None:
    assert value.__module__ == module
