"""
A pytest plugin useful to test tox itself (and its plugins).
"""

import os
import sys
import textwrap
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Sequence

import pytest
from _pytest.capture import CaptureFixture as _CaptureFixture
from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch

import tox.run
from tox.config.main import Config
from tox.execute.api import Outcome
from tox.execute.request import shell_cmd
from tox.report import LOGGER
from tox.run import run as tox_run
from tox.run import setup_state as previous_setup_state
from tox.session.cmd.run.parallel import ENV_VAR_KEY
from tox.session.state import State

if TYPE_CHECKING:
    CaptureFixture = _CaptureFixture[str]
else:
    CaptureFixture = _CaptureFixture


@pytest.fixture(autouse=True)
def ensure_logging_framework_not_altered() -> Iterator[None]:
    before_handlers = list(LOGGER.handlers)
    yield
    LOGGER.handlers = before_handlers


@contextmanager
def check_os_environ() -> Iterator[None]:
    old = os.environ.copy()
    to_clean = {k: os.environ.pop(k, None) for k in {ENV_VAR_KEY, "TOX_WORK_DIR", "PYTHONPATH"}}

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
        path: Path,
        capsys: CaptureFixture,
        monkeypatch: MonkeyPatch,
    ) -> None:
        self.path = path
        self._capsys = capsys
        self.monkeypatch = monkeypatch
        self._setup_files(self.path, files)

    @staticmethod
    def _setup_files(dest: Path, content: Dict[str, Any]) -> None:
        for key, value in content.items():
            if not isinstance(key, str):
                raise TypeError(f"{key!r} at {dest}")  # pragma: no cover
            at_path = dest / key
            if isinstance(value, dict):
                at_path.mkdir(exist_ok=True)
                ToxProject._setup_files(at_path, value)
            elif isinstance(value, str):
                at_path.write_text(textwrap.dedent(value))
            else:
                msg = "could not handle {} with content {!r}".format(at_path / key, value)  # pragma: no cover
                raise TypeError(msg)  # pragma: no cover

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

    def config(self) -> Config:
        return tox.run.make_config(self.path, [])

    def run(self, *args: str) -> "ToxRunOutcome":
        cur_dir = os.getcwd()
        state = None
        os.chdir(str(self.path))
        try:
            self._capsys.readouterr()  # start with a clean state - drain
            code = None
            state = None

            def our_setup_state(value: Sequence[str]) -> State:
                nonlocal state
                state = previous_setup_state(value)
                return state

            with self.monkeypatch.context() as m:
                m.setattr(tox.run, "setup_state", our_setup_state)
                try:
                    tox_run(args)
                except SystemExit as exception:
                    code = exception.code
                if code is None:
                    raise RuntimeError("exit code not set")
            out, err = self._capsys.readouterr()
            return ToxRunOutcome(args, self.path, code, out, err, state)
        finally:
            os.chdir(cur_dir)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(path={self.path}) at {id(self)}"


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

    @property
    def success(self) -> bool:
        return self.code == Outcome.OK

    def assert_success(self) -> None:
        if not self.success:
            assert repr(self)

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

    def assert_out_err(self, out: str, err: str, *, dedent: bool = True) -> None:
        if out is not None and dedent:
            out = textwrap.dedent(out).lstrip()
        assert self.out == out
        if err is not None and dedent:
            err = textwrap.dedent(err).lstrip()
        assert self.err == err


ToxProjectCreator = Callable[[Dict[str, Any]], ToxProject]


@pytest.fixture(name="tox_project")
def init_fixture(tmp_path: Path, capsys: CaptureFixture, monkeypatch: MonkeyPatch) -> ToxProjectCreator:
    def _init(files: Dict[str, Any]) -> ToxProject:
        """create tox  projects"""
        return ToxProject(files, tmp_path, capsys, monkeypatch)

    return _init


@pytest.fixture()
def empty_project(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> ToxProject:
    project = tox_project({"tox.ini": ""})
    monkeypatch.chdir(project.path)
    return project


__all__ = (
    "CaptureFixture",
    "LogCaptureFixture",
    "MonkeyPatch",
    "ToxRunOutcome",
    "ToxProject",
    "ToxProjectCreator",
    "check_os_environ",
)
