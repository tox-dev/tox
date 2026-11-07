from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path
from shutil import rmtree
from typing import TYPE_CHECKING, Protocol
from venv import create as create_venv

import pytest

from tox.tox_env.errors import Fail
from tox.tox_env.python.virtual_env.subprocess_adapter import (
    SubprocessCreator,
    SubprocessPythonInfo,
    SubprocessSession,
    _bootstrap_path,  # ruff:ignore[import-private-name]  # sibling module internal
    _has_correct_virtualenv,  # ruff:ignore[import-private-name]  # sibling module internal
    _VersionInfo,  # ruff:ignore[import-private-name]  # sibling module internal
    ensure_bootstrap,
    probe_python,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Final

    from pytest_mock import MockerFixture

    from tox.pytest import ToxProjectCreator

_EXECUTABLE_NAME: Final[str] = "python.exe" if sys.platform == "win32" else "python"


def test_probe_python_current_interpreter() -> None:
    info: Final[SubprocessPythonInfo | None] = probe_python(sys.executable)
    assert info is not None
    assert (info.version_info.major, info.version_info.minor, info.version_info.micro) == (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )
    assert info.implementation == sys.implementation.name
    assert info.architecture in {32, 64}
    assert info.system_executable
    assert info.sysconfig_platform is not None
    assert info.machine  # should be non-empty on all platforms
    assert info.marker_environment is None


def test_subprocess_python_info_positional_constructor() -> None:
    probed: Final[SubprocessPythonInfo | None] = probe_python(sys.executable)
    assert probed is not None
    info: Final[SubprocessPythonInfo] = SubprocessPythonInfo(
        implementation="cpython",
        version_info=probed.version_info,
        version="3.11.0",
        architecture=64,
        platform="linux",
        system_executable="/usr/bin/python3",
        free_threaded=False,
        debug_build=True,
        sysconfig_platform="linux-x86_64",
    )

    assert (info.debug_build, info.sysconfig_platform, info.marker_environment) == (True, "linux-x86_64", None)


def test_probe_python_nonexistent() -> None:
    assert probe_python("/nonexistent/python999") is None


@pytest.mark.parametrize(
    ("sysconfig_platform", "expected_machine"),
    [
        pytest.param("linux-x86_64", "x86_64", id="linux-dash-x86-underscore-64-x86-underscore-64"),
        pytest.param("linux-aarch64", "aarch64", id="linux-dash-aarch64-aarch64"),
        pytest.param("win-amd64", "amd64", id="win-dash-amd64-amd64"),
        pytest.param("macosx-14.0-arm64", "arm64", id="macosx-dash-14-dot-0-dash-arm64-arm64"),
        pytest.param("win32", "", id="win32-empty"),
        pytest.param(None, "", id="none-empty"),
    ],
)
def test_subprocess_python_info_machine(sysconfig_platform: str | None, expected_machine: str) -> None:
    vi = _VersionInfo(major=3, minor=12, micro=0, releaselevel="final", serial=0)
    info = SubprocessPythonInfo(
        implementation="cpython",
        version_info=vi,
        version="3.12.0",
        architecture=64,
        platform="linux",
        system_executable="/usr/bin/python3",
        free_threaded=False,
        sysconfig_platform=sysconfig_platform,
    )
    assert info.machine == expected_machine


@pytest.mark.parametrize(
    ("name", "content"),
    [
        pytest.param(
            "bad_python",
            "#!/bin/sh\nexit 1\n",
            id="posix",
            marks=pytest.mark.skipif(sys.platform == "win32", reason="posix shell script"),
        ),
        pytest.param(
            "bad_python.cmd",
            "@exit /b 1\n",
            id="windows",
            marks=pytest.mark.skipif(sys.platform != "win32", reason="windows batch script"),
        ),
    ],
)
def test_probe_python_failing_script(tmp_path: Path, name: str, content: str) -> None:
    bad_script = tmp_path / name
    bad_script.write_text(content)
    bad_script.chmod(0o755)
    assert probe_python(str(bad_script)) is None


def test_subprocess_creator_paths_unix(tmp_path: Path) -> None:
    vi = _VersionInfo(major=3, minor=11, micro=0, releaselevel="final", serial=0)
    env_dir = tmp_path / "env"
    info = SubprocessPythonInfo(
        implementation="cpython",
        version_info=vi,
        version="3.11.0",
        architecture=64,
        platform="linux",
        system_executable="/usr/bin/python3.11",
        free_threaded=False,
    )
    creator = SubprocessCreator(_env_dir=env_dir, interpreter=info, _is_win=False)
    assert (creator.bin_dir, creator.script_dir, creator.purelib, creator.platlib, creator.exe) == (
        env_dir / "bin",
        env_dir / "bin",
        env_dir / "lib" / "python3.11" / "site-packages",
        env_dir / "lib" / "python3.11" / "site-packages",
        env_dir / "bin" / "python",
    )


def test_subprocess_creator_paths_windows(tmp_path: Path) -> None:
    vi = _VersionInfo(major=3, minor=11, micro=0, releaselevel="final", serial=0)
    env_dir = tmp_path / "env"
    info = SubprocessPythonInfo(
        implementation="cpython",
        version_info=vi,
        version="3.11.0",
        architecture=64,
        platform="win32",
        system_executable="C:\\Python311\\python.exe",
        free_threaded=False,
    )
    creator = SubprocessCreator(_env_dir=env_dir, interpreter=info, _is_win=True)
    assert (creator.bin_dir, creator.purelib, creator.exe) == (
        env_dir / "Scripts",
        env_dir / "Lib" / "site-packages",
        env_dir / "Scripts" / "python.exe",
    )


def test_subprocess_session_run_not_found(tmp_path: Path) -> None:
    vi = _VersionInfo(major=3, minor=11, micro=0, releaselevel="final", serial=0)
    info = SubprocessPythonInfo(
        implementation="cpython",
        version_info=vi,
        version="3.11.0",
        architecture=64,
        platform=sys.platform,
        system_executable=sys.executable,
        free_threaded=False,
    )
    session = SubprocessSession(
        env_dir=tmp_path / "env",
        bootstrap_python=Path("/nonexistent/python"),
        env_vars={},
        interpreter=info,
    )
    with pytest.raises(RuntimeError, match="virtualenv subprocess failed"):
        session.run()


def test_subprocess_session_run_nonzero_exit(tmp_path: Path, mocker: MockerFixture) -> None:
    vi = _VersionInfo(major=3, minor=11, micro=0, releaselevel="final", serial=0)
    info = SubprocessPythonInfo(
        implementation="cpython",
        version_info=vi,
        version="3.11.0",
        architecture=64,
        platform=sys.platform,
        system_executable=sys.executable,
        free_threaded=False,
    )
    session = SubprocessSession(
        env_dir=tmp_path / "env",
        bootstrap_python=Path(sys.executable),
        env_vars={},
        interpreter=info,
    )
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=mocker.create_autospec(subprocess.CompletedProcess, instance=True, returncode=1, stderr="error"),
    )
    with pytest.raises(RuntimeError, match="virtualenv subprocess failed \\(exit 1\\)"):
        session.run()


