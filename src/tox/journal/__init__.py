"""This module handles collecting and persisting in json format a tox session."""

from __future__ import annotations

import json  # simplint: ignore[init-module-content]  # API path
from pathlib import Path  # simplint: ignore[init-module-content]  # API path

from .env import EnvJournal
from .main import Journal


def write_journal(path: Path | None, journal: Journal) -> None:
    """Write the journal of the run to a file as JSON.

    :param path: the file to write to, nothing is written when ``None``
    :param journal: the journal to write

    """
    if path is None:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # captured output keeps undecodable bytes as lone surrogates; backslashreplace turns them into JSON \uXXXX escapes
    with Path(path).open("w", encoding="utf-8", errors="backslashreplace") as file_handler:
        json.dump(journal.content, file_handler, indent=2, ensure_ascii=False)


__all__ = [
    "EnvJournal",
    "Journal",
    "write_journal",
]
