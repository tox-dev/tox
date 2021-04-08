from argparse import ArgumentParser
from typing import Any, Callable, TypeVar, cast

import pluggy

from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.tox_env.register import ToxEnvRegister

from . import NAME

_F = TypeVar("_F", bound=Callable[..., Any])
_spec_marker = pluggy.HookspecMarker(NAME)


def _spec(func: _F) -> _F:
    return cast(_F, _spec_marker(func))


@_spec
def tox_register_tox_env(register: ToxEnvRegister) -> None:  # noqa: U100
    """
    Register new tox environment type. You can register:

    - **run environment**: by default this is a local subprocess backed virtualenv Python
    - **packaging environment**: by default this is a PEP-517 compliant local subprocess backed virtualenv Python

    :param register: a object that can be used to register new tox environment types
    """


@_spec
def tox_add_option(parser: ArgumentParser) -> None:  # noqa: U100
    """
    Add a command line argument. This is the first hook to be called, right after the logging setup and config source
    discovery.

    :param parser: the command line parser
    """


@_spec
def tox_add_core_config(core: ConfigSet) -> None:  # noqa: U100
    """
    Define a new core (non test environment bound) settings for tox. Called the first time the core configuration is
    used (at the start of the provision check).

    :param core: the core configuration object
    """


@_spec
def tox_configure(config: Config) -> None:  # noqa: U100
    """
    Called after command line options are parsed and ini-file has been read.

    :param config: the configuration object
    """


__all__ = (
    "NAME",
    "tox_register_tox_env",
    "tox_add_option",
    "tox_add_core_config",
    "tox_configure",
)
