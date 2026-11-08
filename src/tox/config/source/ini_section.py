from __future__ import annotations

from typing import Final

from tox.config.loader.ini.factor import extend_factors
from tox.config.loader.section import Section


class IniSection(Section):
    """A section of an ini configuration file."""

    @classmethod
    def test_env(cls, name: str) -> IniSection:
        """Get the section of a tox environment.

        :param name: the name of the environment

        :returns: the section of the environment

        """
        return cls(TEST_ENV_PREFIX, name)

    @property
    def is_test_env(self) -> bool:
        """Whether the section is the one of a tox environment."""
        return self.prefix == TEST_ENV_PREFIX

    @property
    def names(self) -> list[str]:
        """The environment names the section declares, expanded from its factors."""
        return list(extend_factors(self.name))


TEST_ENV_PREFIX: Final[str] = "testenv"
"""Prefix of the sections that configure tox environments."""
PKG_ENV_PREFIX: Final[str] = "pkgenv"
"""Prefix of the sections that configure the packaging environments."""
CORE: Final[IniSection] = IniSection(None, "tox")
"""The core section of the ini configuration file."""

__all__ = [
    "CORE",
    "PKG_ENV_PREFIX",
    "TEST_ENV_PREFIX",
    "IniSection",
]
