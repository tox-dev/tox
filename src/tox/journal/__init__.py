"""This module handles collecting and persisting in json format a tox session"""
import json
from pathlib import Path
from typing import Optional

from .env import EnvJournal
from .main import Journal


def write_journal(path: Optional[Path], journal: Journal) -> None:
    if path is None:
        return
    with open(path, "wt") as file_handler:
        json.dump(journal.content, file_handler, indent=2, ensure_ascii=False)


__all__ = (
    "Journal",
    "EnvJournal",
    "write_journal",
)
