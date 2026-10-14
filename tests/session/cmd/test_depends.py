from __future__ import annotations

import json
import sys
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.conftest import PatchPrevPy
    from tox.pytest import ToxProjectCreator


def test_depends_wheel(tox_project: ToxProjectCreator, patch_prev_py: PatchPrevPy) -> None:
    prev_ver, impl, _ = patch_prev_py(True)  # has previous python
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


def test_depends_sdist(tox_project: ToxProjectCreator, patch_prev_py: PatchPrevPy) -> None:
    prev_ver, _impl, _ = patch_prev_py(True)  # has previous python
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


@pytest.mark.parametrize("fmt", ["toml", "ini"])
@pytest.mark.parametrize(
    ("env_list", "depends", "expected"),
    [
        pytest.param(
            ["3.12", "3.13", "3.14", "lint", "cov"],
            ["3.*"],
            """\
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
            """,
            id="star",
        ),
        pytest.param(
            ["a1", "a2", "ab", "cov"],
            ["a?"],
            """\
            Execution order: a1, a2, ab, cov
            ALL
               a1
               a2
               ab
               cov
                  a1
                  a2
                  ab
            """,
            id="question_mark",
        ),
        pytest.param(
            ["lint", "cov"],
            ["py*"],
            """\
            Execution order: lint, cov
            ALL
               lint
               cov
            """,
            id="no_match",
        ),
        pytest.param(
            ["3.13", "3.14", "lint", "cov"],
            ["lint", "3.*"],
            """\
            Execution order: 3.13, 3.14, lint, cov
            ALL
               3.13
               3.14
               lint
               cov
                  3.13
                  3.14
                  lint
            """,
            id="mixed",
        ),
        pytest.param(
            ["a", "b", "cov"],
            ["*"],
            """\
            Execution order: a, b, cov
            ALL
               a
               b
               cov
                  a
                  b
            """,
            id="excludes_self",
        ),
    ],
)
def test_depends_glob(
    tox_project: ToxProjectCreator, fmt: str, env_list: list[str], depends: list[str], expected: str
) -> None:
    if fmt == "toml":
        conf = f"""
        env_list = {json.dumps(env_list)}
        [env_run_base]
        package = "skip"
        [env.cov]
        depends = {json.dumps(depends)}
        """
    else:
        conf = f"""
        [tox]
        env_list = {",".join(env_list)}
        [testenv]
        skip_install = true
        [testenv:cov]
        depends = {",".join(depends)}
        """
    project = tox_project({f"tox.{fmt}": conf})
    outcome = project.run("de")
    outcome.assert_success()
    assert outcome.out == dedent(expected)


def test_depends_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("de", "-h")
    outcome.assert_success()


def test_depends_circular(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nenv_list = a,b\n[testenv]\npackage = skip\n[testenv:a]\ndepends = b\n[testenv:b]\ndepends = a\n"
    project = tox_project({"tox.ini": ini})

    outcome = project.run("de")

    outcome.assert_failed(code=-2)
    assert "circular dependency detected between environments: a | b" in outcome.out, outcome.out


def test_depends_circular_run(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nenv_list = a,b\n[testenv]\npackage = skip\n[testenv:a]\ndepends = b\n[testenv:b]\ndepends = a\n"
    project = tox_project({"tox.ini": ini})

    outcome = project.run("r", "--notest")

    outcome.assert_failed(code=-2)
    assert "circular dependency detected between environments: a | b" in outcome.out, outcome.out
    assert "Traceback" not in outcome.err, outcome.err
