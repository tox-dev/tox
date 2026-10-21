from __future__ import annotations

import json
import socket
import sys
from typing import TYPE_CHECKING, Any

import pytest

from tox import __version__
from tox.journal import write_journal
from tox.journal.main import Journal

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="session")
def base_info() -> dict[str, Any]:
    return {
        "reportversion": "1",
        "toxversion": __version__,
        "platform": sys.platform,
        "host": socket.getfqdn(),
    }


def test_journal_enabled_default(base_info: dict[str, Any]) -> None:
    journal = Journal(enabled=True)
    assert bool(journal) is True
    assert journal.content == base_info


def test_journal_disabled_default() -> None:
    journal = Journal(enabled=False)
    assert bool(journal) is False
    assert journal.content == {}


def test_env_journal_enabled(base_info: dict[str, Any]) -> None:
    journal = Journal(enabled=True)
    env = journal.get_env_journal("a")
    assert journal.get_env_journal("a") is env
    env["demo"] = 1

    assert bool(env) is True
    base_info["testenvs"] = {"a": {"demo": 1}}
    assert journal.content == base_info


def test_env_journal_disabled() -> None:
    journal = Journal(enabled=False)
    env = journal.get_env_journal("a")
    assert bool(env) is False

    env["demo"] = 2
    assert journal.content == {"testenvs": {"a": {"demo": 2}}}


def test_write_journal_is_utf8_regardless_of_locale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("locale.getpreferredencoding", lambda do_setlocale=True: "cp1252")  # ruff:ignore[unused-lambda-argument]
    journal = Journal(enabled=True)
    journal.get_env_journal("py")["output"] = "\u2713 passed"
    path = tmp_path / "out.json"

    write_journal(path, journal)

    assert json.loads(path.read_text(encoding="utf-8"))["testenvs"]["py"]["output"] == "\u2713 passed"
