from __future__ import annotations

from tests.config.loader.ini.replace.conftest import ReplaceOne
from tox.pytest import MonkeyPatch


def test_replace_env_set(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    monkeypatch.setenv("MAGIC", "something good")
    result = replace_one("{env:MAGIC}")
    assert result == "something good"


def test_replace_env_set_double_bs(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """Double backslash should escape to single backslash and not affect surrounding replacements."""
    monkeypatch.setenv("MAGIC", "something good")
    result = replace_one(r"{env:MAGIC}\\{env:MAGIC}")
    assert result == r"something good\something good"


def test_replace_env_set_triple_bs(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """Triple backslash should escape to single backslash also escape subsequent replacement."""
    monkeypatch.setenv("MAGIC", "something good")
    result = replace_one(r"{env:MAGIC}\\\{env:MAGIC}")
    assert result == r"something good\{env:MAGIC}"


def test_replace_env_set_quad_bs(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """Quad backslash should escape to two backslashes and not affect surrounding replacements."""
    monkeypatch.setenv("MAGIC", "something good")
    result = replace_one(r"\\{env:MAGIC}\\\\{env:MAGIC}\\")
    assert result == r"\something good\\something good" + "\\"


def test_replace_env_missing(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    monkeypatch.delenv("MAGIC", raising=False)
    result = replace_one("{env:MAGIC}")
    assert result == ""


def test_replace_env_missing_default(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    monkeypatch.delenv("MAGIC", raising=False)
    result = replace_one("{env:MAGIC:def}")
    assert result == "def"


def test_replace_env_missing_default_from_env(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    monkeypatch.delenv("MAGIC", raising=False)
    monkeypatch.setenv("MAGIC_DEFAULT", "yes")
    result = replace_one("{env:MAGIC:{env:MAGIC_DEFAULT}}")
    assert result == "yes"


def test_replace_env_var_circular(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    monkeypatch.setenv("MAGIC", "{env:MAGIC}")
    result = replace_one("{env:MAGIC}")
    assert result == "{env:MAGIC}"


def test_replace_env_default_with_colon(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    monkeypatch.delenv("MAGIC", raising=False)
    result = replace_one("{env:MAGIC:https://some.url.org}")
    assert result == "https://some.url.org"
