from __future__ import annotations

import sys
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@pytest.fixture(scope="session")
def pkg_with_extras_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    setup_cfg = f"""
    [metadata]
    name = demo
    version = 1.0.0
    [options]
    packages = find:
    install_requires =
        platformdirs>=4.3.8
        colorama>=0.4.6

    [options.extras_require]
    testing =
        covdefaults>=1.2; python_version == '2.7' or python_version == '{py_ver}'
        pytest>=5.4.1; python_version == '{py_ver}'
    docs =
        sphinx>=3
        sphinx-rtd-theme>=0.4.3,<1
    format =
        black>=3
        flake8
    """
    tmp_path = tmp_path_factory.mktemp("prj")
    (tmp_path / "setup.cfg").write_text(dedent(setup_cfg))
    (tmp_path / "README").write_text("")
    (tmp_path / "setup.py").write_text("from setuptools import setup; setup()")
    toml = '[build-system]\nrequires=["setuptools"]\nbuild-backend = "setuptools.build_meta"'
    (tmp_path / "pyproject.toml").write_text(toml)
    return tmp_path


@pytest.fixture(scope="session")
def pkg_with_pdm_backend(
    tmp_path_factory: pytest.TempPathFactory,
    pkg_builder: Callable[[Path, Path, list[str], bool], Path],
) -> Path:
    tmp_path = tmp_path_factory.mktemp("skeleton")

    pyproject_toml = """
    [build-system]
    requires = ["pdm-backend"]
    build-backend = "pdm.backend"

    [project]
    name = "skeleton"
    description = "Just a skeleton for reproducing #3512."
    version = "0.1.1337"
    dependencies = [
        "requests",
    ]

    [tool.pdm.build]
    includes = [
        "skeleton/",
    ]
    source-includes = [
        "tox.ini",
    ]
    """
    (tmp_path / "pyproject.toml").write_text(dedent(pyproject_toml))
    (tmp_path / "skeleton").mkdir(exist_ok=True)
    (tmp_path / "skeleton" / "__init__.py").touch()

    dist = tmp_path / "dist"
    pkg_builder(dist, tmp_path, ["sdist"], False)

    return tmp_path
