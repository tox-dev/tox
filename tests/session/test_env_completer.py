from __future__ import annotations

from argparse import Action, ArgumentParser, Namespace
from typing import TYPE_CHECKING, Protocol, TypedDict, cast

import pytest

from tox.report import HandledError
from tox.session.env_select import register_env_select_flags

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pytest_mock import MockerFixture


class _CompleterArgs(TypedDict):
    prefix: str
    action: Action
    parser: ArgumentParser
    parsed_args: Namespace


class _CompleterAction(Protocol):
    completer: Callable[[str, Action, ArgumentParser, Namespace], list[str]]


@pytest.fixture
def completer_args() -> _CompleterArgs:
    parser = ArgumentParser()
    register_env_select_flags(parser, default=None, multiple=False)
    return {
        "prefix": "",
        "action": next(a for a in parser._actions if a.dest == "env"),  # ruff:ignore[private-member-access]  # parser API
        "parser": parser,
        "parsed_args": Namespace(),
    }


def test_env_completer_ini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, completer_args: _CompleterArgs) -> None:
    (tmp_path / "tox.ini").write_text("[tox]\nenv_list = py311,lint\n[testenv:docs]\n")
    monkeypatch.chdir(tmp_path)
    result = _complete_env(completer_args)
    assert "ALL" in result
    assert "py311" in result
    assert "lint" in result
    assert "docs" in result


def _complete_env(args: _CompleterArgs) -> list[str]:
    return cast("_CompleterAction", args["action"]).completer(
        args["prefix"], args["action"], args["parser"], args["parsed_args"]
    )


def test_env_completer_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, completer_args: _CompleterArgs) -> None:
    (tmp_path / "tox.toml").write_text('[env.lint]\ncommands = [["ruff", "check"]]\n')
    monkeypatch.chdir(tmp_path)
    result = _complete_env(completer_args)
    assert "ALL" in result
    assert "lint" in result


def test_env_completer_no_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, completer_args: _CompleterArgs
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _complete_env(completer_args)
    assert result == ["ALL"]


def test_env_completer_handled_error(mocker: MockerFixture, completer_args: _CompleterArgs) -> None:
    mocker.patch("tox.session.env_select.discover_source", autospec=True, side_effect=HandledError("bad config"))
    result = _complete_env(completer_args)
    assert result == []


def test_env_completer_includes_plugin_envs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, completer_args: _CompleterArgs
) -> None:
    (tmp_path / "tox.ini").write_text("[tox]\nenv_list = py311\n")
    monkeypatch.chdir(tmp_path)
    mocker.patch("tox.plugin.manager.Plugin.tox_extend_envs", autospec=True, return_value=[["plugin-env"]])
    result = _complete_env(completer_args)
    assert "ALL" in result
    assert "py311" in result
    assert "plugin-env" in result
