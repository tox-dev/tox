import os
import pipes
import sys
import textwrap
from threading import Thread

import pytest

import tox
from tox.exception import MissingDependency, MissingDirectory
from tox.package import resolve_package
from tox.reporter import Verbosity


def test_resolve_pkg_missing_directory(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    spec = distshare.join("pkg123-*")
    with pytest.raises(MissingDirectory):
        resolve_package(spec)


def test_resolve_pkg_missing_directory_in_distshare(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    spec = distshare.join("pkg123-*")
    distshare.ensure(dir=1)
    with pytest.raises(MissingDependency):
        resolve_package(spec)


def test_resolve_pkg_multiple_valid_versions(tmpdir, mocksession):
    mocksession.logging_levels(quiet=Verbosity.DEFAULT, verbose=Verbosity.DEBUG)
    distshare = tmpdir.join("distshare")
    distshare.ensure("pkg123-1.3.5.zip")
    p = distshare.ensure("pkg123-1.4.5.zip")
    result = resolve_package(distshare.join("pkg123-*"))
    assert result == p
    mocksession.report.expect("info", "determin*pkg123*")


def test_resolve_pkg_with_invalid_version(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")

    distshare.ensure("pkg123-1.something_bad.zip")
    distshare.ensure("pkg123-1.3.5.zip")
    p = distshare.ensure("pkg123-1.4.5.zip")

    result = resolve_package(distshare.join("pkg123-*"))
    mocksession.report.expect("warning", "*1.something_bad*")
    assert result == p


def test_resolve_pkg_with_alpha_version(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    distshare.ensure("pkg123-1.3.5.zip")
    distshare.ensure("pkg123-1.4.5a1.tar.gz")
    p = distshare.ensure("pkg123-1.4.5.zip")
    result = resolve_package(distshare.join("pkg123-*"))
    assert result == p


def test_resolve_pkg_doubledash(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    p = distshare.ensure("pkg-mine-1.3.0.zip")
    res = resolve_package(distshare.join("pkg-mine*"))
    assert res == p
    distshare.ensure("pkg-mine-1.3.0a1.zip")
    res = resolve_package(distshare.join("pkg-mine*"))
    assert res == p


def test_skip_sdist(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "setup.py": """
            syntax error
        """,
            "tox.ini": """
            [tox]
            skipsdist=True
            [testenv]
            commands=python -c "print('done')"
        """,
        },
    )
    result = cmd()
    result.assert_success()


def test_skip_install_skip_package(cmd, initproj, mock_venv):
    initproj(
        "pkg123-0.7",
        filedefs={
            "setup.py": """raise RuntimeError""",
            "tox.ini": """
            [tox]
            envlist = py

            [testenv]
            skip_install = true
        """,
        },
    )
    result = cmd("--notest")
    result.assert_success()


@pytest.fixture()
def venv_filter_project(initproj, cmd):
    def func(*args):
        initproj(
            "pkg123-0.7",
            filedefs={
                "tox.ini": """
                    [tox]
                    envlist = {py27,py36}-{nocov,cov,diffcov}{,-extra}
                    skipsdist = true

                    [testenv]
                    skip_install = true
                    commands = python -c 'print("{envname}")'
                """
            },
        )
        result = cmd(*args)
        result.assert_success(is_run_test_env=False)
        active = [i.name for i in result.session.existing_venvs.values()]
        return active, result

    yield func


def test_venv_filter_empty_all_active(venv_filter_project, monkeypatch):
    monkeypatch.delenv("TOX_SKIP_ENV", raising=False)
    active, result = venv_filter_project("-a")
    assert result.outlines == [
        "py27-nocov",
        "py27-nocov-extra",
        "py27-cov",
        "py27-cov-extra",
        "py27-diffcov",
        "py27-diffcov-extra",
        "py36-nocov",
        "py36-nocov-extra",
        "py36-cov",
        "py36-cov-extra",
        "py36-diffcov",
        "py36-diffcov-extra",
    ]
    assert active == result.outlines


def test_venv_filter_match_all_none_active(venv_filter_project, monkeypatch):
    monkeypatch.setenv("TOX_SKIP_ENV", ".*")
    active, result = venv_filter_project("-a")
    assert not active
    existing_envs = result.outlines

    _, result = venv_filter_project("-avv")
    for name in existing_envs:
        msg = "skip environment {}, matches filter '.*'".format(name)
        assert msg in result.outlines


def test_venv_filter_match_some_some_active(venv_filter_project, monkeypatch):
    monkeypatch.setenv("TOX_SKIP_ENV", "py27.*")
    active, result = venv_filter_project("-avvv")
    assert active == [
        "py36-nocov",
        "py36-nocov-extra",
        "py36-cov",
        "py36-cov-extra",
        "py36-diffcov",
        "py36-diffcov-extra",
    ]


@pytest.fixture()
def popen_env_test(initproj, cmd, monkeypatch):
    def func(tox_env, isolated_build):
        files = {
            "tox.ini": """
               [tox]
               isolated_build = {}
               [testenv:{}]
               commands = python -c "print('ok')"
               """.format(
                "True" if isolated_build else "False", tox_env
            )
        }
        if isolated_build:
            files[
                "pyproject.toml"
            ] = """
                [build-system]
                requires = ["setuptools >= 35.0.2", "setuptools_scm >= 2.0.0, <3"]
                build-backend = 'setuptools.build_meta'
                """
        initproj("env_var_test", filedefs=files)

        class IsolatedResult(object):
            def __init__(self):
                self.popens = []
                self.cwd = None

        res = IsolatedResult()

        class EnvironmentTestRun(Thread):
            """we wrap this invocation into a thread to avoid modifying in any way the
             current threads environment variable (e.g. on failure of this test incorrect teardown)
             """

            def run(self):
                prev_build = tox.session.build_session

                def build_session(config):
                    res.session = prev_build(config)
                    res._popen = res.session.popen
                    monkeypatch.setattr(res.session, "popen", popen)
                    return res.session

                monkeypatch.setattr(tox.session, "build_session", build_session)

                def popen(cmd, **kwargs):
                    activity_id = _actions[-1].name
                    activity_name = _actions[-1].activity
                    ret = "NOTSET"
                    try:
                        ret = res._popen(cmd, **kwargs)
                    except tox.exception.InvocationError as exception:
                        ret = exception
                    finally:
                        res.popens.append(
                            (activity_id, activity_name, kwargs.get("env"), ret, cmd)
                        )
                    return ret

                _actions = []
                from tox.action import Action

                _prev_enter = Action.__enter__

                def enter(self):
                    _actions.append(self)
                    return _prev_enter(self)

                monkeypatch.setattr(Action, "__enter__", enter)

                _prev_exit = Action.__exit__

                def exit_func(self, *args, **kwargs):
                    del _actions[_actions.index(self)]
                    _prev_exit(self, *args, **kwargs)

                monkeypatch.setattr(Action, "__exit__", exit_func)

                res.result = cmd("-e", tox_env)
                res.cwd = os.getcwd()

        thread = EnvironmentTestRun()
        thread.start()
        thread.join()
        return res

    yield func


@pytest.mark.network
def test_tox_env_var_flags_inserted_non_isolated(popen_env_test):
    res = popen_env_test("py", False)
    assert_popen_env(res)


@pytest.mark.network
def test_tox_env_var_flags_inserted_isolated(popen_env_test):
    res = popen_env_test("py", True)
    assert_popen_env(res)


def assert_popen_env(res):
    res.result.assert_success()
    for tox_id, _, env, __, ___ in res.popens:
        assert env["TOX_WORK_DIR"] == os.path.join(res.cwd, ".tox")
        if tox_id != "GLOB":
            assert env["TOX_ENV_NAME"] == tox_id
            assert env["TOX_ENV_DIR"] == os.path.join(res.cwd, ".tox", tox_id)


def test_command_prev_post_ok(cmd, initproj, mock_venv):
    initproj(
        "pkg_command_test_123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            envlist = py

            [testenv]
            commands_pre = python -c 'print("pre")'
            commands = python -c 'print("command")'
            commands_post = python -c 'print("post")'
        """
        },
    )
    result = cmd()
    result.assert_success()
    expected = textwrap.dedent(
        """
        py run-test-pre: commands[0] | python -c 'print("pre")'
        pre
        py run-test: commands[0] | python -c 'print("command")'
        command
        py run-test-post: commands[0] | python -c 'print("post")'
        post
        ___________________________________ summary ___________________________________{}
          py: commands succeeded
          congratulations :)
    """.format(
            "_" if sys.platform != "win32" else ""
        )
    ).lstrip()
    have = result.out.replace(os.linesep, "\n")
    actual = have[len(have) - len(expected) :]
    assert actual == expected


def test_command_prev_fail_command_skip_post_run(cmd, initproj, mock_venv):
    initproj(
        "pkg_command_test_123-0.7",
        filedefs={
            "tox.ini": """
                [tox]
                envlist = py

                [testenv]
                commands_pre = python -c 'raise SystemExit(2)'
                commands = python -c 'print("command")'
                commands_post = python -c 'print("post")'
            """
        },
    )
    result = cmd()
    result.assert_fail()
    expected = textwrap.dedent(
        """
            py run-test-pre: commands[0] | python -c 'raise SystemExit(2)'
            ERROR: InvocationError for command {} -c 'raise SystemExit(2)' (exited with code 2)
            py run-test-post: commands[0] | python -c 'print("post")'
            post
            ___________________________________ summary ___________________________________{}
            ERROR:   py: commands failed
        """.format(
            pipes.quote(sys.executable), "_" if sys.platform != "win32" else ""
        )
    )
    have = result.out.replace(os.linesep, "\n")
    actual = have[len(have) - len(expected) :]
    assert actual == expected


def test_help_compound_ve_works(cmd, initproj, monkeypatch):
    initproj("test-0.1", {"tox.ini": ""})
    result = cmd("-ve", "py", "-a")
    result.assert_success(is_run_test_env=False)
    assert not result.err
    assert result.outlines[0].startswith("using")
    assert result.outlines[1].startswith("using")
    assert result.outlines[2] == "additional environments:"
    assert result.outlines[3] == "py -> [no description]"
    assert len(result.outlines) == 4
