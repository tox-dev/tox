from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProject, ToxProjectCreator
    from tox.session.state import State


@pytest.fixture
def project_state(tox_project: ToxProjectCreator) -> tuple[ToxProject, State]:
    project = tox_project({"tox.toml": 'env_list = ["a"]'})
    return project, project.run("c").state


def test_config_get_returns_declared_type(project_state: tuple[ToxProject, State]) -> None:
    project, state = project_state
    assert state.conf.core.get("tox_root", Path) == project.path


def test_config_get_container(project_state: tuple[ToxProject, State]) -> None:
    assert "LANG" in project_state[1].conf.get_env("a").get("pass_env", list[str])


def test_config_get_type_mismatch(project_state: tuple[ToxProject, State]) -> None:
    with pytest.raises(TypeError, match=r"tox_root is \w+Path, expected <class 'int'>"):
        project_state[1].conf.core.get("tox_root", int)
