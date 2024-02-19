from __future__ import annotations

import sys
from textwrap import dedent
from typing import TYPE_CHECKING

from packaging.version import Version

from tox.version import version as __version__

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_quickstart_ok(tox_project: ToxProjectCreator) -> None:
    project = tox_project({})
    tox_ini = project.path / "demo" / "tox.ini"
    assert not tox_ini.exists()

    outcome = project.run("q", str(tox_ini.parent))
    outcome.assert_success()

    assert tox_ini.exists()
    found = tox_ini.read_text()

    version = str(Version(__version__.split("+")[0]))
    text = f"""
            [tox]
            env_list =
                py{"".join(str(i) for i in sys.version_info[0:2])}
            minversion = {version}

            [testenv]
            description = run the tests with pytest
            package = wheel
            wheel_build_env = .pkg
            deps =
                pytest>=6
            commands =
                pytest {{tty:--color=yes}} {{posargs}}
        """
    content = dedent(text).lstrip()
    assert found == content


def test_quickstart_refuse(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": ""})
    outcome = project.run("q", str(project.path))
    outcome.assert_failed(code=1)
    assert "tox.ini already exist, refusing to overwrite" in outcome.out


def test_quickstart_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("q", "-h")
    outcome.assert_success()


def test_quickstart_no_args(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({}).run("q")
    outcome.assert_success()
