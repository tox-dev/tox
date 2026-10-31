from __future__ import annotations

import json
import re
import sys
import tomllib
from copy import copy
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Final

import pytest
from packaging.markers import default_environment
from python_discovery import PythonInfo

from tox.tox_env.errors import Fail
from tox.tox_env.python.api import PythonInfo as ToxPythonInfo
from tox.tox_env.python.pylock import Pylock

if TYPE_CHECKING:
    from collections.abc import Sequence
    from unittest.mock import MagicMock

    from packaging.markers import Environment
    from pytest_mock import MockerFixture

    from tox.pytest import ToxProject, ToxProjectCreator, ToxRunOutcome

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


@pytest.mark.parametrize(
    "files",
    [
        pytest.param(
            {
                "tox.toml": '[env_run_base]\nskip_install = true\npylock = "pylock.toml"',
                "pylock.toml": PYLOCK_TOML,
            },
            id="tox-root",
        ),
        pytest.param(
            {
                "tox.toml": 'package_root = "sub"\n[env_run_base]\nskip_install = true\npylock = "pylock.toml"',
                "sub": {"pylock.toml": PYLOCK_TOML},
            },
            id="package-root",
        ),
    ],
)
def test_pylock_install(tox_project: ToxProjectCreator, files: dict[str, str | dict[str, str]]) -> None:
    project: Final[ToxProject] = tox_project(files)
    execute_calls: Final[MagicMock] = project.patch_execute()
    project.run("r", "-e", "py").assert_success()

    req_file: Final[str] = str(project.path / ".tox" / "py" / "pylock.txt")
    found_calls: Final[list[tuple[str, str, Sequence[str]]]] = [
        (call[0][0].conf.name, call[0][3].run_id, call[0][3].cmd) for call in execute_calls.call_args_list
    ]
    assert found_calls == [
        ("py", "install_pylock", ["python", "-I", "-m", "pip", "install", "--no-deps", "-r", req_file]),
    ]
    assert (
        project.path / ".tox" / "py" / "pylock.txt"
    ).read_text() == "alpha==1.0.0 --hash=sha256:abc123\nbeta==2.0.0 --hash=sha256:def456"


def test_dependency_groups_use_package_root_without_package_env(tox_project: ToxProjectCreator) -> None:
    project: Final[ToxProject] = tox_project(
        {
            "tox.toml": """
            package_root = "sub"

            [env_run_base]
            skip_install = true
            dependency_groups = ["dev"]
            """,
            "sub": {"pyproject.toml": '[dependency-groups]\ndev = ["six"]\n'},
        },
    )
    execute_calls: Final[MagicMock] = project.patch_execute()
    project.run("r", "-e", "py").assert_success()

    found_calls: Final[list[tuple[str, str]]] = [
        (call[0][0].conf.name, call[0][3].run_id) for call in execute_calls.call_args_list
    ]
    assert found_calls == [("py", "install_dependency-groups")]
    assert "six" in execute_calls.call_args_list[0][0][3].cmd


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


@pytest.mark.parametrize(
    "deps",
    [pytest.param('"-i https://pypi.org/simple"', id="default-index"), pytest.param('"# a note"', id="comment")],
)
def test_pylock_allows_deps_that_install_nothing(tox_project: ToxProjectCreator, deps: str) -> None:
    project = tox_project(
        {
            "tox.toml": f"""
            [env_run_base]
            skip_install = true
            deps = [{deps}]
            pylock = "pylock.toml"
            """,
            "pylock.toml": PYLOCK_TOML,
        },
    )
    result = project.run("c", "-e", "py", "-k", "pylock")

    result.assert_success()
    assert result.out == "[testenv:py]\npylock = pylock.toml\n"


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


