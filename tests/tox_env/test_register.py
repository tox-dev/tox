from __future__ import annotations

import pytest

from tox.tox_env.python.virtual_env.runner import VirtualEnvRunner
from tox.tox_env.register import ToxEnvRegister


def test_register_set_new_default_no_register() -> None:
    register = ToxEnvRegister()
    with pytest.raises(ValueError, match="run env must be registered before setting it as default"):
        register.default_env_runner = "new-env"


def test_register_set_new_default_with_register() -> None:
    class B(VirtualEnvRunner):
        @staticmethod
        def id() -> str:
            return "B"

    register = ToxEnvRegister()
    register.add_run_env(VirtualEnvRunner)
    assert register.default_env_runner == VirtualEnvRunner.id()
    register.add_run_env(B)
    assert register.default_env_runner == VirtualEnvRunner.id()
    register.default_env_runner = B.id()
    assert register.default_env_runner == "B"
