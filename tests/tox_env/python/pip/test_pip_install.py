from __future__ import annotations

import json
import os
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import MagicMock, Mock
from zipfile import ZipFile

import pytest
from packaging.requirements import Requirement

from tox.report import HandledError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from tox.pytest import CaptureFixture, SubRequest, ToxProject, ToxProjectCreator, ToxRunOutcome


@pytest.mark.parametrize("arg", [object, [object]])
def test_pip_install_bad_type(tox_project: ToxProjectCreator, capfd: CaptureFixture, arg: Any) -> None:
    proj = tox_project({"tox.ini": ""})
    result = proj.run("l")
    result.assert_success()
    pip = result.state.envs["py"].installer

    with pytest.raises(SystemExit, match="1"):
        pip.install(arg, "section", "type")
    out, err = capfd.readouterr()
    assert not err
    assert f"pip cannot install {object!r}" in out


def test_pip_install_empty_list(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": ""})
    result = proj.run("l")
    result.assert_success()

    pip = result.state.envs["py"].installer
    execute_calls = proj.patch_execute(Mock())
    pip.install([], "section", "type")
    assert execute_calls.call_count == 0


def test_pip_install_empty_command_error(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\ninstall_command="})
    result = proj.run("l")
    pip = result.state.envs["py"].installer

    with pytest.raises(
        HandledError, match=r"failed to load py\.install_command: attempting to parse '' into a command"
    ):
        pip.install([Requirement("name")], "section", "type")


@pytest.mark.parametrize(
    ("key", "use"),
    [
        pytest.param(
            "install_command",
            lambda pip: pip.install([Requirement("name")], "section", "type"),
            id="install_command",
        ),
        pytest.param("list_dependencies_command", lambda pip: pip.installed(), id="list_dependencies_command"),
    ],
)
def test_pip_toml_empty_command_error(tox_project: ToxProjectCreator, key: str, use: Callable[[Any], object]) -> None:
    proj = tox_project({"tox.toml": f"[env.py]\n{key} = []"})
    pip = proj.run("l").state.envs["py"].installer

    with pytest.raises(HandledError, match=rf"failed to load py\.{key}: attempting to parse \[\] into a command"):
        use(pip)


def test_pip_install_flags_only_error(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv:py]\ndeps=-i a"})
    result = proj.run("r")
    result.assert_failed()
    assert "no dependencies for tox env py within deps" in result.out


@pytest.mark.parametrize(
    ("content", "error"),
    [
        pytest.param(
            "-r requirements.txt",
            "only constraints files or URLs can be provided",
            id="requirements file are not constraints files",
        ),
        pytest.param(
            "-c constraints.txt",
            "only constraints files or URLs can be provided",
            id="constraints flag is unnecessary",
        ),
        pytest.param("tox==4.23.0", "Could not open requirements file", id="constraints must be specified in a file"),
    ],
)
def test_pip_install_invalid_constraints_error(tox_project: ToxProjectCreator, content: str, error: str) -> None:
    proj = tox_project({"tox.ini": f"[testenv:py]\nconstraints={content}\nskip_install=true"})

    result = proj.run("r")
    result.assert_failed()
    assert error in result.out


def test_pip_install_new_flag_recreates(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv:py]\ndeps=a\nskip_install=true"})
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")
    result.assert_success()

    (proj.path / "tox.ini").write_text("[testenv:py]\ndeps=a\n -i i\nskip_install=true")
    result_second = proj.run("r")
    result_second.assert_success()
    assert "recreate env because changed install flag(s) added index_url=['i']" in result_second.out
    assert "install_deps> python -I -m pip install a -i i" in result_second.out


def test_pip_install_no_binary_on_separate_lines(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.ini": "[testenv:py]\ndeps=\n --no-binary six\n --no-binary packaging\n a\nskip_install=true"
    })
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")

    result.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == [
        "python",
        "-I",
        "-m",
        "pip",
        "install",
        "a",
        "--no-binary",
        "packaging,six",
    ]


@pytest.mark.parametrize(
    "files",
    [
        pytest.param(
            {"tox.toml": '[env_run_base]\npackage="skip"\ndeps=["a=={env:VERSION}", "-c c.txt"]'}, id="toml-list"
        ),
        pytest.param({"tox.toml": '[env_run_base]\npackage="skip"\ndeps="a=={env:VERSION}\\n-c c.txt"'}, id="toml-str"),
        pytest.param(
            {
                "tox.toml": '[env_run_base]\npackage="skip"\ndeps=["a=={env:VERSION}"]\n'
                '[env.py]\ndeps=["{[env_run_base]deps}", "-c c.txt"]'
            },
            id="toml-reference",
        ),
        pytest.param(
            {"tox.toml": '[env_run_base]\npackage="skip"\ndeps=["{env:MISSING:a=={env:VERSION}}"]'},
            id="nested-default",
        ),
        pytest.param({"tox.ini": "[testenv]\npackage=skip\ndeps=\n a=={env:VERSION}\n -c c.txt"}, id="ini"),
    ],
)
@pytest.mark.parametrize(
    ("version", "message"),
    [
        pytest.param("1\n--pre", "cannot add a line break", id="line-feed"),
        pytest.param("1\u2028--pre", "cannot add a line break", id="line-separator"),
        pytest.param("1 \\", "cannot end a line with a backslash", id="line-continuation"),
    ],
)
def test_pip_install_deps_substitution_cannot_add_line(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch, files: dict[str, str], version: str, message: str
) -> None:
    monkeypatch.setenv("VERSION", version)
    monkeypatch.delenv("MISSING", raising=False)
    project: Final = tox_project({**files, "c.txt": ""})
    execute_calls: Final = project.patch_execute(lambda request: 0 if "install" in request.run_id else None)

    result: Final = project.run("r", "-e", "py")

    result.assert_failed()
    assert message in result.out
    assert execute_calls.call_count == 0


@pytest.mark.parametrize(
    "files",
    [
        pytest.param({"tox.toml": '[env_run_base]\npackage="skip"\ndeps="a"\nconstraints=["{env:C}.txt"]'}, id="toml"),
        pytest.param({"tox.ini": "[testenv]\npackage=skip\ndeps=a\nconstraints={env:C}.txt"}, id="ini"),
    ],
)
def test_pip_install_constraints_substitution_cannot_add_line(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch, files: dict[str, str]
) -> None:
    monkeypatch.setenv("C", "c.txt\nd")
    project: Final = tox_project({**files, "c.txt": "", "d.txt": ""})
    execute_calls: Final = project.patch_execute(lambda request: 0 if "install" in request.run_id else None)

    result: Final = project.run("r", "-e", "py")

    result.assert_failed()
    assert "a substitution within a requirement cannot add a line break" in result.out
    assert execute_calls.call_count == 0


@pytest.mark.parametrize(
    "files",
    [
        pytest.param(
            {"tox.toml": '[env_run_base]\npackage="skip"\ndeps=["--extra-index-url https://host/{env:PART}", "pkg"]'},
            id="toml",
        ),
        pytest.param(
            {"tox.ini": "[testenv]\npackage=skip\ndeps=\n --extra-index-url https://host/{env:PART}\n pkg"},
            id="ini",
        ),
    ],
)
def test_pip_install_deps_substitution_cannot_add_option(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch, files: dict[str, str]
) -> None:
    monkeypatch.setenv("PART", "value --index-url=https://other/simple")
    project: Final[ToxProject] = tox_project(files)
    execute_calls: Final[MagicMock] = project.patch_execute(lambda request: 0 if "install" in request.run_id else None)

    result: Final[ToxRunOutcome] = project.run("r", "-e", "py")

    result.assert_failed()
    assert "a requirement substitution cannot change pip options" in result.out
    assert execute_calls.call_count == 0


@pytest.mark.parametrize(
    "files",
    [
        pytest.param(
            {"tox.toml": '[env_run_base]\npackage="skip"\nconstraints=["constraints/{env:PART}.txt"]'},
            id="toml",
        ),
        pytest.param(
            {"tox.ini": "[testenv]\npackage=skip\nconstraints=constraints/{env:PART}.txt"},
            id="ini",
        ),
    ],
)
def test_pip_install_constraints_substitution_cannot_add_option(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch, files: dict[str, str]
) -> None:
    monkeypatch.setenv("PART", "stable.txt --index-url=https://other/simple #")
    result: Final[ToxRunOutcome] = tox_project(files).run("c", "-e", "py", "-k", "constraints")

    result.assert_failed()
    assert "a requirement substitution cannot change pip options" in result.out


def test_pip_install_deps_substitution_keeps_static_options(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PART", "cpu")
    result: Final[ToxRunOutcome] = tox_project({
        "tox.toml": '[env_run_base]\npackage="skip"\ndeps=["--index-url https://host/{env:PART} '
        '--extra-index-url https://mirror/simple", "pkg"]',
    }).run("c", "-e", "py", "-k", "deps")

    result.assert_success()
    assert "  -i https://host/cpu\n  --extra-index-url https://mirror/simple\n" in result.out


def test_pip_install_deps_substitution_cannot_replace_static_option(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PART", "cpu --index-url https://other/simple #")
    result: Final[ToxRunOutcome] = tox_project({
        "tox.toml": '[env_run_base]\npackage="skip"\ndeps=["--index-url https://host/{env:PART} '
        '--index-url https://trusted/simple", "pkg"]',
    }).run("c", "-e", "py", "-k", "deps")

    result.assert_failed()
    assert "a requirement substitution cannot change pip options" in result.out


@pytest.mark.timeout(5)
def test_pip_install_deps_recursive_fan_out_stops(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PART", "{env:PART}" * 100)
    result: Final[ToxRunOutcome] = tox_project({
        "tox.ini": "[testenv]\npackage=skip\ndeps=--index-url https://example.invalid/{env:PART}",
    }).run("c", "-e", "py", "-k", "deps")

    result.assert_success()
    assert result.out.count("Could not expand") == 1
    assert 100 < result.out.count("{env:PART}") < 100_000


@pytest.mark.parametrize(
    ("filename", "content", "namespace"),
    [
        pytest.param("tox.toml", '[env_run_base]\npackage="skip"\ndeps=["a"]', "env_run_base", id="toml"),
        pytest.param("tox.ini", "[testenv]\npackage=skip\ndeps=a", "testenv", id="ini"),
    ],
)
def test_pip_install_deps_override_cannot_add_line(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content: str,
    namespace: str,
) -> None:
    monkeypatch.setenv("VERSION", "1\n--pre")
    result: Final = tox_project({filename: content}).run(
        "c", "-e", "py", "-k", "deps", "-x", f"{namespace}.deps+=a=={{env:VERSION}}"
    )
    result.assert_failed()
    assert "a substitution within a requirement cannot add a line break" in result.out


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("a\n--pre", id="line-break"),
        pytest.param("a\\", id="line-continuation"),
    ],
)
@pytest.mark.skipif(os.name == "nt", reason="Windows file names cannot contain line breaks or trailing backslashes")
def test_pip_install_globbed_requirement_cannot_add_line(tox_project: ToxProjectCreator, name: str) -> None:
    project: Final = tox_project({
        "tox.toml": '[env_run_base]\npackage="skip"\ndeps=[{replace="glob",pattern="wheelhouse/*",extend=true}]',
    })
    wheelhouse: Final = project.path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / name).write_text("")
    result: Final = project.run("c", "-e", "py", "-k", "deps")
    result.assert_failed()
    assert "a globbed requirement path cannot contain a line break or end in a backslash" in result.out


def test_pip_install_substitution_keeps_internal_backslash(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEP_PATH", ".\\")
    result: Final = tox_project({"tox.ini": "[testenv]\npackage=skip\ndeps=-r {env:DEP_PATH}a.txt"}).run(
        "c", "-e", "py", "-k", "deps"
    )

    result.assert_success()
    assert "-r .\\a.txt" in result.out


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        pytest.param({"tox.toml": '[env_run_base]\npackage="skip"\ndeps=["{env:EXTRA_DEPS}"]'}, ["a", "b"], id="toml"),
        pytest.param(
            {"tox.toml": '[env_run_base]\npackage="skip"\ndeps="{env:EXTRA_DEPS}\\u2028c"'},
            ["a", "b", "c"],
            id="toml-unicode-separator",
        ),
        pytest.param(
            {"tox.ini": "[testenv]\npackage=skip\ndeps=\n a\u2028{env:EXTRA_DEPS}"},
            ["a", "b"],
            id="ini-unicode-separator",
        ),
    ],
)
def test_pip_install_whole_substitution_can_supply_requirements(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch, files: dict[str, str], expected: list[str]
) -> None:
    monkeypatch.setenv("EXTRA_DEPS", "a\nb")
    result: Final = tox_project(files).run("c", "-e", "py", "-k", "deps")
    result.assert_success()
    assert result.env_conf("py")["deps"].as_root_args == expected


