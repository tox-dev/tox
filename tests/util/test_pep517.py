import os
import sys
from contextlib import contextmanager
from pathlib import Path
from stat import S_IWGRP, S_IWOTH, S_IWUSR
from subprocess import PIPE, Popen
from threading import Thread
from typing import IO, Any, Iterator, NamedTuple, Optional, Tuple, cast

import pytest
from packaging.requirements import Requirement
from pytest_mock import MockerFixture

from tox.pytest import TempPathFactory
from tox.util.pep517.frontend import BackendFailed, CmdStatus, Frontend

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution, EntryPoint  # type: ignore[attr-defined]
else:  # pragma: no cover (<py38)
    from importlib_metadata import Distribution, EntryPoint  # noqa


class SubprocessCmdStatus(CmdStatus, Thread):
    def __init__(self, process: "Popen[str]") -> None:
        super().__init__()
        self.process = process
        self._out_err: Optional[Tuple[str, str]] = None
        self.start()

    def run(self) -> None:
        self._out_err = self.process.communicate()

    @property
    def done(self) -> bool:
        return self.process.returncode is not None

    def out_err(self) -> Tuple[str, str]:
        return cast(Tuple[str, str], self._out_err)


class SubprocessFrontend(Frontend):
    def __init__(
        self,
        root: Path,
        backend_paths: Tuple[Path, ...],
        backend_module: str,
        backend_obj: Optional[str],
        requires: Tuple[Requirement, ...],
    ):
        super().__init__(root, backend_paths, backend_module, backend_obj, requires, reuse_backend=False)

    @contextmanager
    def _send_msg(self, cmd: str, result_file: Path, msg: str) -> Iterator[CmdStatus]:
        process = Popen(
            args=[sys.executable] + self.backend_args,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
            universal_newlines=True,
            cwd=self._root,
        )
        cast(IO[str], process.stdin).write(f"{os.linesep}{msg}{os.linesep}")
        yield SubprocessCmdStatus(process)

    def send_cmd(self, cmd: str, **kwargs: Any) -> Tuple[Any, str, str]:
        return self._send(cmd, object, **kwargs)


@pytest.fixture(scope="session")
def frontend_setuptools(tmp_path_factory: TempPathFactory) -> SubprocessFrontend:
    prj = tmp_path_factory.mktemp("proj")
    (prj / "pyproject.toml").write_text('requires=["setuptools","wheel"]\nbuild-backend = "setuptools.build_meta"')
    cfg = """
        [metadata]
        name = demo
        version = 1.0

        [options]
        packages = demo
        install_requires =
          requests>2
          magic>3

        [options.entry_points]
        console_scripts =
            demo_exe = demo:a
        """
    (prj / "setup.cfg").write_text(cfg)
    (prj / "setup.py").write_text("from setuptools import setup; setup()")
    demo = prj / "demo"
    demo.mkdir()
    (demo / "__init__.py").write_text("def a(): print('ok')")
    args = SubprocessFrontend.create_args_from_folder(prj)
    return SubprocessFrontend(*args[:-1])


def test_pep517_setuptools_commands(frontend_setuptools: SubprocessFrontend) -> None:
    commands = frontend_setuptools.commands
    assert commands == {
        "_commands",
        "_exit",
        "build_sdist",
        "build_wheel",
        "get_requires_for_build_sdist",
        "get_requires_for_build_wheel",
        "prepare_metadata_for_build_wheel",
    }
    assert commands is frontend_setuptools.commands  # ensure we cache it


def test_pep517_setuptools_get_requires_for_build_sdist(frontend_setuptools: SubprocessFrontend) -> None:
    result = frontend_setuptools.get_requires_for_build_sdist()
    assert result.requires == ()
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)


def test_pep517_setuptools_get_requires_for_build_wheel(frontend_setuptools: SubprocessFrontend) -> None:
    result = frontend_setuptools.get_requires_for_build_wheel()
    for left, right in zip(result.requires, (Requirement("wheel"),)):
        assert isinstance(left, Requirement)
        assert str(left) == str(right)
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)


