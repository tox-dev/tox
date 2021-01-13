import sys
from typing import Callable, Tuple

import pytest

from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize("has_prev", [True, False])
def test_depends(
    tox_project: ToxProjectCreator, patch_prev_py: Callable[[bool], Tuple[str, str]], has_prev: bool
) -> None:
    prev_ver, impl = patch_prev_py(has_prev)
    ver = sys.version_info[0:2]
    py = f"py{''.join(str(i) for i in ver)}"
    prev_py = f"py{prev_ver}"
    project = tox_project(
        {
            "tox.ini": f"""
    [tox]
    env_list = py,{py},{prev_py},py31,cov2,cov
    [testenv]
    package = wheel
    [testenv:cov]
    depends = py,{py},{prev_py},py31
    skip_install = true
    [testenv:cov2]
    depends = cov
    skip_install = true
    """
        }
    )
    outcome = project.run("de")
    outcome.assert_success()
    lines = outcome.out.splitlines()
    assert lines[0] == f"Execution order: py, {py},{f' {prev_py},' if has_prev else '' } cov, cov2"
    expected_lines = [
        "ALL",
        "   py ~ .pkg",
        f"   {py} ~ .pkg",
    ]
    if has_prev:
        expected_lines.append(f"   {prev_py} ~ .pkg | .pkg-{impl}{prev_ver}")
    expected_lines.extend(
        [
            "   cov2",
            "      cov",
            "         py ~ .pkg",
            f"         {py} ~ .pkg",
        ]
    )
    if has_prev:
        expected_lines.append(f"         {prev_py} ~ .pkg | .pkg-{impl}{prev_ver}")
    expected_lines.extend(
        [
            "   cov",
            "      py ~ .pkg",
            f"      {py} ~ .pkg",
        ]
    )
    if has_prev:
        expected_lines.append(f"      {prev_py} ~ .pkg | .pkg-{impl}{prev_ver}")
    assert lines[1:] == expected_lines
