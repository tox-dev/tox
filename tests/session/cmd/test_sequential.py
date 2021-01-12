import json
import re
import sys
from pathlib import Path
from signal import SIGINT
from subprocess import PIPE, Popen
from time import sleep
from typing import Any, Dict, List, Tuple, Union

import pytest
from re_assert import Matches
from virtualenv.discovery.py_info import PythonInfo

from tox import __version__
from tox.pytest import ToxProjectCreator
from tox.tox_env.api import ToxEnv
from tox.tox_env.info import Info


def test_run_ignore_cmd_exit_code(tox_project: ToxProjectCreator) -> None:
    cmd = [
        "- python -c 'import sys; print(\"magic fail\", file=sys.stderr); sys.exit(1)'",
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


@pytest.mark.timeout(120)
@pytest.mark.integration
def test_result_json_sequential(tox_project: ToxProjectCreator) -> None:
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
        }
    )
    log = project.path / "log.json"
    outcome = project.run("r", "-vv", "-e", "py", "--result-json", str(log))
    outcome.assert_success()
    with log.open("rt") as file_handler:
        log_report = json.load(file_handler)

    py_info = PythonInfo.current_system()
    host_python = {
        "executable": py_info.system_executable,
        "extra_version_info": None,
        "implementation": py_info.implementation,
        "is_64": py_info.architecture == 64,
        "sysplatform": py_info.platform,
        "version": py_info.version,
        "version_info": list(py_info.version_info),
    }
    packaging_setup = get_cmd_exit_run_id(log_report, ".pkg", "setup")

    assert packaging_setup == [
        (0, "install_requires"),
        (None, "get_requires_for_build_wheel"),
        (0, "install_requires_for_build_wheel"),
        (0, "freeze"),
        (None, "_exit"),
    ]
    packaging_test = get_cmd_exit_run_id(log_report, ".pkg", "test")
    assert packaging_test == [(None, "build_wheel")]
    packaging_installed = log_report["testenvs"][".pkg"].pop("installed_packages")
    assert {i[: i.find("==")] for i in packaging_installed} == {"pip", "setuptools", "wheel"}

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


def get_cmd_exit_run_id(report: Dict[str, Any], name: str, group: str) -> List[Tuple[Union[int, None], str]]:
    return [(i["retcode"], i["run_id"]) for i in report["testenvs"][name].pop(group)]


