import os
import sys

import py
import pytest

import tox
from tox.interpreters import NoInterpreterInfo
from tox.venv import (
    CreationConfig,
    VirtualEnv,
    getdigest,
    prepend_shebang_interpreter,
    tox_testenv_create,
    tox_testenv_install_deps,
)


def test_getdigest(tmpdir):
    assert getdigest(tmpdir) == "0" * 32


def test_getsupportedinterpreter(monkeypatch, newconfig, mocksession):
    config = newconfig(
        [],
        """
        [testenv:python]
        basepython={}
    """.format(
            sys.executable
        ),
    )
    venv = VirtualEnv(config.envconfigs["python"], session=mocksession)
    interp = venv.getsupportedinterpreter()
    # realpath needed for debian symlinks
    assert py.path.local(interp).realpath() == py.path.local(sys.executable).realpath()
    monkeypatch.setattr(tox.INFO, "IS_WIN", True)
    monkeypatch.setattr(venv.envconfig, "basepython", "jython")
    with pytest.raises(tox.exception.UnsupportedInterpreter):
        venv.getsupportedinterpreter()
    monkeypatch.undo()
    monkeypatch.setattr(venv.envconfig, "envname", "py1")
    monkeypatch.setattr(venv.envconfig, "basepython", "notexistingpython")
    with pytest.raises(tox.exception.InterpreterNotFound):
        venv.getsupportedinterpreter()
    monkeypatch.undo()
    # check that we properly report when no version_info is present
    info = NoInterpreterInfo(name=venv.name)
    info.executable = "something"
    monkeypatch.setattr(config.interpreters, "get_info", lambda *args, **kw: info)
    with pytest.raises(tox.exception.InvocationError):
        venv.getsupportedinterpreter()


def test_create(mocksession, newconfig):
    config = newconfig(
        [],
        """
        [testenv:py123]
    """,
    )
    envconfig = config.envconfigs["py123"]
    venv = VirtualEnv(envconfig, session=mocksession)
    assert venv.path == envconfig.envdir
    assert not venv.path.check()
    action = mocksession.newaction(venv, "getenv")
    tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) >= 1
    args = pcalls[0].args
    assert "virtualenv" == str(args[2])
    if not tox.INFO.IS_WIN:
        # realpath is needed for stuff like the debian symlinks
        our_sys_path = py.path.local(sys.executable).realpath()
        assert our_sys_path == py.path.local(args[0]).realpath()
        # assert Envconfig.toxworkdir in args
        assert venv.getcommandpath("easy_install", cwd=py.path.local())
    interp = venv._getliveconfig().python
    assert interp == venv.envconfig.python_info.executable
    assert venv.path_config.check(exists=False)


def test_commandpath_venv_precedence(tmpdir, monkeypatch, mocksession, newconfig):
    config = newconfig(
        [],
        """
        [testenv:py123]
    """,
    )
    envconfig = config.envconfigs["py123"]
    venv = VirtualEnv(envconfig, session=mocksession)
    tmpdir.ensure("easy_install")
    monkeypatch.setenv("PATH", str(tmpdir), prepend=os.pathsep)
    envconfig.envbindir.ensure("easy_install")
    p = venv.getcommandpath("easy_install")
    assert py.path.local(p).relto(envconfig.envbindir), p


def test_create_sitepackages(mocksession, newconfig):
    config = newconfig(
        [],
        """
        [testenv:site]
        sitepackages=True

        [testenv:nosite]
        sitepackages=False
    """,
    )
    envconfig = config.envconfigs["site"]
    venv = VirtualEnv(envconfig, session=mocksession)
    action = mocksession.newaction(venv, "getenv")
    tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) >= 1
    args = pcalls[0].args
    assert "--system-site-packages" in map(str, args)
    mocksession._clearmocks()

    envconfig = config.envconfigs["nosite"]
    venv = VirtualEnv(envconfig, session=mocksession)
    action = mocksession.newaction(venv, "getenv")
    tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) >= 1
    args = pcalls[0].args
    assert "--system-site-packages" not in map(str, args)
    assert "--no-site-packages" not in map(str, args)


