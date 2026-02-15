from __future__ import annotations

from argparse import Action, ArgumentParser, Namespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from tox.report import HandledError
from tox.session.env_select import _env_completer, register_env_select_flags  # noqa: PLC2701

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


@pytest.fixture
def completer_args() -> dict[str, Action | ArgumentParser | Namespace | str]:
    return {
        "prefix": "",
        "action": MagicMock(spec=Action),
        "parser": MagicMock(spec=ArgumentParser),
        "parsed_args": MagicMock(spec=Namespace),
    }


def test_env_completer_ini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, completer_args: dict[str, object]) -> None:
    config = tmp_path / "tox.ini"
    config.write_text("[tox]\nenv_list = py311,lint\n[testenv:docs]\n")
    monkeypatch.chdir(tmp_path)
    result = _env_completer(**completer_args)  # type: ignore[arg-type]
    assert "ALL" in result
    assert "py311" in result
    assert "lint" in result
    assert "docs" in result


def test_env_completer_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, completer_args: dict[str, object]) -> None:
    config = tmp_path / "tox.toml"
    config.write_text('[env.lint]\ncommands = [["ruff", "check"]]\n')
    monkeypatch.chdir(tmp_path)
    result = _env_completer(**completer_args)  # type: ignore[arg-type]
    assert "ALL" in result
    assert "lint" in result


def test_env_completer_no_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, completer_args: dict[str, object]
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _env_completer(**completer_args)  # type: ignore[arg-type]
    assert result == ["ALL"]


def test_env_completer_handled_error(mocker: MockerFixture, completer_args: dict[str, object]) -> None:
    mocker.patch("tox.session.env_select.discover_source", side_effect=HandledError("bad config"))
    result = _env_completer(**completer_args)  # type: ignore[arg-type]
    assert result == []


def test_env_completer_includes_plugin_envs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, completer_args: dict[str, object]
) -> None:
    config = tmp_path / "tox.ini"
    config.write_text("[tox]\nenv_list = py311\n")
    monkeypatch.chdir(tmp_path)
    mocker.patch("tox.plugin.manager.Plugin.tox_extend_envs", return_value=[["plugin-env"]])
    result = _env_completer(**completer_args)  # type: ignore[arg-type]
    assert "ALL" in result
    assert "py311" in result
    assert "plugin-env" in result


def test_register_env_select_attaches_completer() -> None:
    parser = ArgumentParser()
    register_env_select_flags(parser, default=None, multiple=False)
    action = next(a for a in parser._actions if a.dest == "env")  # noqa: SLF001
    assert hasattr(action, "completer")
    assert action.completer is _env_completer
