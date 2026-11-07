"""Generate json report of a tox run."""

from __future__ import annotations

import socket
import sys
from typing import TYPE_CHECKING

from tox.version import version

from .env import EnvJournal

if TYPE_CHECKING:
    from tox.util.json_types import JsonValue


class Journal:
    """The result of a tox session.

    :param enabled: whether the journal records anything

    """

    def __init__(  # keeps the signature
        self,
        enabled: bool,  # ruff:ignore[boolean-type-hint-positional-argument]  # keeps the signature
    ) -> None:
        self._enabled = enabled
        self._content: dict[str, JsonValue] = {}
        self._env: dict[str, EnvJournal] = {}

        if self._enabled:
            self._content.update(
                {
                    "reportversion": "1",
                    "toxversion": version,
                    "platform": sys.platform,
                    "host": socket.getfqdn(),
                },
            )

    def __bool__(self) -> bool:
        return self._enabled

    @property
    def content(self) -> dict[str, JsonValue]:
        """The journal of the run, with the journal of each environment under its name."""
        test_env_journals: dict[str, JsonValue] = {}
        for name, value in self._env.items():
            test_env_journals[name] = value.content
        if test_env_journals:
            self._content["testenvs"] = test_env_journals
        return self._content

    def get_env_journal(self, name: str) -> EnvJournal:
        """Return the env log of an environment (create on first call).

        :param name: the name of the tox environment

        :returns: the journal of the environment

        """
        if name not in self._env:
            self._env[name] = EnvJournal(self._enabled, name)
        return self._env[name]


__all__ = [
    "Journal",
]
