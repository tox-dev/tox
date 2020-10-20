"""
Declare and handle the tox env info file (a file at the root of every tox environment that contains information about
the status of the tox environment - python version of the environment, installed packages, etc.).
"""
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional, Tuple


class Info:
    def __init__(self, path: Path) -> None:
        self._path = path / ".tox-info.json"
        try:
            value = json.loads(self._path.read_text())
        except (ValueError, OSError):
            value = {}
        self._content = value

    @contextmanager
    def compare(
        self, value: Any, section: str, sub_section: Optional[str] = None
    ) -> Iterator[Tuple[bool, Optional[Any]]]:
        old = self._content.get(section)
        if sub_section is not None and old is not None:
            old = old.get(sub_section)

        if old == value:
            yield True, None
        else:
            yield False, old
            # if no exception thrown update
            if sub_section is None:
                self._content[section] = value
            else:
                if self._content.get(section) is None:
                    self._content[section] = {sub_section: value}
                else:
                    self._content[section][sub_section] = value
            self._write()

    def update(self, section: str, value: str) -> None:
        self._content[section] = value

    def _write(self) -> None:
        self._path.write_text(json.dumps(self._content, indent=2))


__all__ = ("Info",)