def test_pep517_setuptools_prepare_metadata_for_build_wheel(
    frontend_setuptools: SubprocessFrontend, tmp_path: Path
) -> None:
    result = frontend_setuptools.prepare_metadata_for_build_wheel(metadata_directory=tmp_path)
    dist = Distribution.at(str(result.metadata))
    assert dist.entry_points == [EntryPoint(name="demo_exe", value="demo:a", group="console_scripts")]
    assert dist.version == "1.0"
    assert dist.metadata["Name"] == "demo"
    assert [v for k, v in dist.metadata.items() if k == "Requires-Dist"] == ["requests (>2)", "magic (>3)"]
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)

    # call it again regenerates it because frontend always deletes earlier content
    before = result.metadata.stat().st_mtime
    result = frontend_setuptools.prepare_metadata_for_build_wheel(metadata_directory=tmp_path)
    after = result.metadata.stat().st_mtime
    assert after > before


def test_pep517_setuptools_build_sdist(frontend_setuptools: SubprocessFrontend, tmp_path: Path) -> None:
    result = frontend_setuptools.build_sdist(tmp_path)
    sdist = result.sdist
    assert sdist.exists()
    assert sdist.is_file()
    assert sdist.name == "demo-1.0.tar.gz"
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)


def test_pep517_setuptools_build_wheel(frontend_setuptools: SubprocessFrontend, tmp_path: Path) -> None:
    result = frontend_setuptools.build_wheel(tmp_path)
    wheel = result.wheel
    assert wheel.exists()
    assert wheel.is_file()
    assert wheel.name == "demo-1.0-py3-none-any.whl"
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)


def test_pep517_setuptools_exit(frontend_setuptools: SubprocessFrontend) -> None:
    result, out, err = frontend_setuptools.send_cmd("_exit")
    assert isinstance(out, str)
    assert isinstance(err, str)
    assert result == 0


def test_pep517_setuptools_missing_command(frontend_setuptools: SubprocessFrontend) -> None:
    result, out, err = frontend_setuptools.send_cmd("missing_command")
    assert isinstance(out, str)
    assert isinstance(err, str)
    assert result is object


def test_pep517_setuptools_exception(frontend_setuptools: SubprocessFrontend) -> None:
    with pytest.raises(BackendFailed) as context:
        frontend_setuptools.send_cmd("build_wheel")
    assert isinstance(context.value.out, str)
    assert isinstance(context.value.err, str)
    assert context.value.exc_type == "TypeError"
    assert context.value.exc_msg == "build_wheel() missing 1 required positional argument: 'wheel_directory'"
    assert context.value.code == 1
    assert context.value.args == ()
    assert repr(context.value)
    assert str(context.value)
    assert repr(context.value) != str(context.value)


def test_pep517_bad_message(frontend_setuptools: SubprocessFrontend, tmp_path: Path) -> None:
    with frontend_setuptools._send_msg("bad_cmd", tmp_path / "a", "{") as status:
        while not status.done:
            pass
    out, err = status.out_err()
    assert not out
    assert "Backend: incorrect request to backend: {" in err


def test_pep517_result_missing(frontend_setuptools: SubprocessFrontend, tmp_path: Path, mocker: MockerFixture) -> None:
    class _Result(NamedTuple):
        name: str

    @contextmanager
    def named_temporary_file(prefix: str) -> Iterator[_Result]:
        write = S_IWUSR | S_IWGRP | S_IWOTH
        base = tmp_path / prefix
        result = base.with_suffix(".json")
        result.write_text("")
        result.chmod(result.stat().st_mode & ~write)  # force json write to fail due to R/O
        patch = mocker.patch("tox.util.pep517.frontend.Path.exists", return_value=False)  # make it missing
        try:
            yield _Result(str(base))
        finally:
            patch.stop()
            result.chmod(result.stat().st_mode | write)  # cleanup
            result.unlink()

    mocker.patch("tox.util.pep517.frontend.NamedTemporaryFile", named_temporary_file)
    with pytest.raises(BackendFailed) as context:
        frontend_setuptools.send_cmd("_exit")
    exc = context.value
    assert exc.exc_msg == f"Backend response file {tmp_path / 'pep517__exit-.json'} is missing"
    assert exc.exc_type == "RuntimeError"
    assert exc.code == 1
    assert "Traceback" in exc.err
    assert "PermissionError" in exc.err
