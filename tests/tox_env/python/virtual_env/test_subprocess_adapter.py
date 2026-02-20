from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tox.tox_env.python.virtual_env.subprocess_adapter import (
    SubprocessCreator,
    SubprocessPythonInfo,
    SubprocessSession,
    _bootstrap_path,  # noqa: PLC2701
    _has_correct_virtualenv,  # noqa: PLC2701
    _VersionInfo,  # noqa: PLC2701
    ensure_bootstrap,
    probe_python,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import ToxProjectCreator


def test_probe_python_current_interpreter() -> None:
    info = probe_python(sys.executable)
    assert info is not None
    assert info.version_info.major == sys.version_info.major
    assert info.version_info.minor == sys.version_info.minor
    assert info.version_info.micro == sys.version_info.micro
    assert info.implementation == sys.implementation.name
    assert info.architecture in {32, 64}
    assert info.system_executable


def test_probe_python_nonexistent() -> None:
    assert probe_python("/nonexistent/python999") is None


def test_probe_python_failing_script(tmp_path: Path) -> None:
    if sys.platform == "win32":
        bad_script = tmp_path / "bad_python.cmd"
        bad_script.write_text("@exit /b 1\n")
    else:
        bad_script = tmp_path / "bad_python"
        bad_script.write_text("#!/bin/sh\nexit 1\n")
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
    assert creator.bin_dir == env_dir / "bin"
    assert creator.script_dir == env_dir / "bin"
    assert creator.purelib == env_dir / "lib" / "python3.11" / "site-packages"
    assert creator.platlib == env_dir / "lib" / "python3.11" / "site-packages"
    assert creator.exe == env_dir / "bin" / "python"


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
    assert creator.bin_dir == env_dir / "Scripts"
    assert creator.purelib == env_dir / "Lib" / "site-packages"
    assert creator.exe == env_dir / "Scripts" / "python.exe"


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
        return_value=mocker.MagicMock(returncode=1, stderr="error"),
    )
    with pytest.raises(RuntimeError, match="virtualenv subprocess failed \\(exit 1\\)"):
        session.run()


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
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run")
    run_mock.return_value = mocker.MagicMock(returncode=0, stdout="20.21.1\n")
    assert _has_correct_virtualenv(python, "virtualenv<20.22.0") is True


def test_has_correct_virtualenv_bare_spec(tmp_path: Path, mocker: MockerFixture) -> None:
    python = tmp_path / "python"
    python.touch()
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run")
    run_mock.return_value = mocker.MagicMock(returncode=0, stdout="20.21.1\n")
    assert _has_correct_virtualenv(python, "virtualenv") is True


def test_has_correct_virtualenv_subprocess_fails(tmp_path: Path, mocker: MockerFixture) -> None:
    python = tmp_path / "python"
    python.touch()
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run")
    run_mock.return_value = mocker.MagicMock(returncode=1)
    assert _has_correct_virtualenv(python, "virtualenv<20.22.0") is False


def test_has_correct_virtualenv_subprocess_error(tmp_path: Path, mocker: MockerFixture) -> None:
    python = tmp_path / "python"
    python.touch()
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run",
        side_effect=OSError("boom"),
    )
    assert _has_correct_virtualenv(python, "virtualenv<20.22.0") is False


def test_ensure_bootstrap_creates_and_caches(tmp_path: Path, mocker: MockerFixture) -> None:
    venv_create = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create")
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run")
    run_mock.return_value = mocker.MagicMock(returncode=0, stdout="20.21.1\n")

    has_correct = mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter._has_correct_virtualenv",
        side_effect=[False, False, True],
    )

    result = ensure_bootstrap(tmp_path, "virtualenv<20.22.0")
    assert result.name == ("python.exe" if sys.platform == "win32" else "python")
    venv_create.assert_called_once()
    run_mock.assert_called_once()

    result2 = ensure_bootstrap(tmp_path, "virtualenv<20.22.0")
    assert result == result2
    assert has_correct.call_count == 3


def test_ensure_bootstrap_race_inside_lock(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter._has_correct_virtualenv",
        side_effect=[False, True],
    )
    result = ensure_bootstrap(tmp_path, "virtualenv<20.22.0")
    assert result.name == ("python.exe" if sys.platform == "win32" else "python")


def test_ensure_bootstrap_removes_stale_base(tmp_path: Path, mocker: MockerFixture) -> None:
    base = _bootstrap_path(tmp_path, "virtualenv<20.22.0")
    base.mkdir(parents=True)
    (base / "stale_file").touch()

    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create")
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run")
    run_mock.return_value = mocker.MagicMock(returncode=1, stderr="fail")
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter._has_correct_virtualenv",
        return_value=False,
    )

    with pytest.raises(RuntimeError, match="failed to install"):
        ensure_bootstrap(tmp_path, "virtualenv<20.22.0")
    assert not (base / "stale_file").exists()


def test_ensure_bootstrap_install_failure(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.venv.create")
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter._has_correct_virtualenv",
        return_value=False,
    )
    run_mock = mocker.patch("tox.tox_env.python.virtual_env.subprocess_adapter.subprocess.run")
    run_mock.return_value = mocker.MagicMock(returncode=1, stderr="no matching distribution")

    with pytest.raises(RuntimeError, match="failed to install"):
        ensure_bootstrap(tmp_path, "virtualenv==999.999.999")


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
        "tox.tox_env.python.virtual_env.subprocess_adapter.ensure_bootstrap",
        return_value=Path(sys.executable),
    )
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.probe_python",
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
    result = proj.run("r", "-e", "py")
    result.assert_success()


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
