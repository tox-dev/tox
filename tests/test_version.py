from __future__ import annotations

from unittest import mock

from tox.plugin.manager import MANAGER
from tox.pytest import ToxProjectCreator


def test_version() -> None:
    from tox import __version__

    assert __version__


def test_version_without_plugin(tox_project: ToxProjectCreator) -> None:
    from tox import __version__

    outcome = tox_project({"tox.ini": ""}).run("--version")
    outcome.assert_success()
    assert __version__ in outcome.out
    assert "plugin" not in outcome.out


def test_version_with_plugin(tox_project: ToxProjectCreator) -> None:
    from tox import __version__

    mock_module = mock.Mock(__file__="dummy-path")

    mock_egg_info = mock.Mock(
        project_name="dummy-project",
        version="1.0",
    )

    with mock.patch.object(MANAGER.manager, "list_plugin_distinfo", return_value=[(mock_module, mock_egg_info)]):
        outcome = tox_project({"tox.ini": ""}).run("--version")
        outcome.assert_success()
        assert __version__ in outcome.out
        assert "registered plugins:" in outcome.out
        assert "dummy-path" in outcome.out
        assert "dummy-project" in outcome.out
        assert "1.0" in outcome.out
