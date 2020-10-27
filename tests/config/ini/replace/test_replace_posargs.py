import sys

from tests.config.ini.replace.conftest import ReplaceOne
from tox.pytest import MonkeyPatch


def test_replace_pos_args_empty_sys_argv(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{posargs}") as result:
        monkeypatch.setattr(sys, "argv", [])
    assert result.val == ""


def test_replace_pos_args_extra_sys_argv(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{posargs}") as result:
        monkeypatch.setattr(sys, "argv", [sys.executable, "magic"])
    assert result.val == ""


def test_replace_pos_args(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{posargs}") as result:
        monkeypatch.setattr(sys, "argv", [sys.executable, "magic", "--", "ok", "what", " yes "])
    quote = '"' if sys.platform == "win32" else "'"
    assert result.val == f"ok what {quote} yes {quote}"
