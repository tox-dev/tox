from __future__ import annotations

import pytest

from tox.tox_env.python.virtual_env.runner import VirtualEnvRunner
from tox.tox_env.register import ToxEnvRegister
from tox.util.typing_compat import override


def test_register_set_new_default_no_register() -> None:
    register = ToxEnvRegister()
    with pytest.raises(ValueError, match="run env must be registered before setting it as default"):
        register.default_env_runner = "new-env"


def test_register_set_new_default_with_register() -> None:
    class NewDefaultRunner(VirtualEnvRunner):
        @staticmethod
        @override
        def id() -> str:
            return "B"

    register = ToxEnvRegister()
    register.add_run_env(VirtualEnvRunner)
    assert register.default_env_runner == VirtualEnvRunner.id()
    register.add_run_env(NewDefaultRunner)
    assert register.default_env_runner == VirtualEnvRunner.id()
    register.default_env_runner = NewDefaultRunner.id()
    assert register.default_env_runner == "B"