def test_pip_install_path(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv:py]\ndeps=.{/}a\nskip_install=true"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", f".{os.sep}a"]


@pytest.mark.parametrize(
    ("content", "args"),
    [
        pytest.param("-e .", ["-e", "."], id="short editable"),
        pytest.param("--editable .", ["-e", "."], id="long editable"),
        pytest.param(
            "git+ssh://git.example.com/MyProject\\#egg=MyProject",
            ["git+ssh://git.example.com/MyProject#egg=MyProject"],
            id="vcs with ssh",
        ),
        pytest.param(
            "git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709\\#egg=MyProject",
            ["git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709#egg=MyProject"],
            id="vcs with commit hash pin",
        ),
    ],
)
def test_pip_install_req_file_req_like(tox_project: ToxProjectCreator, content: str, args: list[str]) -> None:
    proj = tox_project({"tox.ini": f"[testenv:py]\ndeps={content}\nskip_install=true"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")
    result.assert_success()

    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", *args]

    # check that adding a new dependency correctly finds the previous one
    (proj.path / "tox.ini").write_text(f"[testenv:py]\ndeps={content}\n a\nskip_install=true")
    execute_calls.reset_mock()

    result_second = proj.run("r")
    result_second.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a", *args]


def test_pip_req_path(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv:py]\ndeps=.\nskip_install=true"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")
    result.assert_success()

    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "."]


