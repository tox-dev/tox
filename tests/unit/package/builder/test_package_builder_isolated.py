import os

import py
import pytest

from tox.package.builder.isolated import get_build_info
from tox.reporter import _INSTANCE


def test_verbose_isolated_build(initproj, mock_venv, cmd):
    initproj(
        "example123-0.5",
        filedefs={
            "tox.ini": """
                    [tox]
                    isolated_build = true
                    """,
            "pyproject.toml": """
                    [build-system]
                    requires = ["setuptools >= 35.0.2"]
                    build-backend = 'setuptools.build_meta'
                                """,
        },
    )
    result = cmd("--sdistonly", "-v", "-v", "-v", "-e", "py")
    assert "running sdist" in result.out, result.out
    assert "running egg_info" in result.out, result.out
    assert "Writing example123-0.5{}setup.cfg".format(os.sep) in result.out, result.out


def test_dist_exists_version_change(mock_venv, initproj, cmd):
    base = initproj(
        "package_toml-{}".format("0.1"),
        filedefs={
            "tox.ini": """
                [tox]
                isolated_build = true
                        """,
            "pyproject.toml": """
                [build-system]
                requires = ["setuptools >= 35.0.2"]
                build-backend = 'setuptools.build_meta'
                            """,
        },
    )
    result = cmd("-e", "py")
    result.assert_success()

    new_code = base.join("setup.py").read_text("utf-8").replace("0.1", "0.2")
    base.join("setup.py").write_text(new_code, "utf-8")

    result = cmd("-e", "py")
    result.assert_success()


def test_package_isolated_no_pyproject_toml(initproj, cmd):
    initproj(
        "package_no_toml-0.1",
        filedefs={
            "tox.ini": """
                [tox]
                isolated_build = true
            """
        },
    )
    result = cmd("--sdistonly", "-e", "py")
    result.assert_fail()
    assert result.outlines == ["ERROR: missing {}".format(py.path.local().join("pyproject.toml"))]


def toml_file_check(initproj, version, message, toml):
    initproj(
        "package_toml-{}".format(version),
        filedefs={
            "tox.ini": """
                        [tox]
                        isolated_build = true
                    """,
            "pyproject.toml": toml,
        },
    )

    with pytest.raises(SystemExit, match="1"):
        get_build_info(py.path.local())
    toml_file = py.path.local().join("pyproject.toml")
    msg = "ERROR: {} inside {}".format(message, toml_file)
    assert _INSTANCE.messages == [msg]


def test_package_isolated_toml_no_build_system(initproj):
    toml_file_check(initproj, 1, "build-system section missing", "")


def test_package_isolated_toml_no_requires(initproj):
    toml_file_check(
        initproj,
        2,
        "missing requires key at build-system section",
        """
    [build-system]
    """,
    )


def test_package_isolated_toml_no_backend(initproj):
    toml_file_check(
        initproj,
        3,
        "missing build-backend key at build-system section",
        """
    [build-system]
    requires = []
    """,
    )


def test_package_isolated_toml_bad_requires(initproj):
    toml_file_check(
        initproj,
        4,
        "requires key at build-system section must be a list of string",
        """
    [build-system]
    requires = ""
    build-backend = ""
    """,
    )


def test_package_isolated_toml_bad_backend(initproj):
    toml_file_check(
        initproj,
        5,
        "build-backend key at build-system section must be a string",
        """
    [build-system]
    requires = []
    build-backend = []
    """,
    )