def test_install_deps_wildcard(newmocksession):
    mocksession = newmocksession(
        [],
        """
        [tox]
        distshare = {toxworkdir}/distshare
        [testenv:py123]
        deps=
            {distshare}/dep1-*
    """,
    )
    venv = mocksession.getenv("py123")
    action = mocksession.newaction(venv, "getenv")
    tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    distshare = venv.session.config.distshare
    distshare.ensure("dep1-1.0.zip")
    distshare.ensure("dep1-1.1.zip")

    tox_testenv_install_deps(action=action, venv=venv)
    assert len(pcalls) == 2
    args = pcalls[-1].args
    assert pcalls[-1].cwd == venv.envconfig.config.toxinidir
    assert "pip" in str(args[0])
    assert args[1] == "install"
    args = [arg for arg in args if str(arg).endswith("dep1-1.1.zip")]
    assert len(args) == 1


def test_install_deps_indexserver(newmocksession):
    mocksession = newmocksession(
        [],
        """
        [tox]
        indexserver =
            abc = ABC
            abc2 = ABC
        [testenv:py123]
        deps=
            dep1
            :abc:dep2
            :abc2:dep3
    """,
    )
    venv = mocksession.getenv("py123")
    action = mocksession.newaction(venv, "getenv")
    tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    pcalls[:] = []

    tox_testenv_install_deps(action=action, venv=venv)
    # two different index servers, two calls
    assert len(pcalls) == 3
    args = " ".join(pcalls[0].args)
    assert "-i " not in args
    assert "dep1" in args

    args = " ".join(pcalls[1].args)
    assert "-i ABC" in args
    assert "dep2" in args
    args = " ".join(pcalls[2].args)
    assert "-i ABC" in args
    assert "dep3" in args


def test_install_deps_pre(newmocksession):
    mocksession = newmocksession(
        [],
        """
        [testenv]
        pip_pre=true
        deps=
            dep1
    """,
    )
    venv = mocksession.getenv("python")
    action = mocksession.newaction(venv, "getenv")
    tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    pcalls[:] = []

    tox_testenv_install_deps(action=action, venv=venv)
    assert len(pcalls) == 1
    args = " ".join(pcalls[0].args)
    assert "--pre " in args
    assert "dep1" in args


def test_installpkg_indexserver(newmocksession, tmpdir):
    mocksession = newmocksession(
        [],
        """
        [tox]
        indexserver =
            default = ABC
    """,
    )
    venv = mocksession.getenv("python")
    pcalls = mocksession._pcalls
    p = tmpdir.ensure("distfile.tar.gz")
    mocksession.installpkg(venv, p)
    # two different index servers, two calls
    assert len(pcalls) == 1
    args = " ".join(pcalls[0].args)
    assert "-i ABC" in args


def test_install_recreate(newmocksession, tmpdir):
    pkg = tmpdir.ensure("package.tar.gz")
    mocksession = newmocksession(
        ["--recreate"],
        """
        [testenv]
        deps=xyz
    """,
    )
    venv = mocksession.getenv("python")

    action = mocksession.newaction(venv, "update")
    venv.update(action)
    mocksession.installpkg(venv, pkg)
    mocksession.report.expect("verbosity0", "*create*")
    venv.update(action)
    mocksession.report.expect("verbosity0", "*recreate*")


def test_install_wheel_extras(newmocksession):
    mocksession = newmocksession(
        [],
        """
        [testenv]
        extras = testing
            development
    """,
    )
    venv = mocksession.getenv("python")
    action = mocksession.newaction(venv, "getenv")
    tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    pcalls[:] = []

    venv.installpkg("distfile.whl", action=action)
    assert "distfile.whl[testing,development]" in pcalls[-1].args


def test_develop_extras(newmocksession, tmpdir):
    mocksession = newmocksession(
        [],
        """
        [testenv]
        extras = testing
            development
    """,
    )
    venv = mocksession.getenv("python")
    action = mocksession.newaction(venv, "getenv")
    tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    pcalls[:] = []

    venv.developpkg(tmpdir, action=action)
    expected = "{}[testing,development]".format(tmpdir.strpath)
    assert expected in pcalls[-1].args