def test_rerun_sequential_skip(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=skip\ncommands=python -c 'print(1)'"})
    result_first = proj.run("--root", str(demo_pkg_inline))
    result_first.assert_success()
    result_rerun = proj.run("--root", str(demo_pkg_inline))
    result_rerun.assert_success()


def test_rerun_sequential_wheel(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project(
        {"tox.ini": "[testenv]\npackage=wheel\ncommands=python -c 'from demo_pkg_inline import do; do()'"}
    )
    result_first = proj.run("--root", str(demo_pkg_inline))
    result_first.assert_success()
    result_rerun = proj.run("--root", str(demo_pkg_inline))
    result_rerun.assert_success()


@pytest.mark.integration
def test_rerun_sequential_sdist(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project(
        {"tox.ini": "[testenv]\npackage=sdist\ncommands=python -c 'from demo_pkg_inline import do; do()'"}
    )
    result_first = proj.run("--root", str(demo_pkg_inline))
    result_first.assert_success()
    result_rerun = proj.run("--root", str(demo_pkg_inline))
    result_rerun.assert_success()


def test_recreate_package(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project(
        {"tox.ini": "[testenv]\npackage=wheel\ncommands=python -c 'from demo_pkg_inline import do; do()'"}
    )
    result_first = proj.run("--root", str(demo_pkg_inline), "-r")
    result_first.assert_success()

    result_rerun = proj.run("-r", "--root", str(demo_pkg_inline), "--no-recreate-pkg")
    result_rerun.assert_success()


def test_package_deps_change(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    toml = (demo_pkg_inline / "pyproject.toml").read_text()
    build = (demo_pkg_inline / "build.py").read_text()
    ini = "[testenv]\npackage=wheel\ncommands=python -c 'from demo_pkg_inline import do; do()'"
    proj = tox_project({"tox.ini": ini, "pyproject.toml": toml, "build.py": build})

    result_first = proj.run("r")
    result_first.assert_success()
    assert ".pkg: install" not in result_first.out  # no deps initially

    # new deps are picked up
    (proj.path / "pyproject.toml").write_text(toml.replace("requires = []", 'requires = ["wheel"]'))
    (proj.path / "build.py").write_text(
        build.replace(
            "def get_requires_for_build_wheel(config_settings):\n    return []",
            "def get_requires_for_build_wheel(config_settings):\n    return ['setuptools']",
        )
    )

    result_rerun = proj.run("r")
    result_rerun.assert_success()

    # and installed
    rerun_install = [i for i in result_rerun.out.splitlines() if i.startswith(".pkg: install")]
    assert len(rerun_install) == 2
    assert rerun_install[0].endswith("wheel")
    assert rerun_install[1].endswith("setuptools")


@pytest.mark.skipif(sys.platform == "win32", reason="You need a conhost shell for keyboard interrupt")
def test_keyboard_interrupt(tox_project: ToxProjectCreator, demo_pkg_inline: Path, tmp_path: Path) -> None:
    marker = tmp_path / "a"
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel\ncommands=python -c "
            f'\'from time import sleep; from pathlib import Path; p = Path("{str(marker)}"); p.write_text("");'
            " sleep(5)'\n"
            "[testenv:dep]\ndepends=py",
            "pyproject.toml": (demo_pkg_inline / "pyproject.toml").read_text(),
            "build.py": (demo_pkg_inline / "build.py").read_text(),
        }
    )
    cmd = [sys.executable, "-m", "tox", "-c", str(proj.path / "tox.ini"), "r", "-e", f"py,py{sys.version_info[0]},dep"]
    process = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    while not marker.exists():
        sleep(0.05)
    process.send_signal(SIGINT)
    out, err = process.communicate()
    assert process.returncode != 0
    assert "KeyboardInterrupt" in err, err
    assert "KeyboardInterrupt - teardown started\n" in out, out
    assert "interrupt tox environment: py\n" in out, out
    assert "requested interrupt of" in out, out
    assert "send signal SIGINT" in out, out
    assert "interrupt finished with success" in out, out
    assert "interrupt tox environment: .pkg" in out, out


def test_package_build_fails(tox_project: ToxProjectCreator) -> None:
    proj = tox_project(
        {
            "tox.ini": "[testenv]\npackage=wheel",
            "pyproject.toml": '[build-system]\nrequires=[]\nbuild-backend="build"\nbackend-path=["."]',
            "build.py": "",
        }
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
        }
    )

    result = proj.run("r")
    result.assert_failed(code=-5)
    assert "packaging backend failed (code=-5), with FailedToStart: could not start backend" in result.out, result.out


def test_missing_interpreter_skip_on(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nskip_missing_interpreters=true\n[testenv]\npackage=skip\nbase_python=missing-interpreter"
    proj = tox_project({"tox.ini": ini})

    result = proj.run("r")
    result.assert_success()
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

    tox_env = result_first.state.tox_env("py")
    assert repr(tox_env) == "VirtualEnvRunner(name=py)"
    path = tox_env.conf["env_dir"]
    with Info(path).compare({"name": "p", "type": "magical"}, ToxEnv.__name__):
        pass

    result_second = proj.run("r")
    result_second.assert_success()
    output = (
        "py: env type changed from {'name': 'p', 'type': 'magical'} to "
        "{'name': 'py', 'type': 'VirtualEnvRunner'}, will recreate"
    )
    assert output in result_second.out
    assert "py: remove tox env folder" in result_second.out


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


def test_skip_pkg_install(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel\n"})
    result_first = proj.run("--root", str(demo_pkg_inline), "--skip-pkg-install")
    result_first.assert_success()
    assert result_first.out.startswith("py: skip building and installing the package"), result_first.out


def test_skip_develop_mode(tox_project: ToxProjectCreator, demo_pkg_setuptools: Path) -> None:
    proj = tox_project({"tox.ini": "[testenv]\npackage=wheel\n"})
    execute_calls = proj.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    result = proj.run("--root", str(demo_pkg_setuptools), "--develop")
    result.assert_success()
    calls = [(i[0][0].conf.name, i[0][3].run_id) for i in execute_calls.call_args_list]
    expected = [
        (".pkg", "install_requires"),
        (".pkg", "get_requires_for_build_wheel"),
        (".pkg", "install_requires_for_build_wheel"),
        (".pkg", "prepare_metadata_for_build_wheel"),
        (".pkg", "get_requires_for_build_sdist"),
        ("py", "install_package_deps"),
        ("py", "install_package"),
        (".pkg", "_exit"),
    ]
    assert calls == expected
