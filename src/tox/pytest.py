"""
A pytest plugin useful to test tox itself (and its plugins).
"""

import os
import random
import re
import shutil
import socket
import string
import sys
import textwrap
import warnings
from contextlib import closing, contextmanager
from pathlib import Path
from subprocess import PIPE, Popen, check_call
from threading import Thread
from types import TracebackType
from typing import IO, TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Type, cast
from unittest.mock import MagicMock

import pytest
from _pytest.capture import CaptureFixture as _CaptureFixture
from _pytest.config import Config as PyTestConfig
from _pytest.config.argparsing import Parser
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from _pytest.python import Function
from _pytest.tmpdir import TempPathFactory
from pytest_mock import MockerFixture
from virtualenv.discovery.py_info import PythonInfo
from virtualenv.info import IS_WIN, fs_supports_symlink

import tox.run
from tox.config.sets import EnvConfigSet
from tox.execute.api import Execute, ExecuteInstance, ExecuteStatus, Outcome
from tox.execute.request import ExecuteRequest, shell_cmd
from tox.execute.stream import SyncWrite
from tox.report import LOGGER, OutErr
from tox.run import run as tox_run
from tox.run import setup_state as previous_setup_state
from tox.session.cmd.run.parallel import ENV_VAR_KEY
from tox.session.state import State
from tox.tox_env import api as tox_env_api
from tox.tox_env.api import ToxEnv

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from typing import Protocol
else:  # pragma: no cover (<py38)
    from typing_extensions import Protocol  # noqa

if TYPE_CHECKING:
    CaptureFixture = _CaptureFixture[str]
else:
    CaptureFixture = _CaptureFixture

os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
os.environ["PIP_NO_PYTHON_VERSION_WARNING"] = "1"

if fs_supports_symlink():  # pragma: no cover # used to speed up test suite run time where possible
    os.environ["VIRTUALENV_SYMLINK_APP_DATA"] = "1"
    os.environ["VIRTUALENV_SYMLINKS"] = "1"


@pytest.fixture(autouse=True)
def ensure_logging_framework_not_altered() -> Iterator[None]:
    before_handlers = list(LOGGER.handlers)
    yield
    LOGGER.handlers = before_handlers


@contextmanager
def check_os_environ() -> Iterator[None]:
    old = os.environ.copy()
    to_clean = {k: os.environ.pop(k, None) for k in {ENV_VAR_KEY, "TOX_WORK_DIR", "PYTHONPATH", "COV_CORE_CONTEXT"}}

    yield

    for key, value in to_clean.items():
        if value is not None:
            os.environ[key] = value

    new = os.environ
    extra = {k: new[k] for k in set(new) - set(old)}
    extra.pop("PLAT", None)
    miss = {k: old[k] for k in set(old) - set(new)}
    diff = {
        f"{k} = {old[k]} vs {new[k]}" for k in set(old) & set(new) if old[k] != new[k] and not k.startswith("PYTEST_")
    }
    if extra or miss or diff:
        msg = "test changed environ"
        if extra:
            msg += f" extra {extra}"
        if miss:
            msg += f" miss {miss}"
        if diff:
            msg += f" diff {diff}"
        pytest.fail(msg)


@pytest.fixture(autouse=True)
def check_os_environ_stable(monkeypatch: MonkeyPatch) -> Iterator[None]:
    with check_os_environ():
        yield
        monkeypatch.undo()


@pytest.fixture(autouse=True)
def no_color(monkeypatch: MonkeyPatch, check_os_environ_stable: None) -> None:
    monkeypatch.setenv("NO_COLOR", "yes")


