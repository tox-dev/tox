from __future__ import annotations

import sys
import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from packaging.requirements import Requirement

from tox.journal import EnvJournal
from tox.tox_env.package import PathPackage
from tox.tox_env.python.extras import resolve_extras_static
from tox.tox_env.python.runner import PythonRun
from tox.tox_env.python.virtual_env.package.cmd_builder import VenvCmdBuilder

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_deps_config_path_req(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.ini": "[testenv:py]\ndeps =-rpath.txt\n -r {toxinidir}{/}path2.txt\n pytest",
            "path.txt": "alpha",
            "path2.txt": "beta",
        },
    )
    result = project.run("c", "-e", "py")
    result.assert_success()
    deps = result.state.conf.get_env("py")["deps"]
    assert deps.unroll() == ([], ["alpha", "beta", "pytest"])
    assert deps.as_root_args == ["pytest", "-r", "path.txt", "-r", str(project.path / "path2.txt")]
    assert str(deps) == f"-r {project.path / 'tox.ini'}"


def test_journal_package_empty() -> None:
    journal = EnvJournal(enabled=True, name="a")

    PythonRun._handle_journal_package(journal, [])  # noqa: SLF001

    content = journal.content
    assert content == {}


def test_journal_one_wheel_file(tmp_path: Path) -> None:
    wheel = tmp_path / "a.whl"
    wheel.write_bytes(b"magical")
    journal = EnvJournal(enabled=True, name="a")

    PythonRun._handle_journal_package(journal, [PathPackage(wheel)])  # noqa: SLF001

    content = journal.content
    assert content == {
        "installpkg": {
            "basename": "a.whl",
            "sha256": "0ce2d4c7087733c06b1087b28db95e114d7caeb515b841c6cdec8960cf884654",
            "type": "file",
        },
    }


def test_journal_multiple_wheel_file(tmp_path: Path) -> None:
    wheel_1 = tmp_path / "a.whl"
    wheel_1.write_bytes(b"magical")
    wheel_2 = tmp_path / "b.whl"
    wheel_2.write_bytes(b"magic")
    journal = EnvJournal(enabled=True, name="a")

    PythonRun._handle_journal_package(journal, [PathPackage(wheel_1), PathPackage(wheel_2)])  # noqa: SLF001

    content = journal.content
    assert content == {
        "installpkg": [
            {
                "basename": "a.whl",
                "sha256": "0ce2d4c7087733c06b1087b28db95e114d7caeb515b841c6cdec8960cf884654",
                "type": "file",
            },
            {
                "basename": "b.whl",
                "sha256": "3be7a505483c0050243c5cbad4700da13925aa4137a55e9e33efd8bc4d05850f",
                "type": "file",
            },
        ],
    }


def test_journal_package_dir(tmp_path: Path) -> None:
    journal = EnvJournal(enabled=True, name="a")

    PythonRun._handle_journal_package(journal, [PathPackage(tmp_path)])  # noqa: SLF001

    content = journal.content
    assert content == {
        "installpkg": {
            "basename": tmp_path.name,
            "type": "dir",
        },
    }


