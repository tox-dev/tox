from __future__ import annotations

from itertools import chain
from typing import Sequence

from tox.config.loader.ini.factor import extend_factors
from tox.config.loader.section import BaseSection

# TODO: Shouldn't this be loaded from config?
BASE_TEST_ENV = "testenv"
TEST_ENV_PREFIX = ("tox", "env")
# TODO: PKG_ENV_PREFIX?
PKG_ENV_PREFIX = "pkgenv"


# TODO: Duplicates IniSection API
class TomlSection(BaseSection[Sequence[str]]):
    def __init__(self, prefix: Sequence[str] | None, name: str) -> None:
        super().__init__(tuple(prefix or ()), name)

    @classmethod
    def from_key(cls: type[TomlSection], key: str) -> TomlSection:
        """
        Create a section from a section key.

        :param key: the section key
        :return: the constructed section
        """
        chunks = key.split(cls.SEP)
        return cls(chunks[:-1], chunks[-1])

    @property
    def key(self) -> str:
        """:return: the section key"""
        return self.SEP.join(chain(self._prefix, (self._name,)))

    @classmethod
    def test_env(cls, name: str) -> TomlSection:
        return cls(TEST_ENV_PREFIX, name)

    @property
    def is_test_env(self) -> bool:
        return self.prefix == TEST_ENV_PREFIX and self.name != BASE_TEST_ENV

    @property
    def names(self) -> list[str]:
        return list(extend_factors(self.name))


CORE = TomlSection(None, "tox")
TEST_ENV_ROOT = TomlSection(TEST_ENV_PREFIX[:-1], TEST_ENV_PREFIX[-1])