def test_deps_remove_recreate(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip\ndeps=wheel\n setuptools"})
    execute_calls = proj.patch_execute(lambda request: 0)  # ruff:ignore[unused-lambda-argument]
    result_first = proj.run("r")
    result_first.assert_success()
    assert execute_calls.call_count == 1

    (proj.path / "tox.ini").write_text("[testenv]\npackage=skip\ndeps=setuptools\n")
    result_second = proj.run("r")
    result_second.assert_success()
    assert "py: recreate env because requirements removed: wheel" in result_second.out, result_second.out
    assert execute_calls.call_count == 2


def test_pkg_dep_remove_recreate(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    build = (demo_pkg_inline / "build.py").read_text()
    build_with_dep = build.replace("Summary: UNKNOWN\n", "Summary: UNKNOWN\n        Requires-Dist: wheel\n")
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": (demo_pkg_inline / "pyproject.toml").read_text(),
            "build.py": build_with_dep,
        },
    )
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result_first = proj.run("r")
    result_first.assert_success()
    run_ids = [i[0][3].run_id for i in execute_calls.call_args_list]
    assert run_ids == [
        "_optional_hooks",
        "get_requires_for_build_wheel",
        "build_wheel",
        "install_package_deps",
        "install_package",
        "_exit",
    ]
    execute_calls.reset_mock()

    (proj.path / "build.py").write_text(build)
    result_second = proj.run("r")
    result_second.assert_success()
    assert "py: recreate env because dependencies removed: wheel" in result_second.out, result_second.out
    run_ids = [i[0][3].run_id for i in execute_calls.call_args_list]
    assert run_ids == ["_optional_hooks", "get_requires_for_build_wheel", "build_wheel", "install_package", "_exit"]