def test_env_variables_added_to_needs_reinstall(tmpdir, mocksession, newconfig, monkeypatch):
    tmpdir.ensure("setup.py")
    monkeypatch.setenv("TEMP_PASS_VAR", "123")
    monkeypatch.setenv("TEMP_NOPASS_VAR", "456")
    config = newconfig(
        [],
        """
        [testenv:python]
        passenv = temp_pass_var
        setenv =
            CUSTOM_VAR = 789
    """,
    )

    venv = VirtualEnv(config.envconfigs["python"], session=mocksession)
    action = mocksession.newaction(venv, "hello")

    venv._needs_reinstall(tmpdir, action)

    pcalls = mocksession._pcalls
    assert len(pcalls) == 2
    env = pcalls[0].env

    # should have access to setenv vars
    assert "CUSTOM_VAR" in env
    assert env["CUSTOM_VAR"] == "789"

    # should have access to passenv vars
    assert "TEMP_PASS_VAR" in env
    assert env["TEMP_PASS_VAR"] == "123"

    # should also have access to full invocation environment,
    # for backward compatibility, and to match behavior of venv.run_install_command()
    assert "TEMP_NOPASS_VAR" in env
    assert env["TEMP_NOPASS_VAR"] == "456"


def test_test_hashseed_is_in_output(newmocksession, monkeypatch):
    seed = "123456789"
    monkeypatch.setattr("tox.config.make_hashseed", lambda: seed)
    mocksession = newmocksession([], "")
    venv = mocksession.getenv("python")
    action = mocksession.newaction(venv, "update")
    venv.update(action)
    venv.test()
    mocksession.report.expect("verbosity0", "runtests: PYTHONHASHSEED='{}'".format(seed))


def test_test_runtests_action_command_is_in_output(newmocksession):
    mocksession = newmocksession(
        [],
        """
        [testenv]
        commands = echo foo bar
    """,
    )
    venv = mocksession.getenv("python")
    action = mocksession.newaction(venv, "update")
    venv.update(action)
    venv.test()
    mocksession.report.expect("verbosity0", "*runtests*commands?0? | echo foo bar")


def test_install_error(newmocksession):
    mocksession = newmocksession(
        ["--recreate"],
        """
        [testenv]
        deps=xyz
        commands=
            qwelkqw
    """,
    )
    venv = mocksession.getenv("python")
    venv.test()
    mocksession.report.expect("error", "*not find*qwelkqw*")
    assert venv.status == "commands failed"


def test_install_command_not_installed(newmocksession):
    mocksession = newmocksession(
        ["--recreate"],
        """
        [testenv]
        commands=
            pytest
    """,
    )
    venv = mocksession.getenv("python")
    venv.test()
    mocksession.report.expect("warning", "*test command found but not*")
    assert venv.status == 0


def test_install_command_whitelisted(newmocksession):
    mocksession = newmocksession(
        ["--recreate"],
        """
        [testenv]
        whitelist_externals = pytest
                              xy*
        commands=
            pytest
            xyz
    """,
    )
    venv = mocksession.getenv("python")
    venv.test()
    mocksession.report.expect("warning", "*test command found but not*", invert=True)
    assert venv.status == "commands failed"


def test_install_command_not_installed_bash(newmocksession):
    mocksession = newmocksession(
        ["--recreate"],
        """
        [testenv]
        commands=
            bash
    """,
    )
    venv = mocksession.getenv("python")
    venv.test()
    mocksession.report.expect("warning", "*test command found but not*")


def test_install_python3(newmocksession):
    if not py.path.local.sysfind("python3"):
        pytest.skip("needs python3")
    mocksession = newmocksession(
        [],
        """
        [testenv:py123]
        basepython=python3
        deps=
            dep1
            dep2
    """,
    )
    venv = mocksession.getenv("py123")
    action = mocksession.newaction(venv, "getenv")
    tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    args = pcalls[0].args
    assert str(args[2]) == "virtualenv"
    pcalls[:] = []
    action = mocksession.newaction(venv, "hello")
    venv._install(["hello"], action=action)
    assert len(pcalls) == 1
    args = pcalls[0].args
    assert "pip" in args[0]
    for _ in args:
        assert "--download-cache" not in args, args


