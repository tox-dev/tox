"""
Defines the abstract base traits of a tox environment.
"""
import logging
import os
import re
import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Union, cast

from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.execute.api import Execute, Outcome
from tox.execute.request import ExecuteRequest
from tox.journal import EnvJournal
from tox.tox_env.errors import Recreate

from .info import Info

if TYPE_CHECKING:
    from tox.config.cli.parser import Parsed


class ToxEnv(ABC):
    def __init__(self, conf: ConfigSet, core: ConfigSet, options: "Parsed", journal: EnvJournal) -> None:
        self.journal = journal
        self.conf: ConfigSet = conf
        self.core: ConfigSet = core
        self.options = options
        self._executor = self.executor()
        self.register_config()
        self._cache = Info(self.conf["env_dir"])
        self._paths: List[Path] = []
        self.logger = logging.getLogger(self.conf["env_name"])
        self._env_vars: Optional[Dict[str, str]] = None
        self.setup_done = False
        self.clean_done = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.conf['env_name']})"

    @abstractmethod
    def executor(self) -> Execute:
        raise NotImplementedError

    def register_config(self) -> None:
        self.conf.add_constant(
            keys=["env_name", "envname"],
            desc="the name of the tox environment",
            value=self.conf.name,
        )
        self.conf.add_config(
            keys=["env_dir", "envdir"],
            of_type=Path,
            default=lambda conf, name: cast(Path, conf.core["work_dir"]) / cast(str, self.conf["env_name"]),
            desc="directory assigned to the tox environment",
        )
        self.conf.add_config(
            keys=["env_tmp_dir", "envtmpdir"],
            of_type=Path,
            default=lambda conf, name: cast(Path, conf.core["work_dir"]) / cast(str, self.conf["env_name"]) / "tmp",
            desc="a folder that is always reset at the start of the run",
        )

        def set_env_post_process(values: Dict[str, str], config: Config) -> Dict[str, str]:
            env = self.default_set_env()
            env.update(values)
            return env

        self.conf.add_config(
            keys=["set_env", "setenv"],
            of_type=Dict[str, str],
            default={},
            desc="environment variables to set when running commands in the tox environment",
            post_process=set_env_post_process,
        )

        def pass_env_post_process(values: List[str], config: Config) -> List[str]:
            values.extend(self.default_pass_env())
            return sorted(list({k: None for k in values}.keys()))

        self.conf.add_config(
            keys=["pass_env", "passenv"],
            of_type=List[str],
            default=[],
            desc="environment variables to pass on to the tox environment",
            post_process=pass_env_post_process,
        )

    def default_set_env(self) -> Dict[str, str]:
        return {}

    def default_pass_env(self) -> List[str]:
        env = [
            "https_proxy",
            "http_proxy",
            "no_proxy",
        ]
        if sys.stdout.isatty():  # if we're on a interactive shell pass on the TERM
            env.append("TERM")
        if sys.platform == "win32":  # pragma: win32 cover
            env.extend(
                [
                    "TEMP",
                    "TMP",
                ]
            )
        else:  # pragma: win32 no cover
            env.append("TMPDIR")
        return env

    def setup(self) -> None:
        """
        1. env dir exists
        2. contains a runner with the same type.
        """
        env_dir: Path = self.conf["env_dir"]
        conf = {"name": self.conf.name, "type": type(self).__name__}
        try:
            with self._cache.compare(conf, ToxEnv.__name__) as (eq, old):
                try:
                    if eq is True:
                        return
                    # if either the name or type changed and already exists start over
                    self.clean()
                finally:
                    env_dir.mkdir(exist_ok=True, parents=True)
        finally:
            self._handle_env_tmp_dir()
        self.setup_done, self.clean_done = True, False

    def ensure_setup(self, recreate: bool = False) -> None:
        if self.setup_done is True:
            return
        if recreate:
            self.clean()
        try:
            self.setup()
        except Recreate:
            if not recreate:
                self.clean()
                self.setup()
        self.setup_has_been_done()

    def setup_has_been_done(self) -> None:
        """called when setup is done"""

    def _handle_env_tmp_dir(self) -> None:
        """Ensure exists and empty"""
        env_tmp_dir: Path = self.conf["env_tmp_dir"]
        if env_tmp_dir.exists():
            logging.debug("removing %s", env_tmp_dir)
            shutil.rmtree(env_tmp_dir, ignore_errors=True)
        env_tmp_dir.mkdir(parents=True)

    def clean(self) -> None:
        if self.clean_done is True:
            return
        env_dir: Path = self.conf["env_dir"]
        if env_dir.exists():
            logging.info("remove tox env folder %s", env_dir)
            shutil.rmtree(env_dir)
        self._cache.reset()
        self.setup_done, self.clean_done = False, True

    @property
    def environment_variables(self) -> Dict[str, str]:
        if self._env_vars is not None:
            return self._env_vars
        result: Dict[str, str] = {}

        pass_env: List[str] = self.conf["pass_env"]
        glob_pass_env = [re.compile(e.replace("*", ".*")) for e in pass_env if "*" in e]
        literal_pass_env = [e for e in pass_env if "*" not in e]
        for env in literal_pass_env:
            if env in os.environ:
                result[env] = os.environ[env]
        if glob_pass_env:
            for env, value in os.environ.items():
                if any(g.match(env) is not None for g in glob_pass_env):
                    result[env] = value
        set_env: Dict[str, str] = self.conf["set_env"]
        result.update(set_env)
        result["PATH"] = os.pathsep.join([str(i) for i in self._paths] + os.environ.get("PATH", "").split(os.pathsep))
        self._env_vars = result
        return result

    def execute(
        self,
        cmd: Sequence[Union[Path, str]],
        allow_stdin: bool,
        show_on_standard: Optional[bool] = None,
        cwd: Optional[Path] = None,
        run_id: str = "",
    ) -> Outcome:
        if cwd is None:
            cwd = self.core["tox_root"]
        if show_on_standard is None:
            show_on_standard = self.options.verbosity > 3
        request = ExecuteRequest(cmd, cwd, self.environment_variables, allow_stdin)
        if _CWD == request.cwd:
            repr_cwd = ""
        else:
            try:
                repr_cwd = f" {_CWD.relative_to(cwd)}"
            except ValueError:
                repr_cwd = str(cwd)
        self.logger.warning("%s%s> %s", run_id, repr_cwd, request.shell_cmd)
        outcome = self._executor(request=request, show_on_standard=show_on_standard, colored=self.options.colored)
        if self.journal:
            self.journal.add_execute(outcome, run_id)
        return outcome

    @staticmethod
    @abstractmethod
    def id() -> str:
        raise NotImplementedError

    def hide_display(self) -> None:
        """No longer show"""
        assert self.logger.name

    def resume_display(self) -> None:
        """No longer show"""
        assert self.logger.name


_CWD = Path.cwd()
