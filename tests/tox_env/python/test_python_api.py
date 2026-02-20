from __future__ import annotations

import sys
import sysconfig
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from tox.tox_env.errors import Fail
from tox.tox_env.python.api import Python

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

    from tox.pytest import ToxProjectCreator


def test_requirements_txt(tox_project: ToxProjectCreator) -> None:
    prj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=skip\ndeps=-rrequirements.txt",
            "requirements.txt": "nose",
        },
    )
    execute_calls = prj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = prj.run("r", "-e", "py")
    result.assert_success()

    assert execute_calls.call_count == 1
    exp = ["python", "-I", "-m", "pip", "install", "-r", "requirements.txt"]
    got_cmd = execute_calls.call_args[0][3].cmd

    assert got_cmd == exp


def test_conflicting_base_python_factor() -> None:
    major, minor = sys.version_info[0:2]
    name = f"py{major}{minor}-py{major}{minor - 1}"
    with pytest.raises(ValueError, match=f"conflicting factors py{major}{minor}, py{major}{minor - 1} in {name}"):
        Python.extract_base_python(name)


def test_build_wheel_in_non_base_pkg_env(
    tox_project: ToxProjectCreator,
    patch_prev_py: Callable[[bool], tuple[str, str]],
    demo_pkg_inline: Path,
    mocker: MockerFixture,
) -> None:
    def _fake_session(env_dir: list[str], **_: object) -> MagicMock:
        bin_dir = Path(env_dir[0]) / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / "python").symlink_to(sys.executable)
        mock = MagicMock()
        mock.creator.bin_dir = bin_dir
        mock.creator.script_dir = bin_dir
        return mock

    mocker.patch("tox.tox_env.python.virtual_env.api.session_via_cli", side_effect=_fake_session)
    prev_ver, impl = patch_prev_py(True)
    prev_py = f"py{prev_ver}"
    prj = tox_project({"tox.ini": f"[tox]\nenv_list= {prev_py}\n[testenv]\npackage=wheel"})
    execute_calls = prj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = prj.run("-r", "--root", str(demo_pkg_inline), "--workdir", str(prj.path / ".tox"))
    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    assert calls == [
        (f".pkg-{impl}{prev_ver}", "_optional_hooks"),
        (f".pkg-{impl}{prev_ver}", "get_requires_for_build_wheel"),
        (f".pkg-{impl}{prev_ver}", "build_wheel"),
        (f"py{prev_ver}", "install_package"),
        (f".pkg-{impl}{prev_ver}", "_exit"),
    ]


def test_diff_msg_added_removed_changed() -> None:
    before = {"A": "1", "F": "8", "C": "3", "D": "4", "E": "6"}
    after = {"G": "9", "B": "2", "C": "3", "D": "5", "E": "7"}
    expected = "python added A='1' | F='8', removed G='9' | B='2', changed D='5'->'4' | E='7'->'6'"
    assert Python._diff_msg(before, after) == expected  # noqa: SLF001


def test_diff_msg_no_diff() -> None:
    assert Python._diff_msg({}, {}) == "python "  # noqa: SLF001


@pytest.mark.parametrize(
    ("env", "base_python"),
    [
        ("py3", "py3"),
        ("py3t", "py3t"),
        ("py311", "py311"),
        ("py311t", "py311t"),
        ("py3.12", "py3.12"),
        ("py3.12t", "py3.12t"),
        ("pypy2", "pypy2"),
        ("pypy2t", "pypy2t"),
        ("rustpython3", "rustpython3"),
        ("rustpython3t", "rustpython3t"),
        ("graalpy", "graalpy"),
        ("graalpyt", None),
        ("jython", "jython"),
        ("jythont", None),
        ("cpython3.8", "cpython3.8"),
        ("cpython3.8t", "cpython3.8t"),
        ("ironpython2.7", "ironpython2.7"),
        ("ironpython2.7t", "ironpython2.7t"),
        ("functional-py310", "py310"),
        ("functional-py310t", "py310t"),
        ("bar-pypy2-foo", "pypy2"),
        ("bar-foo2t-py2", "py2"),
        ("bar-pypy2t-foo", "pypy2t"),
        ("py", None),
        ("pyt", None),
        ("django-32", None),
        ("django-32t", None),
        ("eslint-8.3", None),
        ("eslint-8.3t", None),
        ("py-310", None),
        ("py-310t", None),
        ("py3000", None),
        ("py3000t", None),
        ("4.foo", None),
        ("4.foot", None),
        ("310", None),
        ("310t", None),
        ("5", None),
        ("5t", None),
        ("2000", None),
        ("2000t", None),
        ("4000", None),
        ("4000t", None),
        ("3.10", "3.10"),
        ("3.10t", "3.10t"),
        ("3.9", "3.9"),
        ("3.9t", "3.9t"),
        ("2.7", "2.7"),
        ("2.7t", "2.7t"),
        ("pypy-3.10", "pypy3.10"),
        ("pypy-3.10t", "pypy3.10t"),
    ],
    ids=lambda a: "|".join(a) if isinstance(a, list) else str(a),
)
def test_extract_base_python(env: str, base_python: str | None) -> None:
    result = Python.extract_base_python(env)
    assert result == base_python