@pytest.mark.parametrize(
    ("tox_setting", "header", "packages", "expected"),
    [
        pytest.param(
            'extras = ["docs"]',
            'extras = ["docs", "test"]\n',
            [
                ("alpha", "1.0.0", "abc", None),
                ("sphinx", "7.0.0", "def", "'docs' in extras"),
                ("pytest", "8.0.0", "ghi", "'test' in extras"),
            ],
            "alpha==1.0.0 --hash=sha256:abc\nsphinx==7.0.0 --hash=sha256:def",
            id="extras",
        ),
        pytest.param(
            'dependency_groups = ["dev"]',
            'dependency-groups = ["dev", "ci"]\n',
            [
                ("alpha", "1.0.0", "abc", None),
                ("ruff", "0.5.0", "def", "'dev' in dependency_groups"),
                ("coverage", "7.0.0", "ghi", "'ci' in dependency_groups"),
            ],
            "alpha==1.0.0 --hash=sha256:abc\nruff==0.5.0 --hash=sha256:def",
            id="dependency-groups",
        ),
        pytest.param(
            "",
            'dependency-groups = ["dev"]\ndefault-groups = ["default"]\n',
            [
                ("six", "1.17.0", "abc", "'default' in dependency_groups"),
                ("ruff", "0.5.0", "def", "'dev' in dependency_groups"),
            ],
            "six==1.17.0 --hash=sha256:abc",
            id="default-groups-when-none-selected",
        ),
        pytest.param(
            'dependency_groups = ["dev"]',
            'dependency-groups = ["dev"]\ndefault-groups = ["default"]\n',
            [
                ("six", "1.17.0", "abc", "'default' in dependency_groups"),
                ("ruff", "0.5.0", "def", "'dev' in dependency_groups"),
            ],
            "ruff==0.5.0 --hash=sha256:def",
            id="selected-group-excludes-default",
        ),
    ],
)
def test_pylock_filters_by_selected_group(
    tox_project: ToxProjectCreator,
    tox_setting: str,
    header: str,
    packages: list[tuple[str, str, str, str | None]],
    expected: str,
) -> None:
    project = tox_project(
        {
            "tox.toml": f"""
            [env_run_base]
            skip_install = true
            pylock = "pylock.toml"
            {tox_setting}
            """,
            "pylock.toml": _render_pylock(header, packages),
        },
    )
    project.patch_execute()
    result = project.run("r", "-e", "py")

    result.assert_success()
    assert (project.path / ".tox" / "py" / "pylock.txt").read_text() == expected


def _render_pylock(header: str, packages: list[tuple[str, str, str, str | None]]) -> str:
    blocks = [f'lock-version = "1.0"\ncreated-by = "test-tool"\n{header}']
    for name, version, sha256, marker in packages:
        marker_line = f'marker = "{marker}"\n' if marker else ""
        blocks.append(
            f'[[packages]]\nname = "{name}"\nversion = "{version}"\n{marker_line}\n'
            f'[[packages.wheels]]\nurl = "https://files.example.com/{name}-{version}-py3-none-any.whl"\n\n'
            f'[packages.wheels.hashes]\nsha256 = "{sha256}"\n'
        )
    return "\n".join(blocks)


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

    assert pylock.install_lines() == ["alpha==1.0.0 --hash=sha256:abc123", "beta==2.0.0 --hash=sha256:def456"]


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

    with_extras = Pylock(path=lock_file, extras=frozenset({"docs"})).install_lines()
    assert with_extras == ["alpha==1.0.0 --hash=sha256:abc", "sphinx==7.0.0 --hash=sha256:def"]

    without_extras = Pylock(path=lock_file).install_lines()
    assert without_extras == ["alpha==1.0.0 --hash=sha256:abc"]


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
        pylock.install_lines()


@pytest.mark.parametrize(
    ("content", "cause"),
    [
        pytest.param(b'lock-version = "1.0"\n\n[[packages]\nname = "alpha"\n', tomllib.TOMLDecodeError, id="toml"),
        pytest.param(b"\xff", UnicodeDecodeError, id="utf8"),
    ],
)
def test_pylock_requirements_invalid_file(
    tmp_path: Path, content: bytes, cause: type[tomllib.TOMLDecodeError | UnicodeDecodeError]
) -> None:
    lock_file: Final[Path] = tmp_path / "pylock.toml"
    lock_file.write_bytes(content)

    with pytest.raises(Fail, match=rf"invalid pylock file {re.escape(str(lock_file))}:") as caught:
        Pylock(path=lock_file).install_lines()

    assert isinstance(caught.value.__cause__, cause)
    assert str(caught.value.__cause__) in str(caught.value)


def test_pylock_requirements_with_utf8_bom(tmp_path: Path) -> None:
    lock_file: Final[Path] = tmp_path / "pylock.toml"
    lock_file.write_bytes(b"\xef\xbb\xbf" + PYLOCK_TOML.encode())

    assert Pylock(path=lock_file).install_lines() == [
        "alpha==1.0.0 --hash=sha256:abc123",
        "beta==2.0.0 --hash=sha256:def456",
    ]