def test_subprocess_session_run_passes_interpreter(tmp_path: Path, mocker: MockerFixture) -> None:
    info: Final = SubprocessPythonInfo(
        implementation="cpython",
        version_info=_VersionInfo(major=3, minor=11, micro=0, releaselevel="final", serial=0),
        version="3.11.0",
        architecture=64,
        platform=sys.platform,
        system_executable="/opt/a:b,c/python",
        free_threaded=False,
    )
    run_mock: Final = mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=mocker.create_autospec(subprocess.CompletedProcess, instance=True, returncode=0),
    )
    SubprocessSession(
        env_dir=tmp_path / "env",
        bootstrap_python=Path(sys.executable),
        env_vars={},
        interpreter=info,
    ).run()
    assert run_mock.call_args.args[0] == [
        sys.executable,
        "-m",
        "virtualenv",
        "--python=/opt/a:b,c/python",
        str(tmp_path / "env"),
    ]


def test_subprocess_session_no_interpreter(tmp_path: Path) -> None:
    session = SubprocessSession(
        env_dir=tmp_path / "env",
        bootstrap_python=tmp_path / "bootstrap" / "bin" / "python",
        env_vars={},
        interpreter=None,
    )
    with pytest.raises(RuntimeError, match="no interpreter discovered"):
        _ = session.creator


