"""Persist a tox session journal to a json file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main import Journal


__all__ = [
    "write_journal",
]


def write_journal(path: Path | None, journal: Journal) -> None:
    if path is None:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # captured output keeps undecodable bytes as lone surrogates; backslashreplace turns them into JSON \uXXXX escapes
    with Path(path).open("w", encoding="utf-8", errors="backslashreplace") as file_handler:
        json.dump(journal.content, file_handler, indent=2, ensure_ascii=False)