@pytest.mark.slow
@pytest.mark.integration
def test_pylock_install_integration(
    tox_project: ToxProjectCreator,
    enable_pip_pypi_access: str | None,  # ruff:ignore[unused-function-argument]
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
                sha256 = "4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274"
            """),
        },
    )
    result = project.run("r", "-e", "py")

    result.assert_success()
    assert "1.17.0" in result.out


@pytest.fixture
def pylock_run_base() -> str:
    return dedent("""\
        [env_run_base]
        skip_install = true
        pylock = "pylock.toml"
    """)


@pytest.mark.parametrize(
    ("lock", "expected"),
    [
        pytest.param(
            dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "example-pkg"
                version = "1.0"
                requires-python = "<3.9"

                [[packages.wheels]]
                url = "https://files.example.com/example_pkg-1.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "aaa111"

                [[packages]]
                name = "example-pkg"
                version = "2.0"
                requires-python = ">=3.9"

                [[packages.wheels]]
                url = "https://files.example.com/example_pkg-2.0-py3-none-any.whl"

                [packages.wheels.hashes]
                sha256 = "bbb222"
            """),
            "example-pkg==2.0 --hash=sha256:bbb222",
            id="requires-python selects the matching entry",
        ),
        pytest.param(
            dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "my-local-pkg"

                [packages.directory]
                path = "sub/my_local_pkg"
            """),
            "my-local-pkg @ {project_uri}/sub/my_local_pkg",
            id="directory installs from the locked path",
        ),
        pytest.param(
            dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "my-local-pkg"

                [packages.directory]
                path = "."
                editable = true
            """),
            "-e {project_uri}",
            id="editable directory installs with -e",
        ),
        pytest.param(
            dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "my-vcs-pkg"

                [packages.vcs]
                type = "git"
                url = "https://example.com/repo.git"
                commit-id = "abc123"
            """),
            "my-vcs-pkg @ git+https://example.com/repo.git@abc123",
            id="vcs installs from the locked commit",
        ),
        pytest.param(
            dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "my-vcs-pkg"

                [packages.vcs]
                type = "git"
                url = "https://example.com/repo.git"
                commit-id = "abc123"
                requested-revision = "branch name"
            """),
            "my-vcs-pkg @ git+https://example.com/repo.git@abc123",
            id="requested revision is informational",
        ),
        pytest.param(
            dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "my-vcs-pkg"

                [packages.vcs]
                type = "git"
                url = "https://example.com/repo.git"
                commit-id = "abc123"
                subdirectory = ""
            """),
            "my-vcs-pkg @ git+https://example.com/repo.git@abc123#subdirectory=",
            id="empty subdirectory stays valid",
        ),
        pytest.param(
            dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "my-archive-pkg"
                version = "1.0"

                [packages.archive]
                url = "https://example.com/my-archive-pkg-1.0.tar.gz"

                [packages.archive.hashes]
                sha256 = "abc123"
            """),
            "my-archive-pkg @ https://example.com/my-archive-pkg-1.0.tar.gz --hash=sha256:abc123",
            id="archive installs from the locked url with its hash",
        ),
        pytest.param(
            dedent("""\
                lock-version = "1.0"
                created-by = "test-tool"

                [[packages]]
                name = "my-archive-pkg"
                version = "1.0"

                [packages.archive]
                url = "https://example.com/my-archive-pkg-1.0.tar.gz"
                subdirectory = ""

                [packages.archive.hashes]
                sha256 = "abc123"
            """),
            "my-archive-pkg @ https://example.com/my-archive-pkg-1.0.tar.gz#subdirectory= --hash=sha256:abc123",
            id="empty archive subdirectory stays valid",
        ),
    ],
)
def test_pylock_locked_sources_install_as_locked(
    tox_project: ToxProjectCreator, pylock_run_base: str, lock: str, expected: str
) -> None:
    project: Final[ToxProject] = tox_project({"tox.toml": pylock_run_base, "pylock.toml": lock})
    project.patch_execute()

    project.run("r", "-e", "py").assert_success()
    assert (project.path / ".tox" / "py" / "pylock.txt").read_text() == expected.format(
        project_uri=project.path.as_uri()
    )


def test_pylock_reinstall_on_resolution_env_change(tox_project: ToxProjectCreator, pylock_run_base: str) -> None:
    """Changing a pip resolution environment variable invalidates the pylock install cache."""
    project = tox_project({"tox.toml": pylock_run_base, "pylock.toml": PYLOCK_TOML})
    execute_calls = project.patch_execute()
    result = project.run("r", "-e", "py")
    result.assert_success()
    assert len(execute_calls.call_args_list) == 1

    (project.path / "tox.toml").write_text(
        f'{pylock_run_base}set_env = {{ PIP_INDEX_URL = "https://mirror.invalid/simple" }}\n'
    )
    execute_calls.reset_mock()
    result_second = project.run("r", "-e", "py")

    result_second.assert_success()
    assert len(execute_calls.call_args_list) == 1