def test_bootstrap_path_deterministic(tmp_path: Path) -> None:
    path1 = _bootstrap_path(tmp_path, "virtualenv<20.22.0")
    path2 = _bootstrap_path(tmp_path, "virtualenv<20.22.0")
    path3 = _bootstrap_path(tmp_path, "virtualenv<21.0.0")
    assert path1 == path2
    assert path1 != path3
    assert path1.parent == tmp_path / ".virtualenv-bootstrap"


def test_has_correct_virtualenv_nonexistent(tmp_path: Path) -> None:
    assert _has_correct_virtualenv(tmp_path / "nonexistent", "virtualenv") is False


def test_has_correct_virtualenv_matching(tmp_path: Path, mocker: MockerFixture) -> None:
    python = tmp_path / "python"
    python.touch()
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run", autospec=True)
    run_mock.return_value = mocker.create_autospec(
        subprocess.CompletedProcess, instance=True, returncode=0, stdout="20.21.1\n"
    )
    assert _has_correct_virtualenv(python, "virtualenv<20.22.0") is True


def test_has_correct_virtualenv_bare_spec(tmp_path: Path, mocker: MockerFixture) -> None:
    python = tmp_path / "python"
    python.touch()
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run", autospec=True)
    run_mock.return_value = mocker.create_autospec(
        subprocess.CompletedProcess, instance=True, returncode=0, stdout="20.21.1\n"
    )
    assert _has_correct_virtualenv(python, "virtualenv") is True


def test_ensure_bootstrap_reuses_normalized_name(tmp_path: Path, mocker: MockerFixture) -> None:
    create = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=mocker.create_autospec(
            subprocess.CompletedProcess, instance=True, returncode=0, stdout="20.21.1\n"
        ),
    )
    python = ensure_bootstrap(tmp_path, "Virtualenv <22")
    python.parent.mkdir(parents=True)
    python.touch()

    assert ensure_bootstrap(tmp_path, "Virtualenv <22") == python
    create.assert_called_once()


def test_has_correct_virtualenv_subprocess_fails(tmp_path: Path, mocker: MockerFixture) -> None:
    python = tmp_path / "python"
    python.touch()
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run", autospec=True)
    run_mock.return_value = mocker.create_autospec(subprocess.CompletedProcess, instance=True, returncode=1)
    assert _has_correct_virtualenv(python, "virtualenv<20.22.0") is False


def test_has_correct_virtualenv_subprocess_error(tmp_path: Path, mocker: MockerFixture) -> None:
    python = tmp_path / "python"
    python.touch()
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        side_effect=OSError("boom"),
    )
    assert _has_correct_virtualenv(python, "virtualenv<20.22.0") is False


def test_ensure_bootstrap_creates_and_caches(tmp_path: Path, mocker: MockerFixture) -> None:
    venv_create = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run", autospec=True)
    run_mock.return_value = mocker.create_autospec(
        subprocess.CompletedProcess, instance=True, returncode=0, stdout="20.21.1\n"
    )

    has_correct = mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter._has_correct_virtualenv",
        autospec=True,
        side_effect=[False, False, True],
    )

    result = ensure_bootstrap(tmp_path, "virtualenv<20.22.0")
    assert result.name == _EXECUTABLE_NAME
    venv_create.assert_called_once()
    run_mock.assert_called_once()

    result2 = ensure_bootstrap(tmp_path, "virtualenv<20.22.0")
    assert result == result2
    assert has_correct.call_count == 3


