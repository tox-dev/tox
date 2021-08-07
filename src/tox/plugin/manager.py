"""Contains the plugin manager object"""
from pathlib import Path

import pluggy

from tox import provision
from tox.config.cli.parser import ToxParser
from tox.config.loader import api as loader_api
from tox.config.sets import ConfigSet
from tox.session import state
from tox.session.cmd import depends, devenv, exec_, legacy, list_env, quickstart, show_config, version_flag
from tox.session.cmd.run import parallel, sequential
from tox.tox_env import package as package_api
from tox.tox_env.python.virtual_env import runner
from tox.tox_env.python.virtual_env.package import api
from tox.tox_env.register import REGISTER, ToxEnvRegister

from . import NAME, spec
from .inline import load_inline


class Plugin:
    def __init__(self) -> None:
        self.manager: pluggy.PluginManager = pluggy.PluginManager(NAME)
        self.manager.add_hookspecs(spec)

        internal_plugins = (
            loader_api,
            provision,
            runner,
            api,
            legacy,
            version_flag,
            exec_,
            quickstart,
            show_config,
            devenv,
            list_env,
            depends,
            parallel,
            sequential,
            package_api,
        )

        for plugin in internal_plugins:
            self.manager.register(plugin)
        self.manager.load_setuptools_entrypoints(NAME)
        self.manager.register(state)
        self.manager.check_pending()

    def tox_add_option(self, parser: ToxParser) -> None:
        self.manager.hook.tox_add_option(parser=parser)

    def tox_add_core_config(self, core: ConfigSet) -> None:
        self.manager.hook.tox_add_core_config(core=core)

    def tox_register_tox_env(self, register: "ToxEnvRegister") -> None:
        self.manager.hook.tox_register_tox_env(register=register)

    def load_inline_plugin(self, path: Path) -> None:
        result = load_inline(path)
        if result is not None:
            self.manager.register(result)
        REGISTER._register_tox_env_types(self)  # noqa
        if result is not None:  #: recheck pending for the inline plugins
            self.manager.check_pending()


MANAGER = Plugin()

__all__ = (
    "MANAGER",
    "Plugin",
)