def test_pylock_install_lines_utf8_bom(tmp_path: Path) -> None:
    pylock = tmp_path / "pylock.toml"
    pylock.write_bytes(b"\xef\xbb\xbf" + PYLOCK_TOML.encode("utf-8"))

    lines = Pylock(path=pylock).install_lines()

    assert lines == ["alpha==1.0.0 --hash=sha256:abc123", "beta==2.0.0 --hash=sha256:def456"]


@pytest.mark.parametrize(
    ("source_table", "field_label"),
    [
        pytest.param(
            '[[packages.wheels]]\nurl = "https://x/alpha-1.0.0-py3-none-any.whl"\n'
            'hashes = { sha256 = "abc\\n--index-url file:///evil/simple" }\n',
            "sha256 hash",
            id="hash-newline",
        ),
        pytest.param(
            '[[packages.wheels]]\nurl = "https://x/alpha-1.0.0-py3-none-any.whl"\n'
            'hashes = { sha256 = "abc --hash=sha256:def" }\n',
            "sha256 hash",
            id="hash-space",
        ),
        pytest.param(
            '[[packages.wheels]]\nurl = "https://x/alpha-1.0.0-py3-none-any.whl"\nhashes = { "sha 256" = "abc" }\n',
            "hash algorithm",
            id="hash-algorithm-space",
        ),
        pytest.param(
            '[packages.archive]\nurl = "https://x/a.tar.gz\\r\\n-e file:///evil"\nhashes = { sha256 = "abc" }\n',
            "archive url",
            id="archive-url-newline",
        ),
        pytest.param(
            '[packages.archive]\nurl = "https://x/a.tar.gz"\nsubdirectory = "sub\\u2028--pre"\n'
            'hashes = { sha256 = "abc" }\n',
            "archive subdirectory",
            id="archive-subdirectory-line-separator",
        ),
        pytest.param(
            '[packages.vcs]\ntype = "git"\nurl = "https://x/a.git"\ncommit-id = "abc\\n--index-url file:///evil"\n',
            "vcs commit-id",
            id="vcs-commit-newline",
        ),
        pytest.param(
            '[packages.vcs]\ntype = "git"\nurl = "https://x/a.git"\ncommit-id = ""\nrequested-revision = "main"\n',
            "vcs commit-id",
            id="empty vcs commit",
        ),
    ],
)
def test_pylock_rejects_field_injecting_requirements_syntax(
    tmp_path: Path, source_table: str, field_label: str
) -> None:
    lock_file: Final[Path] = tmp_path / "pylock.toml"
    lock_file.write_text(
        'lock-version = "1.0"\ncreated-by = "test-tool"\n\n[[packages]]\n'
        f'name = "alpha"\nversion = "1.0.0"\n\n{source_table}',
        encoding="utf-8",
    )

    with pytest.raises(
        Fail, match=rf"invalid pylock file .*'alpha' {field_label} .* no whitespace or control characters"
    ):
        Pylock(path=lock_file).install_lines()


def test_pylock_uses_complete_target_marker_environment(
    tox_project: ToxProjectCreator, pylock_run_base: str, mocker: MockerFixture
) -> None:
    environment: Final[Environment] = {
        **default_environment(),
        "implementation_name": "target-implementation",
        "implementation_version": "0.0.1",
        "os_name": "target-os",
        "platform_machine": "target-machine",
        "platform_release": "target-release",
        "platform_system": "target-system",
        "platform_version": "target-platform-version",
        "python_full_version": "0.0.1",
        "platform_python_implementation": "TargetPython",
        "python_version": "0.0",
        "sys_platform": "target-platform",
    }
    assert dict(environment).items().isdisjoint(default_environment().items())
    mocker.patch.object(
        PythonInfo, "marker_environment", create=True, new_callable=mocker.PropertyMock, return_value=environment
    )
    packages: Final[str] = "\n\n".join(
        f'[[packages]]\nname = "marker-{index}"\nversion = "1.0"\n'
        f"marker = {json.dumps(f'{key} == {json.dumps(value)}')}\n\n"
        f'[[packages.wheels]]\nurl = "https://example.invalid/marker_{index}-1.0-py3-none-any.whl"\n\n'
        f'[packages.wheels.hashes]\nsha256 = "{index:03d}"'
        for index, (key, value) in enumerate(environment.items())
    )
    project: Final[ToxProject] = tox_project({
        "tox.toml": pylock_run_base,
        "pylock.toml": f'lock-version = "1.0"\ncreated-by = "test-tool"\n\n{packages}\n',
    })
    project.patch_execute()

    project.run("r", "-e", "py").assert_success()

    assert _pylock_txt(project) == "\n".join(
        sorted(f"marker-{index}==1.0 --hash=sha256:{index:03d}" for index in range(len(environment)))
    )


