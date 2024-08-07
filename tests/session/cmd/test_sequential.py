from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from re_assert import Matches
from virtualenv.discovery.py_info import PythonInfo

from tox import __version__
from tox.tox_env.api import ToxEnv
from tox.tox_env.info import Info

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize("prefix", ["-", "- "])
def test_run_ignore_cmd_exit_code(tox_project: ToxProjectCreator, prefix: str) -> None:
    cmd = [
        f"{prefix}python -c 'import sys; print(\"magic fail\", file=sys.stderr); sys.exit(1)'",
        "python -c 'import sys; print(\"magic pass\", file=sys.stdout); sys.exit(0)'",
    ]
    project = tox_project({"tox.ini": f"[tox]\nno_package=true\n[testenv]\ncommands={cmd[0]}\n {cmd[1]}"})
    outcome = project.run("r", "-e", "py")
    outcome.assert_success()
    assert "magic pass" in outcome.out
    assert "magic fail" in outcome.err


def test_run_sequential_fail(tox_project: ToxProjectCreator) -> None:
    def _cmd(value: int) -> str:
        return f"python -c 'import sys; print(\"exit {value}\"); sys.exit({value})'"

    ini = f"[tox]\nenv_list=a,b\nno_package=true\n[testenv:a]\ncommands={_cmd(1)}\n[testenv:b]\ncommands={_cmd(0)}"
    project = tox_project({"tox.ini": ini})
    outcome = project.run("r", "-e", "a,b")
    outcome.assert_failed()
    reports = outcome.out.splitlines()[-3:]
    assert Matches(r"  evaluation failed :\( \(.* seconds\)") == reports[-1]
    assert Matches(r"  b: OK \(.*=setup\[.*\]\+cmd\[.*\] seconds\)") == reports[-2]
    assert Matches(r"  a: FAIL code 1 \(.*=setup\[.*\]\+cmd\[.*\] seconds\)") == reports[-3]


