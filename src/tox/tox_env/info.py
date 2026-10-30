"""Handle the tox env info file.

This file at the root of every tox environment contains information about the status of the tox environment: python
version, installed packages, etc.

"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from tox.util.typing_compat import override

if TYPE_CHECKING:
    from collections.abc import Generator


class Info:
    """Stores metadata about the tox environment."""

    def __init__(self, path: Path) -> None:
        self._path = path / ".tox-info.json"
        try:
            value = {} if self._path.is_symlink() else json.loads(self._path.read_text())
        except (ValueError, OSError):
            value = {}
        # a corrupted file must trigger recreation rather than crash, whatever shape the corruption takes
        self._content = value if isinstance(value, dict) else {}

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self._path})"

    @contextmanager
    def compare(
        self,
        value: Any,
        section: str,
        sub_section: str | None = None,
    ) -> Generator[tuple[bool, Any | None], None, None]:
        """Compare new information with the existing one and update if differs.

        :param value: the value stored
        :param section: the primary key of the information
        :param sub_section: the secondary key of the information

        :returns: a tuple where the first value is if it differs and the second is the old value

        """
        old = self._content.get(section)
        if sub_section is not None:
            old = old.get(sub_section) if isinstance(old, dict) else None
        if isinstance(value, dict) and not isinstance(old, dict):
            old = None

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
        # Replace the state path itself so a link cannot redirect the write.
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=self._path.parent, prefix=f"{self._path.name}.", suffix=".tmp"
        )
        temporary_path: Final[Path] = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handler:
                handler.write(json.dumps(self._content, indent=2))
            temporary_path.replace(self._path)
        finally:
            temporary_path.unlink(missing_ok=True)


__all__ = [
    "Info",
]