def test_package_temp_dir_view(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=wheel"})
    result = project.run(
        "r",
        "-vv",
        "-e",
        "py",
        "--root",
        str(demo_pkg_inline),
        "--workdir",
        str(project.path / ".tox"),
    )
    result.assert_success()
    wheel_name = "demo_pkg_inline-1.0.0-py3-none-any.whl"
    session_path = Path(".tmp") / "package" / "1" / wheel_name
    msg = f" D package {session_path} copied to {Path('.pkg') / 'dist' / wheel_name} ({project.path / '.tox'}) "
    assert msg in result.out
    assert f" D delete package {project.path / '.tox' / session_path}" in result.out


@pytest.mark.parametrize(
    ("extra", "used_extra"),
    [
        ("d_oc", "d-oc"),
        ("d-oc", "d-oc"),
        ("d.oc", "d-oc"),
    ],
)
def test_extras_are_normalized(
    tox_project: ToxProjectCreator,
    demo_pkg_inline: Path,
    extra: str,
    used_extra: str,
) -> None:
    project = tox_project({"tox.ini": f"[testenv]\nextras={extra}"})
    result = project.run(
        "c",
        "-e",
        "py",
        "--root",
        str(demo_pkg_inline),
        "--workdir",
        str(project.path / ".tox"),
        "-k",
        "extras",
    )
    result.assert_success()
    assert result.out == f"[testenv:py]\nextras = {used_extra}\n"


@pytest.mark.parametrize(
    ("config", "cli", "expected"),
    [("false", "true", True), ("true", "false", False), ("false", "config", False), ("true", "config", True)],
)
def test_config_skip_missing_interpreters(
    tox_project: ToxProjectCreator,
    config: str,
    cli: str,
    expected: bool,
) -> None:
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    project = tox_project({"tox.ini": f"[tox]\nenvlist=py4,py{py_ver}\nskip_missing_interpreters={config}"})
    result = project.run(f"--skip-missing-interpreters={cli}")
    assert result.code == (0 if expected else 1)


SYS_PY_VER = "".join(str(i) for i in sys.version_info[0:2]) + (
    "t" if sysconfig.get_config_var("Py_GIL_DISABLED") == 1 else ""
)


@pytest.mark.parametrize(
    ("skip", "env", "retcode"),
    [
        ("true", f"py{SYS_PY_VER}", 0),
        ("false", f"py{SYS_PY_VER}", 0),
        ("true", "py31", 1),
        ("false", "py31", 1),
        ("true", None, 0),
        ("false", None, 1),
    ],
)
def test_skip_missing_interpreters_specified_env(
    tox_project: ToxProjectCreator,
    skip: str,
    env: str | None,
    retcode: int,
) -> None:
    project = tox_project({"tox.ini": f"[tox]\nenvlist=py31,py{SYS_PY_VER}\n[testenv]\nusedevelop=true"})
    args = [f"--skip-missing-interpreters={skip}"]
    if env:
        args += ["-e", env]
    result = project.run(*args)
    assert result.code == retcode


def test_per_env_skip_missing_interpreters_override_global_false(tox_project: ToxProjectCreator) -> None:
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    project = tox_project({
        "tox.ini": (
            f"[tox]\nenvlist=py31,py{py_ver}\nskip_missing_interpreters=false\n"
            "[testenv:py31]\nskip_missing_interpreters=true\n"
        ),
    })
    result = project.run()
    assert result.code == 0


def test_per_env_skip_missing_interpreters_override_global_true(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.ini": (
            "[tox]\nenvlist=py31\nskip_missing_interpreters=true\n[testenv:py31]\nskip_missing_interpreters=false\n"
        ),
    })
    result = project.run()
    assert result.code == 1


def test_per_env_skip_missing_interpreters_cli_overrides_env(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.ini": (
            "[tox]\nenvlist=py31\nskip_missing_interpreters=false\n[testenv:py31]\nskip_missing_interpreters=false\n"
        ),
    })
    result = project.run("--skip-missing-interpreters=true")
    assert result.code == 1


def test_per_env_skip_missing_interpreters_unset_falls_to_global(tox_project: ToxProjectCreator) -> None:
    py_ver = ".".join(str(i) for i in sys.version_info[0:2])
    project = tox_project({
        "tox.ini": f"[tox]\nenvlist=py31,py{py_ver}\nskip_missing_interpreters=true\n",
    })
    result = project.run()
    assert result.code == 0


