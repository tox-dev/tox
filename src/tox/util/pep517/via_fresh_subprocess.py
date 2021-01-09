import os
import sys
from contextlib import contextmanager
from pathlib import Path
from subprocess import PIPE, Popen
from threading import Thread
from typing import IO, Any, Iterator, Optional, Tuple, cast

from packaging.requirements import Requirement

from .frontend import CmdStatus, Frontend


class SubprocessCmdStatus(CmdStatus, Thread):
    def __init__(self, process: "Popen[str]") -> None:
        super().__init__()
        self.process = process
        self._out_err: Optional[Tuple[str, str]] = None
        self.start()

    def run(self) -> None:
        self._out_err = self.process.communicate()

    @property
    def done(self) -> bool:
        return self.process.returncode is not None

    def out_err(self) -> Tuple[str, str]:
        return cast(Tuple[str, str], self._out_err)


class SubprocessFrontend(Frontend):
    def __init__(
        self,
        root: Path,
        backend_paths: Tuple[Path, ...],
        backend_module: str,
        backend_obj: Optional[str],
        requires: Tuple[Requirement, ...],
    ):
        super().__init__(root, backend_paths, backend_module, backend_obj, requires, reuse_backend=False)

    @contextmanager
    def _send_msg(  # type: ignore[override]
        self, cmd: str, result_file: Path, msg: str
    ) -> Iterator[SubprocessCmdStatus]:
        env = os.environ.copy()
        backend = os.pathsep.join(str(i) for i in self._backend_paths).strip()
        if backend:
            env["PYTHONPATH"] = backend
        process = Popen(
            args=[sys.executable] + self.backend_args,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
            universal_newlines=True,
            cwd=self._root,
            env=env,
        )
        cast(IO[str], process.stdin).write(f"{os.linesep}{msg}{os.linesep}")
        yield SubprocessCmdStatus(process)

    def send_cmd(self, cmd: str, **kwargs: Any) -> Tuple[Any, str, str]:
        return self._send(cmd, **kwargs)


__all__ = (
    "SubprocessCmdStatus",
    "SubprocessFrontend",
)
