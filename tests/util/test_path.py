from __future__ import annotations

import errno
import os
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from tox.util.path import ensure_cachedir_tag, ensure_empty_dir, ensure_gitignore

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _typeshed import StrPath
    from pytest_mock import MockerFixture

_EXPECTED_CACHEDIR_TAG = """\
Signature: 8a477f597d28d172789f06886806bc55
# This file is a cache directory tag created by tox.
# For information about cache directory tags, see:
#\thttps://bford.info/cachedir/spec.html
"""


def test_ensure_cachedir_tag_creates_file(tmp_path: Path) -> None:
    ensure_cachedir_tag(tmp_path)
    tag = tmp_path / "CACHEDIR.TAG"
    assert tag.is_file()
    content = tag.read_text(encoding="utf-8")
    assert content.startswith("Signature: 8a477f597d28d172789f06886806bc55\n")
    assert content == _EXPECTED_CACHEDIR_TAG


def test_ensure_cachedir_tag_creates_parent_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    ensure_cachedir_tag(nested)
    assert (nested / "CACHEDIR.TAG").is_file()


def test_ensure_cachedir_tag_idempotent(tmp_path: Path) -> None:
    ensure_cachedir_tag(tmp_path)
    tag = tmp_path / "CACHEDIR.TAG"
    first_content = tag.read_text(encoding="utf-8")
    ensure_cachedir_tag(tmp_path)
    assert tag.read_text(encoding="utf-8") == first_content


def test_ensure_cachedir_tag_does_not_overwrite(tmp_path: Path) -> None:
    tag = tmp_path / "CACHEDIR.TAG"
    tag.write_text("Signature: 8a477f597d28d172789f06886806bc55\n# custom\n", encoding="utf-8")
    ensure_cachedir_tag(tmp_path)
    assert tag.read_text(encoding="utf-8") == "Signature: 8a477f597d28d172789f06886806bc55\n# custom\n"


def test_ensure_empty_dir_file(tmp_path: Path) -> None:
    dest = tmp_path / "a"
    dest.write_text("")
    ensure_empty_dir(dest)
    assert dest.is_dir()
    assert not list(dest.iterdir())


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_ensure_empty_dir_unlinks_dir_symlink(tmp_path: Path) -> None:
    (target := tmp_path / "target").mkdir()
    (payload := target / "payload").write_text("keep")
    (dest := tmp_path / "dest").mkdir()
    (dest / "link").symlink_to(target, target_is_directory=True)
    ensure_empty_dir(dest)
    assert (list(dest.iterdir()), payload.read_text()) == ([], "keep")


@pytest.mark.usefixtures("windows_unlink")
@pytest.mark.parametrize(
    "relative",
    [
        pytest.param("read_only.txt", id="top-level"),
        pytest.param("sub/read_only.txt", id="nested"),
    ],
)
def test_ensure_empty_dir_removes_read_only_file(tmp_path: Path, relative: str) -> None:
    (read_only := tmp_path / "dest" / relative).parent.mkdir(parents=True)
    read_only.write_text("data")
    read_only.chmod(stat.S_IREAD)
    ensure_empty_dir(tmp_path / "dest")
    assert list((tmp_path / "dest").iterdir()) == []


def test_ensure_empty_dir_leaves_locked_nested_file(tmp_path: Path, windows_unlink: set[str]) -> None:
    (sub := tmp_path / "dest" / "sub").mkdir(parents=True)
    (sub / "locked.txt").write_text("data")
    (sub / "other.txt").write_text("data")
    windows_unlink.add("locked.txt")
    ensure_empty_dir(tmp_path / "dest")
    assert [entry.name for entry in sub.iterdir()] == ["locked.txt"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_ensure_empty_dir_leaves_unreadable_nested_dir(tmp_path: Path, unreadable_nested_dir: Path) -> None:
    ensure_empty_dir(tmp_path / "dest")
    assert [entry.name for entry in unreadable_nested_dir.parent.iterdir()] == ["unreadable"]


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_ensure_empty_dir_keeps_locked_symlink_target_mode(tmp_path: Path, windows_unlink: set[str]) -> None:
    (target := tmp_path / "target.txt").write_text("keep")
    target.chmod(stat.S_IREAD)
    (dest := tmp_path / "dest").mkdir()
    (dest / "link").symlink_to(target)
    windows_unlink.add("link")
    with pytest.raises(PermissionError):
        ensure_empty_dir(dest)
    assert stat.S_IMODE(target.stat().st_mode) == stat.S_IREAD


def test_ensure_empty_dir_keeps_except_filename(tmp_path: Path) -> None:
    (dest := tmp_path / "dest").mkdir()
    (keep := dest / "file.lock").write_text("keep")
    (dest / "other.txt").write_text("remove")
    (dest / "sub").mkdir()
    (dest / "sub" / "nested.txt").write_text("remove")
    ensure_empty_dir(dest, except_filename="file.lock")
    assert (list(dest.iterdir()), keep.read_text()) == ([keep], "keep")


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_ensure_empty_dir_unlinks_file_symlink(tmp_path: Path) -> None:
    (target := tmp_path / "target.txt").write_text("keep")
    (dest := tmp_path / "dest").mkdir()
    (dest / "link").symlink_to(target)
    ensure_empty_dir(dest)
    assert (list(dest.iterdir()), target.read_text()) == ([], "keep")


def test_ensure_gitignore_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "work"
    target.mkdir()
    ensure_gitignore(target)
    gitignore = target / ".gitignore"
    assert gitignore.exists()
    assert gitignore.read_text(encoding="utf-8") == "*\n"


def test_ensure_gitignore_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c"
    ensure_gitignore(target)
    gitignore = target / ".gitignore"
    assert gitignore.exists()
    assert gitignore.read_text(encoding="utf-8") == "*\n"


def test_ensure_gitignore_does_not_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "work"
    target.mkdir()
    gitignore = target / ".gitignore"
    gitignore.write_text("custom\n", encoding="utf-8")
    ensure_gitignore(target)
    assert gitignore.read_text(encoding="utf-8") == "custom\n"


def test_ensure_gitignore_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "work"
    target.mkdir()
    ensure_gitignore(target)
    ensure_gitignore(target)
    assert (target / ".gitignore").read_text(encoding="utf-8") == "*\n"


@pytest.fixture
def windows_unlink(mocker: MockerFixture) -> set[str]:
    """Names added to the returned set fail to unlink, like a file another process holds open."""
    locked: Final[set[str]] = set()
    real_unlink: Final = os.unlink

    # POSIX lets the owner unlink a read-only file while Windows refuses, so emulate Windows at the syscall
    def unlink(path: StrPath, *, dir_fd: int | None = None) -> None:
        if Path(path).name in locked or not os.stat(path, dir_fd=dir_fd, follow_symlinks=False).st_mode & stat.S_IWRITE:
            raise PermissionError(errno.EACCES, "Access is denied", path)
        real_unlink(path, dir_fd=dir_fd)

    mocker.patch("os.unlink", autospec=True, side_effect=unlink)
    # on 3.10 Path.unlink calls the os.unlink captured at import, so route it through the patched one
    mocker.patch.object(Path, "unlink", autospec=True, side_effect=os.unlink)
    return locked


@pytest.fixture
def unreadable_nested_dir(tmp_path: Path) -> Iterator[Path]:
    (unreadable := tmp_path / "dest" / "sub" / "unreadable").mkdir(parents=True)
    unreadable.chmod(0)
    yield unreadable
    unreadable.chmod(stat.S_IRWXU)  # let pytest delete tmp_path