@pytest.mark.parametrize("ignore_conflict", [True, False])
@pytest.mark.parametrize(
    ("env", "base_python"),
    [
        ("magic", ["pypy"]),
        ("magic", ["py39"]),
    ],
    ids=lambda a: "|".join(a) if isinstance(a, list) else str(a),
)
def test_base_python_env_no_conflict(env: str, base_python: list[str], ignore_conflict: bool) -> None:
    result = Python._validate_base_python(env, base_python, ignore_conflict)  # noqa: SLF001
    assert result is base_python


@pytest.mark.parametrize("ignore_conflict", [True, False])
@pytest.mark.parametrize(
    ("env", "base_python", "expected", "conflict"),
    [
        ("pypy", ["cpython"], "pypy", ["cpython"]),
        ("pypy2", ["pypy3"], "pypy2", ["pypy3"]),
        ("py3", ["py2"], "py3", ["py2"]),
        ("py38", ["py39"], "py38", ["py39"]),
        ("py38", ["py38", "py39"], "py38", ["py39"]),
        ("py38", ["python3"], "py38", ["python3"]),
        ("py310", ["py38", "py39"], "py310", ["py38", "py39"]),
        ("py3.11", ["py310"], "py3.11", ["py310"]),
        ("py310-magic", ["py39"], "py310", ["py39"]),
    ],
    ids=lambda a: "|".join(a) if isinstance(a, list) else str(a),
)
def test_base_python_env_conflict(
    env: str,
    base_python: list[str],
    expected: str,
    conflict: list[str],
    ignore_conflict: bool,
) -> None:
    if ignore_conflict:
        result = Python._validate_base_python(env, base_python, ignore_conflict)  # noqa: SLF001
        assert result == [expected]
    else:
        msg = f"env name {env} conflicting with base python {conflict[0]}"
        with pytest.raises(Fail, match=msg):
            Python._validate_base_python(env, base_python, ignore_conflict)  # noqa: SLF001


@pytest.mark.parametrize("ignore_conflict", [True, False, None])
def test_base_python_env_conflict_show_conf(tox_project: ToxProjectCreator, ignore_conflict: bool) -> None:
    py_ver = "".join(str(i) for i in sys.version_info[0:2])
    py_ver_next = "".join(str(i) for i in (sys.version_info[0], sys.version_info[1] + 2))
    ini = f"[testenv]\npackage=skip\nbase_python=py{py_ver_next}"
    if ignore_conflict is not None:
        ini += f"\n[tox]\nignore_base_python_conflict={ignore_conflict}"
    project = tox_project({"tox.ini": ini})
    result = project.run("c", "-e", f"py{py_ver}", "-k", "base_python", raise_on_config_fail=False)
    if ignore_conflict:
        result.assert_success()
    else:
        result.assert_failed(code=-1)
    if ignore_conflict:
        out = f"[testenv:py{py_ver}]\nbase_python = py{py_ver}\n"
    else:
        comma_in_exc = sys.version_info[0:2] <= (3, 6)
        out = (
            f"[testenv:py{py_ver}]\nbase_python = # Exception: Fail('env name py{py_ver} conflicting with"
            f" base python py{py_ver_next}'{',' if comma_in_exc else ''})\n"
        )
    result.assert_out_err(out, "")


