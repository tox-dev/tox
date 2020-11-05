from pathlib import Path
from typing import Dict

import pytest

from tox.execute.request import ExecuteRequest


def test_execute_request_raise_on_empty_cmd(os_env: Dict[str, str]) -> None:
    with pytest.raises(ValueError, match="cannot execute an empty command"):
        ExecuteRequest(cmd=[], cwd=Path().absolute(), env=os_env, allow_stdin=False)
