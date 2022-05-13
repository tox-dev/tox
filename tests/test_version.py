from __future__ import annotations

from types import SimpleNamespace

from pytest_mock import MockFixture

from tox import __version__
from tox.plugin.manager import MANAGER
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
            mocker.create_autospec("types.ModuleType", __file__=f"{i}-path"),
            SimpleNamespace(project_name=i, version=v),
        )
        for i, v in (("B", "1.0"), ("A", "2.0"))
    ]
    mocker.patch.object(MANAGER.manager, "list_plugin_distinfo", return_value=dist)

    outcome = tox_project({"tox.ini": ""}).run("--version")

    outcome.assert_success()
    assert not outcome.err
    lines = outcome.out.splitlines()
    assert lines[0].startswith(__version__)

    assert lines[1:] == [
        "registered plugins:",
        "    B-1.0 at B-path",
        "    A-2.0 at A-path",
    ]
