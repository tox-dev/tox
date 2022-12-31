from __future__ import annotations

import threading
from typing import Generator

import pytest

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


def test_replace_env_when_value_is_backslash(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """When the replacement value is backslash, it shouldn't affect the next replacement."""
    monkeypatch.setenv("MAGIC", "tragic")
    monkeypatch.setenv("BS", "\\")
    result = replace_one(r"{env:BS}{env:MAGIC}")
    assert result == r"\tragic"


def test_replace_env_when_value_is_stuff_then_backslash(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """When the replacement value is a string containing backslash, it can affect the next replacement."""
    monkeypatch.setenv("MAGIC", "tragic")
    monkeypatch.setenv("BS", "stuff\\")
    result = replace_one(r"{env:BS}{env:MAGIC}")
    assert result == r"stuff{env:MAGIC}"


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
    """Replacement values will not infinitely loop"""
    monkeypatch.setenv("MAGIC", "{env:MAGIC}")
    result = replace_one("{env:MAGIC}")
    assert result == "{env:MAGIC}"


@pytest.fixture()
def reset_env_var_after_delay(monkeypatch: MonkeyPatch) -> Generator[threading.Thread, None, None]:
    timeout = 2

    def avoid_infinite_loop() -> None:  # pragma: no cover
        monkeypatch.setenv("TRAGIC", f"envvar forcibly reset after {timeout} sec")

    timer = threading.Timer(2, avoid_infinite_loop)
    timer.start()
    yield timer
    timer.cancel()
    timer.join()


@pytest.mark.usefixtures("reset_env_var_after_delay")
def test_replace_env_var_circular_flip_flop(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """Replacement values will not infinitely loop back and forth"""
    monkeypatch.setenv("TRAGIC", "{env:MAGIC}")
    monkeypatch.setenv("MAGIC", "{env:TRAGIC}")
    result = replace_one("{env:MAGIC}")
    assert result == "{env:TRAGIC}"


@pytest.mark.parametrize("fallback", [True, False])
def test_replace_env_var_chase(replace_one: ReplaceOne, monkeypatch: MonkeyPatch, fallback: bool) -> None:
    """Resolve variable to be replaced and default value via indirection."""
    monkeypatch.setenv("WALK", "THIS")
    def_val = "or that one"
    monkeypatch.setenv("DEF", def_val)
    if fallback:
        monkeypatch.delenv("THIS", raising=False)
        exp_result = def_val
    else:
        this_val = "path"
        monkeypatch.setenv("THIS", this_val)
        exp_result = this_val
    result = replace_one("{env:{env:WALK}:{env:DEF}}")
    assert result == exp_result


def test_replace_env_default_with_colon(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    monkeypatch.delenv("MAGIC", raising=False)
    result = replace_one("{env:MAGIC:https://some.url.org}")
    assert result == "https://some.url.org"


def test_replace_env_default_deep(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """Get the value through a long tree of nested defaults."""
    monkeypatch.delenv("M", raising=False)
    assert replace_one("{env:M:{env:M:{env:M:{env:M:{env:M:foo}}}}}") == "foo"
