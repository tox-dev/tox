from __future__ import annotations

from tox import __version__
from tox.pytest import ToxProjectCreator


def test_version_no_plugin(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": "", "pyproject.toml": ""}).run("r", "--version")
    assert __version__ in outcome.out
    assert "plugin" not in outcome.out
