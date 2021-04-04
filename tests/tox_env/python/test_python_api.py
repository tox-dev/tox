import sys
from pathlib import Path
from typing import Callable, Tuple

import pytest
from pytest_mock import MockerFixture

from tox.pytest import ToxProjectCreator
from tox.tox_env.python.api import Python


def test_requirements_txt(tox_project: ToxProjectCreator) -> None:
    prj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=skip\ndeps=-rrequirements.txt",
            "requirements.txt": "nose",
        }
    )
    execute_calls = prj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = prj.run("r", "-e", "py")
    result.assert_success()

    assert execute_calls.call_count == 1
    exp = ["python", "-I", "-m", "pip", "install", "-r", "requirements.txt"]
    got_cmd = execute_calls.call_args[0][3].cmd

    assert got_cmd == exp


def test_conflicting_base_python() -> None:
    major, minor = sys.version_info[0:2]
    name = f"py{major}{minor}-py{major}{minor-1}"
    with pytest.raises(ValueError, match=f"conflicting factors py{major}{minor}, py{major}{minor-1} in {name}"):
        Python.extract_base_python(name)


def test_build_wheel_in_non_base_pkg_env(
    tox_project: ToxProjectCreator,
    patch_prev_py: Callable[[bool], Tuple[str, str]],
    demo_pkg_inline: Path,
    mocker: MockerFixture,
) -> None:
    mocker.patch("tox.tox_env.python.virtual_env.api.session_via_cli")
    prev_ver, impl = patch_prev_py(True)
    prev_py = f"py{prev_ver}"
    prj = tox_project({"tox.ini": f"[tox]\nenv_list= {prev_py}\n[testenv]\npackage=wheel"})
    execute_calls = prj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = prj.run("-r", "--root", str(demo_pkg_inline))
    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert calls == [
        (f".pkg-{impl}{prev_ver}", "get_requires_for_build_wheel"),
        (f".pkg-{impl}{prev_ver}", "build_wheel"),
        (f"py{prev_ver}", "install_package"),
        (f".pkg-{impl}{prev_ver}", "_exit"),
    ]


def test_diff_msg_added_removed_changed() -> None:
    before = {"A": "1", "F": "8", "C": "3", "D": "4", "E": "6"}
    after = {"G": "9", "B": "2", "C": "3", "D": "5", "E": "7"}
    expected = "python added A='1' | F='8', removed G='9' | B='2', changed D='4'->'5' | E='6'->'7'"
    assert Python._diff_msg(before, after) == expected


def test_diff_msg_no_diff() -> None:
    assert Python._diff_msg({}, {}) == "python "
