from __future__ import annotations

from argparse import Action, ArgumentParser, Namespace
from typing import TYPE_CHECKING, TypedDict

import pytest

from tox.report import HandledError
from tox.session.env_select import (
    _env_completer,  # ruff:ignore[import-private-name]  # private names under test
    register_env_select_flags,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


class _CompleterArgs(TypedDict):
    prefix: str
    action: Action
    parser: ArgumentParser
    parsed_args: Namespace


@pytest.fixture
def completer_args(mocker: MockerFixture) -> _CompleterArgs:
    return {
        "prefix": "",
        "action": mocker.MagicMock(spec=Action),
        "parser": mocker.MagicMock(spec=ArgumentParser),
        "parsed_args": mocker.MagicMock(spec=Namespace),
    }


def test_env_completer_ini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, completer_args: _CompleterArgs) -> None:
    (tmp_path / "tox.ini").write_text("[tox]\nenv_list = py311,lint\n[testenv:docs]\n")
    monkeypatch.chdir(tmp_path)
    result = _env_completer(**completer_args)
    assert "ALL" in result
    assert "py311" in result
    assert "lint" in result
    assert "docs" in result


def test_env_completer_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, completer_args: _CompleterArgs) -> None:
    (tmp_path / "tox.toml").write_text('[env.lint]\ncommands = [["ruff", "check"]]\n')
    monkeypatch.chdir(tmp_path)
    result = _env_completer(**completer_args)
    assert "ALL" in result
    assert "lint" in result


def test_env_completer_no_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, completer_args: _CompleterArgs
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _env_completer(**completer_args)
    assert result == ["ALL"]


def test_env_completer_handled_error(mocker: MockerFixture, completer_args: _CompleterArgs) -> None:
    mocker.patch("tox.session.env_select.discover_source", autospec=True, side_effect=HandledError("bad config"))
    result = _env_completer(**completer_args)
    assert result == []


def test_env_completer_includes_plugin_envs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, completer_args: _CompleterArgs
) -> None:
    (tmp_path / "tox.ini").write_text("[tox]\nenv_list = py311\n")
    monkeypatch.chdir(tmp_path)
    mocker.patch("tox.plugin.manager.Plugin.tox_extend_envs", autospec=True, return_value=[["plugin-env"]])
    result = _env_completer(**completer_args)
    assert "ALL" in result
    assert "py311" in result
    assert "plugin-env" in result


def test_register_env_select_attaches_completer(mocker: MockerFixture) -> None:
    parser = ArgumentParser()
    add_argument = mocker.spy(parser, "add_argument")
    register_env_select_flags(parser, default=None, multiple=False)
    action = add_argument.spy_return_list[0]
    assert hasattr(action, "completer")
    assert action.completer is _env_completer