class TestCreationConfig:
    def test_basic(self, newconfig, mocksession, tmpdir):
        config = newconfig([], "")
        envconfig = config.envconfigs["python"]
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        assert cconfig.matches(cconfig)
        path = tmpdir.join("configdump")
        cconfig.writeconfig(path)
        newconfig = CreationConfig.readconfig(path)
        assert newconfig.matches(cconfig)
        assert cconfig.matches(newconfig)

    def test_matchingdependencies(self, newconfig, mocksession):
        config = newconfig(
            [],
            """
            [testenv]
            deps=abc
        """,
        )
        envconfig = config.envconfigs["python"]
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        config = newconfig(
            [],
            """
            [testenv]
            deps=xyz
        """,
        )
        envconfig = config.envconfigs["python"]
        venv = VirtualEnv(envconfig, session=mocksession)
        otherconfig = venv._getliveconfig()
        assert not cconfig.matches(otherconfig)

    def test_matchingdependencies_file(self, newconfig, mocksession):
        config = newconfig(
            [],
            """
            [tox]
            distshare={toxworkdir}/distshare
            [testenv]
            deps=abc
                 {distshare}/xyz.zip
        """,
        )
        xyz = config.distshare.join("xyz.zip")
        xyz.ensure()
        envconfig = config.envconfigs["python"]
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        assert cconfig.matches(cconfig)
        xyz.write("hello")
        newconfig = venv._getliveconfig()
        assert not cconfig.matches(newconfig)

    def test_matchingdependencies_latest(self, newconfig, mocksession):
        config = newconfig(
            [],
            """
            [tox]
            distshare={toxworkdir}/distshare
            [testenv]
            deps={distshare}/xyz-*
        """,
        )
        config.distshare.ensure("xyz-1.2.0.zip")
        xyz2 = config.distshare.ensure("xyz-1.2.1.zip")
        envconfig = config.envconfigs["python"]
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        md5, path = cconfig.deps[0]
        assert path == xyz2
        assert md5 == path.computehash()

    def test_python_recreation(self, tmpdir, newconfig, mocksession):
        pkg = tmpdir.ensure("package.tar.gz")
        config = newconfig([], "")
        envconfig = config.envconfigs["python"]
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        action = mocksession.newaction(venv, "update")
        venv.update(action)
        assert not venv.path_config.check()
        mocksession.installpkg(venv, pkg)
        assert venv.path_config.check()
        assert mocksession._pcalls
        args1 = map(str, mocksession._pcalls[0].args)
        assert "virtualenv" in " ".join(args1)
        mocksession.report.expect("*", "*create*")
        # modify config and check that recreation happens
        mocksession._clearmocks()
        action = mocksession.newaction(venv, "update")
        venv.update(action)
        mocksession.report.expect("*", "*reusing*")
        mocksession._clearmocks()
        action = mocksession.newaction(venv, "update")
        cconfig.python = py.path.local("balla")
        cconfig.writeconfig(venv.path_config)
        venv.update(action)
        mocksession.report.expect("verbosity0", "*recreate*")

    def test_dep_recreation(self, newconfig, mocksession):
        config = newconfig([], "")
        envconfig = config.envconfigs["python"]
        venv = VirtualEnv(envconfig, session=mocksession)
        action = mocksession.newaction(venv, "update")
        venv.update(action)
        cconfig = venv._getliveconfig()
        cconfig.deps[:] = [("1" * 32, "xyz.zip")]
        cconfig.writeconfig(venv.path_config)
        mocksession._clearmocks()
        action = mocksession.newaction(venv, "update")
        venv.update(action)
        mocksession.report.expect("*", "*recreate*")

    def test_develop_recreation(self, newconfig, mocksession):
        config = newconfig([], "")
        envconfig = config.envconfigs["python"]
        venv = VirtualEnv(envconfig, session=mocksession)
        action = mocksession.newaction(venv, "update")
        venv.update(action)
        cconfig = venv._getliveconfig()
        cconfig.usedevelop = True
        cconfig.writeconfig(venv.path_config)
        mocksession._clearmocks()
        action = mocksession.newaction(venv, "update")
        venv.update(action)
        mocksession.report.expect("verbosity0", "*recreate*")


