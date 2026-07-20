"""Handle the tox env info file.

This file at the root of every tox environment contains information about the status of the tox environment: python
version, installed packages, etc.

"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class Info:
    """Stores metadata about the tox environment."""

    def __init__(self, path: Path) -> None:
        self._path = path / ".tox-info.json"
        try:
            value = json.loads(self._path.read_text())
        except (ValueError, OSError):
            value = {}
        # a corrupted file must trigger recreation rather than crash, whatever shape the corruption takes
        self._content = value if isinstance(value, dict) else {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self._path})"

    @contextmanager
    def compare(
        self,
        value: Any,
        section: str,
        sub_section: str | None = None,
    ) -> Iterator[tuple[bool, Any | None]]:
        """Compare new information with the existing one and update if differs.

        :param value: the value stored
        :param section: the primary key of the information
        :param sub_section: the secondary key of the information

        :returns: a tuple where the first value is if it differs and the second is the old value

        """
        old = self._content.get(section)
        if sub_section is not None:
            # a non-dict section is corruption: treat it as absent so it gets replaced below
            old = old.get(sub_section) if isinstance(old, dict) else None

        if old == value:
            yield True, old
        else:
            raised = True
            try:
                yield False, old
                raised = False
            finally:
                if not raised:  # only update when the body did not raise
                    if sub_section is None:
                        self._content[section] = value
                    elif isinstance(self._content.get(section), dict):
                        self._content[section][sub_section] = value
                    else:
                        self._content[section] = {sub_section: value}
                    self._write()

    def reset(self) -> None:
        self._content = {}

    def _write(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._content, indent=2))


__all__ = ("Info",)