@pytest.mark.skipif(sys.platform != "win32", reason="Windows bootstrap relocation")
@pytest.mark.usefixtures("bootstrap_without_pip")
def test_ensure_bootstrap_relocated_python(tmp_path: Path) -> None:
    python: Final[Path] = ensure_bootstrap(tmp_path, "virtualenv<20.22.0")
    _assert_bootstrap_prefix(python, python.parent.parent)


def _assert_bootstrap_prefix(python: Path, expected: Path) -> None:
    subprocess.check_call(
        [
            str(python),
            "-c",
            "import os, sys; assert os.path.samefile(sys.prefix, sys.argv[1])",
            str(expected),
        ],
        stdout=subprocess.DEVNULL,
    )


@pytest.fixture
def bootstrap_without_pip(mocker: MockerFixture) -> None:
    def create_without_pip(path: str, *, with_pip: bool) -> None:
        assert with_pip
        create_venv(path, with_pip=False)

    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.venv.create",
        autospec=True,
        side_effect=create_without_pip,
    )
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess([], 0),
    )


def test_ensure_bootstrap_race_inside_lock(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter._has_correct_virtualenv",
        autospec=True,
        side_effect=[False, True],
    )
    result = ensure_bootstrap(tmp_path, "virtualenv<20.22.0")
    assert result.name == _EXECUTABLE_NAME


def test_ensure_bootstrap_removes_stale_base(tmp_path: Path, mocker: MockerFixture) -> None:
    base = _bootstrap_path(tmp_path, "virtualenv<20.22.0")
    base.mkdir(parents=True)
    (base / "stale_file").touch()

    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run", autospec=True)
    run_mock.return_value = mocker.create_autospec(
        subprocess.CompletedProcess, instance=True, returncode=1, stderr="fail"
    )
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter._has_correct_virtualenv",
        autospec=True,
        return_value=False,
    )

    with pytest.raises(RuntimeError, match="failed to install"):
        ensure_bootstrap(tmp_path, "virtualenv<20.22.0")
    assert (base / "stale_file").exists() is (sys.platform == "win32")


def test_ensure_bootstrap_swap_at_venv_create_keeps_target(tmp_path: Path, victim: Path, mocker: MockerFixture) -> None:
    def swap_then_create(env_dir: str, **options: bool) -> None:
        base: Final[Path] = Path(env_dir)
        rmtree(base)
        _symlink_or_skip(base, victim)
        create_venv(env_dir, with_pip=False, clear=options.get("clear", False))

    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True, side_effect=swap_then_create
    )

    with pytest.raises(ValueError, match="Unable to create directory"):
        ensure_bootstrap(tmp_path, "virtualenv<20.22.0")

    assert (victim / "keep").read_text() == "data"
    assert not (victim / "pyvenv.cfg").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="junctions exist only on Windows")
def test_ensure_bootstrap_junction_swap_keeps_target(
    tmp_path: Path, victim: Path, bootstrap_base: Path, mocker: MockerFixture
) -> None:
    def swap_then_create(env_dir: str, *, with_pip: bool) -> None:
        assert with_pip
        bootstrap_base.mkdir()
        bootstrap_base.rmdir()
        subprocess.check_call(
            [os.environ["COMSPEC"], "/c", "mklink", "/J", str(bootstrap_base), str(victim)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        create_venv(env_dir, with_pip=False)

    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True, side_effect=swap_then_create
    )
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess([], 0),
    )
    with pytest.raises(OSError, match="Cannot call rmtree on a symbolic link"):
        ensure_bootstrap(tmp_path, "virtualenv<20.22.0")

    assert sorted(path.name for path in victim.iterdir()) == ["keep"]