def test_run_sequential_quiet(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nenv_list=a\nno_package=true\n[testenv]\ncommands=python -V"
    project = tox_project({"tox.ini": ini})
    outcome = project.run("r", "-q", "-e", "a")
    outcome.assert_success()
    reports = outcome.out.splitlines()[-3:]
    assert Matches(r"  congratulations :\) \(.* seconds\)") == reports[-1]
    assert Matches(r"  a: OK \([\d.]+ seconds\)") == reports[-2]


@pytest.mark.integration
def test_result_json_sequential(
    tox_project: ToxProjectCreator,
    enable_pip_pypi_access: str | None,  # noqa: ARG001
) -> None:
    cmd = [
        "- python -c 'import sys; print(\"magic fail\", file=sys.stderr); sys.exit(1)'",
        "python -c 'import sys; print(\"magic pass\"); sys.exit(0)'",
    ]
    project = tox_project(
        {
            "tox.ini": f"[tox]\nenvlist=py\n[testenv]\npackage=wheel\ncommands={cmd[0]}\n {cmd[1]}",
            "setup.py": "from setuptools import setup\nsetup(name='a', version='1.0', py_modules=['run'],"
            "install_requires=['setuptools>44'])",
            "run.py": "print('run')",
            "pyproject.toml": '[build-system]\nrequires=["setuptools","wheel"]\nbuild-backend="setuptools.build_meta"',
        },
    )
    log = project.path / "log.json"
    outcome = project.run("r", "-vv", "-e", "py", "--result-json", str(log))
    outcome.assert_success()
    with log.open("rt") as file_handler:
        log_report = json.load(file_handler)

    py_info = PythonInfo.current_system()
    host_python = {
        "executable": str(Path(py_info.system_executable).resolve()),
        "extra_version_info": None,
        "implementation": py_info.implementation,
        "is_64": py_info.architecture == 64,
        "sysplatform": py_info.platform,
        "version": py_info.version,
        "version_info": list(py_info.version_info),
    }
    packaging_setup = get_cmd_exit_run_id(log_report, ".pkg", "setup")
    assert "result" not in log_report["testenvs"][".pkg"]

    assert packaging_setup[-1][0] in {0, None}
    assert packaging_setup == [
        (0, "install_requires"),
        (None, "_optional_hooks"),
        (None, "get_requires_for_build_wheel"),
        (0, "freeze"),
    ]
    packaging_test = get_cmd_exit_run_id(log_report, ".pkg", "test")
    assert packaging_test == [(None, "build_wheel")]
    packaging_installed = log_report["testenvs"][".pkg"].pop("installed_packages")
    assert {i[: i.find("==")] for i in packaging_installed} == {"pip", "setuptools", "wheel"}

    result_py = log_report["testenvs"]["py"].pop("result")
    assert result_py.pop("duration") > 0
    assert result_py == {"success": True, "exit_code": 0}

    py_setup = get_cmd_exit_run_id(log_report, "py", "setup")
    assert py_setup == [(0, "install_package_deps"), (0, "install_package"), (0, "freeze")]
    py_test = get_cmd_exit_run_id(log_report, "py", "test")
    assert py_test == [(1, "commands[0]"), (0, "commands[1]")]
    packaging_installed = log_report["testenvs"]["py"].pop("installed_packages")
    expected_pkg = {"pip", "setuptools", "wheel", "a"}
    assert {i[: i.find("==")] if "@" not in i else "a" for i in packaging_installed} == expected_pkg
    install_package = log_report["testenvs"]["py"].pop("installpkg")
    assert re.match("^[a-fA-F0-9]{64}$", install_package.pop("sha256"))
    assert install_package == {"basename": "a-1.0-py3-none-any.whl", "type": "file"}

    expected = {
        "reportversion": "1",
        "toxversion": __version__,
        "platform": sys.platform,
        "testenvs": {
            "py": {"python": host_python},
            ".pkg": {"python": host_python},
        },
    }
    assert "host" in log_report
    assert log_report.pop("host")
    assert log_report == expected


def get_cmd_exit_run_id(report: dict[str, Any], name: str, group: str) -> list[tuple[int | None, str]]:
    return [(i["retcode"], i["run_id"]) for i in report["testenvs"][name].pop(group)]


def test_rerun_sequential_skip(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands=python -c 'print(1)'"})
    result_first = proj.run("--root", str(demo_pkg_inline))
    result_first.assert_success()
    result_rerun = proj.run("--root", str(demo_pkg_inline))
    result_rerun.assert_success()


def test_rerun_sequential_wheel(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project(
        {"tox.ini": "[testenv]\npackage=wheel\ncommands=python -c 'from demo_pkg_inline import do; do()'"},
    )
    result_first = proj.run("--root", str(demo_pkg_inline))
    result_first.assert_success()
    result_rerun = proj.run("--root", str(demo_pkg_inline))
    result_rerun.assert_success()


@pytest.mark.integration
def test_rerun_sequential_sdist(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project(
        {"tox.ini": "[testenv]\npackage=sdist\ncommands=python -c 'from demo_pkg_inline import do; do()'"},
    )
    result_first = proj.run("--root", str(demo_pkg_inline))
    result_first.assert_success()
    result_rerun = proj.run("--root", str(demo_pkg_inline))
    result_rerun.assert_success()


def test_recreate_package(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project(
        {"tox.ini": "[testenv]\npackage=wheel\ncommands=python -c 'from demo_pkg_inline import do; do()'"},
    )
    result_first = proj.run("--root", str(demo_pkg_inline), "-r")
    result_first.assert_success()

    result_rerun = proj.run("-r", "--root", str(demo_pkg_inline), "--no-recreate-pkg")
    result_rerun.assert_success()


def test_package_deps_change(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    toml = (demo_pkg_inline / "pyproject.toml").read_text()
    build = (demo_pkg_inline / "build.py").read_text()
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel", "pyproject.toml": toml, "build.py": build})
    proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)

    result_first = proj.run("r")
    result_first.assert_success()
    assert ".pkg: install" not in result_first.out  # no deps initially

    # new deps are picked up
    (proj.path / "pyproject.toml").write_text(toml.replace("requires = [\n]", 'requires = ["wheel"]'))
    (proj.path / "build.py").write_text(build.replace("return []", "return ['setuptools']"))

    result_rerun = proj.run("r")
    result_rerun.assert_success()

    # and installed
    rerun_install = [i for i in result_rerun.out.splitlines() if i.startswith(".pkg: install")]
    assert len(rerun_install) == 2
    assert rerun_install[0].endswith("wheel")
    assert rerun_install[1].endswith("setuptools")


def test_package_build_fails(tox_project: ToxProjectCreator) -> None:
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": '[build-system]\nrequires=[]\nbuild-backend="build"\nbackend-path=["."]',
            "build.py": "",
        },
    )

    result = proj.run("r")
    result.assert_failed(code=1)
    assert "has no attribute 'build_wheel'" in result.out, result.out


def test_backend_not_found(tox_project: ToxProjectCreator) -> None:
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": '[build-system]\nrequires=[]\nbuild-backend="build"',
            "build.py": "",
        },
    )

    result = proj.run("r")
    result.assert_failed(code=-5)
    assert "packaging backend failed (code=-5), with FailedToStart: could not start backend" in result.out, result.out


def test_missing_interpreter_skip_on(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nskip_missing_interpreters=true\n[testenv]\npackage=skip\nbase_python=missing-interpreter"
    proj = tox_project({"tox.ini": ini})

    result = proj.run("r")
    result.assert_failed()
    assert "py: SKIP" in result.out


def test_missing_interpreter_skip_off(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nskip_missing_interpreters=false\n[testenv]\npackage=skip\nbase_python=missing-interpreter"
    proj = tox_project({"tox.ini": ini})

    result = proj.run("r")
    result.assert_failed()
    exp = "py: failed with could not find python interpreter matching any of the specs missing-interpreter"
    assert exp in result.out


def test_env_tmp_dir_reset(tox_project: ToxProjectCreator) -> None:
    ini = '[testenv]\npackage=skip\ncommands=python -c \'import os; os.mkdir(os.path.join( r"{env_tmp_dir}", "a"))\''
    proj = tox_project({"tox.ini": ini})
    result_first = proj.run("r")
    result_first.assert_success()

    result_second = proj.run("r", "-v", "-v")
    result_second.assert_success()
    assert "D clear env temp folder " in result_second.out, result_second.out


def test_env_name_change_recreate(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands=\n"})
    result_first = proj.run("r")
    result_first.assert_success()

    tox_env = result_first.state.envs["py"]
    assert repr(tox_env) == "VirtualEnvRunner(name=py)"
    path = tox_env.env_dir
    with Info(path).compare({"name": "p", "type": "magical"}, ToxEnv.__name__):
        pass

    result_second = proj.run("r")
    result_second.assert_success()
    output = (
        "recreate env because env type changed from {'name': 'p', 'type': 'magical'} "
        "to {'name': 'py', 'type': 'VirtualEnvRunner'}"
    )
    assert output in result_second.out
    assert "py: remove tox env folder" in result_second.out


def test_skip_pkg_install(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel\n"})
    result_first = proj.run("--root", str(demo_pkg_inline), "--skip-pkg-install")
    result_first.assert_success()
    assert result_first.out.startswith("py: skip building and installing the package"), result_first.out


def test_skip_develop_mode(tox_project: ToxProjectCreator, demo_pkg_setuptools: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel\n"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("--root", str(demo_pkg_setuptools), "--develop", "--workdir", str(proj.path / ".tox"))
    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    expected = [
        (".pkg", "install_requires"),
        (".pkg", "_optional_hooks"),
        (".pkg", "get_requires_for_build_editable"),
        (".pkg", "build_editable"),
        ("py", "install_package"),
    ]
    assert calls == expected


def _c(code: int) -> str:
    return f"python -c 'raise SystemExit({code})'"


def test_commands_pre_fail_post_runs(tox_project: ToxProjectCreator) -> None:
    ini = f"[testenv]\npackage=skip\ncommands_pre={_c(8)}\ncommands={_c(0)}\ncommands_post={_c(9)}"
    proj = tox_project({"tox.ini": ini})
    result = proj.run()
    result.assert_failed(code=8)
    assert "commands_pre[0]" in result.out
    assert "commands[0]" not in result.out
    assert "commands_post[0]" in result.out


def test_commands_pre_pass_post_runs_main_fails(tox_project: ToxProjectCreator) -> None:
    ini = f"[testenv]\npackage=skip\ncommands_pre={_c(0)}\ncommands={_c(8)}\ncommands_post={_c(9)}"
    proj = tox_project({"tox.ini": ini})
    result = proj.run()
    result.assert_failed(code=8)
    assert "commands_pre[0]" in result.out
    assert "commands[0]" in result.out
    assert "commands_post[0]" in result.out


def test_commands_post_fails_exit_code(tox_project: ToxProjectCreator) -> None:
    ini = f"[testenv]\npackage=skip\ncommands_pre={_c(0)}\ncommands={_c(0)}\ncommands_post={_c(9)}"
    proj = tox_project({"tox.ini": ini})
    result = proj.run()
    result.assert_failed(code=9)
    assert "commands_pre[0]" in result.out
    assert "commands[0]" in result.out
    assert "commands_post[0]" in result.out


@pytest.mark.parametrize(
    ("pre", "main", "post", "outcome"),
    [
        (0, 8, 0, 8),
        (0, 0, 8, 8),
        (8, 0, 0, 8),
    ],
)
def test_commands_ignore_errors(tox_project: ToxProjectCreator, pre: int, main: int, post: int, outcome: int) -> None:
    def _s(key: str, code: int) -> str:
        return f"\ncommands{key}=\n {_c(code)}\n {'' if code == 0 else _c(code + 1)}"

    ini = f"[testenv]\npackage=skip\nignore_errors=True{_s('_pre', pre)}{_s('', main)}{_s('_post', post)}"
    proj = tox_project({"tox.ini": ini})
    result = proj.run()
    result.assert_failed(code=outcome)
    assert "commands_pre[0]" in result.out
    assert "commands[0]" in result.out
    assert "commands_post[0]" in result.out


def test_ignore_outcome(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nno_package=true\n[testenv]\ncommands=python -c 'exit(1)'\nignore_outcome=true"
    project = tox_project({"tox.ini": ini})
    result = project.run("r")

    result.assert_success()
    reports = result.out.splitlines()

    assert Matches(r"  py: IGNORED FAIL code 1 .*") == reports[-2]
    assert Matches(r"  congratulations :\) .*") == reports[-1]


def test_platform_does_not_match_run_env(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip\nplatform=wrong_platform"
    proj = tox_project({"tox.ini": ini})

    result = proj.run("r")
    result.assert_failed()
    exp = f"py: skipped because platform {sys.platform} does not match wrong_platform"
    assert exp in result.out


def test_platform_matches_run_env(tox_project: ToxProjectCreator) -> None:
    ini = f"[testenv]\npackage=skip\nplatform={sys.platform}"
    proj = tox_project({"tox.ini": ini})
    result = proj.run("r")
    result.assert_success()


def test_platform_does_not_match_package_env(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    toml = (demo_pkg_inline / "pyproject.toml").read_text()
    build = (demo_pkg_inline / "build.py").read_text()
    ini = "[tox]\nenv_list=a,b\n[testenv]\npackage=wheel\n[testenv:.pkg]\nplatform=wrong_platform"
    proj = tox_project({"tox.ini": ini, "pyproject.toml": toml, "build.py": build})
    result = proj.run("r", "-e", "a,b")
    result.assert_failed()  # tox run fails as all envs are skipped
    assert "a: SKIP" in result.out
    assert "b: SKIP" in result.out
    msg = f"skipped because platform {sys.platform} does not match wrong_platform for package environment .pkg"
    assert f"a: {msg}" in result.out
    assert f"b: {msg}" in result.out


def test_sequential_run_all(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nenv_list=a\n[testenv]\npackage=skip\n[testenv:b]"
    outcome = tox_project({"tox.ini": ini}).run("r", "-e", "ALL")
    assert "a: OK" in outcome.out
    assert "b: OK" in outcome.out


def test_virtualenv_cache(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\npackage=skip"
    proj = tox_project({"tox.ini": ini})
    result_first = proj.run("r", "-v", "-v")
    result_first.assert_success()
    assert " create virtual environment via " in result_first.out

    result_second = proj.run("r", "-v", "-v")
    result_second.assert_success()
    assert " create virtual environment via " not in result_second.out


def test_sequential_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("r", "-h")
    outcome.assert_success()


def test_sequential_clears_pkg_at_most_once(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    project = tox_project({"tox.ini": "[tox]\nenv_list=a,b"})
    result = project.run("r", "--root", str(demo_pkg_inline), "-e", "a,b", "-r")
    result.assert_success()


def test_sequential_inserted_env_vars(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    ini = """
    [testenv]
    commands=python -c 'import os; [print(f"{k}={v}") for k, v in os.environ.items() if \
                        k.startswith("TOX_") or k == "VIRTUAL_ENV"]'
    """
    project = tox_project({"tox.ini": ini})
    result = project.run("r", "--root", str(demo_pkg_inline), "--workdir", str(project.path / ".tox"))
    result.assert_success()

    assert re.search(f"TOX_PACKAGE={re.escape(str(project.path))}.*.tar.gz{os.linesep}", result.out)
    assert f"TOX_ENV_NAME=py{os.linesep}" in result.out
    work_dir = project.path / ".tox"
    assert f"TOX_WORK_DIR={work_dir}{os.linesep}" in result.out
    env_dir = work_dir / "py"
    assert f"TOX_ENV_DIR={env_dir}{os.linesep}" in result.out
    assert f"VIRTUAL_ENV={env_dir}{os.linesep}" in result.out


def test_missing_command_success_if_ignored(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\ncommands= - missing-command\nskip_install=true"})
    result = project.run()
    result.assert_success()
    assert "py: command failed but is marked ignore outcome so handling it as success" in result.out
