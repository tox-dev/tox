from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize("trail", [[], ["--"]], ids=["no_posargs", "empty_posargs"])
def test_exec_fail_no_posargs(tox_project: ToxProjectCreator, trail: list[str]) -> None:
    outcome = tox_project({"tox.ini": ""}).run("e", "-e", "py39", *trail)
    outcome.assert_failed()
    msg = "ROOT: HandledError| You must specify a command as positional arguments, use -- <command>\n"
    outcome.assert_out_err(msg, "")


def test_exec_fail_multiple_target(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("e", "-e", "py39,py38", "--", "py")
    outcome.assert_failed()
    msg = "ROOT: HandledError| exactly one target environment allowed in exec mode but found py39, py38\n"
    outcome.assert_out_err(msg, "")


@pytest.mark.parametrize("exit_code", [1, 0])
def test_exec(tox_project: ToxProjectCreator, exit_code: int) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip"})
    py_cmd = f"import sys; print(sys.version); raise SystemExit({exit_code})"
    outcome = prj.run("e", "-e", "py", "--", "python", "-c", py_cmd)
    if exit_code:
        outcome.assert_failed()
    else:
        outcome.assert_success()
    assert sys.version in outcome.out


def test_exec_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("e", "-h")
    outcome.assert_success()
