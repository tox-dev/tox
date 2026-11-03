from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from tox.util.file_view import create_session_view

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

    from tox.pytest import MonkeyPatch


def test_create_session_view_copies(tmp_path: Path) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    result: Final[Path] = create_session_view(package, tmp_path / "temp")
    assert result.read_bytes() == b"data"
    assert result.parent.parent == tmp_path / "temp"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
@pytest.mark.parametrize(
    "umask",
    [pytest.param(0o002, id="group"), pytest.param(0o000, id="all"), pytest.param(0o022, id="owner")],
)
def test_create_session_view_private_directories(tmp_path: Path, umask: int) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    staging: Final[Path] = tmp_path / ".tox" / ".tmp" / "package"
    previous: Final[int] = os.umask(umask)
    try:
        result: Final[Path] = create_session_view(package, staging, tmp_path)
    finally:
        os.umask(previous)

    assert result.read_bytes() == b"data"
    for directory in (staging.parent.parent, staging.parent, staging, result.parent):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
@pytest.mark.parametrize("mode", [pytest.param(0o775, id="group"), pytest.param(0o2775, id="setgid")])
def test_create_session_view_repairs_existing_staging(tmp_path: Path, mode: int) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    previous: Final[int] = os.umask(0o002)
    try:
        staging.mkdir(parents=True)
    finally:
        os.umask(previous)
    for directory in (work_dir, staging.parent, staging):
        directory.chmod(mode)
    tmp_path.chmod(0o775)

    result: Final[Path] = create_session_view(package, staging, tmp_path, work_dir)

    assert result.read_bytes() == b"data"
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o775
    for directory in (work_dir, staging.parent, staging):
        assert stat.S_IMODE(directory.stat().st_mode) & stat.S_IWGRP == 0


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_repairs_work_dir_at_project_root(tmp_path: Path) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    staging: Final[Path] = tmp_path / ".tmp" / "package"
    staging.mkdir(parents=True)
    tmp_path.chmod(0o775)
    for directory in (staging.parent, staging):
        directory.chmod(0o775)

    result: Final[Path] = create_session_view(package, staging, tmp_path, tmp_path)

    assert result.read_bytes() == b"data"
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o775
    for directory in (staging.parent, staging):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o755


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_keeps_link_target_permissions(tmp_path: Path) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    work_dir: Final[Path] = tmp_path / ".tox"
    work_dir.mkdir()
    outside: Final[Path] = tmp_path / "outside"
    (outside / "package").mkdir(parents=True)
    outside.chmod(0o775)
    (work_dir / ".tmp").symlink_to(outside, target_is_directory=True)

    with pytest.raises(PermissionError):
        create_session_view(package, work_dir / ".tmp" / "package", tmp_path, work_dir)

    assert stat.S_IMODE(outside.stat().st_mode) == 0o775


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_does_not_repair_outside_work_dir(tmp_path: Path) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    work_dir: Final[Path] = tmp_path / ".tox"
    work_dir.mkdir()
    staging: Final[Path] = tmp_path / "outside" / "package"
    staging.mkdir(parents=True)
    staging.parent.chmod(0o775)

    with pytest.raises(PermissionError):
        create_session_view(package, staging, tmp_path, work_dir)

    assert stat.S_IMODE(staging.parent.stat().st_mode) == 0o775


def test_create_session_view_no_common_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "pkg.whl").write_bytes(b"data")
    monkeypatch.chdir(tmp_path)

    result: Final[Path] = create_session_view(Path("dist/pkg.whl"), tmp_path / "temp", tmp_path)

    assert result.is_absolute()
    assert result.read_bytes() == b"data"


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_create_session_view_replaces_staging_link(tmp_path: Path) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    outside: Final[Path] = tmp_path / "outside"
    outside.mkdir()
    staging: Final[Path] = tmp_path / "temp"
    staging.symlink_to(outside, target_is_directory=True)

    result: Final[Path] = create_session_view(package, staging, tmp_path)

    assert (result.read_bytes(), staging.is_symlink(), list(outside.iterdir())) == (b"data", False, [])


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_create_session_view_does_not_follow_destination_link(tmp_path: Path, mocker: MockerFixture) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    outside: Final[Path] = tmp_path / "outside"
    outside.write_bytes(b"keep")
    mkdir: Final[Callable[[Path, int, bool, bool], None]] = Path.mkdir

    def mkdir_with_link(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        mkdir(path, mode, parents, exist_ok)
        if path.name == "1":
            (path / package.name).symlink_to(outside)

    mocker.patch.object(Path, "mkdir", autospec=True, side_effect=mkdir_with_link)

    with pytest.raises(FileExistsError):
        create_session_view(package, tmp_path / "temp", tmp_path)

    assert outside.read_bytes() == b"keep"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_rejects_writable_staging_parent(tmp_path: Path) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    parent: Final[Path] = tmp_path / "temp"
    parent.mkdir(mode=0o777)
    parent.chmod(0o777)
    staging: Final[Path] = parent / "package"
    staging.mkdir()

    with pytest.raises(PermissionError):
        create_session_view(package, staging, tmp_path, parent)

    assert stat.S_IMODE(parent.stat().st_mode) == 0o777
    assert list(staging.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory ownership")
def test_create_session_view_rejects_other_account_staging_parent(tmp_path: Path, mocker: MockerFixture) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    work_dir: Final[Path] = tmp_path / ".tox"
    staging: Final[Path] = work_dir / ".tmp" / "package"
    staging.mkdir(parents=True)
    work_dir.chmod(0o775)
    mocker.patch("os.geteuid", autospec=True, return_value=work_dir.stat().st_uid + 1)

    with pytest.raises(PermissionError):
        create_session_view(package, staging, tmp_path, work_dir)

    assert stat.S_IMODE(work_dir.stat().st_mode) == 0o775
    assert list(staging.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX sticky directory permissions")
def test_create_session_view_rejects_foreign_link_in_sticky_parent(tmp_path: Path, mocker: MockerFixture) -> None:
    package: Final[Path] = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    sticky: Final[Path] = tmp_path / "sticky"
    sticky.mkdir()
    sticky.chmod(0o1777)
    target: Final[Path] = tmp_path / "target"
    target.mkdir()
    link: Final[Path] = sticky / "link"
    link.symlink_to(target, target_is_directory=True)
    original_lstat: Final[Callable[[Path], os.stat_result]] = Path.lstat

    def lstat_as_other_account(path: Path) -> os.stat_result:
        values: Final[list[int | float]] = list(original_lstat(path))
        values[4] += int(path == link)
        return os.stat_result(values)

    mocker.patch.object(Path, "lstat", autospec=True, side_effect=lstat_as_other_account)

    with pytest.raises(PermissionError):
        create_session_view(package, link / "package", tmp_path)

    assert list((target / "package").iterdir()) == []
