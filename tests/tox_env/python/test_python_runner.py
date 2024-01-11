from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tox.journal import EnvJournal
from tox.tox_env.package import PathPackage
from tox.tox_env.python.runner import PythonRun

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
    msg = f" D package {session_path} links to {Path('.pkg') / 'dist' / wheel_name} ({project.path / '.tox'}) "
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
    result = project.run("c", "-e", "py", "--root", str(demo_pkg_inline), "-k", "extras")
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
    assert result.code == (0 if expected else -1)


@pytest.mark.parametrize(
    ("skip", "env", "retcode"),
    [
        ("true", f"py{''.join(str(i) for i in sys.version_info[0:2])}", 0),
        ("false", f"py{''.join(str(i) for i in sys.version_info[0:2])}", 0),
        ("true", "py31", -1),
        ("false", "py31", 1),
        ("true", None, 0),
        ("false", None, -1),
    ],
)
def test_skip_missing_interpreters_specified_env(
    tox_project: ToxProjectCreator,
    skip: str,
    env: str | None,
    retcode: int,
) -> None:
    py_ver = "".join(str(i) for i in sys.version_info[0:2])
    project = tox_project({"tox.ini": f"[tox]\nenvlist=py31,py{py_ver}\n[testenv]\nusedevelop=true"})
    args = [f"--skip-missing-interpreters={skip}"]
    if env:
        args += ["-e", env]
    result = project.run(*args)
    assert result.code == retcode
