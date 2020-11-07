import json
import sys

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


def test_result_json_run_one(tox_project: ToxProjectCreator) -> None:
    cmd = [
        "- python -c 'import sys; print(\"magic fail\", file=sys.stderr); sys.exit(1)'",
        "python -c 'import sys; print(\"magic pass\"); sys.exit(0)'",
    ]
    project = tox_project({"tox.ini": f"[tox]\nenvlist=py\nno_package=true\n[testenv]\ncommands={cmd[0]}\n {cmd[1]}"})
    log = project.path / "log.json"
    outcome = project.run("r", "-e", "py", "--result-json", str(log))

    outcome.assert_success()
    with log.open("rt") as file_handler:
        log_report = json.load(file_handler)

    py_info = PythonInfo.current_system()
    expected = {
        "reportversion": "1",
        "toxversion": __version__,
        "commands": [],
        "platform": sys.platform,
        "testenvs": {
            "py": {
                "python": {
                    "executable": py_info.system_executable,
                    "extra_version_info": None,
                    "implementation": py_info.implementation,
                    "is_64": py_info.architecture == 64,
                    "sysplatform": py_info.platform,
                    "version": py_info.version,
                    "version_info": list(py_info.version_info),
                },
            },
        },
    }
    assert "host" in log_report
    assert log_report.pop("host")
    assert log_report == expected
