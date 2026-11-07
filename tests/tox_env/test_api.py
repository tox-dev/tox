from __future__ import annotations

import os
import stat
import sys
from typing import TYPE_CHECKING, Final

import pytest

from tox.tox_env.api import redact_value

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProject, ToxProjectCreator


def test_ensure_temp_dir_exists(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\ncommands=python -c 'import os; os.path.exists(r\"{temp_dir}\")'"})
    project.run().assert_success()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
@pytest.mark.parametrize("umask", [pytest.param(0o002, id="group"), pytest.param(0o000, id="all")])
def test_package_staging_with_permissive_umask(
    tox_project: ToxProjectCreator, demo_pkg_inline: Path, umask: int
) -> None:
    project: Final[ToxProject] = tox_project({"tox.ini": "[testenv]\npackage=wheel"}, base=demo_pkg_inline)
    previous: Final[int] = os.umask(umask)
    try:
        project.run("r", "-e", "py", "--notest").assert_success()
    finally:
        os.umask(previous)

    work_dir: Final[Path] = project.path / ".tox"
    for directory in (work_dir, work_dir / ".tmp", work_dir / ".tmp" / "package"):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_package_staging_reuses_group_writable_directories(
    tox_project: ToxProjectCreator, demo_pkg_inline: Path
) -> None:
    project: Final[ToxProject] = tox_project({"tox.ini": "[testenv]\npackage=wheel"}, base=demo_pkg_inline)
    work_dir: Final[Path] = project.path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    previous: Final[int] = os.umask(0o002)
    try:
        staging.mkdir(parents=True)
        project.path.chmod(0o775)
        project.run("r", "-e", "py", "--notest").assert_success()
    finally:
        os.umask(previous)

    directories: Final[tuple[Path, ...]] = (project.path, work_dir, staging.parent, staging)
    assert [stat.S_IMODE(directory.stat().st_mode) for directory in directories] == [0o775] * 4


def test_dont_cleanup_temp_dir(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    (tmp_path / "foo" / "bar").mkdir(parents=True)
    tox_project({"tox.ini": "[tox]\ntemp_dir=foo"}).run().assert_success()
    assert (tmp_path / "foo" / "bar").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_replace_linked_default_temp_dir(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    project: Final[ToxProject] = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    outside: Final[Path] = tmp_path / "outside"
    outside.mkdir()
    (project.path / ".tox").mkdir()
    temp_dir: Final[Path] = project.path / ".tox" / ".tmp"
    temp_dir.symlink_to(outside, target_is_directory=True)

    project.run("r", "-e", "py").assert_success()

    assert (temp_dir.is_symlink(), temp_dir.is_dir(), list(outside.iterdir())) == (False, True, [])


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_keep_configured_external_temp_dir_link(
    tox_project: ToxProjectCreator, demo_pkg_inline: Path, tmp_path: Path
) -> None:
    project: Final[ToxProject] = tox_project(
        {"tox.ini": "[tox]\ntemp_dir={tox_root}/temp\n[testenv]\npackage=wheel"}, base=demo_pkg_inline
    )
    outside: Final[Path] = tmp_path / "outside"
    outside.mkdir()
    temp_dir: Final[Path] = project.path / "temp"
    temp_dir.symlink_to(outside, target_is_directory=True)

    project.run("r", "-e", "py").assert_success()

    assert temp_dir.is_symlink()


def test_setenv_section_substitution(tox_project: ToxProjectCreator) -> None:
    ini = """[variables]
    var = VAR = val
    [testenv]
    setenv = {[variables]var}
    commands = python -c 'import os; os.environ["VAR"]'"""
    tox_project({"tox.ini": ini}).run().assert_success()


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        pytest.param("SOME_KEY", "***", id="key"),
        pytest.param("API_FOO", "***", id="api"),
        pytest.param("AUTH", "***", id="auth"),
        pytest.param("CLIENT", "***", id="client"),
        pytest.param("DB_PASSWORD", "***", id="password"),
        pytest.param("FOO", "foo", id="foo"),
        pytest.param("GITHUB_TOKEN", "***", id="token"),
        pytest.param("NORMAL_VAR", "foo", id="other"),
        pytest.param("S_PASSWD", "***", id="passwd"),
        pytest.param("SECRET", "***", id="secret"),
        pytest.param("SOME_ACCESS", "***", id="access"),
        pytest.param("MY_CRED", "***", id="cred"),
        pytest.param("MY_PRIVATE", "***", id="private"),
        pytest.param("MY_PWD", "***", id="pwd"),
    ],
)
def test_redact(key: str, expected: str) -> None:
    # Ensures that redact_value works as expected.
    assert redact_value(key, "foo") == expected


def test_info_without_matching_python_section_rebuilds_env(tox_project: ToxProjectCreator) -> None:
    project: Final[ToxProject] = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    env_dir: Final[Path] = project.path / ".tox" / "py"
    env_dir.mkdir(parents=True)
    (env_dir / ".tox-info.json").write_text('{"Python": {}}', encoding="utf-8")
    planted: Final[Path] = env_dir / "planted"
    planted.write_bytes(b"planted")

    project.run("r", "-e", "py").assert_success()

    assert not planted.exists()
