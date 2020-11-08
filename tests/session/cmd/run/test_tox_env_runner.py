import json
import re
import sys
from typing import Any, Dict, List, Tuple

import pytest
from virtualenv.discovery.py_info import PythonInfo

from tox import __version__
from tox.pytest import ToxProjectCreator


def test_ignore_cmd(tox_project: ToxProjectCreator) -> None:
    cmd = [
        "- python -c 'import sys; print(\"magic fail\", file=sys.stderr); sys.exit(1)'",
        "python -c 'import sys; print(\"magic pass\"); sys.exit(0)'",
    ]
    project = tox_project({"tox.ini": f"[tox]\nenvlist=py\nno_package=true\n[testenv]\ncommands={cmd[0]}\n {cmd[1]}"})
    outcome = project.run("r", "-e", "py")
    outcome.assert_success()
    assert "magic pass" in outcome.out
    assert "magic fail" in outcome.err


@pytest.mark.timeout(60)
@pytest.mark.integration
def test_result_json_run_one(tox_project: ToxProjectCreator) -> None:
    cmd = [
        "- python -c 'import sys; print(\"magic fail\", file=sys.stderr); sys.exit(1)'",
        "python -c 'import sys; print(\"magic pass\"); sys.exit(0)'",
    ]
    project = tox_project(
        {
            "tox.ini": f"[tox]\nenvlist=py\nnpackage=wheel\n[testenv]\ncommands={cmd[0]}\n {cmd[1]}",
            "setup.py": "from setuptools import setup\nsetup(name='a', version='1.0', py_modules=['run'],"
            "install_requires=['setuptools>44'])",
            "run.py": "print('run')",
            "pyproject.toml": '[build-system]\nrequires=["setuptools","wheel"]\nbuild-backend="setuptools.build_meta"',
        }
    )
    log = project.path / "log.json"
    outcome = project.run("r", "-e", "py", "--result-json", str(log))

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

    packaging_setup = get_cmd_exit_run_id(log_report, ".package", "setup")
    assert packaging_setup == [(0, "install"), (0, "build requires"), (0, "freeze"), (0, "package meta")]
    packaging_test = get_cmd_exit_run_id(log_report, ".package", "test")
    assert packaging_test == [(0, "build")]
    packaging_installed = log_report["testenvs"][".package"].pop("installed_packages")
    assert {i[: i.find("==")] for i in packaging_installed} == {"pip", "setuptools", "wheel"}

    py_setup = get_cmd_exit_run_id(log_report, "py", "setup")
    assert py_setup == [(0, "install"), (0, "install"), (0, "freeze")]  # install => 1 dep and 1 package
    py_test = get_cmd_exit_run_id(log_report, "py", "test")
    assert py_test == [(1, "commands[0]"), (0, "commands[1]")]
    packaging_installed = log_report["testenvs"]["py"].pop("installed_packages")
    expected_pkg = {"pip", "setuptools", "wheel", "a"}
    assert {i[: i.find("==")] if "@" not in i else "a" for i in packaging_installed} == expected_pkg
    install_package = log_report["testenvs"]["py"].pop("installpkg")
    assert re.match("^[a-fA-F0-9]{64}$", install_package.pop("sha256"))
    assert install_package == {"basename": "a-1.0.tar.gz", "type": "file"}

    expected = {
        "reportversion": "1",
        "toxversion": __version__,
        "platform": sys.platform,
        "testenvs": {
            "py": {"python": host_python},
            ".package": {"python": host_python},
        },
    }
    assert "host" in log_report
    assert log_report.pop("host")
    assert log_report == expected


def get_cmd_exit_run_id(report: Dict[str, Any], name: str, group: str) -> List[Tuple[int, str]]:
    return [(i["retcode"], i["run_id"]) for i in report["testenvs"][name].pop(group)]
