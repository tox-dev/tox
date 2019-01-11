import os

from tox.util import set_os_env_var


def test_set_os_env_var_clean_env(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    with set_os_env_var("ENV", "a"):
        assert os.environ["ENV"] == "a"
    assert "ENV" not in os.environ


def test_set_os_env_var_exist_env(monkeypatch):
    monkeypatch.setenv("ENV", "b")
    with set_os_env_var("ENV", "a"):
        assert os.environ["ENV"] == "a"
    assert os.environ["ENV"] == "b"


def test_set_os_env_var_non_str():
    with set_os_env_var("ENV", 1):
        assert os.environ["ENV"] == "1"
