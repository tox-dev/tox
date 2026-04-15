from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tox.execute.request import ExecuteRequest, StdinSource


def test_execute_request_raise_on_empty_cmd(os_env: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="cannot execute an empty command"):
        ExecuteRequest(cmd=[], cwd=Path().absolute(), env=os_env, stdin=StdinSource.OFF, run_id="")


def test_request_allow_star_is_none() -> None:
    request = ExecuteRequest(
        cmd=[sys.executable],
        cwd=Path.cwd(),
        env={"PATH": os.environ["PATH"]},
        stdin=StdinSource.OFF,
        run_id="run-id",
        allow=["*", "magic"],
    )
    assert request.allow is None


def test_shell_cmd_redacted_masks_secret_flag_value() -> None:
    request = ExecuteRequest(
        cmd=["pytest", "--token=hunter2", "tests"],
        cwd=Path.cwd(),
        env={},
        stdin=StdinSource.OFF,
        run_id="",
    )
    assert "hunter2" not in request.shell_cmd_redacted
    assert "--token=*******" in request.shell_cmd_redacted


def test_shell_cmd_unredacted_preserves_secret_value() -> None:
    request = ExecuteRequest(
        cmd=["pytest", "--token=hunter2"],
        cwd=Path.cwd(),
        env={},
        stdin=StdinSource.OFF,
        run_id="",
    )
    assert "hunter2" in request.shell_cmd


def test_shell_cmd_redacted_leaves_innocuous_args_alone() -> None:
    request = ExecuteRequest(
        cmd=["pytest", "-k", "test_token"],
        cwd=Path.cwd(),
        env={},
        stdin=StdinSource.OFF,
        run_id="",
    )
    assert request.shell_cmd_redacted == request.shell_cmd
