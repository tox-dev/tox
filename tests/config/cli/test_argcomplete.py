from __future__ import annotations

import sys
from io import StringIO
from typing import TYPE_CHECKING, Final

import argcomplete
import pytest

from tox.config.cli.parse import get_options

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_argcomplete_autocomplete_called(mocker: MockerFixture) -> None:
    mock_autocomplete = mocker.patch.object(argcomplete, "autocomplete")
    get_options("r")
    mock_autocomplete.assert_called_once()


def test_argcomplete_missing_does_not_break(mocker: MockerFixture) -> None:
    mocker.patch.dict("sys.modules", {"argcomplete": None})
    result = get_options("r")
    assert result.parsed is not None


@pytest.mark.plugin_test
@pytest.mark.parametrize(
    ("line", "skip", "inline_next_to"),
    [
        pytest.param("tox -c {project}/tox.ini -e ", 1, "project", id="conf"),
        pytest.param("tox --conf={project}/tox.ini r -e ", 1, "project", id="conf-equals"),
        pytest.param("tox -c{project}/tox.ini -e ", 1, "project", id="conf-attached"),
        pytest.param("tox -c '{project}/tox.ini' -", 1, "project", id="conf-quoted"),
        pytest.param("python -m tox -c {project}/tox.ini ", 3, "project", id="conf-python-m"),
        pytest.param("tox -c ", 1, None, id="conf-no-value"),
        pytest.param("tox -c {project}/to", 1, None, id="conf-partial-value"),
        pytest.param("tox --conf={project}/to", 1, None, id="conf-equals-partial-value"),
        pytest.param("tox -c{project}/to", 1, None, id="conf-attached-partial-value"),
        pytest.param("tox -c {project}/missing.ini -e ", 1, None, id="conf-missing"),
        pytest.param("tox --root ", 1, None, id="root-no-value"),
        pytest.param("tox ", 1, "cwd", id="nothing"),
        pytest.param("tox --co", 1, "cwd", id="partial-option"),
        pytest.param("tox r -e ", 1, "cwd", id="env"),
        pytest.param("tox r -e a -- -c ", 1, "cwd", id="conf-within-posargs"),
    ],
)
def test_argcomplete_project_from_typed_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    line: str,
    skip: int,
    inline_next_to: str | None,
) -> None:
    for name in ("project", "cwd"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "tox.ini").write_text("")
        (tmp_path / name / "toxfile.py").write_text(
            "from pathlib import Path\nPath(__file__).with_name('loaded').write_text('loaded')\n"
        )
    monkeypatch.chdir(tmp_path / "cwd")
    typed_line: Final[str] = line.format(project=(tmp_path / "project").as_posix())
    monkeypatch.setenv("_ARGCOMPLETE", str(skip))
    monkeypatch.setenv("COMP_LINE", f"{typed_line}ignored-as-after-cursor")
    monkeypatch.setenv("COMP_POINT", str(len(typed_line)))
    mocker.patch.object(argcomplete, "autocomplete", side_effect=SystemExit(0))

    with pytest.raises(SystemExit):
        get_options()

    assert (tmp_path / "project" / "loaded").exists() is (inline_next_to == "project")
    assert (tmp_path / "cwd" / "loaded").exists() is (inline_next_to == "cwd")


def test_argcomplete_missing_ignores_completion_request(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    mocker.patch.dict("sys.modules", {"argcomplete": None})
    monkeypatch.setenv("_ARGCOMPLETE", "1")
    assert get_options("r").parsed.command == "r"


@pytest.mark.plugin_test
def test_argcomplete_without_line_exits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "toxfile.py").write_text("from pathlib import Path\nPath(__file__).with_name('loaded').touch()\n")
    monkeypatch.setenv("_ARGCOMPLETE", "1")
    monkeypatch.delenv("COMP_LINE", raising=False)

    with pytest.raises(SystemExit) as outcome:
        get_options()

    assert outcome.value.code == 0
    assert not (tmp_path / "loaded").exists()


def test_argcomplete_environment_candidates_from_typed_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    (tmp_path / "tox.ini").write_text("[tox]\nenv_list = cwd\n")
    config: Final[Path] = tmp_path / "project" / "tox.ini"
    config.parent.mkdir()
    config.write_text("[tox]\nenv_list = py311,lint\n")
    monkeypatch.chdir(tmp_path)
    line: Final[str] = f"tox -c {config.as_posix()} -e "
    monkeypatch.setenv("_ARGCOMPLETE", "1")
    monkeypatch.setenv("COMP_LINE", line)
    monkeypatch.setenv("COMP_POINT", str(len(line)))
    output: Final[StringIO] = StringIO()

    def complete(parser: ArgumentParser) -> None:
        argcomplete.CompletionFinder()(parser, exit_method=sys.exit, output_stream=output)

    mocker.patch.object(argcomplete, "autocomplete", side_effect=complete)

    with pytest.raises(SystemExit) as outcome:
        get_options()

    assert outcome.value.code == 0
    assert set(output.getvalue().split("\v")) == {"ALL", "py311", "lint"}