def _pylock_txt(project: ToxProject) -> str:
    return (project.path / ".tox" / "py" / "pylock.txt").read_text()


def test_pylock_uses_discovery_without_marker_probe(pylock_install_project: ToxProject, mocker: MockerFixture) -> None:
    discovery: Final[MagicMock] = mocker.patch("tox.tox_env.python.runner.DiscoveredPythonInfo", autospec=True)
    discovery.from_exe.side_effect = AssertionError("extra probe")

    pylock_install_project.run("r", "-e", "py").assert_success()
    assert _pylock_txt(pylock_install_project) == "alpha==1.0.0 --hash=sha256:abc123\nbeta==2.0.0 --hash=sha256:def456"


@pytest.fixture
def pylock_install_project(tox_project: ToxProjectCreator, pylock_run_base: str) -> ToxProject:
    project: Final[ToxProject] = tox_project({"tox.toml": pylock_run_base, "pylock.toml": PYLOCK_TOML})
    project.patch_execute()
    return project


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({}, id="missing-keys"),
        pytest.param([], id="non-object"),
        pytest.param({**default_environment(), "os_name": 1}, id="non-string-value"),
    ],
)
def test_pylock_rejects_invalid_discovery_markers(
    pylock_install_project: ToxProject, mocker: MockerFixture, values: dict[str, str | int] | list[str]
) -> None:
    mocker.patch.object(
        PythonInfo, "marker_environment", create=True, new_callable=mocker.PropertyMock, return_value=values
    )

    result: Final[ToxRunOutcome] = pylock_install_project.run("r", "-e", "py")

    result.assert_failed()
    assert "incomplete or invalid data" in result.out


def test_pylock_markers_use_target_interpreter(pylock_target_project: ToxProject, mocker: MockerFixture) -> None:
    mocker.patch.object(
        PythonInfo,
        "marker_environment",
        create=True,
        new_callable=mocker.PropertyMock,
        return_value={
            **default_environment(),
            "implementation_version": "0.0.1",
            "platform_release": "target-release",
        },
    )
    result: Final[ToxRunOutcome] = pylock_target_project.run("r", "-e", "py")

    result.assert_success()
    assert _pylock_txt(pylock_target_project) == "target==1.0 --hash=sha256:abc"


@pytest.fixture
def pylock_target_project(tox_project: ToxProjectCreator, pylock_run_base: str, target_marker_lock: str) -> ToxProject:
    project: Final[ToxProject] = tox_project({"tox.toml": pylock_run_base, "pylock.toml": target_marker_lock})
    project.patch_execute()
    return project


@pytest.fixture
def target_marker_lock() -> str:
    return dedent("""\
        lock-version = "1.0"
        created-by = "test-tool"

        [[packages]]
        name = "target"
        version = "1.0"
        marker = "implementation_version == '0.0.1' and platform_release == 'target-release'"

        [[packages.wheels]]
        url = "https://files.example.com/target-1.0-py3-none-any.whl"

        [packages.wheels.hashes]
        sha256 = "abc"

        [[packages]]
        name = "host"
        version = "2.0"
        marker = "implementation_version != '0.0.1' or platform_release != 'target-release'"

        [[packages.wheels]]
        url = "https://files.example.com/host-2.0-py3-none-any.whl"

        [packages.wheels.hashes]
        sha256 = "def"
    """)


