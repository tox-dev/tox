from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final

import pytest

from tox.config.types import Command

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from tests.config.loader.conftest import ReplaceOne
    from tox.pytest import ToxProject, ToxProjectCreator, ToxRunOutcome


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


@pytest.mark.parametrize(
    ("token", "expected_args"),
    [
        pytest.param("{glob:*.txt}", list, id="relative"),
        pytest.param("{glob:{tox_root}{/}*.txt}", list, id="nested"),
        pytest.param("{glob:missing:{glob:*.txt}}", list, id="default"),
        pytest.param('"{glob:*.txt}"', lambda matches: [" ".join(matches)], id="double"),
        pytest.param("'{glob:*.txt}'", lambda matches: [" ".join(matches)], id="single"),
    ],
)
def test_replace_glob_match_one_argument_of_command(
    tox_project: ToxProjectCreator,
    tmp_path: Path,
    token: str,
    expected_args: Callable[[list[str]], list[str]],
) -> None:
    project: Final[ToxProject] = tox_project(
        {"tox.ini": f"[testenv]\ncommands = python {token} -x", "a b.txt": "", "it's.txt": ""},
        prj_path=tmp_path / "my proj",
    )
    outcome: Final[ToxRunOutcome] = project.run("c", "-k", "commands")
    outcome.assert_success()
    matches: Final[list[str]] = [str(project.path / "a b.txt"), str(project.path / "it's.txt")]
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", *expected_args(matches), "-x"])]


def test_replace_glob_match_as_is_outside_command(replace_one: ReplaceOne, tmp_path: Path) -> None:
    matches: Final[list[Path]] = [tmp_path / "a b.txt", tmp_path / "it's.txt"]
    for match in matches:
        match.touch()
    assert replace_one("{glob:*.txt}") == " ".join(str(match) for match in matches)


def test_replace_glob_match_not_substituted(replace_one: ReplaceOne, tmp_path: Path) -> None:
    (tmp_path / "{tox_root}.txt").touch()
    assert replace_one("{glob:*.txt}") == str(tmp_path / "{tox_root}.txt")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows reads z:/fallback as a drive path")
@pytest.mark.parametrize(
    ("existing", "expected"),
    [
        pytest.param("z", "z", id="match"),
        pytest.param("y", "/fallback", id="default"),
    ],
)
def test_replace_glob_single_letter_pattern_absolute_default(
    replace_one: ReplaceOne, tmp_path: Path, existing: str, expected: str
) -> None:
    (tmp_path / existing).touch()
    assert replace_one("{glob:z:/fallback}") == str(tmp_path / expected)
