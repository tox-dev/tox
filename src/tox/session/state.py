from typing import TYPE_CHECKING, Dict, Iterator, Optional, Sequence, Set, Tuple, cast

from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.plugin.impl import impl
from tox.report import HandledError
from tox.session.common import CliEnv
from tox.tox_env.package import PackageToxEnv
from tox.tox_env.runner import RunToxEnv

if TYPE_CHECKING:

    from tox.config.cli.parse import Handlers
    from tox.config.cli.parser import Parsed, ToxParser


class State:
    def __init__(
        self,
        conf: Config,
        opt_parse: Tuple["Parsed", "Handlers"],
        args: Sequence[str],
    ) -> None:
        self.conf = conf
        self.conf.register_config_set = self.register_config_set
        options, handlers = opt_parse
        self.options = options
        self.handlers = handlers
        self.args = args

        self._run_env: Dict[str, RunToxEnv] = {}
        self._pkg_env: Dict[str, PackageToxEnv] = {}
        self._pkg_env_discovered: Set[str] = set()

    def env_list(self, everything: bool = False) -> Iterator[str]:
        if everything:
            yield from self.conf
            return
        use_env_list: Optional[CliEnv] = getattr(self.options, "env", None)
        if use_env_list is None or use_env_list.all:
            use_env_list = self.conf.core["env_list"]
        if use_env_list is not None:
            yield from use_env_list

    def tox_env(self, name: str) -> RunToxEnv:
        if name in self._pkg_env_discovered:
            raise KeyError(f"{name} is a packaging tox environment")
        tox_env = self._run_env.get(name)
        if tox_env is not None:
            return tox_env
        env_conf = self.conf.get_env(name)
        tox_env = self._build_run_env(env_conf, name)
        self._run_env[name] = tox_env
        return tox_env

    def register_config_set(self, name: str) -> None:
        """Ensure the config set with the given name has been registered with configuration values"""
        # during the creation of hte tox environment we automatically register configurations, so to ensure
        # config sets have a set of defined values in it we have to ensure the tox environment is created
        if name in self._pkg_env_discovered:
            return  # packaging environments are created explicitly, nothing to do here
        if name not in self._run_env:
            self.tox_env(name)  # runtime environments are created upon lookup via the tox_env method, call it

    def _build_run_env(self, env_conf: ConfigSet, env_name: str) -> RunToxEnv:
        env_conf.add_config(
            keys="runner",
            desc="the tox execute used to evaluate this environment",
            of_type=str,
            default=self.options.default_runner,  # noqa
        )
        runner = cast(str, env_conf["runner"])
        from tox.tox_env.register import REGISTER

        builder = REGISTER.runner(runner)
        env: RunToxEnv = builder(env_conf, self.conf.core, self.options)
        self._build_package_env(env)
        return env

    def _build_package_env(self, env: RunToxEnv) -> None:
        pkg_env_gen = env.set_package_env()
        try:
            name, packager = next(pkg_env_gen)
        except StopIteration:
            pass
        else:
            if name in self._run_env:
                raise HandledError(f"{name} is already defined as a run environment, cannot be packaging too")
            package_tox_env = self._get_package_env(packager, name)
            try:
                pkg_env_gen.send(package_tox_env)
            except StopIteration:
                pass

    def _get_package_env(self, packager: str, name: str) -> PackageToxEnv:
        if name in self._pkg_env:  # if already created reuse
            pkg_tox_env: PackageToxEnv = self._pkg_env[name]
        else:
            if name in self._run_env:  # if already detected as runner remove
                del self._run_env[name]
            from tox.tox_env.register import REGISTER

            package_type = REGISTER.package(packager)
            self._pkg_env_discovered.add(name)
            pkg_conf = self.conf.get_env(name, package=True)
            pkg_tox_env = package_type(pkg_conf, self.conf.core, self.options)
            self._pkg_env[name] = pkg_tox_env
        return pkg_tox_env


@impl
def tox_add_option(parser: "ToxParser") -> None:
    from tox.tox_env.register import REGISTER

    parser.add_argument(
        "--runner",
        dest="default_runner",
        help="default execute",
        default=REGISTER.default_run_env,
        choices=list(REGISTER.run_envs),
    )