class TestVenvTest:
    def test_envbindir_path(self, newmocksession, monkeypatch):
        monkeypatch.setenv("PIP_RESPECT_VIRTUALENV", "1")
        mocksession = newmocksession(
            [],
            """
            [testenv:python]
            commands=abc
        """,
        )
        venv = mocksession.getenv("python")
        action = mocksession.newaction(venv, "getenv")
        monkeypatch.setenv("PATH", "xyz")
        sysfind_calls = []
        monkeypatch.setattr(
            "py.path.local.sysfind",
            classmethod(lambda *args, **kwargs: sysfind_calls.append(kwargs) or 0 / 0),
        )

        with pytest.raises(ZeroDivisionError):
            venv._install(list("123"), action=action)
        assert sysfind_calls.pop()["paths"] == [venv.envconfig.envbindir]
        with pytest.raises(ZeroDivisionError):
            venv.test(action)
        assert sysfind_calls.pop()["paths"] == [venv.envconfig.envbindir]
        with pytest.raises(ZeroDivisionError):
            venv.run_install_command(["qwe"], action=action)
        assert sysfind_calls.pop()["paths"] == [venv.envconfig.envbindir]
        monkeypatch.setenv("PIP_RESPECT_VIRTUALENV", "1")
        monkeypatch.setenv("PIP_REQUIRE_VIRTUALENV", "1")
        monkeypatch.setenv("__PYVENV_LAUNCHER__", "1")
        with pytest.raises(ZeroDivisionError):
            venv.run_install_command(["qwe"], action=action)
        assert "PIP_RESPECT_VIRTUALENV" not in os.environ
        assert "PIP_REQUIRE_VIRTUALENV" not in os.environ
        assert "__PYVENV_LAUNCHER__" not in os.environ

    def test_pythonpath_usage(self, newmocksession, monkeypatch):
        monkeypatch.setenv("PYTHONPATH", "/my/awesome/library")
        mocksession = newmocksession(
            [],
            """
            [testenv:python]
            commands=abc
        """,
        )
        venv = mocksession.getenv("python")
        action = mocksession.newaction(venv, "getenv")
        venv.run_install_command(["qwe"], action=action)
        assert "PYTHONPATH" not in os.environ
        mocksession.report.expect("warning", "*Discarding $PYTHONPATH from environment*")

        pcalls = mocksession._pcalls
        assert len(pcalls) == 1
        assert "PYTHONPATH" not in pcalls[0].env

        # passenv = PYTHONPATH allows PYTHONPATH to stay in environment
        monkeypatch.setenv("PYTHONPATH", "/my/awesome/library")
        mocksession = newmocksession(
            [],
            """
            [testenv:python]
            commands=abc
            passenv = PYTHONPATH
        """,
        )
        venv = mocksession.getenv("python")
        action = mocksession.newaction(venv, "getenv")
        venv.run_install_command(["qwe"], action=action)
        assert "PYTHONPATH" in os.environ
        mocksession.report.not_expect("warning", "*Discarding $PYTHONPATH from environment*")

        pcalls = mocksession._pcalls
        assert len(pcalls) == 2
        assert pcalls[1].env["PYTHONPATH"] == "/my/awesome/library"


# FIXME this test fails when run in isolation - find what this depends on
# AssertionError: found warning('*Discarding $PYTHONPATH [...]
def test_env_variables_added_to_pcall(tmpdir, mocksession, newconfig, monkeypatch):
    pkg = tmpdir.ensure("package.tar.gz")
    monkeypatch.setenv("X123", "123")
    monkeypatch.setenv("YY", "456")
    config = newconfig(
        [],
        """
        [testenv:python]
        commands=python -V
        passenv = x123
        setenv =
            ENV_VAR = value
            PYTHONPATH = value
    """,
    )
    mocksession._clearmocks()

    venv = VirtualEnv(config.envconfigs["python"], session=mocksession)
    mocksession.installpkg(venv, pkg)
    venv.test()

    pcalls = mocksession._pcalls
    assert len(pcalls) == 2
    for x in pcalls:
        env = x.env
        assert env is not None
        assert "ENV_VAR" in env
        assert env["ENV_VAR"] == "value"
        assert env["VIRTUAL_ENV"] == str(venv.path)
        assert env["X123"] == "123"
        assert "PYTHONPATH" in env
        assert env["PYTHONPATH"] == "value"
    # all env variables are passed for installation
    assert pcalls[0].env["YY"] == "456"
    assert "YY" not in pcalls[1].env

    assert {"ENV_VAR", "VIRTUAL_ENV", "PYTHONHASHSEED", "X123", "PATH"}.issubset(pcalls[1].env)

    # setenv does not trigger PYTHONPATH warnings
    mocksession.report.not_expect("warning", "*Discarding $PYTHONPATH from environment*")

    # for e in os.environ:
    #    assert e in env


