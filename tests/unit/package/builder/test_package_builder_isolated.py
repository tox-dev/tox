import os
import subprocess

import py
import pytest

import tox.helper
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
    assert "The arguments ['--formats=gztar'] were given via `--global-option`." not in result.err
    assert "running sdist" in result.out, result.out
    assert "running egg_info" in result.out, result.out
    assert "example123-0.5.tar.gz" in result.out, result.out


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
            """,
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


def test_package_isolated_toml_bad_backend_path(initproj):
    """Verify that a non-list 'backend-path' is forbidden."""
    toml_file_check(
        initproj,
        6,
        "backend-path key at build-system section must be a list, if specified",
        """
    [build-system]
    requires = []
    build-backend = 'setuptools.build_meta'
    backend-path = 42
    """,
    )


def test_package_isolated_toml_backend_path_outside_root(initproj):
    """Verify that a 'backend-path' outside the project root is forbidden."""
    toml_file_check(
        initproj,
        6,
        "backend-path must exist in the project root",
        """
    [build-system]
    requires = []
    build-backend = 'setuptools.build_meta'
    backend-path = ['..']
    """,
    )


def test_verbose_isolated_build_in_tree(initproj, mock_venv, cmd):
    initproj(
        "example123-0.5",
        filedefs={
            "tox.ini": """
                    [tox]
                    isolated_build = true
                    """,
            "build.py": """
                    from setuptools.build_meta import *
                    """,
            "pyproject.toml": """
                    [build-system]
                    requires = ["setuptools >= 35.0.2"]
                    build-backend = 'build'
                    backend-path = ['.']
                                """,
        },
    )
    result = cmd("--sdistonly", "-v", "-v", "-v", "-e", "py")
    assert "running sdist" in result.out, result.out
    assert "running egg_info" in result.out, result.out
    assert "example123-0.5.tar.gz" in result.out, result.out


def test_isolated_build_script_args(tmp_path):
    """Verify that build_isolated.py can be called with only 2 argurments."""
    # cannot import build_isolated because of its side effects
    script_path = os.path.join(os.path.dirname(tox.helper.__file__), "build_isolated.py")
    subprocess.check_call(("python", script_path, str(tmp_path), "setuptools.build_meta"))


def test_isolated_build_backend_missing_hook(initproj, cmd):
    """Verify that tox works with a backend missing optional hooks

    PEP 517 allows backends to omit get_requires_for_build_sdist hook, in which
    case a default implementation that returns an empty list should be assumed
    instead of raising an error.
    """
    name = "ensconsproj"
    version = "0.1"
    src_root = "src"

    initproj(
        (name, version),
        filedefs={
            "pyproject.toml": """
            [build-system]
            requires = ["pytoml>=0.1", "enscons==0.26.0"]
            build-backend = "enscons.api"

            [tool.enscons]
            name = "{name}"
            version = "{version}"
            description = "Example enscons project"
            license = "MIT"
            packages = ["{name}"]
            src_root = "{src_root}"
            """.format(
                name=name, version=version, src_root=src_root
            ),
            "tox.ini": """
            [tox]
            isolated_build = true
            """,
            "SConstruct": """
            import enscons

            env = Environment(
                tools=["default", "packaging", enscons.generate],
                PACKAGE_METADATA=dict(
                    name = "{name}",
                    version = "{version}"
                ),
                WHEEL_TAG="py2.py3-none-any"
            )

            py_source = env.Glob("src/{name}/*.py")

            purelib = env.Whl("purelib", py_source, root="{src_root}")
            whl = env.WhlFile(purelib)

            sdist = env.SDist(source=FindSourceFiles() + ["PKG-INFO"])
            env.NoClean(sdist)
            env.Alias("sdist", sdist)

            develop = env.Command("#DEVELOP", enscons.egg_info_targets(env), enscons.develop)
            env.Alias("develop", develop)

            env.Default(whl, sdist)
            """.format(
                name=name, version=version, src_root=src_root
            ),
        },
    )

    result = cmd("--sdistonly", "-v", "-v", "-e", "py")
    assert "scons: done building targets" in result.out, result.out
