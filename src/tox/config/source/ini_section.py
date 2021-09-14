from tox.config.loader.section import Section


class IniSection(Section):
    @classmethod
    def test_env(cls, name: str) -> "IniSection":
        return cls(TEST_ENV_PREFIX, name)

    @property
    def is_test_env(self) -> bool:
        return self.prefix == TEST_ENV_PREFIX


TEST_ENV_PREFIX = "testenv"
CORE = IniSection(None, "tox")

__all__ = [
    "IniSection",
    "CORE",
    "TEST_ENV_PREFIX",
]
