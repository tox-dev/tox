from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import ANY

import pytest

from tox.config.set_env import SetEnv

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import MonkeyPatch, ToxProjectCreator

from typing import Protocol


def test_set_env_explicit() -> None:
    set_env = SetEnv("\nA=1\nB = 2\nC= 3\nD= 4", "py", "py", Path())
    set_env.update({"E": "5 ", "F": "6"}, override=False)

    keys = list(set_env)
    assert keys == ["E", "F", "A", "B", "C", "D"]
    values = [set_env.load(k) for k in keys]
    assert values == ["5 ", "6", "1", "2", "3", "4"]

    for key in keys:
        assert key in set_env
    assert "MISS" not in set_env


def test_set_env_merge() -> None:
    a = SetEnv("\nA=1\nB = 2\nC= 3\nD= 4", "py", "py", Path())
    b = SetEnv("\nA=2\nE = 5", "py", "py", Path())
    a.update(b, override=False)

    keys = list(a)
    assert keys == ["E", "A", "B", "C", "D"]
    values = [a.load(k) for k in keys]
    assert values == ["5", "1", "2", "3", "4"]

    a.update(b, override=True)

    values = [a.load(k) for k in keys]
    assert values == ["5", "2", "2", "3", "4"]


def test_set_env_bad_line() -> None:
    with pytest.raises(ValueError, match="A"):
        SetEnv("A", "py", "py", Path())


class EvalSetEnv(Protocol):
    def __call__(
        self,
        tox_ini: str,
        extra_files: dict[str, Any] | None = ...,
        from_cwd: Path | None = ...,
    ) -> SetEnv: ...


@pytest.fixture
def eval_set_env(tox_project: ToxProjectCreator) -> EvalSetEnv:
    def func(tox_ini: str, extra_files: dict[str, Any] | None = None, from_cwd: Path | None = None) -> SetEnv:
        prj = tox_project({"tox.ini": tox_ini, **(extra_files or {})})
        result = prj.run("c", "-k", "set_env", "-e", "py", from_cwd=None if from_cwd is None else prj.path / from_cwd)
        result.assert_success()
        set_env: SetEnv = result.env_conf("py")["set_env"]
        return set_env

    return func


def test_set_env_default(eval_set_env: EvalSetEnv) -> None:
    set_env = eval_set_env("")
    keys = list(set_env)
    assert keys == ["PYTHONHASHSEED", "PIP_DISABLE_PIP_VERSION_CHECK", "PYTHONIOENCODING"]
    values = [set_env.load(k) for k in keys]
    assert values == [ANY, "1", "utf-8"]


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
    result.assert_success()
    assert "replace failed in py.set_env with MatchRecursionError" in result.out, result.out
    assert "circular chain between set env a, b" in result.out, result.out


def test_set_env_invalid_lines(eval_set_env: EvalSetEnv) -> None:
    with pytest.raises(ValueError, match="a"):
        eval_set_env("[testenv]\npackage=skip\nset_env=a\n b")


def test_set_env_replacer(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MAGIC", "\nb=2\n")
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=a=1\n {env:MAGIC}")
    env = {k: set_env.load(k) for k in set_env}
    assert env == {
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "a": "1",
        "b": "2",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONHASHSEED": ANY,
    }


def test_set_env_honor_override(eval_set_env: EvalSetEnv) -> None:
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=PIP_DISABLE_PIP_VERSION_CHECK=0")
    assert set_env.load("PIP_DISABLE_PIP_VERSION_CHECK") == "0"


def test_set_env_environment_file(eval_set_env: EvalSetEnv) -> None:
    env_file = """
    A=1
    B= 2
    C = 1
    # D = comment # noqa: E800
    E = "1"
    F =
    """
    extra = {"A": {"a.txt": env_file}, "B": None, "C": None}
    ini = "[testenv]\npackage=skip\nset_env=file|A{/}a.txt\nchange_dir=C"
    set_env = eval_set_env(ini, extra_files=extra, from_cwd=Path("B"))
    content = {k: set_env.load(k) for k in set_env}
    assert content == {
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONHASHSEED": ANY,
        "A": "1",
        "B": "2",
        "C": "1",
        "E": '"1"',
        "F": "",
        "PYTHONIOENCODING": "utf-8",
    }


def test_set_env_environment_file_missing(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\nset_env=file|magic.txt"})
    result = project.run("r")
    result.assert_failed()
    assert f"py: failed with {project.path / 'magic.txt'} does not exist for set_env" in result.out
