from __future__ import annotations

from _pytest.monkeypatch import MonkeyPatch

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


def test_version_with_plugin(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    from tox import __version__

    def dummy_plugin():
        class MockModule:
            __file__ = "dummy-path"

        class MockEggInfo:
            project_name = "dummy-project"
            version = "1.0"

        return [(MockModule, MockEggInfo)]

    monkeypatch.setattr(MANAGER.manager, "list_plugin_distinfo", dummy_plugin)

    outcome = tox_project({"tox.ini": ""}).run("--version")
    outcome.assert_success()
    assert __version__ in outcome.out
    assert "registered plugins:" in outcome.out
    assert "dummy-path" in outcome.out
    assert "dummy-project" in outcome.out
    assert "1.0" in outcome.out
