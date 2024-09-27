from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_config_in_toml_core(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
    [tool.tox]
    env_list = [ "A", "B"]

    [tool.tox.env_run_base]
    description = "Do magical things"
    commands = [
        ["python", "--version"],
        ["python", "-c", "import sys; print(sys.executable)"]
    ]
    """
    })

    outcome = project.run("c", "--core")
    outcome.assert_success()
    assert "# Exception: " not in outcome.out, outcome.out
    assert "# !!! unused: " not in outcome.out, outcome.out


def test_config_in_toml_non_default(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
    [tool.tox.env.C]
    description = "Do magical things in C"
    commands = [
        ["python", "--version"]
    ]
    """
    })

    outcome = project.run("c", "-e", "C", "--core")
    outcome.assert_success()
    assert "# Exception: " not in outcome.out, outcome.out
    assert "# !!! unused: " not in outcome.out, outcome.out


def test_config_in_toml_extra(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
    [tool.tox.env_run_base]
    description = "Do magical things"
    commands = [
        ["python", "--version"]
    ]
    """
    })

    outcome = project.run("c", "-e", ".".join(str(i) for i in sys.version_info[0:2]))
    outcome.assert_success()
    assert "# Exception: " not in outcome.out, outcome.out
    assert "# !!! unused: " not in outcome.out, outcome.out