class ToxProject:
    def __init__(
        self,
        files: Dict[str, Any],
        base: Optional[Path],
        path: Path,
        capfd: CaptureFixture,
        monkeypatch: MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        self.path: Path = path
        self.monkeypatch: MonkeyPatch = monkeypatch
        self.mocker = mocker
        self._capfd = capfd
        self._setup_files(self.path, base, files)

    @staticmethod
    def _setup_files(dest: Path, base: Optional[Path], content: Dict[str, Any]) -> None:
        if base is not None:
            shutil.copytree(str(base), str(dest))
        dest.mkdir(exist_ok=True)
        for key, value in content.items():
            if not isinstance(key, str):
                raise TypeError(f"{key!r} at {dest}")  # pragma: no cover
            at_path = dest / key
            if isinstance(value, dict):
                at_path.mkdir(exist_ok=True)
                ToxProject._setup_files(at_path, None, value)
            elif isinstance(value, str):
                at_path.write_text(textwrap.dedent(value))
            else:
                msg = "could not handle {} with content {!r}".format(at_path / key, value)  # pragma: no cover
                raise TypeError(msg)  # pragma: no cover

    def patch_execute(self, handle: Callable[[ExecuteRequest], Optional[int]]) -> MagicMock:
        class MockExecute(Execute):
            def __init__(self, colored: bool, exit_code: int) -> None:
                self.exit_code = exit_code
                super().__init__(colored)

            def build_instance(self, request: ExecuteRequest, out: SyncWrite, err: SyncWrite) -> ExecuteInstance:
                return MockExecuteInstance(request, out, err, self.exit_code)

        class MockExecuteStatus(ExecuteStatus):
            def __init__(self, out: SyncWrite, err: SyncWrite, exit_code: int) -> None:
                super().__init__(out, err)
                self._exit_code = exit_code

            @property
            def exit_code(self) -> Optional[int]:
                return self._exit_code

            def wait(self, timeout: Optional[float] = None) -> None:
                """"""

            def write_stdin(self, content: str) -> None:
                """"""

            def interrupt(self) -> None:
                """"""

        class MockExecuteInstance(ExecuteInstance):
            def __init__(self, request: ExecuteRequest, out: SyncWrite, err: SyncWrite, exit_code: int) -> None:
                super().__init__(request, out, err)
                self.exit_code = exit_code

            def __enter__(self) -> ExecuteStatus:
                return MockExecuteStatus(self._out, self._err, self.exit_code)

            def __exit__(
                self,
                exc_type: Optional[Type[BaseException]],
                exc_val: Optional[BaseException],
                exc_tb: Optional[TracebackType],
            ) -> None:
                pass

            @property
            def cmd(self) -> Sequence[str]:
                return self.request.cmd

        @contextmanager
        def _execute_call(
            self: ToxEnv, executor: Execute, out_err: OutErr, request: ExecuteRequest, show: bool  # noqa
        ) -> Iterator[ExecuteStatus]:
            exit_code = handle(request)
            if exit_code is not None:
                executor = MockExecute(colored=executor._colored, exit_code=exit_code)  # noqa
            with original_execute_call(self, executor, out_err, request, show) as status:
                yield status

        original_execute_call = ToxEnv._execute_call  # noqa
        result = self.mocker.patch.object(ToxEnv, "_execute_call", side_effect=_execute_call, autospec=True)
        return result

    @property
    def structure(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for dir_name, _, files in os.walk(str(self.path)):
            dir_path = Path(dir_name)
            into = result
            relative = dir_path.relative_to(str(self.path))
            for elem in relative.parts:
                into = into.setdefault(elem, {})
            for file_name in files:
                into[file_name] = (dir_path / file_name).read_text()
        return result

    @contextmanager
    def chdir(self) -> Iterator[None]:
        cur_dir = os.getcwd()
        os.chdir(str(self.path))
        try:
            yield
        finally:
            os.chdir(cur_dir)

    def run(self, *args: str) -> "ToxRunOutcome":
        with self.chdir():
            state = None
            self._capfd.readouterr()  # start with a clean state - drain
            code = None
            state = None

            def our_setup_state(value: Sequence[str]) -> State:
                nonlocal state
                state = previous_setup_state(value)
                return state

            with self.monkeypatch.context() as m:
                m.setattr(tox_env_api, "_CWD", self.path)
                m.setattr(tox.run, "setup_state", our_setup_state)
                m.setattr(sys, "argv", [sys.executable, "-m", "tox"] + list(args))
                m.setenv("VIRTUALENV_SYMLINK_APP_DATA", "1")
                m.setenv("VIRTUALENV_SYMLINKS", "1")
                m.setenv("VIRTUALENV_PIP", "embed")
                m.setenv("VIRTUALENV_WHEEL", "embed")
                m.setenv("VIRTUALENV_SETUPTOOLS", "embed")
                try:
                    tox_run(args)
                except SystemExit as exception:
                    code = exception.code
                if code is None:
                    raise RuntimeError("exit code not set")
            out, err = self._capfd.readouterr()
            return ToxRunOutcome(args, self.path, code, out, err, state)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(path={self.path}) at {id(self)}"


@pytest.fixture(autouse=True, scope="session")
def enable_pep517_backend_coverage() -> Iterator[None]:
    try:
        import coverage  # noqa: F401
    except ImportError:  # pragma: no cover
        yield  # pragma: no cover
        return  # pragma: no cover
    # the COV_ env variables needs to be passed on for the PEP-517 backend
    from tox.tox_env.python.virtual_env.package.api import Pep517VirtualEnvPackage

    def default_pass_env(self: Pep517VirtualEnvPackage) -> List[str]:
        result = previous(self)
        result.append("COV_*")
        return result

    previous = Pep517VirtualEnvPackage.default_pass_env
    try:
        Pep517VirtualEnvPackage.default_pass_env = default_pass_env  # type: ignore
        yield
    finally:
        Pep517VirtualEnvPackage.default_pass_env = previous  # type: ignore


class ToxRunOutcome:
    def __init__(self, cmd: Sequence[str], cwd: Path, code: int, out: str, err: str, state: Optional[State]) -> None:
        extended_cmd = [sys.executable, "-m", "tox"]
        extended_cmd.extend(cmd)
        self.cmd: List[str] = extended_cmd
        self.cwd: Path = cwd
        self.code: int = code
        self.out: str = out
        self.err: str = err
        self._state: Optional[State] = state

    @property
    def state(self) -> State:
        if self._state is None:
            raise RuntimeError("no state")
        return self._state

    def env_conf(self, name: str) -> EnvConfigSet:
        return self.state.conf.get_env(name)

    @property
    def success(self) -> bool:
        return self.code == Outcome.OK

    def assert_success(self) -> None:
        assert self.success, repr(self)

    def assert_failed(self, code: Optional[int] = None) -> None:
        status_match = self.code != 0 if code is None else self.code == code
        assert status_match, f"should be {code}, got {self}"

    def __repr__(self) -> str:
        return "\n".join(
            "{}{}{}".format(k, "\n" if "\n" in v else ": ", v)
            for k, v in (
                ("code", str(self.code)),
                ("cmd", self.shell_cmd),
                ("cwd", str(self.cwd)),
                ("standard output", self.out),
                ("standard error", self.err),
            )
            if v
        )

    @property
    def shell_cmd(self) -> str:
        return shell_cmd(self.cmd)

    def assert_out_err(self, out: str, err: str, *, dedent: bool = True, regex: bool = False) -> None:
        if dedent:
            out = textwrap.dedent(out).lstrip()
        if regex:
            self.matches(out, self.out, re.MULTILINE | re.DOTALL)
        else:
            assert self.out == out
        if dedent:
            err = textwrap.dedent(err).lstrip()
        if regex:
            self.matches(err, self.err, re.MULTILINE | re.DOTALL)
        else:
            assert self.err == err

    @staticmethod
    def matches(pattern: str, text: str, flags: int = 0) -> None:
        try:
            from re_assert import Matches
        except ImportError:  # pragma: no cover # hard to test
            match = re.match(pattern, text, flags)
            if match is None:
                warnings.warn("install the re-assert PyPi package for bette error message", UserWarning)
            assert match
        else:
            assert Matches(pattern, flags=flags) == text


class ToxProjectCreator(Protocol):
    def __call__(self, files: Dict[str, Any], base: Optional[Path] = None) -> ToxProject:
        ...


@pytest.fixture(name="tox_project")
def init_fixture(
    tmp_path: Path, capfd: CaptureFixture, monkeypatch: MonkeyPatch, mocker: MockerFixture
) -> ToxProjectCreator:
    def _init(files: Dict[str, Any], base: Optional[Path] = None) -> ToxProject:
        """create tox  projects"""
        return ToxProject(files, base, tmp_path / "p", capfd, monkeypatch, mocker)

    return _init  # noqa


@pytest.fixture()
def empty_project(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> ToxProject:
    project = tox_project({"tox.ini": ""})
    monkeypatch.chdir(project.path)
    return project


def pytest_addoption(parser: Parser) -> None:
    parser.addoption("--run-integration", action="store_true", help="run the integration tests")


def pytest_configure(config: PyTestConfig) -> None:
    config.addinivalue_line("markers", "integration")


@pytest.mark.trylast
def pytest_collection_modifyitems(config: PyTestConfig, items: List[Function]) -> None:
    # do not require flags if called directly
    if len(items) == 1:  # pragma: no cover # hard to test
        return

    skip_int = pytest.mark.skip(reason="integration tests not run (no --run-int flag)")

    def is_integration(test_item: Function) -> bool:
        return test_item.get_closest_marker("integration") is not None

    integration_enabled = config.getoption("--run-integration")
    if not integration_enabled:  # pragma: no cover # hard to test
        for item in items:
            if is_integration(item):
                item.add_marker(skip_int)
    # run integration tests after unit tests
    items.sort(key=lambda i: 1 if is_integration(i) else 0)


class Index:
    def __init__(self, base_url: str, name: str, client_cmd_base: List[str]) -> None:
        self._client_cmd_base = client_cmd_base
        self._server_url = base_url
        self.name = name

    @property
    def url(self) -> str:
        return f"{self._server_url}/{self.name}/+simple"

    def upload(self, files: Sequence[Path]) -> None:
        check_call(self._client_cmd_base + ["upload", "--index", self.name] + [str(i) for i in files])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(url={self.url})"  # pragma: no cover

    def use(self, monkeypatch: MonkeyPatch) -> None:
        enable_pypi_server(monkeypatch, self.url)


def enable_pypi_server(monkeypatch: MonkeyPatch, url: Optional[str]) -> None:
    if url is None:  # pragma: no cover # only one of the branches can be hit depending on env
        monkeypatch.delenv("PIP_INDEX_URL", raising=False)
    else:  # pragma: no cover
        monkeypatch.setenv("PIP_INDEX_URL", url)
    monkeypatch.setenv("PIP_RETRIES", str(5))
    monkeypatch.setenv("PIP_TIMEOUT", str(2))


def _find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as socket_handler:
        socket_handler.bind(("", 0))
        return cast(int, socket_handler.getsockname()[1])


class IndexServer:
    def __init__(self, path: Path) -> None:
        self.path = path

        self.host, self.port = "localhost", _find_free_port()
        self._passwd = "".join(random.choice(string.ascii_letters) for _ in range(8))

        def _exe(name: str) -> str:
            return str(Path(scripts_dir) / f"{name}{'.exe' if IS_WIN else ''}")

        scripts_dir = PythonInfo.current().sysconfig_path("scripts")
        self._init: str = _exe("devpi-init")
        self._server: str = _exe("devpi-server")
        self._client: str = _exe("devpi")

        self._server_dir = self.path / "server"
        self._client_dir = self.path / "client"
        self._indexes: Dict[str, Index] = {}
        self._process: Optional["Popen[str]"] = None
        self._has_use = False
        self._stdout_drain: Optional[Thread] = None

    def __enter__(self) -> "IndexServer":
        self._create_and_start_server()
        self._setup_client()
        return self

    def _create_and_start_server(self) -> None:
        self._server_dir.mkdir(exist_ok=True)
        server_at = str(self._server_dir)
        # 1. create the server
        cmd = [self._init, "--serverdir", server_at]
        cmd.extend(("--no-root-pypi", "--role", "standalone", "--root-passwd", self._passwd))
        check_call(cmd, stdout=PIPE, stderr=PIPE)
        # 2. start the server
        cmd = [self._server, "--serverdir", server_at, "--port", str(self.port), "--offline-mode"]
        self._process = Popen(cmd, stdout=PIPE, universal_newlines=True)
        stdout = self._drain_stdout()
        for line in stdout:  # pragma: no branch # will always loop at least once
            if "serving at url" in line:

                def _keep_draining() -> None:
                    for _ in stdout:
                        pass

                # important to keep draining the stdout, otherwise once the buffer is full Windows blocks the processg s
                self._stdout_drain = Thread(target=_keep_draining, name="tox-test-stdout-drain")
                self._stdout_drain.start()
                break

    def _drain_stdout(self) -> Iterator[str]:
        process = cast("Popen[str]", self._process)
        stdout = cast(IO[str], process.stdout)
        while True:
            if process.poll() is not None:  # pragma: no cover
                print(f"devpi server with pid {process.pid} at {self._server_dir} died")
                break
            yield stdout.readline()

    def _setup_client(self) -> None:
        """create a user on the server and authenticate it"""
        self._client_dir.mkdir(exist_ok=True)
        base = ["--clientdir", str(self._client_dir)]
        check_call([self._client, "use"] + base + [self.url], stdout=PIPE, stderr=PIPE)
        check_call([self._client, "login"] + base + ["root", "--password", self._passwd], stdout=PIPE, stderr=PIPE)

    def create_index(self, name: str, *args: str) -> Index:
        if name in self._indexes:  # pragma: no cover
            raise ValueError(f"index {name} already exists")
        base = [self._client, "--clientdir", str(self._client_dir)]
        check_call(base + ["index", "-c", name, *args], stdout=PIPE, stderr=PIPE)
        index = Index(f"{self.url}/root", name, base)
        if not self._has_use:
            self._has_use = True
            check_call(base + ["use", f"root/{name}"], stdout=PIPE, stderr=PIPE)
        self._indexes[name] = index
        return index

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        if self._process is not None:  # pragma: no cover # defend against devpi startup fail
            self._process.terminate()
        if self._stdout_drain is not None and self._stdout_drain.is_alive():  # pragma: no cover # devpi startup fail
            self._stdout_drain.join()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(url={self.url}, indexes={list(self._indexes)})"  # pragma: no cover


@pytest.fixture(scope="session")
def pypi_server(tmp_path_factory: TempPathFactory) -> Iterator[IndexServer]:
    # takes around 2.5s
    path = tmp_path_factory.mktemp("pypi")
    with IndexServer(path) as server:
        server.create_index("empty", "volatile=False")
        yield server


@pytest.fixture(scope="session")
def _invalid_index_fake_port() -> int:
    return _find_free_port()


@pytest.fixture(autouse=True)
def disable_pip_pypi_access(_invalid_index_fake_port: int, monkeypatch: MonkeyPatch) -> Tuple[str, Optional[str]]:
    """set a fake pip index url, tests that want to use a pypi server should create and overwrite this"""
    previous_url = os.environ.get("PIP_INDEX_URL")
    new_url = f"http://localhost:{_invalid_index_fake_port}/bad-pypi-server"
    monkeypatch.setenv("PIP_INDEX_URL", new_url)
    monkeypatch.setenv("PIP_RETRIES", str(0))
    monkeypatch.setenv("PIP_TIMEOUT", str(0.001))
    return new_url, previous_url


@pytest.fixture(name="enable_pip_pypi_access")
def enable_pip_pypi_access_fixture(
    disable_pip_pypi_access: Tuple[str, Optional[str]], monkeypatch: MonkeyPatch
) -> Optional[str]:
    """set a fake pip index url, tests that want to use a pypi server should create and overwrite this"""
    _, previous_url = disable_pip_pypi_access
    enable_pypi_server(monkeypatch, previous_url)
    return previous_url


__all__ = (
    "CaptureFixture",
    "LogCaptureFixture",
    "TempPathFactory",
    "MonkeyPatch",
    "ToxRunOutcome",
    "ToxProject",
    "ToxProjectCreator",
    "check_os_environ",
    "IndexServer",
    "Index",
)