@pytest.mark.skipif(sys.platform != "win32", reason="junctions exist only on Windows")
@pytest.mark.usefixtures("bootstrap_without_pip")
def test_ensure_bootstrap_allows_linked_work_dir(tmp_path: Path) -> None:
    actual: Final[Path] = tmp_path / "actual"
    actual.mkdir()
    work_dir: Final[Path] = tmp_path / "linked"
    subprocess.check_call(
        [os.environ["COMSPEC"], "/c", "mklink", "/J", str(work_dir), str(actual)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    python: Final[Path] = ensure_bootstrap(work_dir, "virtualenv<20.22.0")
    _assert_bootstrap_prefix(python, actual / ".virtualenv-bootstrap" / python.parent.parent.name)


@pytest.fixture
def victim(tmp_path: Path) -> Path:
    path: Final[Path] = tmp_path / "victim"
    path.mkdir()
    (path / "keep").write_text("data")
    return path


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as error:  # pragma: no cover - Windows may require a symlink privilege.
        pytest.skip(f"cannot create symlink: {error}")


def _junction_to(link: Path, target: Path) -> None:  # pragma: no cover - Windows-only setup.
    subprocess.run(
        [os.environ["COMSPEC"], "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=True
    )


@pytest.mark.parametrize(
    "make_link",
    [
        pytest.param(_symlink_or_skip, id="symlink"),
        pytest.param(_junction_to, id="junction", marks=pytest.mark.skipif(os.name != "nt", reason="Windows only")),
    ],
)
def test_ensure_bootstrap_rejects_cache_parent_outside_work_dir(
    tmp_path: Path, victim: Path, mocker: MockerFixture, make_link: _StaleEntryMaker
) -> None:
    work_dir: Final[Path] = tmp_path / "work"
    work_dir.mkdir()
    make_link(work_dir / ".virtualenv-bootstrap", victim)
    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess([], 0),
    )

    with pytest.raises(Fail, match="bootstrap cache directory must stay within work directory"):
        ensure_bootstrap(work_dir, "virtualenv<20.22.0")

    assert list(victim.iterdir()) == [victim / "keep"]


@pytest.mark.skipif(sys.platform == "win32", reason="Windows builds the bootstrap outside the cache")
def test_ensure_bootstrap_link_swapped_after_removal_fails(tmp_path: Path, victim: Path, mocker: MockerFixture) -> None:
    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=mocker.create_autospec(subprocess.CompletedProcess, instance=True, returncode=0),
    )
    base: Final[Path] = ensure_bootstrap(tmp_path, "virtualenv<20.22.0").parent.parent
    (base / "stale").write_text("stale")

    def remove_then_swap(path: Path) -> None:
        (path / "stale").unlink()
        path.rmdir()
        _symlink_or_skip(path, victim)

    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.shutil.rmtree", autospec=True, side_effect=remove_then_swap
    )

    with pytest.raises(FileExistsError):
        ensure_bootstrap(tmp_path, "virtualenv<20.22.0")

    assert (victim / "keep").read_text() == "data"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows bootstrap publication")
def test_ensure_bootstrap_link_swapped_before_publication_fails(
    tmp_path: Path, victim: Path, bootstrap_base: Path, mocker: MockerFixture
) -> None:
    rename: Final[Callable[[Path, Path], Path]] = Path.rename
    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess([], 0),
    )

    def swap_before_rename(source: Path, target: Path) -> Path:
        subprocess.check_call(
            [os.environ["COMSPEC"], "/c", "mklink", "/J", str(bootstrap_base), str(victim)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        return rename(source, target)

    mocker.patch.object(Path, "rename", autospec=True, side_effect=swap_before_rename)

    with pytest.raises(FileExistsError):
        ensure_bootstrap(tmp_path, "virtualenv<20.22.0")

    assert sorted(path.name for path in victim.iterdir()) == ["keep"]


@pytest.fixture
def bootstrap_base(tmp_path: Path, mocker: MockerFixture) -> Path:
    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess([], 0),
    )
    base: Final[Path] = ensure_bootstrap(tmp_path, "virtualenv<20.22.0").parent.parent
    rmtree(base)
    mocker.stopall()
    return base


@pytest.mark.parametrize(
    "make_stale",
    [
        pytest.param(_symlink_or_skip, id="link"),
        pytest.param(lambda base, _victim: base.write_text("stale"), id="file"),
    ],
)
def test_ensure_bootstrap_replaces_non_directory_stale_entry(
    tmp_path: Path, victim: Path, mocker: MockerFixture, make_stale: _StaleEntryMaker
) -> None:
    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        autospec=True,
        return_value=mocker.create_autospec(subprocess.CompletedProcess, instance=True, returncode=0),
    )
    base: Final[Path] = ensure_bootstrap(tmp_path, "virtualenv<20.22.0").parent.parent
    rmtree(base)
    make_stale(base, victim)

    ensure_bootstrap(tmp_path, "virtualenv<20.22.0")

    assert (base.is_dir(), base.is_symlink(), (victim / "keep").read_text()) == (True, False, "data")


