from __future__ import annotations

from typing import TYPE_CHECKING

from tox.util.path import ensure_cachedir_tag, ensure_empty_dir

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
