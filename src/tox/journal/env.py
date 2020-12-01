"""Record information about tox environments"""
from typing import Any, Dict, List, Tuple

from tox.execute import Outcome


class EnvJournal:
    """Report the status of a tox environment"""

    def __init__(self, enabled: bool, name: str) -> None:
        self._enabled = enabled
        self.name = name
        self._content: Dict[str, Any] = {}
        self._executes: List[Tuple[str, Outcome]] = []

    def __setitem__(self, key: str, value: Any) -> None:
        self._content[key] = value

    @property
    def content(self) -> Dict[str, Any]:
        tests: List[Dict[str, Any]] = []
        setup: List[Dict[str, Any]] = []
        for run_id, outcome in self._executes:
            one = {
                "command": outcome.cmd,
                "output": outcome.out,
                "err": outcome.err,
                "retcode": outcome.exit_code,
                "elapsed": outcome.elapsed,
                "show_on_standard": outcome.show_on_standard,
                "run_id": run_id,
                "start": outcome.start,
                "end": outcome.end,
            }
            if run_id.startswith("commands") or run_id.startswith("build"):
                tests.append(one)
            else:
                setup.append(one)
        if tests:
            self["test"] = tests
        if setup:
            self["setup"] = setup
        return self._content

    def __bool__(self) -> bool:
        return self._enabled

    def add_execute(self, outcome: Outcome, run_id: str) -> None:
        self._executes.append((run_id, outcome))


__all__ = ("EnvJournal",)