class _StaleEntryMaker(Protocol):
    def __call__(self, base: Path, victim: Path) -> int | None: ...


def test_ensure_bootstrap_install_failure(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter._has_correct_virtualenv",
        autospec=True,
        return_value=False,
    )
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run", autospec=True)
    run_mock.return_value = mocker.create_autospec(
        subprocess.CompletedProcess, instance=True, returncode=1, stderr="no matching distribution"
    )

    with pytest.raises(RuntimeError, match="failed to install"):
        ensure_bootstrap(tmp_path, "virtualenv==999.999.999")


@pytest.mark.parametrize(
    "virtualenv_spec",
    [
        pytest.param("--requirement=https://example.invalid/requirements.txt", id="pip-option"),
        pytest.param("virtualenv @ file:///tmp/other.whl", id="direct-reference"),
        pytest.param("virtualenv-other", id="other-project"),
        pytest.param("virtualenv===/tmp/other.whl", id="arbitrary-equality"),
        pytest.param("virtualenv[extra]", id="extra"),
        pytest.param('virtualenv; python_version < "3.15"', id="marker"),
    ],
)
def test_ensure_bootstrap_rejects_non_version_requirement(
    tmp_path: Path, mocker: MockerFixture, virtualenv_spec: str
) -> None:
    create = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create", autospec=True)
    install = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run", autospec=True)

    with pytest.raises(Fail, match="virtualenv_spec must name virtualenv"):
        ensure_bootstrap(tmp_path, virtualenv_spec)
    create.assert_not_called()
    install.assert_not_called()


def test_ensure_bootstrap_invalid_spec_does_not_echo_value(tmp_path: Path) -> None:
    with pytest.raises(Fail) as error:
        ensure_bootstrap(tmp_path, "--password=secret")
    assert "secret" not in str(error.value)


def test_virtualenv_spec_rejects_pip_option(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_run_base]
            package = "skip"
            virtualenv_spec = "--requirement=https://example.invalid/requirements.txt"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = proj.run("r", "-e", "py")
    result.assert_failed()
    assert "virtualenv_spec must name virtualenv" in result.out


def test_virtualenv_spec_config_shown(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_run_base]
            package = "skip"
            virtualenv_spec = "virtualenv<20.22.0"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = proj.run("c", "-e", "py", "-k", "virtualenv_spec")
    result.assert_success()
    assert "virtualenv<20.22.0" in result.out


def test_virtualenv_spec_cache_includes_spec(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    mocker.patch(
        "tox.tox_env.python.virtual_env.api.ensure_bootstrap",
        autospec=True,
        return_value=Path(sys.executable),
    )
    mocker.patch(
        "tox.tox_env.python.virtual_env.api.probe_python",
        autospec=True,
        return_value=SubprocessPythonInfo(
            implementation=sys.implementation.name,
            version_info=_VersionInfo(*sys.version_info[:5]),
            version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            architecture=64,
            platform=sys.platform,
            system_executable=sys.executable,
            free_threaded=False,
        ),
    )

    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_run_base]
            package = "skip"
            virtualenv_spec = "virtualenv<20.22.0"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    proj.run("r", "-e", "py").assert_success()


def test_virtualenv_spec_empty_uses_imported(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_run_base]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = proj.run("r", "-e", "py")
    result.assert_success()
    assert "ok" in result.out
