import sys

from tests.config.ini.replace.conftest import ReplaceOne
from tox.pytest import MonkeyPatch


def test_replace_pos_args_empty_sys_argv(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    monkeypatch.setattr(sys, "argv", [])
    result = replace_one("{posargs}", [])
    assert result == ""


def test_replace_pos_args_extra_sys_argv(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    monkeypatch.setattr(sys, "argv", [sys.executable, "magic"])
    result = replace_one("{posargs}", [])

    assert result == ""


def test_replace_pos_args(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    result = replace_one("{posargs}", ["ok", "what", " yes "])
    quote = '"' if sys.platform == "win32" else "'"
    assert result == f"ok what {quote} yes {quote}"
