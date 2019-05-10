import os
import sys

import py
import pytest

import tox
from tox.interpreters import NoInterpreterInfo
from tox.session.commands.run.sequential import installpkg, runtestenv
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
        """\
        [testenv:python]
        basepython={}
        """.format(
            sys.executable
        ),
    )
    mocksession.new_config(config)
    venv = mocksession.getvenv("python")
    interp = venv.getsupportedinterpreter()
    # realpath needed for debian symlinks
    assert py.path.local(interp).realpath() == py.path.local(sys.executable).realpath()
    monkeypatch.setattr(tox.INFO, "IS_WIN", True)
    monkeypatch.setattr(venv.envconfig, "basepython", "jython")
    with pytest.raises(tox.exception.UnsupportedInterpreter):
        venv.getsupportedinterpreter()
    monkeypatch.undo()
    monkeypatch.setattr(venv.envconfig, "envname", "py1")
    monkeypatch.setattr(venv.envconfig, "basepython", "notexisting")
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
        """\
        [testenv:py123]
        """,
    )
    envconfig = config.envconfigs["py123"]
    mocksession.new_config(config)
    venv = mocksession.getvenv("py123")
    assert venv.path == envconfig.envdir
    assert not venv.path.check()
    with mocksession.newaction(venv.name, "getenv") as action:
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
    interp = venv._getliveconfig().base_resolved_python_path
    assert interp == venv.envconfig.python_info.executable
    assert venv.path_config.check(exists=False)


def test_create_KeyboardInterrupt(mocksession, newconfig, mocker):
    config = newconfig(
        [],
        """\
        [testenv:py123]
        """,
    )
    mocksession.new_config(config)
    venv = mocksession.getvenv("py123")
    with mocker.patch.object(venv, "_pcall", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            venv.setupenv()

    assert venv.status == "keyboardinterrupt"


def test_commandpath_venv_precedence(tmpdir, monkeypatch, mocksession, newconfig):
    config = newconfig(
        [],
        """\
        [testenv:py123]
        """,
    )
    mocksession.new_config(config)
    venv = mocksession.getvenv("py123")
    envconfig = venv.envconfig
    tmpdir.ensure("easy_install")
    monkeypatch.setenv("PATH", str(tmpdir), prepend=os.pathsep)
    envconfig.envbindir.ensure("easy_install")
    p = venv.getcommandpath("easy_install")
    assert py.path.local(p).relto(envconfig.envbindir), p


def test_create_sitepackages(mocksession, newconfig):
    config = newconfig(
        [],
        """\
        [testenv:site]
        sitepackages=True

        [testenv:nosite]
        sitepackages=False
        """,
    )
    mocksession.new_config(config)
    venv = mocksession.getvenv("site")
    with mocksession.newaction(venv.name, "getenv") as action:
        tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) >= 1
    args = pcalls[0].args
    assert "--system-site-packages" in map(str, args)
    mocksession._clearmocks()

    venv = mocksession.getvenv("nosite")
    with mocksession.newaction(venv.name, "getenv") as action:
        tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) >= 1
    args = pcalls[0].args
    assert "--system-site-packages" not in map(str, args)
    assert "--no-site-packages" not in map(str, args)


def test_install_deps_wildcard(newmocksession):
    mocksession = newmocksession(
        [],
        """\
        [tox]
        distshare = {toxworkdir}/distshare
        [testenv:py123]
        deps=
            {distshare}/dep1-*
        """,
    )
    venv = mocksession.getvenv("py123")
    with mocksession.newaction(venv.name, "getenv") as action:
        tox_testenv_create(action=action, venv=venv)
        pcalls = mocksession._pcalls
        assert len(pcalls) == 1
        distshare = venv.envconfig.config.distshare
        distshare.ensure("dep1-1.0.zip")
        distshare.ensure("dep1-1.1.zip")

        tox_testenv_install_deps(action=action, venv=venv)
        assert len(pcalls) == 2
        args = pcalls[-1].args
        assert pcalls[-1].cwd == venv.envconfig.config.toxinidir

    assert py.path.local.sysfind("python") == args[0]
    assert ["-m", "pip"] == args[1:3]
    assert args[3] == "install"
    args = [arg for arg in args if str(arg).endswith("dep1-1.1.zip")]
    assert len(args) == 1


