from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tox.util.file_view import create_session_view

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import MonkeyPatch


def test_create_session_view_copies(tmp_path: Path) -> None:
    package = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    result = create_session_view(package, tmp_path / "temp")
    assert result.read_bytes() == b"data"
    assert result.parent.parent == tmp_path / "temp"


def test_create_session_view_no_common_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """A source without a common path with the session dir (e.g. cross-drive) must not crash the copy."""
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "pkg.whl").write_bytes(b"data")
    monkeypatch.chdir(tmp_path)

    result = create_session_view(Path("dist/pkg.whl"), tmp_path / "temp")

    assert result.is_absolute()
    assert result.read_bytes() == b"data"


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_create_session_view_replaces_staging_link(tmp_path: Path) -> None:
    (package := tmp_path / "pkg.whl").write_bytes(b"data")
    (outside := tmp_path / "outside").mkdir()
    (staging := tmp_path / "temp").symlink_to(outside, target_is_directory=True)

    result = create_session_view(package, staging)

    assert (result.read_bytes(), staging.is_symlink(), list(outside.iterdir())) == (b"data", False, [])


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_create_session_view_does_not_follow_destination_link(tmp_path: Path, mocker: MockerFixture) -> None:
    (package := tmp_path / "pkg.whl").write_bytes(b"data")
    (outside := tmp_path / "outside").write_bytes(b"keep")
    mkdir = Path.mkdir

    def mkdir_with_link(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)
        if path.name == "1":
            (path / package.name).symlink_to(outside)

    mocker.patch.object(Path, "mkdir", autospec=True, side_effect=mkdir_with_link)

    with pytest.raises(FileExistsError):
        create_session_view(package, tmp_path / "temp")

    assert outside.read_bytes() == b"keep"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory permissions")
def test_create_session_view_rejects_writable_staging_parent(tmp_path: Path) -> None:
    (package := tmp_path / "pkg.whl").write_bytes(b"data")
    (parent := tmp_path / "temp").mkdir(mode=0o777)
    parent.chmod(0o777)
    (staging := parent / "package").mkdir()

    with pytest.raises(PermissionError):
        create_session_view(package, staging)

    assert list(staging.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory ownership")
def test_create_session_view_rejects_other_account_staging_parent(tmp_path: Path, mocker: MockerFixture) -> None:
    (package := tmp_path / "pkg.whl").write_bytes(b"data")
    (staging := tmp_path / "temp").mkdir()
    mocker.patch("os.geteuid", autospec=True, return_value=staging.stat().st_uid + 1)

    with pytest.raises(PermissionError):
        create_session_view(package, staging)

    assert list(staging.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX sticky directory permissions")
def test_create_session_view_rejects_foreign_link_in_sticky_parent(tmp_path: Path, mocker: MockerFixture) -> None:
    (package := tmp_path / "pkg.whl").write_bytes(b"data")
    (sticky := tmp_path / "sticky").mkdir()
    sticky.chmod(0o1777)
    (target := tmp_path / "target").mkdir()
    (link := sticky / "link").symlink_to(target, target_is_directory=True)
    original_lstat = Path.lstat

    def lstat_as_other_account(path: Path) -> os.stat_result:
        values = list(original_lstat(path))
        values[4] += int(path == link)
        return os.stat_result(values)

    mocker.patch.object(Path, "lstat", autospec=True, side_effect=lstat_as_other_account)

    with pytest.raises(PermissionError):
        create_session_view(package, link / "package")

    assert list((target / "package").iterdir()) == []
