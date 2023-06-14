"""This module handles collecting and persisting in json format a tox session."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .env import EnvJournal
from .main import Journal

if TYPE_CHECKING:
    from pathlib import Path


def write_journal(path: Path | None, journal: Journal) -> None:
    if path is None:
        return
    with open(path, "w") as file_handler:
        json.dump(journal.content, file_handler, indent=2, ensure_ascii=False)


__all__ = (
    "Journal",
    "EnvJournal",
    "write_journal",
)
