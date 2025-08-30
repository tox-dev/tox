from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize("value", ["1", "0", "", "arbitrary_value"])
def test_ci_passthrough_present(value: str, tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", value)
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands=python -c 'print(0)'\n"})
    execute_calls = prj.patch_execute(lambda _r: 0)
    result = prj.run("r", "-e", "py")
    result.assert_success()
    req = execute_calls.call_args[0][3]
    assert req.env["__TOX_ENVIRONMENT_VARIABLE_ORIGINAL_CI"] == value


def test_ci_passthrough_absent(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands=python -c 'print(0)'\n"})
    execute_calls = prj.patch_execute(lambda _r: 0)
    result = prj.run("r", "-e", "py")
    result.assert_success()
    req = execute_calls.call_args[0][3]
    assert "__TOX_ENVIRONMENT_VARIABLE_ORIGINAL_CI" not in req.env
