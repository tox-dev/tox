from __future__ import annotations

import sys
from argparse import ArgumentTypeError
from signal import SIGINT
from subprocess import PIPE, Popen
from time import sleep
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from tox.session.cmd.run import parallel
from tox.session.cmd.run.parallel import parse_num_processes
from tox.tox_env.api import ToxEnv
from tox.tox_env.errors import Fail

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tox.pytest import MonkeyPatch, ToxProjectCreator


def test_parse_num_processes_all() -> None:
    assert parse_num_processes("all") is None


def test_parse_num_processes_auto() -> None:
    auto = parse_num_processes("auto")
    assert isinstance(auto, int)
    assert auto > 0


def test_parse_num_processes_exact() -> None:
    assert parse_num_processes("3") == 3


def test_parse_num_processes_not_number() -> None:
    with pytest.raises(ArgumentTypeError, match="value must be a positive number"):
        parse_num_processes("3df")


def test_parse_num_processes_minus_one() -> None:
    with pytest.raises(ArgumentTypeError, match="value must be positive"):
        parse_num_processes("-1")


def test_parallel_general(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, mocker: MockerFixture) -> None:
    def setup(self: ToxEnv) -> None:
        if self.name == "f":
            msg = "something bad happened"
            raise Fail(msg)
        return prev_setup(self)

    prev_setup = ToxEnv._setup_env  # noqa: SLF001
    mocker.patch.object(ToxEnv, "_setup_env", autospec=True, side_effect=setup)
    monkeypatch.setenv("PATH", "")

    ini = """
    [tox]
    no_package=true
    skip_missing_interpreters = true
    env_list= a, b, c, d, e, f
    [testenv]
    commands=python -c 'print("run {env_name}")'
    depends = !c: c
    parallel_show_output = c: true
    [testenv:d]
    base_python = missing_skip
    [testenv:e]
    commands=python -c 'import sys; print("run {env_name}"); sys.exit(1)'
    """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("p", "-p", "all")
    outcome.assert_failed()

    out = outcome.out
    oks, skips, fails = {"a", "b", "c"}, {"d"}, {"e", "f"}
    missing = set()
    for env in "a", "b", "c", "d", "e", "f":
        if env in {"c", "e"}:
            assert "run c" in out, out
        elif env == "f":
            assert "f: failed with something bad happened" in out, out
        else:
            assert f"run {env}" not in out, out
        of_type = "OK" if env in oks else ("SKIP" if env in skips else "FAIL")
        of_type_icon = "✔" if env in oks else ("⚠" if env in skips else "✖")
        env_done = f"{env}: {of_type} {of_type_icon}"
        is_missing = env_done not in out
        if is_missing:
            missing.add(env_done)
        env_report = f"  {env}: {of_type} {'code 1 ' if env in fails else ''}("
        assert env_report in out, out
        if not is_missing:
            assert out.index(env_done) < out.index(env_report), out
    assert len(missing) == 1, out


def test_parallel_run_live_out(tox_project: ToxProjectCreator) -> None:
    ini = """
    [tox]
    no_package=true
    env_list= a, b
    [testenv]
    commands=python -c 'print("run {env_name}")'
    """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("p", "-p", "2", "--parallel-live")
    outcome.assert_success()
    assert "python -c" in outcome.out
    assert "run a" in outcome.out
    assert "run b" in outcome.out


def test_parallel_show_output_with_pkg(tox_project: ToxProjectCreator, demo_pkg_inline: Path) -> None:
    ini = "[testenv]\nparallel_show_output=True\ncommands=python -c 'print(\"r {env_name}\")'"
    project = tox_project({"tox.ini": ini})
    result = project.run("p", "--root", str(demo_pkg_inline))
    assert "r py" in result.out


@pytest.mark.skipif(sys.platform == "win32", reason="You need a conhost shell for keyboard interrupt")
@pytest.mark.flaky(max_runs=3, min_passes=1)
def test_keyboard_interrupt(tox_project: ToxProjectCreator, demo_pkg_inline: Path, tmp_path: Path) -> None:
    marker = tmp_path / "a"
    ini = f"""
    [testenv]
    package=wheel
    commands=python -c 'from time import sleep; from pathlib import Path; \
                        p = Path("{marker!s}"); p.write_text(""); sleep(100)'
    [testenv:dep]
    depends=py
    """
    proj = tox_project(
        {
            "tox.ini": ini,
            "pyproject.toml": (demo_pkg_inline / "pyproject.toml").read_text(),
            "build.py": (demo_pkg_inline / "build.py").read_text(),
        },
    )
    cmd = ["-c", str(proj.path / "tox.ini"), "p", "-p", "1", "-e", f"py,py{sys.version_info[0]},dep"]
    process = Popen([sys.executable, "-m", "tox", *cmd], stdout=PIPE, stderr=PIPE, universal_newlines=True)
    while not marker.exists() and (process.poll() is None):
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


def test_parallels_help(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("p", "-h")
    outcome.assert_success()


def test_parallel_legacy_accepts_no_arg(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("-p", "-h")
    outcome.assert_success()


def test_parallel_requires_arg(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("p", "-p", "-h")
    outcome.assert_failed()
    assert "argument -p/--parallel: expected one argument" in outcome.err


def test_parallel_no_spinner(tox_project: ToxProjectCreator) -> None:
    """Ensure passing `--parallel-no-spinner` implies `--parallel`."""
    with mock.patch.object(parallel, "execute") as mocked:
        tox_project({"tox.ini": ""}).run("p", "--parallel-no-spinner")

    mocked.assert_called_once_with(
        mock.ANY,
        max_workers=None,
        has_spinner=False,
        live=False,
    )


def test_parallel_no_spinner_ci(
    tox_project: ToxProjectCreator, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure spinner is disabled by default in CI."""
    mocked = mocker.patch.object(parallel, "execute")
    monkeypatch.setenv("CI", "1")

    tox_project({"tox.ini": ""}).run("p")

    mocked.assert_called_once_with(
        mock.ANY,
        max_workers=None,
        has_spinner=False,
        live=False,
    )


def test_parallel_no_spinner_legacy(tox_project: ToxProjectCreator) -> None:
    with mock.patch.object(parallel, "execute") as mocked:
        tox_project({"tox.ini": ""}).run("--parallel-no-spinner")

    mocked.assert_called_once_with(
        mock.ANY,
        max_workers=None,
        has_spinner=False,
        live=False,
    )
