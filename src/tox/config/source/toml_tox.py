"""Load from a tox.toml file."""

from __future__ import annotations

from .toml_pyproject import TomlPyProject, TomlSection


class TomlToxSection(TomlSection):  # simplint: ignore[SMP403]  # imported by tox plugins
    PREFIX = ()


class TomlTox(TomlPyProject):
    """Configuration sourced from a pyproject.toml files.

    :var FILENAME: the name of the configuration file, ``tox.toml``

    """

    FILENAME = "tox.toml"
    _Section = TomlToxSection


__all__ = [
    "TomlTox",
]