def test_per_env_skip_missing_interpreters_toml(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": """
            env_list = ["py31"]
            skip_missing_interpreters = true
            [env.py31]
            skip_missing_interpreters = false
        """,
    })
    result = project.run()
    assert result.code == 1


def test_dependency_groups_single(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            [dependency-groups]
            test = [
              "furo>=2024.8.6",
              "sphinx>=8.0.2",
            ]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        ("py", "install_dependency-groups", ["python", "-I", "-m", "pip", "install", "furo>=2024.8.6", "sphinx>=8.0.2"])
    ]


def test_dependency_groups_extras(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            [project]
            name = "demo_pkg"

            [project.optional-dependencies]
            extra1 = ["extra_pkg>=1.0"]
            [dependency-groups]
            test = [
              "furo>=2024.8.6",
              "sphinx>=8.0.2",
              "demo_pkg[extra1]",
            ]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        (
            "py",
            "install_dependency-groups",
            ["python", "-I", "-m", "pip", "install", "extra_pkg>=1.0", "furo>=2024.8.6", "sphinx>=8.0.2"],
        )
    ]


def test_dependency_groups_nested_extras(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            [project]
            name = "demo_pkg"

            [project.optional-dependencies]
            extra1 = ["extra_pkg>=1.0"]
            extra2 = ["demo_pkg[extra1]"]
            [dependency-groups]
            test = [
              "furo>=2024.8.6",
              "sphinx>=8.0.2",
              "demo_pkg[extra2]",
            ]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        (
            "py",
            "install_dependency-groups",
            ["python", "-I", "-m", "pip", "install", "extra_pkg>=1.0", "furo>=2024.8.6", "sphinx>=8.0.2"],
        )
    ]


def test_dependency_groups_double_extras(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            [project]
            name = "demo_pkg"

            [project.optional-dependencies]
            extra1 = ["extra_pkg>=1.0"]
            extra2 = ["extra_pkg2>=1.0"]
            [dependency-groups]
            test = [
              "furo>=2024.8.6",
              "sphinx>=8.0.2",
              "demo_pkg[extra1,extra2]",
            ]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        (
            "py",
            "install_dependency-groups",
            [
                "python",
                "-I",
                "-m",
                "pip",
                "install",
                "extra_pkg2>=1.0",
                "extra_pkg>=1.0",
                "furo>=2024.8.6",
                "sphinx>=8.0.2",
            ],
        )
    ]


def test_dependency_groups_duplicate_extras(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            [project]
            name = "demo_pkg"

            [project.optional-dependencies]
            extra1 = ["extra_pkg>=1.0"]
            extra2 = ["extra_pkg2>=1.0", "demo_pkg[extra1]"]
            [dependency-groups]
            test = [
              "furo>=2024.8.6",
              "sphinx>=8.0.2",
              "demo_pkg[extra1,extra2]",
            ]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        (
            "py",
            "install_dependency-groups",
            [
                "python",
                "-I",
                "-m",
                "pip",
                "install",
                "extra_pkg2>=1.0",
                "extra_pkg>=1.0",
                "furo>=2024.8.6",
                "sphinx>=8.0.2",
            ],
        )
    ]


def test_dependency_groups_multiple(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test", "type"]
            """,
            "pyproject.toml": """
            [dependency-groups]
            test = [
              "furo>=2024.8.6",
              "sphinx>=8.0.2",
            ]
            type = [
              "furo>=2024.8.6",
              "mypy>=1",
            ]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        (
            "py",
            "install_dependency-groups",
            ["python", "-I", "-m", "pip", "install", "furo>=2024.8.6", "mypy>=1", "sphinx>=8.0.2"],
        )
    ]


def test_dependency_groups_include(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test", "type"]
            """,
            "pyproject.toml": """
            [dependency-groups]
            test = [
              "furo>=2024.8.6",
              "sphinx>=8.0.2",
            ]
            "friendly.Bard" = [
                "bard-song",
            ]
            type = [
              {include-group = "test"},
              {include-group = "FrIeNdLy-._.-bArD"},
              "mypy>=1",
            ]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        (
            "py",
            "install_dependency-groups",
            ["python", "-I", "-m", "pip", "install", "bard-song", "furo>=2024.8.6", "mypy>=1", "sphinx>=8.0.2"],
        )
    ]


def test_dependency_groups_not_table(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            dependency-groups = 1
            """,
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert "py: failed with dependency-groups is int instead of table\n" in result.out


def test_dependency_groups_missing(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["type"]
            """,
            "pyproject.toml": """
            [dependency-groups]
            test = [
              "furo>=2024.8.6",
            ]
            """,
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert "py: failed with dependency group 'type' not found\n" in result.out


def test_dependency_groups_not_list(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["tEst"]
            """,
            "pyproject.toml": """
            [dependency-groups]
            teSt = 1
            """,
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert "py: failed with dependency group 'teSt' is not a list\n" in result.out


def test_dependency_groups_bad_requirement(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            [dependency-groups]
            test = [ "whatever --" ]
            """,
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert (
        "py: failed with 'whatever --' is not valid requirement due to "
        "Expected semicolon (after name with no version specifier) or end\n    whatever --\n             ^\n"
        in result.out
    )


def test_dependency_groups_bad_entry(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            [dependency-groups]
            test = [ { magic = "ok" } ]
            """,
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert "py: failed with invalid dependency group item: {'magic': 'ok'}\n" in result.out


def test_dependency_groups_cyclic(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            skip_install = true
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            [dependency-groups]
            teSt = [ { include-group = "type" } ]
            tyPe = [ { include-group = "test" } ]
            """,
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert "py: failed with Cyclic dependency group include: 'teSt' -> ('teSt', 'tyPe')\n" in result.out


def test_deps_only_static(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            package = "deps-only"
            """,
            "pyproject.toml": """
            [project]
            name = "demo"
            version = "1.0"
            dependencies = ["httpx>=0.27", "rich>=13"]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        ("py", "install_package_deps", ["python", "-I", "-m", "pip", "install", "httpx>=0.27", "rich>=13"])
    ]


def test_deps_only_with_extras(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            package = "deps-only"
            extras = ["docs"]
            """,
            "pyproject.toml": """
            [project]
            name = "demo"
            version = "1.0"
            dependencies = ["httpx>=0.27"]
            [project.optional-dependencies]
            docs = ["sphinx>=7", "furo"]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        (
            "py",
            "install_package_deps",
            ["python", "-I", "-m", "pip", "install", "furo", "httpx>=0.27", "sphinx>=7"],
        )
    ]


def test_deps_only_multiple_extras(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            package = "deps-only"
            extras = ["docs", "testing"]
            """,
            "pyproject.toml": """
            [project]
            name = "demo"
            version = "1.0"
            dependencies = ["httpx>=0.27"]
            [project.optional-dependencies]
            docs = ["sphinx>=7"]
            testing = ["pytest>=8"]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        (
            "py",
            "install_package_deps",
            ["python", "-I", "-m", "pip", "install", "httpx>=0.27", "pytest>=8", "sphinx>=7"],
        )
    ]


def test_deps_only_with_deps(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            package = "deps-only"
            deps = ["coverage[toml]"]
            """,
            "pyproject.toml": """
            [project]
            name = "demo"
            version = "1.0"
            dependencies = ["httpx>=0.27"]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        ("py", "install_deps", ["python", "-I", "-m", "pip", "install", "coverage[toml]"]),
        ("py", "install_package_deps", ["python", "-I", "-m", "pip", "install", "httpx>=0.27"]),
    ]


def test_deps_only_with_dependency_groups(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            package = "deps-only"
            dependency_groups = ["test"]
            """,
            "pyproject.toml": """
            [project]
            name = "demo"
            version = "1.0"
            dependencies = ["httpx>=0.27"]
            [dependency-groups]
            test = ["pytest>=8"]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [
        ("py", "install_dependency-groups", ["python", "-I", "-m", "pip", "install", "pytest>=8"]),
        ("py", "install_package_deps", ["python", "-I", "-m", "pip", "install", "httpx>=0.27"]),
    ]


def test_deps_only_no_extras(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            package = "deps-only"
            """,
            "pyproject.toml": """
            [project]
            name = "demo"
            version = "1.0"
            dependencies = ["httpx>=0.27"]
            [project.optional-dependencies]
            docs = ["sphinx>=7"]
            """,
        },
    )
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id, i[0][3].cmd) for i in execute_calls.call_args_list]
    assert found_calls == [("py", "install_package_deps", ["python", "-I", "-m", "pip", "install", "httpx>=0.27"])]


