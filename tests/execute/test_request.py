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
