from __future__ import annotations

import sys
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from tox.tox_env.errors import Fail
from tox.tox_env.python.pylock import Pylock

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator

PYLOCK_TOML = dedent("""\
    lock-version = "1.0"
    created-by = "test-tool"

    [[packages]]
    name = "alpha"
    version = "1.0.0"

    [[packages.wheels]]
    url = "https://files.example.com/alpha-1.0.0-py3-none-any.whl"

    [packages.wheels.hashes]
    sha256 = "abc123"

    [[packages]]
    name = "beta"
    version = "2.0.0"

    [packages.sdist]
    url = "https://files.example.com/beta-2.0.0.tar.gz"

    [packages.sdist.hashes]
    sha256 = "def456"
""")


def test_pylock_install(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            pylock = "pylock.toml"
            """,
            "pylock.toml": PYLOCK_TOML,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    req_file = str(project.path / ".tox" / "py" / "pylock.txt")
    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        ("py", "install_pylock", ["python", "-I", "-m", "pip", "install", "--no-deps", "-r", req_file]),
    ]
    assert (project.path / ".tox" / "py" / "pylock.txt").read_text() == "alpha==1.0.0\nbeta==2.0.0"


def test_pylock_empty(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()
    assert not execute_calls.call_args_list


def test_pylock_not_found(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            pylock = "missing.toml"
            """,
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert "pylock file 'missing.toml' not found" in result.out


def test_pylock_invalid_toml(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            pylock = "pylock.toml"
            """,
            "pylock.toml": dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"
                packages = "not-a-list"
            """),
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert "invalid pylock file" in result.out


def test_pylock_mutually_exclusive_with_deps(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            deps = ["pytest"]
            pylock = "pylock.toml"
            """,
            "pylock.toml": PYLOCK_TOML,
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert "cannot use both 'deps' and 'pylock'" in result.out


def test_pylock_recreate_on_change(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            pylock = "pylock.toml"
            """,
            "pylock.toml": PYLOCK_TOML,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")
    result.assert_success()

    (project.path / "pylock.toml").write_text(
        dedent("""\
            lock-version = "1.0"
            created-by = "test-tool"

            [[packages]]
            name = "alpha"
            version = "1.0.0"

            [[packages.wheels]]
            url = "https://files.example.com/alpha-1.0.0-py3-none-any.whl"

            [packages.wheels.hashes]
            sha256 = "abc123"
        """),
    )
    execute_calls.reset_mock()
    result_second = project.run("r", "-e", "py")
    result_second.assert_success()
    assert "py: recreate env because" in result_second.out


def test_pylock_no_reinstall_on_rerun(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            pylock = "pylock.toml"
            """,
            "pylock.toml": PYLOCK_TOML,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")
    result.assert_success()
    assert len(execute_calls.call_args_list) == 1

    execute_calls.reset_mock()
    result_second = project.run("r", "-e", "py")
    result_second.assert_success()
    assert not execute_calls.call_args_list


def test_pylock_filters_by_extras(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            pylock = "pylock.toml"
            extras = ["docs"]
            """,
            "pylock.toml": dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"
                extras = ["docs", "test"]

                [[packages]]
                name = "alpha"
                version = "1.0.0"

                [[packages.wheels]]
                url = "https://files.example.com/alpha-1.0.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "abc"

                [[packages]]
                name = "sphinx"
                version = "7.0.0"
                marker = "'docs' in extras"

                [[packages.wheels]]
                url = "https://files.example.com/sphinx-7.0.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "def"

                [[packages]]
                name = "pytest"
                version = "8.0.0"
                marker = "'test' in extras"

                [[packages.wheels]]
                url = "https://files.example.com/pytest-8.0.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "ghi"
            """),
        },
    )
    project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()
    assert (project.path / ".tox" / "py" / "pylock.txt").read_text() == "alpha==1.0.0\nsphinx==7.0.0"


def test_pylock_filters_by_dependency_groups(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            pylock = "pylock.toml"
            dependency_groups = ["dev"]
            """,
            "pylock.toml": dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"
                dependency-groups = ["dev", "ci"]

                [[packages]]
                name = "alpha"
                version = "1.0.0"

                [[packages.wheels]]
                url = "https://files.example.com/alpha-1.0.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "abc"

                [[packages]]
                name = "ruff"
                version = "0.5.0"
                marker = "'dev' in dependency_groups"

                [[packages.wheels]]
                url = "https://files.example.com/ruff-0.5.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "def"

                [[packages]]
                name = "coverage"
                version = "7.0.0"
                marker = "'ci' in dependency_groups"

                [[packages.wheels]]
                url = "https://files.example.com/coverage-7.0.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "ghi"
            """),
        },
    )
    project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()
    assert (project.path / ".tox" / "py" / "pylock.txt").read_text() == "alpha==1.0.0\nruff==0.5.0"


def test_pylock_filters_by_platform_marker(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            pylock = "pylock.toml"
            """,
            "pylock.toml": dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "alpha"
                version = "1.0.0"

                [[packages.wheels]]
                url = "https://files.example.com/alpha-1.0.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "abc"

                [[packages]]
                name = "linuxonly"
                version = "1.0.0"
                marker = "sys_platform == 'linux'"

                [[packages.wheels]]
                url = "https://files.example.com/linuxonly-1.0.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "def"

                [[packages]]
                name = "winonly"
                version = "1.0.0"
                marker = "sys_platform == 'win32'"

                [[packages.wheels]]
                url = "https://files.example.com/winonly-1.0.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "ghi"
            """),
        },
    )
    project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()
    content = (project.path / ".tox" / "py" / "pylock.txt").read_text()
    assert "alpha==1.0.0" in content
    if sys.platform == "win32":
        assert "winonly==1.0.0" in content
        assert "linuxonly" not in content
    elif sys.platform == "linux":
        assert "linuxonly==1.0.0" in content
        assert "winonly" not in content
    else:
        assert "linuxonly" not in content
        assert "winonly" not in content


def test_pylock_requirements(tmp_path: Path) -> None:
    lock_file = tmp_path / "pylock.toml"
    lock_file.write_text(PYLOCK_TOML)
    pylock = Pylock(path=lock_file)

    result = [str(r) for r in pylock.requirements()]

    assert result == ["alpha==1.0.0", "beta==2.0.0"]


def test_pylock_requirements_filters_extras(tmp_path: Path) -> None:
    lock_file = tmp_path / "pylock.toml"
    lock_file.write_text(
        dedent("""\
        lock-version = "1.0"
        created-by = "test-tool"
        extras = ["docs"]

        [[packages]]
        name = "alpha"
        version = "1.0.0"

        [[packages.wheels]]
        url = "https://files.example.com/alpha-1.0.0-py3-none-any.whl"

        [packages.wheels.hashes]
        sha256 = "abc"

        [[packages]]
        name = "sphinx"
        version = "7.0.0"
        marker = "'docs' in extras"

        [[packages.wheels]]
        url = "https://files.example.com/sphinx-7.0.0-py3-none-any.whl"

        [packages.wheels.hashes]
        sha256 = "def"
    """),
    )

    with_extras = [str(r) for r in Pylock(path=lock_file, extras=frozenset({"docs"})).requirements()]
    assert with_extras == ["alpha==1.0.0", "sphinx==7.0.0"]

    without_extras = [str(r) for r in Pylock(path=lock_file).requirements()]
    assert without_extras == ["alpha==1.0.0"]


def test_pylock_requirements_invalid(tmp_path: Path) -> None:
    lock_file = tmp_path / "pylock.toml"
    lock_file.write_text(
        dedent("""\
        lock-version = "1.0"
        created-by = "test-tool"
        packages = "not-a-list"
    """),
    )
    pylock = Pylock(path=lock_file)

    with pytest.raises(Fail, match="invalid pylock file"):
        pylock.requirements()


@pytest.mark.slow
@pytest.mark.integration
def test_pylock_install_integration(
    tox_project: ToxProjectCreator,
    enable_pip_pypi_access: str | None,  # noqa: ARG001
) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            pylock = "pylock.toml"
            commands = [["python", "-c", "import six; print(six.__version__)"]]
            """,
            "pylock.toml": dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "six"
                version = "1.17.0"

                [[packages.wheels]]
                url = "https://files.pythonhosted.org/packages/b7/ce/149a00dd41f10bc29e5921b496af8b574d8413afcd5e30f4c7e48bb4cb87/six-1.17.0-py2.py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8ez91c67d35ad282f3"
            """),
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_success()
    assert "1.17.0" in result.out
