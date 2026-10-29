from __future__ import annotations

from typing import TYPE_CHECKING

import argcomplete
import pytest

from tox.config.cli.parse import get_options
from tox.plugin.manager import MANAGER

if TYPE_CHECKING:
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
    monkeypatch.chdir(tmp_path / "cwd")
    line = line.format(project=tmp_path / "project")
    monkeypatch.setenv("_ARGCOMPLETE", str(skip))
    monkeypatch.setenv("COMP_LINE", f"{line}ignored-as-after-cursor")
    monkeypatch.setenv("COMP_POINT", str(len(line)))
    mocker.patch.object(argcomplete, "autocomplete", side_effect=SystemExit(0))
    load_plugins = mocker.spy(MANAGER, "load_plugins")

    with pytest.raises(SystemExit):
        get_options()

    load_plugins.assert_called_once_with(tmp_path / inline_next_to / "tox.ini" if inline_next_to else None)


def test_argcomplete_missing_ignores_completion_request(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    mocker.patch.dict("sys.modules", {"argcomplete": None})
    monkeypatch.setenv("_ARGCOMPLETE", "1")
    result = get_options("r")
    assert result.parsed.command == "r"


def test_argcomplete_without_line_exits(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    monkeypatch.setenv("_ARGCOMPLETE", "1")
    monkeypatch.delenv("COMP_LINE", raising=False)
    load_plugins = mocker.spy(MANAGER, "load_plugins")

    with pytest.raises(SystemExit) as outcome:
        get_options()

    assert outcome.value.code == 0
    load_plugins.assert_not_called()
