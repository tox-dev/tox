from typing import TYPE_CHECKING, Dict, Iterator, Optional, Sequence, Set, Tuple, cast

from tox.config.main import Config
from tox.config.sets import EnvConfigSet
from tox.journal import Journal
from tox.plugin import impl
from tox.report import HandledError, ToxHandler
from tox.session.common import CliEnv
from tox.tox_env.api import ToxEnvCreateArgs
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
        log_handler: ToxHandler,
    ) -> None:
        self.conf = conf
        self.conf.register_config_set = self.register_config_set
        options, cmd_handlers = opt_parse
        self.options = options
        self.cmd_handlers = cmd_handlers
        self.log_handler = log_handler
        self.args = args

        self._run_env: Dict[str, RunToxEnv] = {}
        self._pkg_env: Dict[str, Tuple[str, PackageToxEnv]] = {}
        self._pkg_env_discovered: Set[str] = set()

        self.journal: Journal = Journal(getattr(options, "result_json", None) is not None)

    def env_list(self, everything: bool = False) -> Iterator[str]:
        fallback_env = "py"
        use_env_list: Optional[CliEnv] = getattr(self.options, "env", None)
        if everything or (use_env_list is not None and use_env_list.all):
            _at = 0
            for _at, env in enumerate(self.conf, start=1):
                yield env
            if _at == 0:  # if we discovered no other env, inject the default
                yield fallback_env
            return
        if use_env_list is not None and use_env_list.use_default_list:
            use_env_list = self.conf.core["env_list"]
        if use_env_list is None or bool(use_env_list) is False:
            use_env_list = CliEnv([fallback_env])
        yield from use_env_list

    def tox_env(self, name: str) -> RunToxEnv:
        if name in self._pkg_env_discovered:
            raise HandledError(f"cannot run packaging environment {name}")
        with self.log_handler.with_context(name):
            tox_env = self._run_env.get(name)
            if tox_env is not None:
                return tox_env
            self.conf.get_env(name)  # the lookup here will trigger register_config_set, which will build it
            return self._run_env[name]

    def register_config_set(self, name: str, config_set: EnvConfigSet) -> None:
        """Ensure the config set with the given name has been registered with configuration values"""
        # during the creation of the tox environment we automatically register configurations, so to ensure
        # config sets have a set of defined values in it we have to ensure the tox environment is created
        if name in self._pkg_env_discovered:
            return  # packaging environments are created explicitly, nothing to do here
        if name in self._run_env:  # pragma: no branch
            raise ValueError(f"{name} run tox env already defined")  # pragma: no cover
        # runtime environments are created upon lookup via the tox_env method, call it
        self._build_run_env(config_set)

    def _build_run_env(self, env_conf: EnvConfigSet) -> None:
        env_conf.add_config(
            keys="runner",
            desc="the tox execute used to evaluate this environment",
            of_type=str,
            default=self.options.default_runner,  # noqa
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
        for tag, name, core_type in env.iter_package_env_types():
            with self.log_handler.with_context(name):
                package_tox_env = self._get_package_env(core_type, name)
                env.notify_of_package_env(tag, package_tox_env)

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

    def run_envs(self) -> Iterator[Tuple[str, RunToxEnv]]:
        yield from self._run_env.items()


@impl
def tox_add_option(parser: "ToxParser") -> None:
    from tox.tox_env.register import REGISTER

    parser.add_argument(
        "--runner",
        dest="default_runner",
        help="the tox run engine to use when not explicitly stated in tox env configuration",
        default=REGISTER.default_run_env,
        choices=list(REGISTER.run_envs),
    )