def test_deps_only_unknown_extra(tox_project: ToxProjectCreator) -> None:
    project = tox_project(
        {
            "tox.toml": """
            [env_run_base]
            package = "deps-only"
            extras = ["nonexistent"]
            """,
            "pyproject.toml": """
            [project]
            name = "demo"
            version = "1.0"
            dependencies = ["httpx>=0.27"]
            [project.optional-dependencies]
            docs = ["sphinx>=7"]
            """,
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_failed()
    assert "extras not found for package demo: nonexistent (available: docs)" in result.out


def test_deps_only_fallback_no_project_table(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    project = tox_project({"tox.toml": '[env_run_base]\npackage = "deps-only"\n'})
    execute_calls = project.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = project.run("r", "-e", "py", "--root", str(demo_pkg_inline), "--workdir", str(project.path / ".tox"))

    result.assert_success()

    found_calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    pkg_calls = [c for c in found_calls if c[0] == "py" and "package_deps" in c[1]]
    assert pkg_calls == []


def test_resolve_extras_static_no_pyproject(tmp_path: Path) -> None:
    assert resolve_extras_static(tmp_path, set()) is None


def test_resolve_extras_static_no_project_table(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]')
    assert resolve_extras_static(tmp_path, set()) is None


def test_resolve_extras_static_dynamic_deps(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "1.0"\ndynamic = ["dependencies"]')
    assert resolve_extras_static(tmp_path, set()) is None


def test_resolve_extras_static_dynamic_optional_deps(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "1.0"\ndynamic = ["optional-dependencies"]'
    )
    assert resolve_extras_static(tmp_path, {"docs"}) is None


def test_cmd_builder_load_deps_for_env() -> None:
    builder = MagicMock(spec=VenvCmdBuilder)
    mock_meta_env = MagicMock()
    mock_meta_env.load_deps_for_env.return_value = [Requirement("requests>=2")]
    builder._sdist_meta_tox_env = mock_meta_env  # noqa: SLF001
    mock_conf = MagicMock()

    result = VenvCmdBuilder.load_deps_for_env(builder, mock_conf)

    assert result == [Requirement("requests>=2")]
    mock_meta_env.load_deps_for_env.assert_called_once_with(mock_conf)
