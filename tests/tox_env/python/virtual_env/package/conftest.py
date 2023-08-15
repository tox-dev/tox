from __future__ import annotations

import sys
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
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
        platformdirs>=2.1
        colorama>=0.4.3

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
    (tmp_path / "setup.py").write_text("from setuptools import setup; setup()")
    toml = '[build-system]\nrequires=["setuptools", "wheel"]\nbuild-backend = "setuptools.build_meta"'
    (tmp_path / "pyproject.toml").write_text(toml)
    return tmp_path
