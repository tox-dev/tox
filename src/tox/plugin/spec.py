"""Hook specifications for the tox project - see https://pluggy.readthedocs.io/"""
from argparse import ArgumentParser
from typing import Any, Callable, Type, TypeVar, cast

import pluggy

from tox.config.sets import ConfigSet
from tox.tox_env.api import ToxEnv
from tox.tox_env.register import ToxEnvRegister

from . import NAME

F = TypeVar("F", bound=Callable[..., Any])
_hook_spec = pluggy.HookspecMarker(NAME)


def hook_spec(func: F) -> F:
    return cast(F, _hook_spec(func))


@hook_spec
def tox_add_option(parser: ArgumentParser) -> None:  # noqa
    """add cli flags"""


@hook_spec
def tox_add_core_config(core: ConfigSet) -> None:  # noqa
    """add options to the core section of the tox"""


@hook_spec
def tox_register_tox_env(register: ToxEnvRegister) -> Type[ToxEnv]:  # noqa
    """register new tox environment types that can have their own argument"""
