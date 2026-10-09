from __future__ import annotations

import stat
import sys
from typing import TYPE_CHECKING

import pytest

from tox.util.path import ensure_cachedir_tag, ensure_empty_dir, ensure_gitignore

if TYPE_CHECKING:
    from pathlib import Path

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


def test_ensure_empty_dir_removes_read_only_file(tmp_path: Path) -> None:
    (dest := tmp_path / "dest").mkdir()
    (read_only := dest / "read_only.txt").write_text("data")
    read_only.chmod(stat.S_IREAD)
    ensure_empty_dir(dest)
    assert dest.is_dir()
    assert not list(dest.iterdir())


def test_ensure_empty_dir_removes_read_only_file_in_sub_dir(tmp_path: Path) -> None:
    (dest := tmp_path / "dest").mkdir()
    (sub_dir := dest / "sub").mkdir()
    (read_only := sub_dir / "read_only.txt").write_text("data")
    read_only.chmod(stat.S_IREAD)
    ensure_empty_dir(dest)
    assert dest.is_dir()
    assert not list(dest.iterdir())


def test_ensure_empty_dir_keeps_except_filename(tmp_path: Path) -> None:
    (dest := tmp_path / "dest").mkdir()
    (keep := dest / "file.lock").write_text("keep")
    (dest / "other.txt").write_text("remove")
    (dest / "sub").mkdir()
    (dest / "sub" / "nested.txt").write_text("remove")
    ensure_empty_dir(dest, except_filename="file.lock")
    assert (list(dest.iterdir()), keep.read_text()) == ([keep], "keep")


def test_ensure_empty_dir_unlinks_file_symlink(tmp_path: Path) -> None:
    (target := tmp_path / "target.txt").write_text("keep")
    (dest := tmp_path / "dest").mkdir()
    try:
        (dest / "link").symlink_to(target)
    except OSError:  # pragma: no cover # creating symlinks needs privileges on Windows
        pytest.skip("cannot create symlinks")
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