@pytest.mark.parametrize(
    ("requires", "forced"),
    [
        pytest.param("wheel", "wheel==0.41.0", id="same-spelling"),
        pytest.param("wheel", "Wheel==0.41.0", id="forced-case"),
        pytest.param("Demo_Dep>=2", "demo-dep==1", id="metadata-unnormalized"),
    ],
)
def test_force_dep_applies_to_package_deps(
    tox_project: ToxProjectCreator, demo_pkg_inline: Path, requires: str, forced: str
) -> None:
    build = (demo_pkg_inline / "build.py").read_text()
    build_with_dep = build.replace("Summary: UNKNOWN\n", f"Summary: UNKNOWN\n        Requires-Dist: {requires}\n")
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": (demo_pkg_inline / "pyproject.toml").read_text(),
            "build.py": build_with_dep,
        },
    )
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    proj.run("le", "-e", "py", "--force-dep", forced).assert_success()

    calls = [i[0][3].cmd[5:] for i in execute_calls.call_args_list if i[0][3].run_id == "install_package_deps"]
    assert calls == [[forced]]


def test_pkg_env_dep_remove_recreate(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    toml = (demo_pkg_inline / "pyproject.toml").read_text()
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": toml.replace("requires = []", 'requires = ["setuptools"]'),
            "build.py": (demo_pkg_inline / "build.py").read_text(),
        },
    )
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result_first = proj.run("r")
    result_first.assert_success()
    run_ids = [i[0][3].run_id for i in execute_calls.call_args_list]
    assert run_ids == [
        "install_requires",
        "_optional_hooks",
        "get_requires_for_build_wheel",
        "build_wheel",
        "install_package",
        "_exit",
    ]
    execute_calls.reset_mock()

    (proj.path / "pyproject.toml").write_text(toml)
    result_second = proj.run("r")
    result_second.assert_success()
    assert ".pkg: recreate env because dependencies removed: setuptools" in result_second.out, result_second.out
    run_ids = [i[0][3].run_id for i in execute_calls.call_args_list]
    assert run_ids == ["_optional_hooks", "get_requires_for_build_wheel", "build_wheel", "install_package", "_exit"]


def test_pip_install_requirements_file_deps(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\ndeps=-r r.txt\nskip_install=true", "r.txt": "a"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "-r", "r.txt"]

    # check that adding a new dependency correctly finds the previous one
    (proj.path / "tox.ini").write_text("[testenv]\ndeps=-r r.txt\n b\nskip_install=true")
    execute_calls.reset_mock()
    result_second = proj.run("r")
    result_second.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "b", "-r", "r.txt"]

    # if the requirement file changes recreate
    (proj.path / "r.txt").write_text("c\nd")
    execute_calls.reset_mock()
    result_third = proj.run("r")
    result_third.assert_success()
    assert "py: recreate env because requirements removed: a" in result_third.out, result_third.out
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "b", "-r", "r.txt"]