def test_installpkg_no_upgrade(tmpdir, newmocksession):
    pkg = tmpdir.ensure("package.tar.gz")
    mocksession = newmocksession([], "")
    venv = mocksession.getenv("python")
    venv.just_created = True
    venv.envconfig.envdir.ensure(dir=1)
    mocksession.installpkg(venv, pkg)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    assert "-U" not in pcalls[0].args


def test_installpkg_upgrade(newmocksession, tmpdir):
    pkg = tmpdir.ensure("package.tar.gz")
    mocksession = newmocksession([], "")
    venv = mocksession.getenv("python")
    assert not hasattr(venv, "just_created")
    mocksession.installpkg(venv, pkg)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    index = pcalls[0].args.index(str(pkg))
    assert index >= 0
    assert "-U" in pcalls[0].args[:index]
    assert "--no-deps" in pcalls[0].args[:index]


def test_run_install_command(newmocksession):
    mocksession = newmocksession([], "")
    venv = mocksession.getenv("python")
    venv.just_created = True
    venv.envconfig.envdir.ensure(dir=1)
    action = mocksession.newaction(venv, "hello")
    venv.run_install_command(packages=["whatever"], action=action)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    assert "pip" in pcalls[0].args[0]
    assert "install" in pcalls[0].args
    env = pcalls[0].env
    assert env is not None


def test_run_custom_install_command(newmocksession):
    mocksession = newmocksession(
        [],
        """
        [testenv]
        install_command=easy_install {opts} {packages}
    """,
    )
    venv = mocksession.getenv("python")
    venv.just_created = True
    venv.envconfig.envdir.ensure(dir=1)
    action = mocksession.newaction(venv, "hello")
    venv.run_install_command(packages=["whatever"], action=action)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    assert "easy_install" in pcalls[0].args[0]
    assert pcalls[0].args[1:] == ["whatever"]


def test_command_relative_issue36(newmocksession, tmpdir, monkeypatch):
    mocksession = newmocksession(
        [],
        """
        [testenv]
    """,
    )
    x = tmpdir.ensure("x")
    venv = mocksession.getenv("python")
    x2 = venv.getcommandpath("./x", cwd=tmpdir)
    assert x == x2
    mocksession.report.not_expect("warning", "*test command found but not*")
    x3 = venv.getcommandpath("/bin/bash", cwd=tmpdir)
    assert x3 == "/bin/bash"
    mocksession.report.not_expect("warning", "*test command found but not*")
    monkeypatch.setenv("PATH", str(tmpdir))
    x4 = venv.getcommandpath("x", cwd=tmpdir)
    assert x4.endswith(os.sep + "x")
    mocksession.report.expect("warning", "*test command found but not*")


def test_ignore_outcome_failing_cmd(newmocksession):
    mocksession = newmocksession(
        [],
        """
        [testenv]
        commands=testenv_fail
        ignore_outcome=True
    """,
    )

    venv = mocksession.getenv("python")
    venv.test()
    assert venv.status == "ignored failed command"
    mocksession.report.expect("warning", "*command failed but result from testenv is ignored*")


def test_tox_testenv_create(newmocksession):
    log = []

    class Plugin:
        @tox.hookimpl
        def tox_testenv_create(self, action, venv):
            assert isinstance(action, tox.session.Action)
            assert isinstance(venv, VirtualEnv)
            log.append(1)

        @tox.hookimpl
        def tox_testenv_install_deps(self, action, venv):
            assert isinstance(action, tox.session.Action)
            assert isinstance(venv, VirtualEnv)
            log.append(2)

    mocksession = newmocksession(
        [],
        """
        [testenv]
        commands=testenv_fail
        ignore_outcome=True
    """,
        plugins=[Plugin()],
    )

    venv = mocksession.getenv("python")
    venv.update(action=mocksession.newaction(venv, "getenv"))
    assert log == [1, 2]


