from __future__ import annotations

import sys
from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from tox.pytest import ToxProjectCreator


def test_depends_wheel(tox_project: ToxProjectCreator, patch_prev_py: Callable[[bool], tuple[str, str]]) -> None:
    prev_ver, impl = patch_prev_py(True)  # has previous python
    ver = sys.version_info[0:2]
    py = f"py{''.join(str(i) for i in ver)}"
    prev_py = f"py{prev_ver}"
    ini = f"""
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
    project = tox_project({"tox.ini": ini, "pyproject.toml": ""})
    outcome = project.run("de")
    outcome.assert_success()

    expected = f"""
    Execution order: py, {py}, {prev_py}, py31, cov, cov2
    ALL
       py ~ .pkg
       {py} ~ .pkg
       {prev_py} ~ .pkg | .pkg-{impl}{prev_ver}
       py31 ~ .pkg
       cov2
          cov
             py ~ .pkg
             {py} ~ .pkg
             {prev_py} ~ .pkg | .pkg-{impl}{prev_ver}
             py31 ~ .pkg
       cov
          py ~ .pkg
          {py} ~ .pkg
          {prev_py} ~ .pkg | .pkg-{impl}{prev_ver}
          py31 ~ .pkg
    """
    assert outcome.out == dedent(expected).lstrip()


def test_depends_sdist(tox_project: ToxProjectCreator, patch_prev_py: Callable[[bool], tuple[str, str]]) -> None:
    prev_ver, _impl = patch_prev_py(True)  # has previous python
    ver = sys.version_info[0:2]
    py = f"py{''.join(str(i) for i in ver)}"
    prev_py = f"py{prev_ver}"
    ini = f"""
    [tox]
    env_list = py,{py},{prev_py},py31,cov2,cov
    [testenv]
    package = sdist
    [testenv:cov]
    depends = py,{py},{prev_py},py31
    skip_install = true
    [testenv:cov2]
    depends = cov
    skip_install = true
    """
    project = tox_project({"tox.ini": ini, "pyproject.toml": ""})
    outcome = project.run("de")
    outcome.assert_success()

    expected = f"""
    Execution order: py, {py}, {prev_py}, py31, cov, cov2
    ALL
       py ~ .pkg
       {py} ~ .pkg
       {prev_py} ~ .pkg
       py31 ~ .pkg
       cov2
          cov
             py ~ .pkg
             {py} ~ .pkg
             {prev_py} ~ .pkg
             py31 ~ .pkg
       cov
          py ~ .pkg
          {py} ~ .pkg
          {prev_py} ~ .pkg
          py31 ~ .pkg
    """
    assert outcome.out == dedent(expected).lstrip()


def test_depends_glob_star(tox_project: ToxProjectCreator) -> None:
    toml = """
    env_list = ["3.12", "3.13", "3.14", "lint", "cov"]
    [env_run_base]
    package = "skip"
    [env.cov]
    depends = ["3.*"]
    """
    project = tox_project({"tox.toml": toml})
    outcome = project.run("de")
    outcome.assert_success()
    expected = dedent("""\
    Execution order: 3.12, 3.13, 3.14, lint, cov
    ALL
       3.12
       3.13
       3.14
       lint
       cov
          3.12
          3.13
          3.14
    """)
    assert outcome.out == expected


def test_depends_glob_question_mark(tox_project: ToxProjectCreator) -> None:
    toml = """
    env_list = ["a1", "a2", "ab", "cov"]
    [env_run_base]
    package = "skip"
    [env.cov]
    depends = ["a?"]
    """
    project = tox_project({"tox.toml": toml})
    outcome = project.run("de")
    outcome.assert_success()
    expected = dedent("""\
    Execution order: a1, a2, ab, cov
    ALL
       a1
       a2
       ab
       cov
          a1
          a2
          ab
    """)
    assert outcome.out == expected


def test_depends_glob_no_match(tox_project: ToxProjectCreator) -> None:
    toml = """
    env_list = ["lint", "cov"]
    [env_run_base]
    package = "skip"
    [env.cov]
    depends = ["py*"]
    """
    project = tox_project({"tox.toml": toml})
    outcome = project.run("de")
    outcome.assert_success()
    expected = dedent("""\
    Execution order: lint, cov
    ALL
       lint
       cov
    """)
    assert outcome.out == expected


def test_depends_glob_mixed(tox_project: ToxProjectCreator) -> None:
    toml = """
    env_list = ["3.13", "3.14", "lint", "cov"]
    [env_run_base]
    package = "skip"
    [env.cov]
    depends = ["lint", "3.*"]
    """
    project = tox_project({"tox.toml": toml})
    outcome = project.run("de")
    outcome.assert_success()
    expected = dedent("""\
    Execution order: 3.13, 3.14, lint, cov
    ALL
       3.13
       3.14
       lint
       cov
          3.13
          3.14
          lint
    """)
    assert outcome.out == expected


def test_depends_glob_excludes_self(tox_project: ToxProjectCreator) -> None:
    toml = """
    env_list = ["a", "b", "cov"]
    [env_run_base]
    package = "skip"
    [env.cov]
    depends = ["*"]
    """
    project = tox_project({"tox.toml": toml})
    outcome = project.run("de")
    outcome.assert_success()
    expected = dedent("""\
    Execution order: a, b, cov
    ALL
       a
       b
       cov
          a
          b
    """)
    assert outcome.out == expected


def test_depends_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("de", "-h")
    outcome.assert_success()
