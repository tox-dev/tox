import os
from pathlib import Path

import pytest

from tox.execute.request import ExecuteRequest


def test_ExecuteRequest_constructor_raises_ValueError_if_empty_cmd_passed() -> None:
    with pytest.raises(ValueError, match="cannot execute an empty command"):
        ExecuteRequest(cmd=[], cwd=Path().absolute(), env=os.environ.copy(), allow_stdin=False)
