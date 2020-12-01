from argparse import ArgumentTypeError

import pytest
from pytest_mock import MockerFixture

from tox.pytest import MonkeyPatch, ToxProjectCreator
from tox.session.cmd.run.parallel import parse_num_processes
from tox.tox_env.api import ToxEnv
from tox.tox_env.errors import Fail


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
        if self.conf["env_name"] == "f":
            raise Fail("something bad happened")
        return prev_setup(self)

    prev_setup = ToxEnv.setup
    mocker.patch.object(ToxEnv, "setup", autospec=True, side_effect=setup)
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
    for env in "a", "b", "c", "d", "e", "f":
        if env in ("c", "e"):
            assert "run c" in out, out
        elif env == "f":
            assert "f: failed with something bad happened" in out, out
        else:
            assert f"run {env}" not in out, out
        of_type = "OK" if env in oks else ("SKIP" if env in skips else "FAIL")
        of_type_icon = "✔" if env in oks else ("⚠" if env in skips else "✖")
        env_done = f"{env}: {of_type} {of_type_icon}"
        assert env_done in out, out

        env_report = f"  {env}: {of_type} {'code 1 ' if env in fails else ''}("
        assert env_report in out, out
        assert out.index(env_done) < out.index(env_report), out


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
