from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING, Iterator, Sequence, cast

from tox.config.main import Config
from tox.config.sets import EnvConfigSet
from tox.journal import Journal
from tox.plugin import impl
from tox.report import HandledError, ToxHandler
from tox.tox_env.api import ToxEnvCreateArgs
from tox.tox_env.errors import Skip
from tox.tox_env.package import PackageToxEnv
from tox.tox_env.runner import RunToxEnv

if TYPE_CHECKING:

    from tox.config.cli.parse import Handlers
    from tox.config.cli.parser import Parsed, ToxParser


class State:
    def __init__(
        self,
        conf: Config,
        opt_parse: tuple[Parsed, Handlers],
        args: Sequence[str],
        log_handler: ToxHandler,
    ) -> None:
        self.conf = conf
        self.conf.register_config_set = self.register_config_set  # type: ignore[assignment]
        options, cmd_handlers = opt_parse
        self.options = options
        self.cmd_handlers = cmd_handlers
        self.log_handler = log_handler
        self.args = args

        self._run_env: dict[str, RunToxEnv] = {}
        self._pkg_env: dict[str, tuple[str, PackageToxEnv]] = {}
        self._pkg_env_discovered: set[str] = set()

        self.journal: Journal = Journal(getattr(options, "result_json", None) is not None)

    def tox_env(self, name: str) -> RunToxEnv:
        if name in self._pkg_env_discovered:
            raise HandledError(f"cannot run packaging environment {name}")
        with self.log_handler.with_context(name):
            tox_env = self._run_env.get(name)
            if tox_env is not None:
                return tox_env
            self.conf.get_env(name)  # the lookup here will trigger register_config_set, which will build it
            return self._run_env[name]

    def register_config_set(self, name: str, env_config_set: EnvConfigSet) -> None:
        """Ensure the config set with the given name has been registered with configuration values"""
        # during the creation of the tox environment we automatically register configurations, so to ensure
        # config sets have a set of defined values in it we have to ensure the tox environment is created
        if name in self._pkg_env_discovered:
            return  # packaging environments are created explicitly, nothing to do here
        if name in self._run_env:  # pragma: no branch
            raise ValueError(f"{name} run tox env already defined")  # pragma: no cover
        # runtime environments are created upon lookup via the tox_env method, call it
        self._build_run_env(env_config_set)

    def _build_run_env(self, env_conf: EnvConfigSet) -> None:
        env_conf.add_config(
            keys="runner",
            desc="the tox execute used to evaluate this environment",
            of_type=str,
            default=self.options.default_runner,
        )
        runner = cast(str, env_conf["runner"])
        from tox.tox_env.register import REGISTER

        builder = REGISTER.runner(runner)
        name = env_conf.name
        journal = self.journal.get_env_journal(name)
        args = ToxEnvCreateArgs(env_conf, self.conf.core, self.options, journal, self.log_handler)
        env: RunToxEnv = builder(args)
        self._run_env[name] = env
        self._build_package_env(env)

    def _build_package_env(self, env: RunToxEnv) -> None:
        pkg_info = env.get_package_env_types()
        if pkg_info is not None:
            name, core_type = pkg_info
            env.package_env = self._build_pkg_env(name, core_type, env)

    def _build_pkg_env(self, name: str, core_type: str, env: RunToxEnv) -> PackageToxEnv:
        with self.log_handler.with_context(name):
            package_tox_env = self._get_package_env(core_type, name)

            child_package_envs = package_tox_env.register_run_env(env)
            try:
                child_name, child_type = next(child_package_envs)
                while True:
                    child_pkg_env = self._build_pkg_env(child_name, child_type, env)
                    child_name, child_type = child_package_envs.send(child_pkg_env)
            except StopIteration:
                pass
            return package_tox_env

    def _get_package_env(self, packager: str, name: str) -> PackageToxEnv:
        if name in self._pkg_env:  # if already created reuse
            old, pkg_tox_env = self._pkg_env[name]
            if old != packager:  # pragma: no branch # same env name is used by different packaging: dpkg vs virtualenv
                msg = f"{name} is already defined as a {old}, cannot be {packager} too"  # pragma: no cover
                raise HandledError(msg)  # pragma: no cover
        else:
            from tox.tox_env.register import REGISTER

            package_type = REGISTER.package(packager)
            self._pkg_env_discovered.add(name)
            if name in self._run_env:
                raise HandledError(f"{name} is already defined as a run environment, cannot be packaging too")
            pkg_conf = self.conf.get_env(name, package=True)
            journal = self.journal.get_env_journal(name)
            args = ToxEnvCreateArgs(pkg_conf, self.conf.core, self.options, journal, self.log_handler)
            pkg_tox_env = package_type(args)
            self._pkg_env[name] = packager, pkg_tox_env
        return pkg_tox_env

    def created_run_envs(self) -> Iterator[tuple[str, RunToxEnv]]:
        yield from self._run_env.items()

    def all_run_envs(self, *, with_skip: bool = True) -> Iterator[str]:
        default_env_list = self.conf.core["env_list"]
        ignore = {self.conf.core["provision_tox_env"]}
        for env in chain(default_env_list.envs, self.conf.env_list(everything=True)):
            if env in ignore:
                continue
            ignore.add(env)  # ignore self
            skip = False
            try:
                tox_env = self.tox_env(env)
            except Skip:
                skip = True
                tox_env = self.tox_env(env)
            ignore.update(i.name for i in tox_env.package_envs)  # ignore package environments
            if not skip or with_skip:
                yield env


@impl
def tox_add_option(parser: ToxParser) -> None:
    from tox.tox_env.register import REGISTER

    parser.add_argument(
        "--runner",
        dest="default_runner",
        help="the tox run engine to use when not explicitly stated in tox env configuration",
        default=REGISTER.default_env_runner,
        choices=list(REGISTER.env_runners),
    )
