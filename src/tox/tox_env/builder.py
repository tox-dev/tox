"""
Build the state of a tox run (creates tox run and build environments).
"""
import copy
from typing import Dict, Sequence, cast

from tox.config.cli.parse import ParsedOptions
from tox.config.cli.parser import Parsed, ToxParser
from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.plugin.impl import impl
from tox.session.state import State

from .package import PackageToxEnv
from .runner import RunToxEnv


def build_tox_envs(
    config: Config,
    options: ParsedOptions,
    args: Sequence[str],
) -> State:
    builder = Builder(options[0], config)
    return State(config, builder.tox_env_to_runner, options, args)


class Builder:
    def __init__(self, options: Parsed, config: Config) -> None:
        self.tox_env_to_runner: Dict[str, RunToxEnv] = {}
        self._tox_env_to_runner_type: Dict[str, str] = {}
        self._pkg_envs: Dict[str, PackageToxEnv] = {}
        self.options = options
        self._config = config
        self._run()

    def _run(self) -> None:
        for name in self._config:
            if name in self._pkg_envs:
                continue
            env_conf = copy.deepcopy(self._config[name])
            tox_env = self._build_run_env(env_conf, name)
            self.tox_env_to_runner[name] = tox_env
        for key, tox_env in self.tox_env_to_runner.items():
            tox_env.conf.add_constant(
                keys=["execute"],
                desc="the tox execute used to evaluate this environment",
                value=self._tox_env_to_runner_type[key],
            )

    def _build_run_env(self, env_conf: ConfigSet, env_name: str) -> RunToxEnv:
        env_conf.add_config(
            keys="runner",
            desc="the tox execute used to evaluate this environment",
            of_type=str,
            default=self.options.default_runner,  # noqa
        )
        runner = cast(str, env_conf["runner"])
        from .register import REGISTER

        builder = REGISTER.runner(runner)
        env: RunToxEnv = builder(env_conf, self._config.core, self.options)
        self._tox_env_to_runner_type[env_name] = runner
        self._build_package_env(env)
        return env

    def _build_package_env(self, env: RunToxEnv) -> None:
        pkg_env_gen = env.set_package_env()
        try:
            name, packager = next(pkg_env_gen)
        except StopIteration:
            pass
        else:
            package_tox_env = self._get_package_env(packager, name)
            try:
                pkg_env_gen.send(package_tox_env)
            except StopIteration:
                pass

    def _get_package_env(self, packager: str, pkg_name: str) -> PackageToxEnv:
        if pkg_name in self._pkg_envs:
            package_tox_env: PackageToxEnv = self._pkg_envs[pkg_name]
        else:
            if pkg_name in self.tox_env_to_runner:  # if already detected as runner remove
                del self.tox_env_to_runner[pkg_name]
            from .register import REGISTER

            package_type = REGISTER.package(packager)
            pkg_conf = self._config[pkg_name]
            pkg_conf.make_package_conf()
            package_tox_env = package_type(pkg_conf, self._config.core, self.options)
            self._pkg_envs[pkg_name] = package_tox_env
        return package_tox_env


@impl
def tox_add_option(parser: ToxParser) -> None:
    from .register import REGISTER

    parser.add_argument(
        "--runner",
        dest="default_runner",
        help="default execute",
        default=REGISTER.default_run_env,
        choices=list(REGISTER.run_envs),
    )
