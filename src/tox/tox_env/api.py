"""
Defines the abstract base traits of a tox environment.
"""
import logging
import os
import re
import shutil
import sys
from abc import ABC, abstractmethod
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Sequence, Tuple, Union, cast

from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.execute.api import Execute, ExecuteStatus, Outcome, StdinSource
from tox.execute.request import ExecuteRequest
from tox.journal import EnvJournal
from tox.report import OutErr, ToxHandler
from tox.tox_env.errors import Recreate

from .info import Info

if TYPE_CHECKING:
    from tox.config.cli.parser import Parsed

LOGGER = logging.getLogger(__name__)


class ToxEnv(ABC):
    def __init__(
        self, conf: ConfigSet, core: ConfigSet, options: "Parsed", journal: EnvJournal, log_handler: ToxHandler
    ) -> None:
        self.journal = journal
        self.conf: ConfigSet = conf
        self.core: ConfigSet = core
        self.options = options
        self._executor: Optional[Execute] = None
        self.register_config()
        self._cache = Info(self.conf["env_dir"])
        self._paths: List[Path] = []
        self._hidden_outcomes: Optional[List[Outcome]] = []
        self.log_handler = log_handler
        self._env_vars: Optional[Dict[str, str]] = None
        self._suspended_out_err: Optional[OutErr] = None
        self.setup_done = False
        self.clean_done = False
        self._execute_statuses: Dict[int, ExecuteStatus] = {}
        self._interrupted = False

    def interrupt(self) -> None:
        logging.warning("interrupt tox environment: %s", self.conf.name)
        self._interrupted = True
        for status in list(self._execute_statuses.values()):
            status.interrupt()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.conf['env_name']})"

    @property
    def executor(self) -> Execute:
        if self._executor is None:
            self._executor = self.build_executor()
        return self._executor

    @property
    def has_display_suspended(self) -> bool:
        return self._suspended_out_err is not None

    @abstractmethod
    def build_executor(self) -> Execute:
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

        self.conf.add_config(
            "parallel_show_output",
            of_type=bool,
            default=False,
            desc="if set to True the content of the output will always be shown  when running in parallel mode",
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
        conf = {"name": self.conf.name, "type": type(self).__name__}
        try:
            with self._cache.compare(conf, ToxEnv.__name__) as (eq, old):
                if eq is False and old is not None:  # recreate if already created and not equals
                    logging.warning(f"env type changed from {old} to {conf}, will recreate")
                    raise Recreate  # recreate if already exists and type changed
                self.setup_done, self.clean_done = True, False
        finally:
            self._handle_env_tmp_dir()

    def ensure_setup(self, recreate: bool = False) -> None:
        if self.setup_done is True:
            return
        if recreate:
            self.clean()
        try:
            self.setup()
        except Recreate:
            if not recreate:  # pragma: no cover
                self.clean()
                self.setup()
        self.setup_has_been_done()

    def setup_has_been_done(self) -> None:
        """called when setup is done"""

    def _handle_env_tmp_dir(self) -> None:
        """Ensure exists and empty"""
        env_tmp_dir: Path = self.conf["env_tmp_dir"]
        if env_tmp_dir.exists() and next(env_tmp_dir.iterdir(), None) is not None:
            LOGGER.debug("clear env temp folder %s", env_tmp_dir)
            shutil.rmtree(env_tmp_dir, ignore_errors=True)
        env_tmp_dir.mkdir(parents=True, exist_ok=True)

    def clean(self) -> None:
        if self.clean_done:  # pragma: no branch
            return  # pragma: no cover
        env_dir: Path = self.conf["env_dir"]
        if env_dir.exists():
            LOGGER.warning("remove tox env folder %s", env_dir)
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
        if glob_pass_env:  # pragma: no branch
            for env, value in os.environ.items():
                if any(g.match(env) is not None for g in glob_pass_env):
                    result[env] = value
        set_env: Dict[str, str] = self.conf["set_env"]
        result.update(set_env)
        result["PATH"] = os.pathsep.join([str(i) for i in self._paths] + os.environ.get("PATH", "").split(os.pathsep))
        columns, lines = shutil.get_terminal_size(fallback=(-1, -1))  # if cannot get (-1) do not set env-vars
        if columns != -1:  # pragma: no branch # no easy way to control get_terminal_size without env-vars
            result["COLUMNS"] = str(columns)
        if columns != 1:  # pragma: no branch # no easy way to control get_terminal_size without env-vars
            result["LINES"] = str(lines)
        self._env_vars = result
        return result

    def execute(
        self,
        cmd: Sequence[Union[Path, str]],
        stdin: StdinSource,
        show: Optional[bool] = None,
        cwd: Optional[Path] = None,
        run_id: str = "",
        executor: Optional[Execute] = None,
    ) -> Outcome:
        with self.execute_async(cmd, stdin, show, cwd, run_id, executor) as status:
            while status.exit_code is None:
                status.wait()
        if status.outcome is None:  # pragma: no cover # this should not happen
            raise RuntimeError  # pragma: no cover
        return status.outcome

    @contextmanager
    def execute_async(
        self,
        cmd: Sequence[Union[Path, str]],
        stdin: StdinSource,
        show: Optional[bool] = None,
        cwd: Optional[Path] = None,
        run_id: str = "",
        executor: Optional[Execute] = None,
    ) -> Iterator[ExecuteStatus]:
        if self._interrupted:
            raise SystemExit(-2)
        if cwd is None:
            cwd = self.core["tox_root"]
        if show is None:
            show = self.options.verbosity > 3
        request = ExecuteRequest(cmd, cwd, self.environment_variables, stdin)
        if _CWD == request.cwd:
            repr_cwd = ""
        else:
            try:
                repr_cwd = f" {_CWD.relative_to(cwd)}"
            except ValueError:
                repr_cwd = f" {cwd}"
        LOGGER.warning("%s%s> %s", run_id, repr_cwd, request.shell_cmd)
        out_err = self.log_handler.stdout, self.log_handler.stderr
        if executor is None:
            executor = self.executor
        with executor.call(
            request=request,
            show=show,
            out_err=out_err,
        ) as execute_status:
            execute_id = id(execute_status)
            try:
                self._execute_statuses[execute_id] = execute_status
                yield execute_status
            finally:
                self._execute_statuses.pop(execute_id)
        if show and self._hidden_outcomes is not None:
            if execute_status.outcome is not None:  # pragma: no cover # if it gets cancelled before even starting
                self._hidden_outcomes.append(execute_status.outcome)
        if self.journal and execute_status.outcome is not None:
            self.journal.add_execute(execute_status.outcome, run_id)

    @staticmethod
    @abstractmethod
    def id() -> str:
        raise NotImplementedError

    @contextmanager
    def display_context(self, suspend: bool) -> Iterator[None]:
        with self.log_context():
            with self.log_handler.suspend_out_err(suspend, self._suspended_out_err) as out_err:
                if suspend:  # only set if suspended
                    self._suspended_out_err = out_err
                yield

    def close_and_read_out_err(self) -> Optional[Tuple[bytes, bytes]]:
        if self._suspended_out_err is None:  # pragma: no branch
            return None  # pragma: no cover
        (out, err), self._suspended_out_err = self._suspended_out_err, None
        out_b, err_b = cast(BytesIO, out.buffer).getvalue(), cast(BytesIO, err.buffer).getvalue()
        out.close()
        err.close()
        return out_b, err_b

    @contextmanager
    def log_context(self) -> Iterator[None]:
        with self.log_handler.with_context(cast(str, self.conf.name)):
            yield

    def teardown(self) -> None:
        """Any cleanup operation on environment done"""


_CWD = Path.cwd()