@pytest.mark.usefixtures("without_discovery_markers")
def test_pylock_discovery_fallback_uses_real_interpreter(
    tox_project: ToxProjectCreator, pylock_run_base: str, mocker: MockerFixture
) -> None:
    project: Final[ToxProject] = tox_project({
        "tox.toml": f'{pylock_run_base}set_env = {{ PYTHONPATH = "{{tox_root}}" }}\n',
        "sitecustomize.py": dedent("""\
            import platform
            import sys

            if sys.prefix != sys.base_prefix:
                platform.release = lambda: "target-release"
        """),
        "pylock.toml": PYLOCK_TOML.replace(
            'version = "1.0.0"', 'version = "1.0.0"\nmarker = "platform_release == \'target-release\'"'
        ),
    })
    project.patch_execute()
    discovery: Final[MagicMock] = mocker.patch(
        "tox.tox_env.python.runner.DiscoveredPythonInfo", spec=PythonInfo, wraps=PythonInfo
    )
    project.run("r", "-e", "py").assert_success()

    discovery.from_exe.assert_called_once()
    assert Path(discovery.from_exe.call_args.args[0]).is_relative_to(project.path / ".tox" / "py")
    assert _pylock_txt(project) == "alpha==1.0.0 --hash=sha256:abc123\nbeta==2.0.0 --hash=sha256:def456"


@pytest.mark.usefixtures("without_discovery_markers")
def test_pylock_discovery_fallback_uses_target_interpreter(
    pylock_target_project: ToxProject,
    mocker: MockerFixture,
) -> None:
    interpreter: Final[PythonInfo | None] = copy(PythonInfo.from_exe(sys.executable))
    assert interpreter is not None
    interpreter.marker_environment = {
        **default_environment(),
        "implementation_version": "0.0.1",
        "platform_release": "target-release",
    }
    discovery: Final[MagicMock] = mocker.patch("tox.tox_env.python.runner.DiscoveredPythonInfo", autospec=True)
    discovery.from_exe.return_value = interpreter

    pylock_target_project.run("r", "-e", "py").assert_success()

    assert _pylock_txt(pylock_target_project) == "target==1.0 --hash=sha256:abc"


@pytest.fixture
def without_discovery_markers(mocker: MockerFixture) -> None:
    mocker.patch.object(
        ToxPythonInfo, "marker_environment", create=True, new_callable=mocker.PropertyMock, return_value=None
    )


@pytest.mark.usefixtures("without_discovery_markers")
def test_pylock_discovery_fallback_failure(pylock_install_project: ToxProject, mocker: MockerFixture) -> None:
    discovery: Final[MagicMock] = mocker.patch("tox.tox_env.python.runner.DiscoveredPythonInfo", autospec=True)
    discovery.from_exe.return_value = None

    result: Final[ToxRunOutcome] = pylock_install_project.run("r", "-e", "py")

    result.assert_failed()
    assert "failed to determine the marker environment" in result.out


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({}, id="missing-keys"),
        pytest.param([], id="non-object"),
        pytest.param({**default_environment(), "os_name": 1}, id="non-string-value"),
    ],
)
@pytest.mark.usefixtures("without_discovery_markers")
def test_pylock_discovery_fallback_invalid(
    pylock_install_project: ToxProject, mocker: MockerFixture, values: dict[str, str | int] | list[str]
) -> None:
    interpreter: Final[PythonInfo | None] = copy(PythonInfo.from_exe(sys.executable))
    assert interpreter is not None
    mocker.patch.object(interpreter, "marker_environment", values)
    discovery: Final[MagicMock] = mocker.patch("tox.tox_env.python.runner.DiscoveredPythonInfo", autospec=True)
    discovery.from_exe.return_value = interpreter

    result: Final[ToxRunOutcome] = pylock_install_project.run("r", "-e", "py")

    result.assert_failed()
    assert "incomplete or invalid data" in result.out


def test_pylock_pinned_virtualenv_uses_discovered_markers(
    tox_project: ToxProjectCreator, pylock_run_base: str, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        PythonInfo,
        "marker_environment",
        create=True,
        new_callable=mocker.PropertyMock,
        return_value={**default_environment(), "platform_release": "target-release"},
    )
    mocker.patch(
        "tox.tox_env.python.virtual_env.subprocess_adapter.ensure_bootstrap",
        autospec=True,
        return_value=Path(sys.executable),
    )
    project: Final[ToxProject] = tox_project({
        "tox.toml": f'{pylock_run_base}virtualenv_spec = "virtualenv"\n',
        "pylock.toml": dedent("""\
            lock-version = "1.0"
            created-by = "test-tool"

            [[packages]]
            name = "target"
            version = "1.0"
            marker = "platform_release == 'target-release'"

            [[packages.wheels]]
            url = "https://files.example.com/target-1.0-py3-none-any.whl"

            [packages.wheels.hashes]
            sha256 = "abc"
        """),
    })
    project.patch_execute()

    project.run("r", "-e", "py").assert_success()

    assert _pylock_txt(project) == "target==1.0 --hash=sha256:abc"
