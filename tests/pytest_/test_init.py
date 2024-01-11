from __future__ import annotations

import os
import sys
from itertools import chain, combinations
from textwrap import dedent
from typing import TYPE_CHECKING, Sequence

import pytest

from tox.pytest import MonkeyPatch, ToxProjectCreator, check_os_environ
from tox.report import HandledError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_tox_project_no_base(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.ini": "[tox]",
            "src": {"__init__.py": "pass", "a": "out", "b": {"c": "out"}, "e": {"f": ""}},
        },
    )
    assert str(project.path) in repr(project)
    assert project.path.exists()
    assert project.structure == {
        "tox.ini": "[tox]",
        "src": {"__init__.py": "pass", "a": "out", "e": {"f": ""}, "b": {"c": "out"}},
    }


def test_tox_project_base(tmp_path: Path, tox_project: ToxProjectCreator) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "out").write_text("a")
    project = tox_project({"tox.ini": "[tox]"}, base=base)
    assert project.structure


COMB = list(chain.from_iterable(combinations(["DIFF", "MISS", "EXTRA"], i) for i in range(4)))


@pytest.mark.parametrize("ops", COMB, ids=["-".join(i) for i in COMB])
def test_env_var(monkeypatch: MonkeyPatch, ops: list[str]) -> None:
    with monkeypatch.context() as m:
        if "DIFF" in ops:
            m.setenv("DIFF", "B")
        if "MISS" in ops:
            m.setenv("MISS", "1")
        m.setenv("NO_CHANGE", "yes")
        m.setenv("PYTHONPATH", "yes")  # values to clean before run

        with check_os_environ():
            assert "PYTHONPATH" not in os.environ
            if "EXTRA" in ops:
                m.setenv("EXTRA", "A")
            if "DIFF" in ops:
                m.setenv("DIFF", "D")
            if "MISS" in ops:
                m.delenv("MISS")

            from tox.pytest import pytest as tox_pytest  # type: ignore[attr-defined]  # noqa: PLC0415

            exp = "test changed environ"
            if "EXTRA" in ops:
                exp += " extra {'EXTRA': 'A'}"
            if "MISS" in ops:
                exp += " miss {'MISS': '1'}"
            if "DIFF" in ops:
                exp += " diff {'DIFF = B vs D'}"

            def fail(msg: str) -> None:
                assert msg == exp

            m.setattr(tox_pytest, "fail", fail)
        assert "PYTHONPATH" in os.environ


def test_tox_run_does_not_return_exit_code(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    project = tox_project({"tox.ini": ""})
    mocker.patch("tox.run.main", return_value=None)
    with pytest.raises(RuntimeError, match="exit code not set"):
        project.run("c")


def test_tox_run_fails_before_state_setup(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    project = tox_project({"tox.ini": ""})
    mocker.patch("tox.run.main", side_effect=HandledError("something went bad"))
    outcome = project.run("c")
    with pytest.raises(RuntimeError, match="no state"):
        assert outcome.state


def test_tox_run_outcome_repr(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": ""})
    outcome = project.run("l")
    msg = dedent(
        f"""
    code: 0
    cmd: {sys.executable} -m tox l
    cwd: {project.path}
    standard output
    default environments:
    py -> [no description]
    """,
    ).lstrip()
    assert repr(outcome) == msg
    assert outcome.shell_cmd == f"{sys.executable} -m tox l"


def test_tox_run_assert_out_err_no_dedent(tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    project = tox_project({"tox.ini": ""})

    def _main(args: Sequence[str]) -> int:  # noqa: ARG001
        print(" goes on out", file=sys.stdout)  # noqa: T201
        print(" goes on err", file=sys.stderr)  # noqa: T201
        return 0

    mocker.patch("tox.run.main", side_effect=_main)
    outcome = project.run("c")
    outcome.assert_out_err(" goes on out\n", " goes on err\n", dedent=False)
