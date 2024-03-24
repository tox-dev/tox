from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest
from packaging.requirements import Requirement

from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import CaptureFixture, SubRequest, ToxProject, ToxProjectCreator


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

    with pytest.raises(Fail, match="unable to determine pip install command"):
        pip.install([Requirement("name")], "section", "type")


def test_pip_install_flags_only_error(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv:py]\ndeps=-i a"})
    result = proj.run("r")
    result.assert_failed()
    assert "no dependencies for tox env py within deps" in result.out


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
    execute_calls = proj.patch_execute(lambda request: 0)  # noqa: ARG005
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


def test_pkg_env_dep_remove_recreate(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    toml = (demo_pkg_inline / "pyproject.toml").read_text()
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": toml.replace("requires = [\n]", 'requires = ["setuptools"]'),
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


def test_pip_install_constraint_file_create_change(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\ndeps=-c c.txt\n a\nskip_install=true", "c.txt": "b"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a", "-c", "c.txt"]

    # a new dependency triggers an install
    (proj.path / "tox.ini").write_text("[testenv]\ndeps=-c c.txt\n a\n d\nskip_install=true")
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


def test_pip_install_constraint_file_new(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\ndeps=a\nskip_install=true"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a"]

    (proj.path / "c.txt").write_text("a")
    (proj.path / "tox.ini").write_text("[testenv]\ndeps=a\n -c c.txt\nskip_install=true")
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
    demo_pkg_inline: Path,
    constrain_package_deps: bool,
    use_frozen_constraints: bool,
) -> tuple[ToxProject, list[str]]:
    toml = (demo_pkg_inline / "pyproject.toml").read_text()
    files = {
        "pyproject.toml": toml.replace("requires = [\n]", 'requires = ["setuptools"]')
        + '\n[project]\nname = "demo"\nversion = "0.1"\ndependencies = ["foo > 2"]',
        "build.py": (demo_pkg_inline / "build.py").read_text(),
    }
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
    return tox_project(files), exp_constraints if constrain_package_deps else []


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
