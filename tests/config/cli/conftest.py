from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import pytest

from tox.session.cmd.depends import depends
from tox.session.cmd.devenv import devenv
from tox.session.cmd.exec_ import exec_
from tox.session.cmd.legacy import legacy
from tox.session.cmd.list_env import list_env
from tox.session.cmd.quickstart import quickstart
from tox.session.cmd.run.parallel import run_parallel
from tox.session.cmd.run.sequential import run_sequential
from tox.session.cmd.show_config import show_config

if TYPE_CHECKING:
    from tox.session.state import State


@pytest.fixture
def core_handlers() -> dict[str, Callable[[State], int]]:
    return {
        "config": show_config,
        "c": show_config,
        "list": list_env,
        "l": list_env,
        "run": run_sequential,
        "r": run_sequential,
        "run-parallel": run_parallel,
        "p": run_parallel,
        "d": devenv,
        "devenv": devenv,
        "q": quickstart,
        "quickstart": quickstart,
        "de": depends,
        "depends": depends,
        "le": legacy,
        "legacy": legacy,
        "e": exec_,
        "exec": exec_,
    }
