from typing import Callable

import pytest
from pytest_mock import MockerFixture

from tox.config.set_env import SetEnv
from tox.pytest import MonkeyPatch, ToxProjectCreator


def test_set_env_explicit(monkeypatch: MonkeyPatch) -> None:
    set_env = SetEnv("\nA=1\nB = 2\nC= 3\nD= 4")
    set_env.update({"E": "5 ", "F": "6"})

    keys = list(set_env)
    assert keys == ["E", "F", "A", "B", "C", "D"]
    values = [set_env.load(k) for k in keys]
    assert values == ["5 ", "6", "1", "2", "3", "4"]

    for key in keys:
        assert key in set_env
    assert "MISS" not in set_env


def test_set_env_bad_line() -> None:
    with pytest.raises(ValueError, match="A"):
        SetEnv("A")


EvalSetEnv = Callable[[str], SetEnv]


@pytest.fixture()
def eval_set_env(tox_project: ToxProjectCreator) -> EvalSetEnv:
    def func(tox_ini: str) -> SetEnv:
        prj = tox_project({"tox.ini": tox_ini})
        result = prj.run("c", "-k", "set_env", "-e", "py")
        result.assert_success()
        set_env: SetEnv = result.env_conf("py")["set_env"]
        return set_env

    return func


def test_set_env_default(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    set_env = eval_set_env("")
    keys = list(set_env)
    assert keys == ["PIP_DISABLE_PIP_VERSION_CHECK", "VIRTUALENV_NO_PERIODIC_UPDATE"]
    values = [set_env.load(k) for k in keys]
    assert values == ["1", "1"]


def test_set_env_self_key(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("a", "1")
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=a={env:a:2}")
    assert set_env.load("a") == "1"


def test_set_env_other_env_set(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("b", "1")
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=a={env:b:2}")
    assert set_env.load("a") == "1"


def test_set_env_other_env_default(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("b", raising=False)
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=a={env:b:2}")
    assert set_env.load("a") == "2"


def test_set_env_delayed_eval(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("b", "c=1")
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env={env:b}")
    assert set_env.load("c") == "1"


def test_set_env_tty_on(eval_set_env: EvalSetEnv, mocker: MockerFixture) -> None:
    mocker.patch("sys.stdout.isatty", return_value=True)
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env={tty:A=1:B=1}")
    assert set_env.load("A") == "1"
    assert "B" not in set_env


def test_set_env_tty_off(eval_set_env: EvalSetEnv, mocker: MockerFixture) -> None:
    mocker.patch("sys.stdout.isatty", return_value=False)
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env={tty:A=1:B=1}")
    assert set_env.load("B") == "1"
    assert "A" not in set_env


def test_set_env_circular_use_os_environ(tox_project: ToxProjectCreator) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\nset_env=a={env:b}\n b={env:a}"})
    result = prj.run("c", "-e", "py")
    result.assert_failed()
    assert "ValueError" in result.out, result.out
    assert "circular chain between set env a, b" in result.out, result.out


def test_set_env_invalid_lines(eval_set_env: EvalSetEnv) -> None:
    with pytest.raises(ValueError, match="a"):
        eval_set_env("[testenv]\npackage=skip\nset_env=a\n b")