@pytest.fixture
def secret_requirements_project(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> ToxProject:
    monkeypatch.setenv("PYPI_TOKEN", "magic-one")
    return tox_project({
        "tox.ini": "[testenv]\ndeps=-r r.txt\nconstraints=c.txt\nskip_install=true",
        "r.txt": "-i https://ci:${PYPI_TOKEN}@host/simple\nhttps://ci:${PYPI_TOKEN}@host/a.whl",
        "c.txt": "https://ci:${PYPI_TOKEN}@host/b.whl",
    })


def test_pip_install_requirements_file_secret_cache(secret_requirements_project: ToxProject) -> None:
    secret_requirements_project.patch_execute(lambda request: 0 if "install" in request.run_id else None)

    result: Final = secret_requirements_project.run("r")

    result.assert_success()
    cache: Final = (secret_requirements_project.path / ".tox" / "py" / ".tox-info.json").read_text()
    assert "magic-one" not in cache
    assert "https://ci:*********@host/" in cache


def test_pip_install_requirements_file_token_rotation(
    secret_requirements_project: ToxProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    execute_calls: Final = secret_requirements_project.patch_execute(
        lambda request: 0 if "install" in request.run_id else None
    )
    secret_requirements_project.run("r").assert_success()

    execute_calls.reset_mock()
    monkeypatch.setenv("PYPI_TOKEN", "magic-two")
    secret_requirements_project.run("r").assert_success()

    assert execute_calls.call_count == 0


def test_pip_install_legacy_secret_cache_migration(
    secret_requirements_project: ToxProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret_requirements_project.patch_execute(lambda request: 0 if "install" in request.run_id else None)
    secret_requirements_project.run("r").assert_success()
    cache: Final = secret_requirements_project.path / ".tox" / "py" / ".tox-info.json"
    old_cache: Final = json.loads(cache.read_text())
    old_cache["PythonRun"]["deps"].pop("redaction_format")
    cache.write_text(json.dumps(old_cache).replace("*********", "legacy-secret"))
    monkeypatch.setenv("PYPI_TOKEN", "magic-two")

    result: Final = secret_requirements_project.run("r")

    result.assert_success()
    assert "recreate env because install cache format changed" in result.out
    assert "legacy-secret" not in result.out
    assert "legacy-secret" not in cache.read_text()


@pytest.mark.parametrize("name", [pytest.param("r.txt", id="requirements"), pytest.param("c.txt", id="constraints")])
def test_pip_install_secret_recreate_warning(secret_requirements_project: ToxProject, name: str) -> None:
    secret_requirements_project.patch_execute(lambda request: 0 if "install" in request.run_id else None)
    secret_requirements_project.run("r").assert_success()
    path: Final = secret_requirements_project.path / name
    path.write_text(path.read_text().replace("@host", "@other"))

    result: Final = secret_requirements_project.run("r")

    result.assert_success()
    assert "recreate env because " in result.out
    assert "https://ci:*********@host/" in result.out
    assert "magic-one" not in result.out


def test_constrain_package_deps_keeps_secret_env_var(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    project: Final = tox_project({
        "tox.ini": "[testenv]\ndeps=-r r.txt\nskip_install=true\nconstrain_package_deps=true",
        "r.txt": "https://ci:${PYPI_TOKEN}@host/a.whl\n-c c.txt",
        "c.txt": "b<2",
    })
    project.patch_execute(lambda request: 0 if "install" in request.run_id else None)
    monkeypatch.setenv("PYPI_TOKEN", "magic")

    result: Final = project.run("r")

    result.assert_success()
    assert (project.path / ".tox" / "py" / "constraints.txt").read_text() == "https://ci:magic@host/a.whl\nb<2"


@pytest.mark.parametrize(
    ("field", "value", "nested", "expected"),
    [
        pytest.param("deps", "-r requirements.txt", "-r missing-${PYPI_TOKEN}.txt", "missing-*****.txt", id="deps"),
        pytest.param(
            "constraints", "requirements.txt", "-c missing-${PYPI_TOKEN}.txt", "missing-*****.txt", id="constraints"
        ),
        pytest.param("deps", "-r requirements.txt", "-r file://${PYPI_TOKEN}/base.txt", "file://*****", id="file-url"),
    ],
)
def test_pip_install_missing_nested_file_redacts_secret(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
    nested: str,
    expected: str,
) -> None:
    monkeypatch.setenv("PYPI_TOKEN", "magic")
    project: Final = tox_project({
        "tox.ini": f"[testenv]\npackage=skip\n{field}={value}",
        "requirements.txt": nested,
    })

    result: Final = project.run("r")

    result.assert_failed()
    assert expected in result.out
    assert "magic" not in result.out


@pytest.fixture(params=[True, False])
def use_constraints_opt(request: SubRequest) -> bool:
    return bool(request.param)


def test_pip_install_constraint_file_create_change(tox_project: ToxProjectCreator, use_constraints_opt: bool) -> None:
    if use_constraints_opt:
        toxini = "[testenv]\ndeps=a\nconstraints=c.txt\nskip_install=true"
    else:
        toxini = "[testenv]\ndeps=-c c.txt\n a\nskip_install=true"
    proj = tox_project({"tox.ini": toxini, "c.txt": "b"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a", "-c", "c.txt"]

    # a new dependency triggers an install
    if use_constraints_opt:
        toxini = "[testenv]\ndeps=a\n d\nconstraints=c.txt\nskip_install=true"
    else:
        toxini = "[testenv]\ndeps=-c c.txt\n a\n d\nskip_install=true"
    (proj.path / "tox.ini").write_text(toxini)
    execute_calls.reset_mock()
    result_second = proj.run("r")
    result_second.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a", "d", "-c", "c.txt"]

    # a new constraints triggers a recreate
    (proj.path / "c.txt").write_text("")
    execute_calls.reset_mock()
    result_third = proj.run("r")
    result_third.assert_success()
    assert "py: recreate env because changed constraint(s) removed b" in result_third.out, result_third.out
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a", "d", "-c", "c.txt"]


def test_pip_install_constraint_file_new(tox_project: ToxProjectCreator, use_constraints_opt: bool) -> None:
    proj = tox_project({"tox.ini": "[testenv]\ndeps=a\nskip_install=true"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a"]

    if use_constraints_opt:
        toxini = "[testenv]\ndeps=a\nconstraints=c.txt\nskip_install=true"
    else:
        toxini = "[testenv]\ndeps=a\n -c c.txt\nskip_install=true"
    (proj.path / "c.txt").write_text("a")
    (proj.path / "tox.ini").write_text(toxini)
    execute_calls.reset_mock()
    result_second = proj.run("r")
    result_second.assert_success()
    assert "py: recreate env because changed constraint(s) added a" in result_second.out, result_second.out
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a", "-c", "c.txt"]


@pytest.fixture(params=[True, False])
def constrain_package_deps(request: SubRequest) -> bool:
    return bool(request.param)


@pytest.fixture(params=[True, False])
def use_frozen_constraints(request: SubRequest) -> bool:
    return bool(request.param)


@pytest.mark.parametrize("mode", ["run", "no-capture", "exec"])
@pytest.mark.parametrize("compatible", [True, False])
def test_frozen_constraints_preserve_pins(tox_project: ToxProjectCreator, mode: str, compatible: bool) -> None:
    project = tox_project({
        "tox.ini": """
        [testenv]
        deps = lib==1.0
        constrain_package_deps = true
        use_frozen_constraints = true
        set_env =
            PIP_NO_INDEX = 1
            PIP_FIND_LINKS = {tox_root}/wheels
        commands = python -c "from importlib.metadata import version; assert version('helper') == '1.0'"
        """,
    })
    wheels = project.path / "wheels"
    wheels.mkdir()
    packages = [("lib", "1.0", ""), ("lib", "2.0", ""), ("helper", "2.0", "lib>=2"), ("app", "1.0", "helper")]
    if compatible:
        packages.append(("helper", "1.0", ""))
    for name, version, requires in packages:
        info = f"{name}-{version}.dist-info"
        metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
        if requires:
            metadata += f"Requires-Dist: {requires}\n"
        with ZipFile(wheels / f"{name}-{version}-py3-none-any.whl", "w") as wheel:
            wheel.writestr(f"{info}/METADATA", metadata)
            wheel.writestr(f"{info}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
            wheel.writestr(f"{info}/RECORD", "")

    if mode == "exec":
        project.run("exec", "-e", "py", "--", "python", "--version").assert_success()
    flags = ["--no-capture"] if mode == "no-capture" else []
    result = project.run("run", "-e", "py", "--installpkg", str(wheels / "app-1.0-py3-none-any.whl"), *flags)
    if compatible:
        result.assert_success()
    else:
        result.assert_failed()
        assert "ResolutionImpossible" in result.out + result.err
    constraints = project.path / ".tox" / "py" / "constraints.txt"
    assert "lib==1.0" in constraints.read_text().splitlines()
    project.run(
        "exec",
        "-e",
        "py",
        "--",
        "python",
        "-c",
        "from importlib.metadata import version; assert version('lib') == '1.0'",
    ).assert_success()


@pytest.fixture(
    params=[
        "explicit",
        "requirements",
        "constraints",
        "explicit+requirements",
        "requirements_indirect",
        "requirements_constraints_indirect",
    ],
)
def constrained_mock_project(
    request: SubRequest,
    tox_project: ToxProjectCreator,
    demo_pkg_with_deps: dict[str, str],
    constrain_package_deps: bool,
    use_frozen_constraints: bool,
) -> tuple[ToxProject, list[str]]:
    files: dict[str, str] = {}
    exp_constraints: list[str] = []
    requirement = "coo==1.2.3"
    constraint = "coo<2"
    if request.param == "explicit":
        deps = requirement
        exp_constraints.append(requirement)
    elif request.param == "requirements":
        files["requirements.txt"] = f"--pre\n{requirement}"
        deps = "-rrequirements.txt"
        exp_constraints.append(requirement)
    elif request.param == "constraints":
        files["constraints.txt"] = constraint
        deps = "-cconstraints.txt"
        exp_constraints.append(constraint)
    elif request.param == "explicit+requirements":
        files["requirements.txt"] = f"--pre\n{requirement}"
        deps = "\n\t-rrequirements.txt\n\tfoo"
        exp_constraints.extend(["foo", requirement])
    elif request.param == "requirements_indirect":
        files["foo.requirements.txt"] = f"--pre\n{requirement}"
        files["requirements.txt"] = "-r foo.requirements.txt"
        deps = "-rrequirements.txt"
        exp_constraints.append(requirement)
    elif request.param == "requirements_constraints_indirect":
        files["foo.requirements.txt"] = f"--pre\n{requirement}"
        files["foo.constraints.txt"] = f"{constraint}"
        files["requirements.txt"] = "-r foo.requirements.txt\n-c foo.constraints.txt"
        deps = "-rrequirements.txt"
        exp_constraints.extend([requirement, constraint])
    else:  # pragma: no cover
        pytest.fail(f"Missing case: {request.param}")
    files["tox.ini"] = (
        "[testenv]\npackage=wheel\n"
        f"constrain_package_deps = {constrain_package_deps}\n"
        f"use_frozen_constraints = {use_frozen_constraints}\n"
        f"deps = {deps}"
    )
    return tox_project({**demo_pkg_with_deps, **files}), exp_constraints if constrain_package_deps else []


@pytest.fixture
def demo_pkg_with_deps(demo_pkg_inline: Path) -> dict[str, str]:
    toml = (demo_pkg_inline / "pyproject.toml").read_text().replace("requires = []", 'requires = ["setuptools"]')
    return {
        "pyproject.toml": f'{toml}\n[project]\nname = "demo"\nversion = "0.1"\ndependencies = ["foo > 2"]',
        "build.py": (demo_pkg_inline / "build.py").read_text(),
    }


def test_constrain_package_deps(
    constrained_mock_project: tuple[ToxProject, list[str]],
    constrain_package_deps: bool,
    use_frozen_constraints: bool,
) -> None:
    proj, exp_constraints = constrained_mock_project
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result_first = proj.run("r")
    result_first.assert_success()
    exp_run_ids = ["install_deps"]
    if constrain_package_deps and use_frozen_constraints:
        exp_run_ids.append("freeze")
    exp_run_ids.extend(
        [
            "install_requires",
            "_optional_hooks",
            "get_requires_for_build_wheel",
            "build_wheel",
            "install_package_deps",
            "install_package",
            "_exit",
        ],
    )
    run_ids = [i[0][3].run_id for i in execute_calls.call_args_list]
    assert run_ids == exp_run_ids
    constraints_file = proj.path / ".tox" / "py" / "constraints.txt"
    if constrain_package_deps:
        constraints = constraints_file.read_text().splitlines()
        for call in execute_calls.call_args_list:
            if call[0][3].run_id == "install_package_deps":
                assert f"-c{constraints_file}" in call[0][3].cmd
        if use_frozen_constraints:
            for c in exp_constraints:
                # when using frozen constraints with this mock, the mock package does NOT
                # actually end up in the constraints, so assert it's not there
                assert c not in constraints
            for c in constraints:
                assert c.partition("==")[0] in {"pip", "setuptools", "wheel"}
        else:
            for c in constraints:
                assert c in exp_constraints
            for c in exp_constraints:
                assert c in constraints
    else:
        assert not constraints_file.exists()


@pytest.mark.parametrize("use_frozen_constraints", [True, False])
def test_constraints_option_disables_constrain_package_deps(
    tox_project: ToxProjectCreator,
    demo_pkg_with_deps: dict[str, str],
    use_frozen_constraints: bool,
) -> None:
    proj = tox_project({
        **demo_pkg_with_deps,
        "constraints.txt": "coo==1.2.3",
        "tox.ini": (
            "[testenv]\npackage=wheel\n"
            "constrain_package_deps = true\n"
            f"use_frozen_constraints = {use_frozen_constraints}\n"
            "deps = coo==1.2.3\n"
            "constraints = constraints.txt"
        ),
    })
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()

    constraints_file = proj.path / ".tox" / "py" / "constraints.txt"
    assert not constraints_file.exists()

    for call in execute_calls.call_args_list:
        if call[0][3].run_id == "install_package_deps":
            cmd = call[0][3].cmd
            assert f"-c{constraints_file}" not in cmd
            assert "-c" in cmd
            assert "constraints.txt" in cmd

    exp_run_ids = ["install_deps"]
    exp_run_ids.extend([
        "install_requires",
        "_optional_hooks",
        "get_requires_for_build_wheel",
        "build_wheel",
        "install_package_deps",
        "install_package",
        "_exit",
    ])
    run_ids = [i[0][3].run_id for i in execute_calls.call_args_list]
    assert run_ids == exp_run_ids


def test_comment_only_constraints_keep_constrain_package_deps(
    tox_project: ToxProjectCreator, demo_pkg_with_deps: dict[str, str]
) -> None:
    proj = tox_project({
        **demo_pkg_with_deps,
        "tox.toml": """
        [env_run_base]
        package = "wheel"
        constrain_package_deps = true
        deps = ["coo==1.2.3"]
        constraints = ["# pinned once the release lands"]
        """,
    })
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    package_deps = next(c[0][3].cmd for c in execute_calls.call_args_list if c[0][3].run_id == "install_package_deps")
    assert f"-c{proj.path / '.tox' / 'py' / 'constraints.txt'}" in package_deps


@pytest.mark.parametrize(
    ("deps", "extra_files", "expected"),
    [
        pytest.param("coo[socks]==1.2.3", {}, ["coo==1.2.3"], id="extras"),
        pytest.param(
            "-rrequirements.txt",
            {"requirements.txt": "coo[socks]==1.2.3"},
            ["coo==1.2.3"],
            id="extras-in-requirements-file",
        ),
        pytest.param("\n\t-e ./sibling\n\tcoo==1.2.3", {}, ["coo==1.2.3"], id="editable"),
        pytest.param("\n\t./sibling\n\tcoo==1.2.3", {}, ["coo==1.2.3"], id="directory"),
        pytest.param("\n\t./coo-1.2.3.tar.gz\n\tbar>1", {}, ["bar>1"], id="source-archive"),
        pytest.param(
            "./coo-1.2.3-py3-none-any.whl[socks]",
            {},
            [f".{os.sep}coo-1.2.3-py3-none-any.whl"],
            id="wheel-extras",
        ),
        pytest.param(
            "./coo-1.2.3-py3-none-any.whl",
            {},
            [f".{os.sep}coo-1.2.3-py3-none-any.whl"],
            id="wheel-kept",
        ),
        pytest.param(
            "git+https://example.com/coo.git\\#egg=coo",
            {},
            ["git+https://example.com/coo.git#egg=coo"],
            id="vcs-egg-kept",
        ),
        pytest.param(
            "git+https://example.com/coo.git\\#subdirectory=src&egg=coo",
            {},
            ["git+https://example.com/coo.git#subdirectory=src&egg=coo"],
            id="vcs-egg-after-subdirectory-kept",
        ),
        pytest.param("https://example.com/coo-1.2.3.tar.gz", {}, [], id="source-archive-url"),
        pytest.param(
            "./build\\#1/coo-1.2.3-py3-none-any.whl",
            {},
            [f"build#1{os.sep}coo-1.2.3-py3-none-any.whl"],
            id="wheel-path-with-hash-sign-kept",
        ),
        pytest.param(
            'coo @ https://example.com/coo.zip ; python_version > "3"',
            {},
            ['coo @ https://example.com/coo.zip ; python_version > "3"'],
            id="named-url-kept",
        ),
        pytest.param(
            "-rrequirements.txt",
            {"requirements.txt": f"coo==1.2.3 --hash sha256:{'a' * 64}"},
            [f"coo==1.2.3 --hash sha256:{'a' * 64}"],
            id="hash-kept",
        ),
        pytest.param(
            "\n\t-cconstraints.txt\n\tbar>1",
            {"constraints.txt": "coo<2"},
            ["bar>1", "coo<2"],
            id="constraints-file-not-duplicated",
        ),
    ],
)
def test_constrain_package_deps_constraint_lines(
    tox_project: ToxProjectCreator,
    demo_pkg_with_deps: dict[str, str],
    deps: str,
    extra_files: dict[str, str],
    expected: list[str],
) -> None:
    proj = tox_project({
        **demo_pkg_with_deps,
        "tox.ini": f"[testenv]\npackage=wheel\nconstrain_package_deps = true\ndeps = {deps}",
        **extra_files,
    })
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    assert (proj.path / ".tox" / "py" / "constraints.txt").read_text().splitlines() == expected


def test_pip_resolution_env_var_change_reinstalls(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.ini": """
                [testenv:py]
                deps = a
                skip_install = true
            """,
    })
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1
    execute_calls.reset_mock()

    (proj.path / "tox.ini").write_text(
        dedent("""
            [testenv:py]
            deps = a
            skip_install = true
            setenv = PIP_INDEX_URL = https://example.com
        """)
    )
    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1


def test_pip_non_resolution_env_var_change_no_reinstall(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.ini": """
                [testenv:py]
                deps = a
                skip_install = true
                setenv = PIP_TIMEOUT = 30
            """,
    })
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1
    execute_calls.reset_mock()

    (proj.path / "tox.ini").write_text(
        dedent("""
            [testenv:py]
            deps = a
            skip_install = true
            setenv = PIP_TIMEOUT = 60
        """)
    )
    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 0


@pytest.mark.parametrize("conf_key", ["constrain_package_deps", "use_frozen_constraints"])
def test_change_constraint_options_recreates(tox_project: ToxProjectCreator, conf_key: str) -> None:
    tox_ini_content = "[testenv:py]\ndeps=a\nskip_install=true"
    proj = tox_project({"tox.ini": f"{tox_ini_content}\n{conf_key} = true"})
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")
    result.assert_success()

    (proj.path / "tox.ini").write_text(f"{tox_ini_content}\n{conf_key} = false")
    result_second = proj.run("r")
    result_second.assert_success()
    assert "recreate env because constraint options changed" in result_second.out
    assert conf_key in result_second.out