def test_tox_testenv_pre_post(newmocksession):
    log = []

    class Plugin:
        @tox.hookimpl
        def tox_runtest_pre(self):
            log.append("started")

        @tox.hookimpl
        def tox_runtest_post(self):
            log.append("finished")

    mocksession = newmocksession(
        [],
        """
        [testenv]
        commands=testenv_fail
    """,
        plugins=[Plugin()],
    )

    venv = mocksession.getenv("python")
    venv.status = None
    assert log == []
    mocksession.runtestenv(venv)
    assert log == ["started", "finished"]


@pytest.mark.skipif("sys.platform == 'win32'")
def test_tox_testenv_interpret_shebang_empty_instance(tmpdir):
    testfile = tmpdir.join("check_shebang_empty_instance.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # empty instance
    testfile.write("")
    args = prepend_shebang_interpreter(base_args)
    assert args == base_args


@pytest.mark.skipif("sys.platform == 'win32'")
def test_tox_testenv_interpret_shebang_empty_interpreter(tmpdir):
    testfile = tmpdir.join("check_shebang_empty_interpreter.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # empty interpreter
    testfile.write("#!")
    args = prepend_shebang_interpreter(base_args)
    assert args == base_args


@pytest.mark.skipif("sys.platform == 'win32'")
def test_tox_testenv_interpret_shebang_empty_interpreter_ws(tmpdir):
    testfile = tmpdir.join("check_shebang_empty_interpreter_ws.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # empty interpreter (whitespaces)
    testfile.write("#!    \n")
    args = prepend_shebang_interpreter(base_args)
    assert args == base_args


@pytest.mark.skipif("sys.platform == 'win32'")
def test_tox_testenv_interpret_shebang_interpreter_simple(tmpdir):
    testfile = tmpdir.join("check_shebang_interpreter_simple.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter (simple)
    testfile.write("#!interpreter")
    args = prepend_shebang_interpreter(base_args)
    assert args == [b"interpreter"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'")
def test_tox_testenv_interpret_shebang_interpreter_ws(tmpdir):
    testfile = tmpdir.join("check_shebang_interpreter_ws.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter (whitespaces)
    testfile.write("#!  interpreter  \n\n")
    args = prepend_shebang_interpreter(base_args)
    assert args == [b"interpreter"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'")
def test_tox_testenv_interpret_shebang_interpreter_arg(tmpdir):
    testfile = tmpdir.join("check_shebang_interpreter_arg.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter with argument
    testfile.write("#!interpreter argx\n")
    args = prepend_shebang_interpreter(base_args)
    assert args == [b"interpreter", b"argx"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'")
def test_tox_testenv_interpret_shebang_interpreter_args(tmpdir):
    testfile = tmpdir.join("check_shebang_interpreter_args.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter with argument (ensure single argument)
    testfile.write("#!interpreter argx argx-part2\n")
    args = prepend_shebang_interpreter(base_args)
    assert args == [b"interpreter", b"argx argx-part2"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'")
def test_tox_testenv_interpret_shebang_real(tmpdir):
    testfile = tmpdir.join("check_shebang_real.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter (real example)
    testfile.write("#!/usr/bin/env python\n")
    args = prepend_shebang_interpreter(base_args)
    assert args == [b"/usr/bin/env", b"python"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'")
def test_tox_testenv_interpret_shebang_long_example(tmpdir):
    testfile = tmpdir.join("check_shebang_long_example.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter (long example)
    testfile.write(
        "#!this-is-an-example-of-a-very-long-interpret-directive-what-should-"
        "be-directly-invoked-when-tox-needs-to-invoked-the-provided-script-"
        "name-in-the-argument-list"
    )
    args = prepend_shebang_interpreter(base_args)
    expected = [
        b"this-is-an-example-of-a-very-long-interpret-directive-what-should-be-"
        b"directly-invoked-when-tox-needs-to-invoked-the-provided-script-name-"
        b"in-the-argument-list"
    ]

    assert args == expected + base_args
