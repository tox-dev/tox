"""Execute that runs on local file system via subprocess-es."""

from __future__ import annotations

from tox.execute.api import Execute, ExecuteInstance, ExecuteOptions, ExecuteStatus, FinishedExecuteStatus
from tox.execute.request import ExecuteRequest, StdinSource
from tox.execute.util import batch_file_command_line, is_batch_file, shebang
from tox.tox_env.errors import Fail
from tox.util.redact import redact_argv
from tox.util.typing_compat import override

from .execute import (
    IS_WIN,
    SIG_INTERRUPT,
    LocalSubprocessExecuteFailedStatus,
    LocalSubProcessExecuteInstance,
    LocalSubprocessExecuteStatus,
    LocalSubProcessExecutor,
    ReadViaThread,
)

__all__ = [
    "IS_WIN",
    "SIG_INTERRUPT",
    "Execute",
    "ExecuteInstance",
    "ExecuteOptions",
    "ExecuteRequest",
    "ExecuteStatus",
    "Fail",
    "FinishedExecuteStatus",
    "LocalSubProcessExecuteInstance",
    "LocalSubProcessExecutor",
    "LocalSubprocessExecuteFailedStatus",
    "LocalSubprocessExecuteStatus",
    "ReadViaThread",
    "StdinSource",
    "batch_file_command_line",
    "is_batch_file",
    "override",
    "redact_argv",
    "shebang",
]