def test_install_deps_indexserver(newmocksession):
    mocksession = newmocksession(
        [],
        """\
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
    venv = mocksession.getvenv("py123")
    with mocksession.newaction(venv.name, "getenv") as action:
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
        """\
        [testenv]
        pip_pre=true
        deps=
            dep1
        """,
    )
    venv = mocksession.getvenv("python")
    with mocksession.newaction(venv.name, "getenv") as action:
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
        """\
        [tox]
        indexserver =
            default = ABC
        """,
    )
    venv = mocksession.getvenv("python")
    pcalls = mocksession._pcalls
    p = tmpdir.ensure("distfile.tar.gz")
    installpkg(venv, p)
    # two different index servers, two calls
    assert len(pcalls) == 1
    args = " ".join(pcalls[0].args)
    assert "-i ABC" in args


def test_install_recreate(newmocksession, tmpdir):
    pkg = tmpdir.ensure("package.tar.gz")
    mocksession = newmocksession(
        ["--recreate"],
        """\
        [testenv]
        deps=xyz
        """,
    )
    venv = mocksession.getvenv("python")

    with mocksession.newaction(venv.name, "update") as action:
        venv.update(action)
        installpkg(venv, pkg)
        mocksession.report.expect("verbosity0", "*create*")
        venv.update(action)
        mocksession.report.expect("verbosity0", "*recreate*")


def test_install_sdist_extras(newmocksession):
    mocksession = newmocksession(
        [],
        """\
        [testenv]
        extras = testing
            development
        """,
    )
    venv = mocksession.getvenv("python")
    with mocksession.newaction(venv.name, "getenv") as action:
        tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    pcalls[:] = []

    venv.installpkg("distfile.tar.gz", action=action)
    assert "distfile.tar.gz[testing,development]" in pcalls[-1].args


def test_develop_extras(newmocksession, tmpdir):
    mocksession = newmocksession(
        [],
        """\
        [testenv]
        extras = testing
            development
        """,
    )
    venv = mocksession.getvenv("python")
    with mocksession.newaction(venv.name, "getenv") as action:
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
        """\
        [testenv:python]
        passenv = temp_pass_var
        setenv =
            CUSTOM_VAR = 789
        """,
    )
    mocksession.new_config(config)
    venv = mocksession.getvenv("python")
    with mocksession.newaction(venv.name, "hello") as action:
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
    venv = mocksession.getvenv("python")
    with mocksession.newaction(venv.name, "update") as action:
        venv.update(action)
    tox.venv.tox_runtest_pre(venv)
    mocksession.report.expect("verbosity0", "run-test-pre: PYTHONHASHSEED='{}'".format(seed))


def test_test_runtests_action_command_is_in_output(newmocksession):
    mocksession = newmocksession(
        [],
        """\
        [testenv]
        commands = echo foo bar
        """,
    )
    venv = mocksession.getvenv("python")
    with mocksession.newaction(venv.name, "update") as action:
        venv.update(action)
    venv.test()
    mocksession.report.expect("verbosity0", "*run-test:*commands?0? | echo foo bar")


def test_install_error(newmocksession):
    mocksession = newmocksession(
        ["--recreate"],
        """\
        [testenv]
        deps=xyz
        commands=
            qwelkqw
        """,
    )
    venv = mocksession.getvenv("python")
    venv.test()
    mocksession.report.expect("error", "*not find*qwelkqw*")
    assert venv.status == "commands failed"


def test_install_command_not_installed(newmocksession):
    mocksession = newmocksession(
        ["--recreate"],
        """\
        [testenv]
        commands=
            pytest
        """,
    )
    venv = mocksession.getvenv("python")
    venv.status = 0
    venv.test()
    mocksession.report.expect("warning", "*test command found but not*")
    assert venv.status == 0


def test_install_command_whitelisted(newmocksession):
    mocksession = newmocksession(
        ["--recreate"],
        """\
        [testenv]
        whitelist_externals = pytest
                              xy*
        commands=
            pytest
            xyz
        """,
    )
    venv = mocksession.getvenv("python")
    venv.test()
    mocksession.report.expect("warning", "*test command found but not*", invert=True)
    assert venv.status == "commands failed"


def test_install_command_not_installed_bash(newmocksession):
    mocksession = newmocksession(
        ["--recreate"],
        """\
        [testenv]
        commands=
            bash
        """,
    )
    venv = mocksession.getvenv("python")
    venv.test()
    mocksession.report.expect("warning", "*test command found but not*")


def test_install_python3(newmocksession):
    if not py.path.local.sysfind("python3"):
        pytest.skip("needs python3")
    mocksession = newmocksession(
        [],
        """\
        [testenv:py123]
        basepython=python3
        deps=
            dep1
            dep2
        """,
    )
    venv = mocksession.getvenv("py123")
    with mocksession.newaction(venv.name, "getenv") as action:
        tox_testenv_create(action=action, venv=venv)
        pcalls = mocksession._pcalls
        assert len(pcalls) == 1
        args = pcalls[0].args
        assert str(args[2]) == "virtualenv"
        pcalls[:] = []
    with mocksession.newaction(venv.name, "hello") as action:
        venv._install(["hello"], action=action)
        assert len(pcalls) == 1
    args = pcalls[0].args
    assert py.path.local.sysfind("python") == args[0]
    assert ["-m", "pip"] == args[1:3]
    for _ in args:
        assert "--download-cache" not in args, args


class TestCreationConfig:
    def test_basic(self, newconfig, mocksession, tmpdir):
        config = newconfig([], "")
        mocksession.new_config(config)
        venv = mocksession.getvenv("python")
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
            """\
            [testenv]
            deps=abc
            """,
        )
        mocksession.new_config(config)
        venv = mocksession.getvenv("python")
        cconfig = venv._getliveconfig()
        config = newconfig(
            [],
            """\
            [testenv]
            deps=xyz
            """,
        )
        mocksession.new_config(config)
        venv = mocksession.getvenv("python")
        otherconfig = venv._getliveconfig()
        assert not cconfig.matches(otherconfig)

    def test_matchingdependencies_file(self, newconfig, mocksession):
        config = newconfig(
            [],
            """\
            [tox]
            distshare={toxworkdir}/distshare
            [testenv]
            deps=abc
                 {distshare}/xyz.zip
            """,
        )
        xyz = config.distshare.join("xyz.zip")
        xyz.ensure()
        mocksession.new_config(config)
        venv = mocksession.getvenv("python")
        cconfig = venv._getliveconfig()
        assert cconfig.matches(cconfig)
        xyz.write("hello")
        newconfig = venv._getliveconfig()
        assert not cconfig.matches(newconfig)

    def test_matchingdependencies_latest(self, newconfig, mocksession):
        config = newconfig(
            [],
            """\
            [tox]
            distshare={toxworkdir}/distshare
            [testenv]
            deps={distshare}/xyz-*
            """,
        )
        config.distshare.ensure("xyz-1.2.0.zip")
        xyz2 = config.distshare.ensure("xyz-1.2.1.zip")
        mocksession.new_config(config)
        venv = mocksession.getvenv("python")
        cconfig = venv._getliveconfig()
        md5, path = cconfig.deps[0]
        assert path == xyz2
        assert md5 == path.computehash()

    def test_python_recreation(self, tmpdir, newconfig, mocksession):
        pkg = tmpdir.ensure("package.tar.gz")
        config = newconfig(["-v"], "")
        mocksession.new_config(config)
        venv = mocksession.getvenv("python")
        create_config = venv._getliveconfig()
        with mocksession.newaction(venv.name, "update") as action:
            venv.update(action)
            assert not venv.path_config.check()
        installpkg(venv, pkg)
        assert venv.path_config.check()
        assert mocksession._pcalls
        args1 = map(str, mocksession._pcalls[0].args)
        assert "virtualenv" in " ".join(args1)
        mocksession.report.expect("*", "*create*")
        # modify config and check that recreation happens
        mocksession._clearmocks()
        with mocksession.newaction(venv.name, "update") as action:
            venv.update(action)
            mocksession.report.expect("*", "*reusing*")
            mocksession._clearmocks()
        with mocksession.newaction(venv.name, "update") as action:
            create_config.base_resolved_python_path = py.path.local("balla")
            create_config.writeconfig(venv.path_config)
            venv.update(action)
            mocksession.report.expect("verbosity0", "*recreate*")

    def test_dep_recreation(self, newconfig, mocksession):
        config = newconfig([], "")
        mocksession.new_config(config)
        venv = mocksession.getvenv("python")
        with mocksession.newaction(venv.name, "update") as action:
            venv.update(action)
            cconfig = venv._getliveconfig()
            cconfig.deps[:] = [("1" * 32, "xyz.zip")]
            cconfig.writeconfig(venv.path_config)
            mocksession._clearmocks()
        with mocksession.newaction(venv.name, "update") as action:
            venv.update(action)
            mocksession.report.expect("*", "*recreate*")

    def test_develop_recreation(self, newconfig, mocksession):
        config = newconfig([], "")
        mocksession.new_config(config)
        venv = mocksession.getvenv("python")
        with mocksession.newaction(venv.name, "update") as action:
            venv.update(action)
            cconfig = venv._getliveconfig()
            cconfig.usedevelop = True
            cconfig.writeconfig(venv.path_config)
            mocksession._clearmocks()
        with mocksession.newaction(venv.name, "update") as action:
            venv.update(action)
            mocksession.report.expect("verbosity0", "*recreate*")


class TestVenvTest:
    def test_envbindir_path(self, newmocksession, monkeypatch):
        monkeypatch.setenv("PIP_RESPECT_VIRTUALENV", "1")
        mocksession = newmocksession(
            [],
            """\
            [testenv:python]
            commands=abc
            """,
        )
        venv = mocksession.getvenv("python")
        with mocksession.newaction(venv.name, "getenv") as action:
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

            prev_pcall = venv._pcall

            def collect(*args, **kwargs):
                env = kwargs["env"]
                assert "PIP_RESPECT_VIRTUALENV" not in env
                assert "PIP_REQUIRE_VIRTUALENV" not in env
                assert "__PYVENV_LAUNCHER__" not in env
                assert env["PIP_USER"] == "0"
                assert env["PIP_NO_DEPS"] == "0"
                return prev_pcall(*args, **kwargs)

            monkeypatch.setattr(venv, "_pcall", collect)
            with pytest.raises(ZeroDivisionError):
                venv.run_install_command(["qwe"], action=action)

    def test_pythonpath_remove(self, newmocksession, monkeypatch, caplog):
        monkeypatch.setenv("PYTHONPATH", "/my/awesome/library")
        mocksession = newmocksession(
            [],
            """\
            [testenv:python]
            commands=abc
            """,
        )
        venv = mocksession.getvenv("python")
        with mocksession.newaction(venv.name, "getenv") as action:
            venv.run_install_command(["qwe"], action=action)
        mocksession.report.expect("warning", "*Discarding $PYTHONPATH from environment*")

        pcalls = mocksession._pcalls
        assert len(pcalls) == 1
        assert "PYTHONPATH" not in pcalls[0].env

    def test_pythonpath_keep(self, newmocksession, monkeypatch, caplog):
        # passenv = PYTHONPATH allows PYTHONPATH to stay in environment
        monkeypatch.setenv("PYTHONPATH", "/my/awesome/library")
        mocksession = newmocksession(
            [],
            """\
            [testenv:python]
            commands=abc
            passenv = PYTHONPATH
            """,
        )
        venv = mocksession.getvenv("python")
        with mocksession.newaction(venv.name, "getenv") as action:
            venv.run_install_command(["qwe"], action=action)
        mocksession.report.not_expect("warning", "*Discarding $PYTHONPATH from environment*")
        assert "PYTHONPATH" in os.environ

        pcalls = mocksession._pcalls
        assert len(pcalls) == 1
        assert pcalls[0].env["PYTHONPATH"] == "/my/awesome/library"

    def test_pythonpath_empty(self, newmocksession, monkeypatch, caplog):
        monkeypatch.setenv("PYTHONPATH", "")
        mocksession = newmocksession(
            [],
            """\
            [testenv:python]
            commands=abc
            """,
        )
        venv = mocksession.getvenv("python")
        with mocksession.newaction(venv.name, "getenv") as action:
            venv.run_install_command(["qwe"], action=action)
        if sys.version_info < (3, 4):
            mocksession.report.expect("warning", "*Discarding $PYTHONPATH from environment*")
        else:
            with pytest.raises(AssertionError):
                mocksession.report.expect("warning", "*Discarding $PYTHONPATH from environment*")
        pcalls = mocksession._pcalls
        assert len(pcalls) == 1
        assert "PYTHONPATH" not in pcalls[0].env


def test_env_variables_added_to_pcall(tmpdir, mocksession, newconfig, monkeypatch):
    monkeypatch.delenv("PYTHONPATH", raising=False)
    pkg = tmpdir.ensure("package.tar.gz")
    monkeypatch.setenv("X123", "123")
    monkeypatch.setenv("YY", "456")
    config = newconfig(
        [],
        """\
        [testenv:python]
        commands=python -V
        passenv = x123
        setenv =
            ENV_VAR = value
            PYTHONPATH = value
        """,
    )
    mocksession._clearmocks()
    mocksession.new_config(config)
    venv = mocksession.getvenv("python")
    installpkg(venv, pkg)
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
    venv = mocksession.getvenv("python")
    venv.just_created = True
    venv.envconfig.envdir.ensure(dir=1)
    installpkg(venv, pkg)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    assert pcalls[0].args[1:-1] == ["-m", "pip", "install", "--exists-action", "w"]


@pytest.mark.parametrize("count, level", [(0, 0), (1, 0), (2, 0), (3, 1), (4, 2), (5, 3), (6, 3)])
def test_install_command_verbosity(tmpdir, newmocksession, count, level):
    pkg = tmpdir.ensure("package.tar.gz")
    mock_session = newmocksession(["-{}".format("v" * count)], "")
    env = mock_session.getvenv("python")
    env.just_created = True
    env.envconfig.envdir.ensure(dir=1)
    installpkg(env, pkg)
    pcalls = mock_session._pcalls
    assert len(pcalls) == 1
    expected = ["-m", "pip", "install", "--exists-action", "w"] + (["-v"] * level)
    assert pcalls[0].args[1:-1] == expected


def test_installpkg_upgrade(newmocksession, tmpdir):
    pkg = tmpdir.ensure("package.tar.gz")
    mocksession = newmocksession([], "")
    venv = mocksession.getvenv("python")
    assert not hasattr(venv, "just_created")
    installpkg(venv, pkg)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    index = pcalls[0].args.index(pkg.basename)
    assert index >= 0
    assert "-U" in pcalls[0].args[:index]
    assert "--no-deps" in pcalls[0].args[:index]


def test_run_install_command(newmocksession):
    mocksession = newmocksession([], "")
    venv = mocksession.getvenv("python")
    venv.just_created = True
    venv.envconfig.envdir.ensure(dir=1)
    with mocksession.newaction(venv.name, "hello") as action:
        venv.run_install_command(packages=["whatever"], action=action)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    args = pcalls[0].args
    assert py.path.local.sysfind("python") == args[0]
    assert ["-m", "pip"] == args[1:3]
    assert "install" in args
    env = pcalls[0].env
    assert env is not None


def test_run_custom_install_command(newmocksession):
    mocksession = newmocksession(
        [],
        """\
        [testenv]
        install_command=easy_install {opts} {packages}
        """,
    )
    venv = mocksession.getvenv("python")
    venv.just_created = True
    venv.envconfig.envdir.ensure(dir=1)
    with mocksession.newaction(venv.name, "hello") as action:
        venv.run_install_command(packages=["whatever"], action=action)
    pcalls = mocksession._pcalls
    assert len(pcalls) == 1
    assert "easy_install" in pcalls[0].args[0]
    assert pcalls[0].args[1:] == ["whatever"]


def test_command_relative_issue36(newmocksession, tmpdir, monkeypatch):
    mocksession = newmocksession(
        [],
        """\
        [testenv]
        """,
    )
    x = tmpdir.ensure("x")
    venv = mocksession.getvenv("python")
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
        """\
        [testenv]
        commands=testenv_fail
        ignore_outcome=True
        """,
    )

    venv = mocksession.getvenv("python")
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
        """\
        [testenv]
        commands=testenv_fail
        ignore_outcome=True
        """,
        plugins=[Plugin()],
    )

    venv = mocksession.getvenv("python")
    with mocksession.newaction(venv.name, "getenv") as action:
        venv.update(action=action)
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
        """\
        [testenv]
        commands=testenv_fail
        """,
        plugins=[Plugin()],
    )

    venv = mocksession.getvenv("python")
    venv.status = None
    assert log == []
    runtestenv(venv, venv.envconfig.config)
    assert log == ["started", "finished"]


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
def test_tox_testenv_interpret_shebang_empty_instance(tmpdir):
    testfile = tmpdir.join("check_shebang_empty_instance.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # empty instance
    testfile.write("")
    args = prepend_shebang_interpreter(base_args)
    assert args == base_args


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
def test_tox_testenv_interpret_shebang_empty_interpreter(tmpdir):
    testfile = tmpdir.join("check_shebang_empty_interpreter.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # empty interpreter
    testfile.write("#!")
    args = prepend_shebang_interpreter(base_args)
    assert args == base_args


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
def test_tox_testenv_interpret_shebang_empty_interpreter_ws(tmpdir):
    testfile = tmpdir.join("check_shebang_empty_interpreter_ws.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # empty interpreter (whitespaces)
    testfile.write("#!    \n")
    args = prepend_shebang_interpreter(base_args)
    assert args == base_args


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
def test_tox_testenv_interpret_shebang_non_utf8(tmpdir):
    testfile = tmpdir.join("check_non_utf8.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    testfile.write_binary(b"#!\x9a\xef\x12\xaf\n")
    args = prepend_shebang_interpreter(base_args)
    assert args == base_args


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
def test_tox_testenv_interpret_shebang_interpreter_simple(tmpdir):
    testfile = tmpdir.join("check_shebang_interpreter_simple.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter (simple)
    testfile.write("#!interpreter")
    args = prepend_shebang_interpreter(base_args)
    assert args == ["interpreter"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
def test_tox_testenv_interpret_shebang_interpreter_ws(tmpdir):
    testfile = tmpdir.join("check_shebang_interpreter_ws.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter (whitespaces)
    testfile.write("#!  interpreter  \n\n")
    args = prepend_shebang_interpreter(base_args)
    assert args == ["interpreter"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
def test_tox_testenv_interpret_shebang_interpreter_arg(tmpdir):
    testfile = tmpdir.join("check_shebang_interpreter_arg.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter with argument
    testfile.write("#!interpreter argx\n")
    args = prepend_shebang_interpreter(base_args)
    assert args == ["interpreter", "argx"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
def test_tox_testenv_interpret_shebang_interpreter_args(tmpdir):
    testfile = tmpdir.join("check_shebang_interpreter_args.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter with argument (ensure single argument)
    testfile.write("#!interpreter argx argx-part2\n")
    args = prepend_shebang_interpreter(base_args)
    assert args == ["interpreter", "argx argx-part2"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
def test_tox_testenv_interpret_shebang_real(tmpdir):
    testfile = tmpdir.join("check_shebang_real.py")
    base_args = [str(testfile), "arg1", "arg2", "arg3"]

    # interpreter (real example)
    testfile.write("#!/usr/bin/env python\n")
    args = prepend_shebang_interpreter(base_args)
    assert args == ["/usr/bin/env", "python"] + base_args


@pytest.mark.skipif("sys.platform == 'win32'", reason="no shebang on Windows")
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
        "this-is-an-example-of-a-very-long-interpret-directive-what-should-be-"
        "directly-invoked-when-tox-needs-to-invoked-the-provided-script-name-"
        "in-the-argument-list"
    ]

    assert args == expected + base_args


@pytest.mark.parametrize("download", [True, False, None])
def test_create_download(mocksession, newconfig, download):
    config = newconfig(
        [],
        """\
        [testenv:env]
        {}
        """.format(
            "download={}".format(download) if download else ""
        ),
    )
    mocksession.new_config(config)
    venv = mocksession.getvenv("env")
    with mocksession.newaction(venv.name, "getenv") as action:
        tox_testenv_create(action=action, venv=venv)
    pcalls = mocksession._pcalls
    assert len(pcalls) >= 1
    args = pcalls[0].args
    if download is True:
        assert "--no-download" not in map(str, args)
    else:
        assert "--no-download" in map(str, args)
    mocksession._clearmocks()
