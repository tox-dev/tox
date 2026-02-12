from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from tox import __version__
from tox.plugin.manager import MANAGER

if TYPE_CHECKING:
    from pytest_mock import MockFixture

    from tox.pytest import ToxProjectCreator


def test_version() -> None:
    assert __version__


def test_version_without_plugin(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("--version")
    outcome.assert_success()
    assert __version__ in outcome.out
    assert "plugin" not in outcome.out


def test_version_with_plugin(tox_project: ToxProjectCreator, mocker: MockFixture) -> None:
    dist = [
        (
            mocker.create_autospec("types.ModuleType", __file__="B-path", tox_append_version_info=lambda: "magic"),
            SimpleNamespace(project_name="B", version="1.0"),
        ),
        (
            mocker.create_autospec("types.ModuleType", __file__="A-path"),
            SimpleNamespace(project_name="A", version="2.0"),
        ),
    ]
    mocker.patch.object(MANAGER.manager, "list_plugin_distinfo", return_value=dist)

    outcome = tox_project({"tox.ini": ""}).run("--version")

    outcome.assert_success()
    assert not outcome.err
    lines = outcome.out.splitlines()
    assert lines[0].startswith(__version__)

    assert lines[1:] == [
        "registered plugins:",
        "    B-1.0 at B-path magic",
        "    A-2.0 at A-path",
    ]


@pytest.mark.plugin_test
def test_version_with_inline_plugin(tox_project: ToxProjectCreator) -> None:
    def plugin() -> None:  # pragma: no cover
        pass

    project = tox_project({"tox.ini": "", "toxfile.py": plugin})
    outcome = project.run("--version")
    outcome.assert_success()
    assert __version__ in outcome.out
    assert "inline plugin:" in outcome.out
    assert "toxfile.py" in outcome.out


@pytest.mark.plugin_test
def test_version_with_inline_plugin_append_version_info(tox_project: ToxProjectCreator) -> None:
    def plugin() -> None:  # pragma: no cover
        def tox_append_version_info() -> str:
            return "custom-info-v1"

    project = tox_project({"tox.ini": "", "toxfile.py": plugin})
    outcome = project.run("--version")
    outcome.assert_success()
    assert "inline plugin:" in outcome.out
    assert "custom-info-v1" in outcome.out
