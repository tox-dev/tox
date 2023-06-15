from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_env_already_packaging(tox_project: ToxProjectCreator) -> None:
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": '[build-system]\nrequires=[]\nbuild-backend="build"',
        },
    )
    result = proj.run("r", "-e", "py,.pkg")
    result.assert_failed(code=-2)
    assert "cannot run packaging environment(s) .pkg" in result.out, result.out


def test_env_run_cannot_be_packaging_too(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel\npackage_env=py", "pyproject.toml": ""})
    result = proj.run("r", "-e", "py")
    result.assert_failed(code=-2)
    assert " py cannot self-package" in result.out, result.out
