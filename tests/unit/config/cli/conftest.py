from typing import Callable, Dict

import pytest

from tox.session.cmd.list_env import list_env
from tox.session.cmd.run.parallel import run_parallel
from tox.session.cmd.run.sequential import run_sequential
from tox.session.cmd.show_config import display_config
from tox.session.state import State


@pytest.fixture()
def core_handlers() -> Dict[str, Callable[[State], int]]:
    return {
        "config": display_config,
        "c": display_config,
        "list": list_env,
        "l": list_env,
        "run": run_sequential,
        "r": run_sequential,
        "run-parallel": run_parallel,
        "p": run_parallel,
    }
