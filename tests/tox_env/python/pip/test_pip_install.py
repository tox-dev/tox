from pathlib import Path
from typing import Any, List
from unittest.mock import Mock

import pytest

from tox.pytest import CaptureFixture, ToxProjectCreator


@pytest.mark.parametrize("arg", [object, [object]])
def test_pip_install_bad_type(tox_project: ToxProjectCreator, capfd: CaptureFixture, arg: Any) -> None:
    proj = tox_project({"tox.ini": ""})
    result = proj.run("l")
    result.assert_success()
    pip = result.state.tox_env("py").installer

    with pytest.raises(SystemExit, match="1"):
        pip.install(arg, "section", "type")
    out, err = capfd.readouterr()
    assert not err
    assert f"pip cannot install {object!r}" in out


def test_pip_install_empty_list(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": ""})
    result = proj.run("l")
    result.assert_success()

    pip = result.state.tox_env("py").installer
    execute_calls = proj.patch_execute(Mock())
    pip.install([], "section", "type")
    assert execute_calls.call_count == 0


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

    (proj.path / "tox.ini").write_text("[testenv:py]\ndeps=a\n -i a\nskip_install=true")
    result_second = proj.run("r")
    result_second.assert_success()
    assert "recreate env because new flag -i a" in result_second.out
    assert "install_deps> python -I -m pip install a -i a" in result_second.out


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
def test_pip_install_req_file_req_like(tox_project: ToxProjectCreator, content: str, args: List[str]) -> None:
    proj = tox_project({"tox.ini": f"[testenv:py]\ndeps={content}\nskip_install=true"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")
    result.assert_success()

    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install"] + args

    # check that adding a new dependency correctly finds the previous one
    (proj.path / "tox.ini").write_text(f"[testenv:py]\ndeps={content}\n a\nskip_install=true")
    execute_calls.reset_mock()

    result_second = proj.run("r")
    result_second.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a"]


def test_pip_req_path(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv:py]\ndeps=.\nskip_install=true"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result = proj.run("r")
    result.assert_success()

    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", str(proj.path)]


def test_deps_remove_recreate(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip\ndeps=wheel\n setuptools"})
    execute_calls = proj.patch_execute(lambda request: 0)
    result_first = proj.run("r")
    result_first.assert_success()
    assert execute_calls.call_count == 1

    (proj.path / "tox.ini").write_text("[testenv]\npackage=skip\ndeps=setuptools\n")
    result_second = proj.run("r")
    result_second.assert_success()
    assert "py: recreate env because dependencies removed: wheel" in result_second.out, result_second.out
    assert execute_calls.call_count == 2


def test_pkg_dep_remove_recreate(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    build = (demo_pkg_inline / "build.py").read_text()
    build_with_dep = build.replace("Summary: UNKNOWN\n", "Summary: UNKNOWN\n        Requires-Dist: wheel\n")
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": (demo_pkg_inline / "pyproject.toml").read_text(),
            "build.py": build_with_dep,
        }
    )
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result_first = proj.run("r")
    result_first.assert_success()
    run_ids = [i[0][3].run_id for i in execute_calls.call_args_list]
    assert run_ids == [
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
    assert run_ids == ["get_requires_for_build_wheel", "build_wheel", "install_package", "_exit"]


def test_pkg_env_dep_remove_recreate(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    toml = (demo_pkg_inline / "pyproject.toml").read_text()
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": toml.replace("requires = []", 'requires = ["setuptools"]'),
            "build.py": (demo_pkg_inline / "build.py").read_text(),
        }
    )
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result_first = proj.run("r")
    result_first.assert_success()
    run_ids = [i[0][3].run_id for i in execute_calls.call_args_list]
    assert run_ids == ["install_requires", "get_requires_for_build_wheel", "build_wheel", "install_package", "_exit"]
    execute_calls.reset_mock()

    (proj.path / "pyproject.toml").write_text(toml)
    result_second = proj.run("r")
    result_second.assert_success()
    assert ".pkg: recreate env because dependencies removed: setuptools" in result_second.out, result_second.out
    run_ids = [i[0][3].run_id for i in execute_calls.call_args_list]
    assert run_ids == ["get_requires_for_build_wheel", "build_wheel", "install_package", "_exit"]


def test_pip_install_requirements_file_deps(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\ndeps=-r r.txt\nskip_install=true", "r.txt": "a"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "-r", "r.txt"]

    # check that adding a new dependency correctly finds the previous one
    (proj.path / "tox.ini").write_text("[testenv]\ndeps=-r r.txt\n a\nskip_install=true")
    execute_calls.reset_mock()
    result_second = proj.run("r")
    result_second.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a"]

    # if the requirement file changes recreate
    (proj.path / "r.txt").write_text("a\nb")
    execute_calls.reset_mock()
    result_third = proj.run("r")
    result_third.assert_success()
    assert "py: recreate env because requirements file r.txt changed" in result_third.out, result_third.out
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "-r", "r.txt", "a"]


def test_pip_install_constraint_file_create_change(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\ndeps=-c c.txt\n a\nskip_install=true", "c.txt": "a"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("r")
    result.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "-c", "c.txt", "a"]

    # a new dependency removes the previous dependency but keeps constraint
    (proj.path / "tox.ini").write_text("[testenv]\ndeps=-c c.txt\n a\n b\nskip_install=true")
    execute_calls.reset_mock()
    result_second = proj.run("r")
    result_second.assert_success()
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "-c", "c.txt", "b"]

    (proj.path / "c.txt").write_text("a\nb")
    execute_calls.reset_mock()
    result_third = proj.run("r")
    result_third.assert_success()
    assert "py: recreate env because constraint file c.txt changed" in result_third.out, result_third.out
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "-c", "c.txt", "a", "b"]


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
    assert "py: recreate env because new constraint file -c c.txt" in result_second.out, result_second.out
    assert execute_calls.call_count == 1
    assert execute_calls.call_args[0][3].cmd == ["python", "-I", "-m", "pip", "install", "a", "-c", "c.txt"]
