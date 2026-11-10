"""Contains the plugin manager object."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import pluggy

from tox import provision
from tox.config.loader import api as loader_api
from tox.session.cmd.run import parallel, sequential
from tox.tox_env import package as package_api
from tox.tox_env.python.virtual_env import pep723_runner, runner
from tox.tox_env.python.virtual_env.package import cmd_builder, pyproject
from tox.tox_env.register import REGISTER, ToxEnvRegister

from . import NAME, spec
from .inline import load_inline

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path
    from types import ModuleType

    from tox.config.cli.parser import ToxParser
    from tox.config.sets import ConfigSet, EnvConfigSet
    from tox.execute import Outcome
    from tox.session.state import State
    from tox.tox_env.api import ToxEnv
    from tox.tox_env.installer import InstallArguments


class Plugin:
    """The plugin manager of tox, which discovers the plugins and calls their hooks.

    :var manager: the pluggy manager the plugins are registered with
    :var inline_module: the inline ``toxfile.py`` module, ``None`` when there is none

    """

    def __init__(self) -> None:
        self.manager: pluggy.PluginManager = pluggy.PluginManager(NAME)
        self.manager.add_hookspecs(spec)
        self.inline_module: ModuleType | None = None

    def tox_extend_envs(self) -> list[Iterable[str]]:
        """Call the ``tox_extend_envs`` hook, which adds environment names to the environment list.

        :returns: the environment names the plugins add

        """
        additional_env_names_hook_value = self.manager.hook.tox_extend_envs()
        # NOTE: S101 is suppressed below to allow for type narrowing in MyPy
        assert isinstance(additional_env_names_hook_value, list)  # ruff:ignore[assert]
        return additional_env_names_hook_value

    def tox_add_option(self, parser: ToxParser) -> None:
        """Call the ``tox_add_option`` hook, which adds command line options.

        :param parser: the parser to add the options to

        """
        self.manager.hook.tox_add_option(parser=parser)

    def tox_add_core_config(self, core_conf: ConfigSet, state: State) -> None:
        """Call the ``tox_add_core_config`` hook, which adds core configuration keys.

        :param core_conf: the core configuration
        :param state: the state of the run

        """
        self.manager.hook.tox_add_core_config(core_conf=core_conf, state=state)

    def tox_add_env_config(self, env_conf: EnvConfigSet, state: State) -> None:
        """Call the ``tox_add_env_config`` hook, which adds configuration keys to each environment.

        :param env_conf: the configuration of the environment
        :param state: the state of the run

        """
        self.manager.hook.tox_add_env_config(env_conf=env_conf, state=state)

    def tox_before_run_commands(self, tox_env: ToxEnv) -> None:
        """Call the ``tox_before_run_commands`` hook, before the commands of an environment run.

        :param tox_env: the environment whose commands are about to run

        """
        self.manager.hook.tox_before_run_commands(tox_env=tox_env)

    def tox_after_run_commands(self, tox_env: ToxEnv, exit_code: int, outcomes: list[Outcome]) -> None:
        """Call the ``tox_after_run_commands`` hook, after the commands of an environment ran.

        :param tox_env: the environment whose commands ran
        :param exit_code: the exit code of the commands
        :param outcomes: the outcome of each command

        """
        self.manager.hook.tox_after_run_commands(tox_env=tox_env, exit_code=exit_code, outcomes=outcomes)

    def tox_on_install(self, tox_env: ToxEnv, arguments: InstallArguments, section: str, of_type: str) -> None:
        """Call the ``tox_on_install`` hook, when packages are installed in an environment.

        :param tox_env: the environment the packages are installed in
        :param arguments: the arguments the packages are installed with
        :param section: the configuration section the arguments come from
        :param of_type: the type of the arguments

        """
        self.manager.hook.tox_on_install(tox_env=tox_env, arguments=arguments, section=section, of_type=of_type)

    def tox_env_teardown(self, tox_env: ToxEnv) -> None:
        """Call the ``tox_env_teardown`` hook, when an environment is torn down.

        :param tox_env: the environment that is torn down

        """
        self.manager.hook.tox_env_teardown(tox_env=tox_env)

    def load_plugins(self, path: Path | None) -> None:
        """Load the plugins, the inline ``toxfile.py`` of the project included, and register the environment types.

        :param path: the path of the project configuration file, ``None`` to load no inline plugin

        """
        for plugin in self.manager.get_plugins():  # make sure we start with a clean state, repeated in memory run
            self.manager.unregister(plugin)
        self._register_plugins(None if path is None else _load_inline(path))
        self.tox_register_tox_env(register=REGISTER)

    def _register_plugins(self, inline: ModuleType | None) -> None:
        from tox.session import state  # ruff:ignore[import-outside-top-level]  # avoids an import cycle
        from tox.session.cmd import (  # ruff:ignore[import-outside-top-level]  # avoids an import cycle
            depends,
            devenv,
            exec_,
            legacy,
            list_env,
            man,
            quickstart,
            schema,
            show_config,
            version_flag,
        )

        self.inline_module = inline
        if inline is not None:
            self.manager.register(inline)
        self._load_external_plugins()
        internal_plugins = (
            loader_api,
            provision,
            pep723_runner,
            runner,
            pyproject,
            cmd_builder,
            legacy,
            version_flag,
            exec_,
            quickstart,
            show_config,
            schema,
            devenv,
            list_env,
            man,
            depends,
            parallel,
            sequential,
            package_api,
        )
        for plugin in internal_plugins:
            self.manager.register(plugin)
        self.manager.register(state)
        try:
            self.manager.check_pending()
        except pluggy.PluginValidationError:
            if inline is None:
                raise
            logging.warning("toxfile.py uses hooks not available in this tox version, skipping inline plugin")
            self.manager.unregister(inline)
            self.inline_module = None
            self.manager.check_pending()

    def _load_external_plugins(self) -> None:
        for name in os.environ.get("TOX_DISABLED_EXTERNAL_PLUGINS", "").split(","):
            self.manager.set_blocked(name)
        self.manager.load_setuptools_entrypoints(NAME)

    def tox_register_tox_env(self, register: ToxEnvRegister) -> None:
        """Call the ``tox_register_tox_env`` hook, which registers environment types.

        :param register: the registry of environment types

        """
        self.manager.hook.tox_register_tox_env(register=register)


def _load_inline(path: Path) -> ModuleType | None:  # used to be able to unregister plugin tests
    return load_inline(path)


MANAGER = Plugin()
"""The plugin manager of this tox process."""

__all__ = [
    "MANAGER",
    "Plugin",
]
