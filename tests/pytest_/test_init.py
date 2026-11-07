from __future__ import annotations

import os
import sys
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from tox.pytest import MonkeyPatch, ToxProjectCreator, check_os_environ
from tox.report import HandledError

if TYPE_CHECKING:
    from collections.abc import Sequence
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


@pytest.mark.parametrize(
    ("changes", "exp"),
    [
        pytest.param([("setenv", "EXTRA", "A")], "test changed environ extra {'EXTRA': 'A'}", id="extra"),
        pytest.param([("delenv", "MISS")], "test changed environ miss {'MISS': '1'}", id="miss"),
        pytest.param([("setenv", "DIFF", "D")], "test changed environ diff {'DIFF = B vs D'}", id="diff"),
        pytest.param(
            [("setenv", "EXTRA", "A"), ("delenv", "MISS")],
            "test changed environ extra {'EXTRA': 'A'} miss {'MISS': '1'}",
            id="extra-miss",
        ),
        pytest.param(
            [("setenv", "EXTRA", "A"), ("setenv", "DIFF", "D")],
            "test changed environ extra {'EXTRA': 'A'} diff {'DIFF = B vs D'}",
            id="extra-diff",
        ),
        pytest.param(
            [("delenv", "MISS"), ("setenv", "DIFF", "D")],
            "test changed environ miss {'MISS': '1'} diff {'DIFF = B vs D'}",
            id="miss-diff",
        ),
        pytest.param(
            [("setenv", "EXTRA", "A"), ("delenv", "MISS"), ("setenv", "DIFF", "D")],
            "test changed environ extra {'EXTRA': 'A'} miss {'MISS': '1'} diff {'DIFF = B vs D'}",
            id="extra-miss-diff",
        ),
    ],
)
def test_env_var(monkeypatch: MonkeyPatch, changes: list[tuple[str, ...]], exp: str) -> None:
    with monkeypatch.context() as m:
        m.setenv("DIFF", "B")
        m.setenv("MISS", "1")
        m.setenv("NO_CHANGE", "yes")
        m.setenv("PYTHONPATH", "yes")  # values to clean before run

        with check_os_environ():
            assert "PYTHONPATH" not in os.environ
            for method, *args in changes:
                getattr(m, method)(*args)

            from tox.pytest import pytest as tox_pytest  # ruff:ignore[import-outside-top-level]  # deferred import

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

    def _main(args: Sequence[str]) -> int:  # ruff:ignore[unused-function-argument]  # interface signature
        print(" goes on out", file=sys.stdout)  # ruff:ignore[print]  # test output
        print(" goes on err", file=sys.stderr)  # ruff:ignore[print]  # test output
        return 0

    mocker.patch("tox.run.main", side_effect=_main)
    project.run("c").assert_out_err(" goes on out\n", " goes on err\n", dedent=False)