def test_python_set_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ[\"PYTHONHASHSEED\"])'"
    prj = tox_project({"tox.ini": ini})
    result = prj.run("r", "-e", "py", "--hashseed", "10")
    result.assert_success()
    assert result.out.splitlines()[1] == "10"


def test_python_generate_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ[\"PYTHONHASHSEED\"])'"
    prj = tox_project({"tox.ini": ini})
    result = prj.run("r", "-e", "py")
    result.assert_success()
    assert 1 <= int(result.out.splitlines()[1]) <= (1024 if sys.platform == "win32" else 4294967295)


def test_python_keep_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = """
    [testenv]
    package=skip
    set_env=PYTHONHASHSEED=12
    commands=python -c 'import os; print(os.environ["PYTHONHASHSEED"])'
    """
    result = tox_project({"tox.ini": ini}).run("r", "-e", "py")
    result.assert_success()
    assert result.out.splitlines()[1] == "12"


def test_python_hash_seed_via_section_substitution(tox_project: ToxProjectCreator) -> None:
    ini = """
    [testenv]
    package=skip
    set_env=PYTHONHASHSEED=12
    [testenv:hs]
    commands=python -c 'import os; print(os.environ["PYTHONHASHSEED"])'
    set_env={[testenv]set_env}
    """
    result = tox_project({"tox.ini": ini}).run("r", "-e", "hs")
    result.assert_success()
    assert result.out.splitlines()[1] == "12"


def test_python_disable_hash_seed(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ.get(\"PYTHONHASHSEED\"))'"
    prj = tox_project({"tox.ini": ini})
    result = prj.run("r", "-e", "py", "--hashseed", "notset")
    result.assert_success()
    assert result.out.splitlines()[1] == "None"


def test_python_set_hash_seed_negative(tox_project: ToxProjectCreator) -> None:
    result = tox_project({"tox.ini": ""}).run("r", "-e", "py", "--hashseed", "-1")
    result.assert_failed(2)
    assert "tox run: error: argument --hashseed: must be greater than zero" in result.err


def test_python_set_hash_seed_incorrect(tox_project: ToxProjectCreator) -> None:
    result = tox_project({"tox.ini": ""}).run("r", "-e", "py", "--hashseed", "ok")
    result.assert_failed(2)
    assert "tox run: error: argument --hashseed: invalid literal for int() with base 10: 'ok'" in result.err


def test_python_use_hash_seed_from_env(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip"
    with patch.dict("os.environ", {"PYTHONHASHSEED": "13"}):
        result = tox_project({"tox.ini": ini}).run("c", "-e", "py", "-k", "setenv")
        result.assert_success()
        assert "PYTHONHASHSEED=13" in result.out


def test_python_hash_seed_from_env_random(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip"
    with patch.dict("os.environ", {"PYTHONHASHSEED": "random"}):
        result = tox_project({"tox.ini": ini}).run("c", "-e", "py", "-k", "setenv")
        result.assert_success()
        assert "PYTHONHASHSEED=" in result.out


def test_python_hash_seed_from_env_and_override(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ.get(\"PYTHONHASHSEED\"))'"
    with patch.dict("os.environ", {"PYTHONHASHSEED": "14"}):
        result = tox_project({"tox.ini": ini}).run("r", "-e", "py", "--hashseed", "15")
        result.assert_success()
        assert result.out.splitlines()[1] == "15"


def test_python_hash_seed_from_env_and_disable(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\ncommands=python -c 'import os; print(os.environ.get(\"PYTHONHASHSEED\"))'"
    with patch.dict("os.environ", {"PYTHONHASHSEED": "16"}):
        result = tox_project({"tox.ini": ini}).run("r", "-e", "py", "--hashseed", "notset")
        result.assert_success()
        assert result.out.splitlines()[1] == "None"


@pytest.mark.parametrize("in_ci", [True, False])
def test_list_installed_deps(in_ci: bool, tox_project: ToxProjectCreator, mocker: MockerFixture) -> None:
    mocker.patch("tox.config.cli.parser.is_ci", return_value=in_ci)
    result = tox_project({"tox.ini": "[testenv]\nskip_install = true"}).run("r", "-e", "py")
    if in_ci:
        assert "pip==" in result.out
    else:
        assert "pip==" not in result.out


@pytest.mark.parametrize("list_deps", ["--list-dependencies", "--no-list-dependencies"])
@pytest.mark.parametrize("in_ci", [True, False])
def test_list_installed_deps_explicit_cli(
    list_deps: str,
    in_ci: bool,
    tox_project: ToxProjectCreator,
    mocker: MockerFixture,
) -> None:
    mocker.patch("tox.config.cli.parser.is_ci", return_value=in_ci)
    result = tox_project({"tox.ini": "[testenv]\nskip_install = true"}).run(list_deps, "r", "-e", "py")
    if list_deps == "--list-dependencies":
        assert "pip==" in result.out
    else:
        assert "pip==" not in result.out


def test_usedevelop_with_nonexistent_basepython(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\nusedevelop = true\n[testenv:unused]\nbasepython = /nonexistent/bin/python"
    project = tox_project({"tox.ini": ini})
    result = project.run()
    assert result.code == 0


def test_default_base_python_used_when_no_factor(tox_project: ToxProjectCreator) -> None:
    py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    toml = f"""\
env_list = ["lint"]

[env_run_base]
package = "skip"
default_base_python = ["python{py_ver}"]
commands = [["python", "-c", "print('ok')"]]
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", "lint", "-k", "base_python")
    result.assert_success()
    assert f"python{py_ver}" in result.out


def test_default_base_python_ignored_when_factor_present(tox_project: ToxProjectCreator) -> None:
    py_ver = f"{sys.version_info[0]}{sys.version_info[1]}"
    toml = f"""\
env_list = ["py{py_ver}"]

[env_run_base]
package = "skip"
default_base_python = ["python3.8"]
commands = [["python", "-c", "print('ok')"]]
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", f"py{py_ver}", "-k", "base_python")
    result.assert_success()
    assert f"py{py_ver}" in result.out
    assert "python3.8" not in result.out


def test_default_base_python_ignored_when_base_python_explicit(tox_project: ToxProjectCreator) -> None:
    py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
    toml = f"""\
env_list = ["lint"]

[env_run_base]
package = "skip"
default_base_python = ["python3.8"]
commands = [["python", "-c", "print('ok')"]]

[env.lint]
base_python = ["python{py_ver}"]
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", "lint", "-k", "base_python")
    result.assert_success()
    assert f"python{py_ver}" in result.out
    assert "python3.8" not in result.out


def test_default_base_python_falls_back_to_sys_executable(tox_project: ToxProjectCreator) -> None:
    toml = """\
env_list = ["lint"]

[env_run_base]
package = "skip"
commands = [["python", "-c", "print('ok')"]]
"""
    result = tox_project({"tox.toml": toml}).run("c", "-e", "lint", "-k", "base_python")
    result.assert_success()
    assert sys.executable in result.out


@pytest.mark.parametrize(
    ("impl", "major", "minor", "arch", "free_threaded"),
    [
        ("cpython", 3, 12, 64, None),
        ("cpython", 3, 13, 64, True),
        ("cpython", 3, 13, 64, False),
        ("pypy", 3, 9, 32, None),
    ],
)
def test_python_spec_for_sys_executable(  # noqa: PLR0913
    impl: str, major: int, minor: int, arch: int, free_threaded: bool | None, mocker: MockerFixture
) -> None:
    get_config_var_ = sysconfig.get_config_var

    def get_config_var(name: str) -> object:
        if name == "Py_GIL_DISABLED":
            return free_threaded
        return get_config_var_(name)

    version_info = SimpleNamespace(major=major, minor=minor, micro=5, releaselevel="final", serial=0)
    implementation = SimpleNamespace(
        name=impl,
        cache_tag=f"{impl}-{major}{minor}",
        version=version_info,
        hexversion=...,
        _multiarch=...,
    )
    mocker.patch.object(sys, "version_info", version_info)
    mocker.patch.object(sys, "implementation", implementation)
    mocker.patch.object(sys, "maxsize", 2**arch // 2 - 1)
    mocker.patch.object(sysconfig, "get_config_var", get_config_var)
    spec = Python._python_spec_for_sys_executable()  # noqa: SLF001
    assert spec.implementation == impl
    assert spec.major == major
    assert spec.minor == minor
    assert spec.architecture == arch
    assert spec.free_threaded == bool(free_threaded)
