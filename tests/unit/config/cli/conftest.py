import pytest

from tox.session.cmd.list_env import list_env
from tox.session.cmd.run.parallel import run_parallel
from tox.session.cmd.run.sequential import run_sequential
from tox.session.cmd.show_config import display_config


@pytest.fixture()
def core_handlers():
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
