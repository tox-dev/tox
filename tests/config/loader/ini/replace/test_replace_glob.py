from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tests.config.loader.conftest import ReplaceOne


def test_replace_glob_matches(replace_one: ReplaceOne, tmp_path: Path) -> None:
    (tmp_path / "a.txt").touch()
    (tmp_path / "b.txt").touch()
    result = replace_one(f"{{glob:{tmp_path}/*.txt}}")
    assert str(tmp_path / "a.txt") in result
    assert str(tmp_path / "b.txt") in result


def test_replace_glob_sorted(replace_one: ReplaceOne, tmp_path: Path) -> None:
    (tmp_path / "c.txt").touch()
    (tmp_path / "a.txt").touch()
    (tmp_path / "b.txt").touch()
    result = replace_one(f"{{glob:{tmp_path}/*.txt}}")
    paths = result.split()
    assert paths == sorted(paths)


def test_replace_glob_no_matches_empty(replace_one: ReplaceOne, tmp_path: Path) -> None:
    result = replace_one(f"{{glob:{tmp_path}/*.xyz}}")
    assert not result


def test_replace_glob_no_matches_default(replace_one: ReplaceOne, tmp_path: Path) -> None:
    result = replace_one(f"{{glob:{tmp_path}/*.xyz:fallback}}")
    assert result == "fallback"


def test_replace_glob_relative_path(replace_one: ReplaceOne, tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "pkg.whl").touch()
    result = replace_one("{glob:dist/*.whl}")
    assert result == str(tmp_path / "dist" / "pkg.whl")


def test_replace_glob_recursive(replace_one: ReplaceOne, tmp_path: Path) -> None:
    sub = tmp_path / "src" / "pkg"
    sub.mkdir(parents=True)
    (sub / "mod.py").touch()
    pattern = tmp_path / "src" / "**" / "*.py"
    result = replace_one(f"{{glob:{pattern}}}")
    assert str(sub / "mod.py") in result


def test_replace_glob_no_pattern_error(replace_one: ReplaceOne) -> None:
    with pytest.raises(Exception, match="No pattern was supplied"):
        replace_one("{glob:}")


def test_replace_glob_nested_substitution(replace_one: ReplaceOne, tmp_path: Path) -> None:
    (tmp_path / "marker.txt").touch()
    result = replace_one("{glob:{tox_root}/*.txt}")
    assert str(tmp_path / "marker.txt") in result
