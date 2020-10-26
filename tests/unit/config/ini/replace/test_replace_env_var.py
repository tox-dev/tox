from tests.unit.config.ini.replace.conftest import ReplaceOne
from tox.pytest import MonkeyPatch


def test_replace_env_set(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{env:MAGIC}") as result:
        monkeypatch.setenv("MAGIC", "something good")
    assert result.val == "something good"


def test_replace_env_missing(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{env:MAGIC}") as result:
        monkeypatch.delenv("MAGIC", raising=False)
    assert result.val == ""


def test_replace_env_missing_default(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{env:MAGIC:def}") as result:
        monkeypatch.delenv("MAGIC", raising=False)
    assert result.val == "def"


def test_replace_env_missing_default_from_env(replace_one: ReplaceOne, monkeypatch: MonkeyPatch) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{env:MAGIC:{env:MAGIC_DEFAULT}}") as result:
        monkeypatch.delenv("MAGIC", raising=False)
        monkeypatch.setenv("MAGIC_DEFAULT", "yes")
    assert result.val == "yes"
