import tox
import pytest
import os, sys
import subprocess
from textwrap import dedent

import py
from tox._config import IniReader, CommandParser
from tox._config import parseconfig

class TestVenvConfig:
    def test_config_parsing_minimal(self, tmpdir, newconfig):
        config = newconfig([], """
            [testenv:py1]
        """)
        assert len(config.envconfigs) == 1
        assert config.toxworkdir.realpath() == tmpdir.join(".tox").realpath()
        assert config.envconfigs['py1'].basepython == sys.executable
        assert config.envconfigs['py1'].deps == []

    def test_config_parsing_multienv(self, tmpdir, newconfig):
        config = newconfig([], """
            [tox]
            toxworkdir = %s
            indexserver =
                xyz = xyz_repo
            [testenv:py1]
            deps=hello
            [testenv:py2]
            deps=
                world1
                :xyz:http://hello/world
        """ % (tmpdir, ))
        assert config.toxworkdir == tmpdir
        assert len(config.envconfigs) == 2
        assert config.envconfigs['py1'].envdir == tmpdir.join("py1")
        dep = config.envconfigs['py1'].deps[0]
        assert dep.name == "hello"
        assert dep.indexserver is None
        assert config.envconfigs['py2'].envdir == tmpdir.join("py2")
        dep1, dep2 = config.envconfigs['py2'].deps
        assert dep1.name == "world1"
        assert dep2.name == "http://hello/world"
        assert dep2.indexserver.name == "xyz"
        assert dep2.indexserver.url == "xyz_repo"

class TestConfigPackage:
    def test_defaults(self, tmpdir, newconfig):
        config = newconfig([], "")
        assert config.setupdir.realpath() == tmpdir.realpath()
        assert config.toxworkdir.realpath() == tmpdir.join(".tox").realpath()
        envconfig = config.envconfigs['python']
        assert envconfig.args_are_paths
        assert not envconfig.recreate

    def test_defaults_distshare(self, tmpdir, newconfig):
        config = newconfig([], "")
        envconfig = config.envconfigs['python']
        homedir = py.path.local._gethomedir()
        assert config.distshare == homedir.join(".tox", "distshare")

    def test_defaults_changed_dir(self, tmpdir, newconfig):
        tmpdir.mkdir("abc").chdir()
        config = newconfig([], "")
        assert config.setupdir.realpath() == tmpdir.realpath()
        assert config.toxworkdir.realpath() == tmpdir.join(".tox").realpath()

    def test_project_paths(self, tmpdir, newconfig):
        config = newconfig("""
            [tox]
            toxworkdir=%s
        """ % tmpdir)
        assert config.toxworkdir == tmpdir

class TestParseconfig:
    def test_search_parents(self, tmpdir):
        b = tmpdir.mkdir("a").mkdir("b")
        toxinipath = tmpdir.ensure("tox.ini")
        old = b.chdir()
        try:
            config = parseconfig([])
        finally:
            old.chdir()
        assert config.toxinipath == toxinipath

class TestIniParser:
    def test_getdefault_single(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key=value
        """)
        reader = IniReader(config._cfg)
        x = reader.getdefault("section", "key")
        assert x == "value"
        assert not reader.getdefault("section", "hello")
        x = reader.getdefault("section", "hello", "world")
        assert x == "world"

    def test_missing_substitution(self, tmpdir, newconfig):
        config = newconfig("""
            [mydefault]
            key2={xyz}
        """)
        reader = IniReader(config._cfg, fallbacksections=['mydefault'])
        py.test.raises(tox.exception.ConfigError,
            'reader.getdefault("mydefault", "key2")')

    def test_getdefault_fallback_sections(self, tmpdir, newconfig):
        config = newconfig("""
            [mydefault]
            key2=value2
            [section]
            key=value
        """)
        reader = IniReader(config._cfg, fallbacksections=['mydefault'])
        x = reader.getdefault("section", "key2")
        assert x == "value2"
        x = reader.getdefault("section", "key3")
        assert not x
        x = reader.getdefault("section", "key3", "world")
        assert x == "world"

    def test_getdefault_substitution(self, tmpdir, newconfig):
        config = newconfig("""
            [mydefault]
            key2={value2}
            [section]
            key={value}
        """)
        reader = IniReader(config._cfg, fallbacksections=['mydefault'])
        reader.addsubstitions(value="newvalue", value2="newvalue2")
        x = reader.getdefault("section", "key2")
        assert x == "newvalue2"
        x = reader.getdefault("section", "key3")
        assert not x
        x = reader.getdefault("section", "key3", "{value2}")
        assert x == "newvalue2"

    def test_getlist(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                item1
                {item2}
        """)
        reader = IniReader(config._cfg)
        reader.addsubstitions(item1="not", item2="grr")
        x = reader.getlist("section", "key2")
        assert x == ['item1', 'grr']

    def test_getdict(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                key1=item1
                key2={item2}
        """)
        reader = IniReader(config._cfg)
        reader.addsubstitions(item1="not", item2="grr")
        x = reader.getdict("section", "key2")
        assert 'key1' in x
        assert 'key2' in x
        assert x['key1'] == 'item1'
        assert x['key2'] == 'grr'

    def test_getdefault_environment_substitution(self, monkeypatch, newconfig):
        monkeypatch.setenv("KEY1", "hello")
        config = newconfig("""
            [section]
            key1={env:KEY1}
            key2={env:KEY2}
        """)
        reader = IniReader(config._cfg)
        x = reader.getdefault("section", "key1")
        assert x == "hello"
        py.test.raises(tox.exception.ConfigError,
            'reader.getdefault("section", "key2")')

    def test_getdefault_other_section_substitution(self, newconfig):
        config = newconfig("""
            [section]
            key = rue
            [testenv]
            key = t{[section]key}
            """)
        reader = IniReader(config._cfg)
        x = reader.getdefault("testenv", "key")
        assert x == "true"

    def test_command_substitution_from_other_section(self, newconfig):
        config = newconfig("""
            [section]
            key = whatever
            [testenv]
            commands =
                echo {[section]key}
            """)
        reader = IniReader(config._cfg)
        x = reader.getargvlist("testenv", "commands")
        assert x == [["echo", "whatever"]]

    def test_argvlist(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                cmd1 {item1} {item2}
                cmd2 {item2}
        """)
        reader = IniReader(config._cfg)
        reader.addsubstitions(item1="with space", item2="grr")
        #py.test.raises(tox.exception.ConfigError,
        #    "reader.getargvlist('section', 'key1')")
        assert reader.getargvlist('section', 'key1') == []
        x = reader.getargvlist("section", "key2")
        assert x == [["cmd1", "with space", "grr"],
                     ["cmd2", "grr"]]

    def test_argvlist_multiline(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                cmd1 {item1} \ # a comment
                     {item2}
        """)
        reader = IniReader(config._cfg)
        reader.addsubstitions(item1="with space", item2="grr")
        #py.test.raises(tox.exception.ConfigError,
        #    "reader.getargvlist('section', 'key1')")
        assert reader.getargvlist('section', 'key1') == []
        x = reader.getargvlist("section", "key2")
        assert x == [["cmd1", "with space", "grr"]]


    def test_argvlist_quoting_in_command(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key1=
                cmd1 'with space' \ # a comment
                     'after the comment'
        """)
        reader = IniReader(config._cfg)
        x = reader.getargvlist("section", "key1")
        assert x == [["cmd1", "with space", "after the comment"]]


    def test_argvlist_positional_substitution(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                cmd1 []
                cmd2 {posargs:{item2} \
                     other}
        """)
        reader = IniReader(config._cfg)
        posargs = ['hello', 'world']
        reader.addsubstitions(posargs, item2="value2")
        #py.test.raises(tox.exception.ConfigError,
        #    "reader.getargvlist('section', 'key1')")
        assert reader.getargvlist('section', 'key1') == []
        argvlist = reader.getargvlist("section", "key2")
        assert argvlist[0] == ["cmd1"] + posargs
        assert argvlist[1] == ["cmd2"] + posargs

        reader = IniReader(config._cfg)
        reader.addsubstitions([], item2="value2")
        #py.test.raises(tox.exception.ConfigError,
        #    "reader.getargvlist('section', 'key1')")
        assert reader.getargvlist('section', 'key1') == []
        argvlist = reader.getargvlist("section", "key2")
        assert argvlist[0] == ["cmd1"]
        assert argvlist[1] == ["cmd2", "value2", "other"]

    def test_positional_arguments_are_only_replaced_when_standing_alone(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key=
                cmd0 []
                cmd1 -m '[abc]'
                cmd2 -m '\'something\'' []
                cmd3 something[]else
        """)
        reader = IniReader(config._cfg)
        posargs = ['hello', 'world']
        reader.addsubstitions(posargs)

        argvlist = reader.getargvlist('section', 'key')
        assert argvlist[0] == ['cmd0'] + posargs
        assert argvlist[1] == ['cmd1', '-m', '[abc]']
        assert argvlist[2] == ['cmd2', '-m', "something"] + posargs
        assert argvlist[3] == ['cmd3', 'something[]else']

    def test_substition_with_multiple_words(self, newconfig):
        inisource = """
            [section]
            key = py.test -n5 --junitxml={envlogdir}/junit-{envname}.xml []
            """
        config = newconfig(inisource)
        reader = IniReader(config._cfg)
        posargs = ['hello', 'world']
        reader.addsubstitions(posargs, envlogdir='ENV_LOG_DIR', envname='ENV_NAME')

        expected = ['py.test', '-n5', '--junitxml=ENV_LOG_DIR/junit-ENV_NAME.xml', 'hello', 'world']
        assert reader.getargvlist('section', 'key')[0] == expected


    def test_getpath(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            path1={HELLO}
        """)
        reader = IniReader(config._cfg)
        reader.addsubstitions(toxinidir=tmpdir, HELLO="mypath")
        x = reader.getpath("section", "path1", tmpdir)
        assert x == tmpdir.join("mypath")

    def test_getbool(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key1=True
            key2=False
            key1a=true
            key2a=falsE
            key5=yes
        """)
        reader = IniReader(config._cfg)
        assert reader.getbool("section", "key1") == True
        assert reader.getbool("section", "key1a") == True
        assert reader.getbool("section", "key2") == False
        assert reader.getbool("section", "key2a") == False
        py.test.raises(KeyError, 'reader.getbool("section", "key3")')
        py.test.raises(tox.exception.ConfigError, 'reader.getbool("section", "key5")')

class TestConfigTestEnv:
    def test_commentchars_issue33(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv] # hello
            deps = http://abc#123
            commands=
                python -c "x ; y"
        """)
        envconfig = config.envconfigs["python"]
        assert envconfig.deps[0].name == "http://abc#123"
        assert envconfig.commands[0] == ["python", "-c", "x ; y"]

    def test_defaults(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            commands=
                xyz --abc
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.commands == [["xyz", "--abc"]]
        assert envconfig.changedir == config.setupdir
        assert envconfig.distribute == True
        assert envconfig.sitepackages == False
        assert envconfig.envlogdir == envconfig.envdir.join("log")
        assert envconfig.setenv is None

    def test_specific_command_overrides(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            commands=xyz
            [testenv:py]
            commands=abc
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['py']
        assert envconfig.commands == [["abc"]]

    def test_changedir(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            changedir=xyz
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.changedir.basename == "xyz"
        assert envconfig.changedir == config.toxinidir.join("xyz")

    def test_envbindir(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            basepython=python
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.envpython == envconfig.envbindir.join("python")

    @pytest.mark.parametrize("bp", ["jython", "pypy"])
    def test_envbindir_jython(self, tmpdir, newconfig, bp):
        config = newconfig("""
            [testenv]
            basepython=%s
        """ % bp)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        # on win32 and linux virtualenv uses "bin" for pypy/jython
        assert envconfig.envbindir.basename == "bin"
        if bp == "jython":
            assert envconfig.envpython == envconfig.envbindir.join(bp)

    def test_setenv_overrides(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            setenv =
                PYTHONPATH = something
                ANOTHER_VAL=else
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert 'PYTHONPATH' in envconfig.setenv
        assert 'ANOTHER_VAL' in envconfig.setenv
        assert envconfig.setenv['PYTHONPATH'] == 'something'
        assert envconfig.setenv['ANOTHER_VAL'] == 'else'

    def test_changedir_override(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            changedir=xyz
            [testenv:python]
            changedir=abc
            basepython=python2.6
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.changedir.basename == "abc"
        assert envconfig.changedir == config.setupdir.join("abc")

    def test_simple(tmpdir, newconfig):
        config = newconfig("""
            [testenv:py24]
            basepython=python2.4
            [testenv:py25]
            basepython=python2.5
        """)
        assert len(config.envconfigs) == 2
        assert "py24" in config.envconfigs
        assert "py25" in config.envconfigs

    def test_substitution_error(tmpdir, newconfig):
        py.test.raises(tox.exception.ConfigError, newconfig, """
            [testenv:py24]
            basepython={xyz}
        """)

    def test_substitution_defaults(tmpdir, newconfig):
        config = newconfig("""
            [testenv:py24]
            commands =
                {toxinidir}
                {toxworkdir}
                {envdir}
                {envbindir}
                {envtmpdir}
                {envpython}
                {homedir}
                {distshare}
                {envlogdir}
        """)
        conf = config.envconfigs['py24']
        argv = conf.commands
        assert argv[0][0] == config.toxinidir
        assert argv[1][0] == config.toxworkdir
        assert argv[2][0] == conf.envdir
        assert argv[3][0] == conf.envbindir
        assert argv[4][0] == conf.envtmpdir
        assert argv[5][0] == conf.envpython
        assert argv[6][0] == str(py.path.local._gethomedir())
        assert argv[7][0] == config.homedir.join(".tox", "distshare")
        assert argv[8][0] == conf.envlogdir

    def test_substitution_positional(self, newconfig):
        inisource = """
            [testenv:py24]
            commands =
                cmd1 [hello] \
                     world
                cmd1 {posargs:hello} \
                     world
        """
        conf = newconfig([], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1", "[hello]", "world"]
        assert argv[1] == ["cmd1", "hello", "world"]
        conf = newconfig(['brave', 'new'], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1", "[hello]", "world"]
        assert argv[1] == ["cmd1", "brave", "new", "world"]

    def test_rewrite_posargs(self, tmpdir, newconfig):
        inisource = """
            [testenv:py24]
            args_are_paths = True
            changedir = tests
            commands = cmd1 {posargs:hello}
        """
        conf = newconfig([], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello"]

        conf = newconfig(["tests/hello"], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1", "tests/hello"]

        tmpdir.ensure("tests", "hello")
        conf = newconfig(["tests/hello"], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello"]

    def test_rewrite_simple_posargs(self, tmpdir, newconfig):
        inisource = """
            [testenv:py24]
            args_are_paths = True
            changedir = tests
            commands = cmd1 {posargs}
        """
        conf = newconfig([], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1"]

        conf = newconfig(["tests/hello"], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1", "tests/hello"]

        tmpdir.ensure("tests", "hello")
        conf = newconfig(["tests/hello"], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello"]

    def test_take_dependencies_from_other_testenv(self, newconfig):
        inisource="""
            [testenv]
            deps=
                pytest
                pytest-cov
            [testenv:py24]
            deps=
                {[testenv]deps}
                fun
        """
        conf = newconfig([], inisource).envconfigs['py24']
        packages = [dep.name for dep in conf.deps]
        assert packages == ['pytest', 'pytest-cov', 'fun']

    def test_take_dependencies_from_other_section(self, newconfig):
        inisource="""
            [testing:pytest]
            deps=
                pytest
                pytest-cov
            [testing:mock]
            deps=
                mock
            [testenv]
            deps=
                {[testing:pytest]deps}
                {[testing:mock]deps}
                fun
        """
        conf = newconfig([], inisource)
        env = conf.envconfigs['python']
        packages = [dep.name for dep in env.deps]
        assert packages == ['pytest', 'pytest-cov', 'mock', 'fun']

    def test_multilevel_substitution(self, newconfig):
        inisource="""
            [testing:pytest]
            deps=
                pytest
                pytest-cov
            [testing:mock]
            deps=
                mock

            [testing]
            deps=
                {[testing:pytest]deps}
                {[testing:mock]deps}

            [testenv]
            deps=
                {[testing]deps}
                fun
        """
        conf = newconfig([], inisource)
        env = conf.envconfigs['python']
        packages = [dep.name for dep in env.deps]
        assert packages == ['pytest', 'pytest-cov', 'mock', 'fun']

    def test_recursive_substitution_cycle_fails(self, newconfig):
        inisource="""
            [testing:pytest]
            deps=
                {[testing:mock]deps}
            [testing:mock]
            deps=
                {[testing:pytest]deps}

            [testenv]
            deps=
                {[testing:pytest]deps}
        """
        py.test.raises(ValueError, newconfig, [], inisource)

    def test_single_value_from_other_secton(self, newconfig, tmpdir):
        inisource = """
            [common]
            changedir = testing
            [testenv]
            changedir = {[common]changedir}
        """
        conf = newconfig([], inisource).envconfigs['python']
        assert conf.changedir.basename == 'testing'
        assert conf.changedir.dirpath().realpath() == tmpdir.realpath()

    @pytest.mark.xfailif("sys.platform == 'win32'")
    def test_substitution_envsitepackagesdir(self, tmpdir, monkeypatch,
                                             newconfig):
        """
         The envsitepackagesdir property is mostly doing system work,
         so this test doesn't excercise it very well.

         Usage of envsitepackagesdir on win32/jython will explicitly
         throw an exception,
        """
        class MockPopen(object):
            returncode = 0

            def __init__(self, *args, **kwargs):
                pass

            def communicate(self, *args, **kwargs):
                return 'onevalue', 'othervalue'

        monkeypatch.setattr(subprocess, 'Popen', MockPopen)
        env = 'py%s' % (''.join(sys.version.split('.')[0:2]))
        config = newconfig("""
            [testenv:%s]
            commands = {envsitepackagesdir}
        """ % (env))
        conf = config.envconfigs[env]
        argv = conf.commands
        assert argv[0][0] == 'onevalue'


class TestGlobalOptions:
    def test_notest(self, newconfig):
        config = newconfig([], "")
        assert not config.option.notest
        config = newconfig(["--notest"], "")
        assert config.option.notest

    def test_verbosity(self, newconfig):
        config = newconfig([], "")
        assert config.option.verbosity == 0
        config = newconfig(["-v"], "")
        assert config.option.verbosity == 1
        config = newconfig(["-vv"], "")
        assert config.option.verbosity == 2

    def test_substitution_jenkins_default(self, tmpdir, monkeypatch, newconfig):
        monkeypatch.setenv("HUDSON_URL", "xyz")
        config = newconfig("""
            [testenv:py24]
            commands =
                {distshare}
        """)
        conf = config.envconfigs['py24']
        argv = conf.commands
        expect_path = config.toxworkdir.join("distshare")
        assert argv[0][0] == expect_path

    def test_substitution_jenkins_context(self, tmpdir, monkeypatch, newconfig):
        monkeypatch.setenv("HUDSON_URL", "xyz")
        monkeypatch.setenv("WORKSPACE", tmpdir)
        config = newconfig("""
            [tox:jenkins]
            distshare = {env:WORKSPACE}/hello
            [testenv:py24]
            commands =
                {distshare}
        """)
        conf = config.envconfigs['py24']
        argv = conf.commands
        assert argv[0][0] == config.distshare
        assert config.distshare == tmpdir.join("hello")

    def test_sdist_specification(self, tmpdir, newconfig):
        config = newconfig("""
            [tox]
            sdistsrc = {distshare}/xyz.zip
        """)
        assert config.sdistsrc == config.distshare.join("xyz.zip")
        config = newconfig([], "")
        assert not config.sdistsrc

    def test_env_selection(self, tmpdir, newconfig, monkeypatch):
        inisource = """
            [tox]
            envlist = py26
            [testenv:py26]
            basepython=python2.6
            [testenv:py31]
            basepython=python3.1
            [testenv:py27]
            basepython=python2.7
        """
        #py.test.raises(tox.exception.ConfigError,
        #    "newconfig(['-exyz'], inisource)")
        config = newconfig([], inisource)
        assert config.envlist == ["py26"]
        config = newconfig(["-epy31"], inisource)
        assert config.envlist == ["py31"]
        monkeypatch.setenv("TOXENV", "py31,py26")
        config = newconfig([], inisource)
        assert config.envlist == ["py31", "py26"]
        monkeypatch.setenv("TOXENV", "ALL")
        config = newconfig([], inisource)
        assert config.envlist == ['py26', 'py27', 'py31']
        config = newconfig(["-eALL"], inisource)
        assert config.envlist == ['py26', 'py27', 'py31']

    def test_py_venv(self, tmpdir, newconfig, monkeypatch):
        config = newconfig(["-epy"], "")
        env = config.envconfigs['py']
        assert str(env.basepython) == sys.executable

    def test_default_environments(self, tmpdir, newconfig, monkeypatch):
        envs = "py24,py25,py26,py27,py31,py32,jython,pypy"
        inisource = """
            [tox]
            envlist = %s
        """ % envs
        config = newconfig([], inisource)
        envlist = envs.split(",")
        assert config.envlist == envlist
        for name in config.envlist:
            env = config.envconfigs[name]
            if name == "jython":
                assert env.basepython == "jython"
            elif name == "pypy":
                assert env.basepython == "pypy"
            else:
                assert name.startswith("py")
                bp = "python%s.%s" %(name[2], name[3])
                assert env.basepython == bp

    def test_minversion(self, tmpdir, newconfig, monkeypatch):
        inisource = """
            [tox]
            minversion = 3.0
        """
        config = newconfig([], inisource)
        assert config.minversion == "3.0"

    def test_defaultenv_commandline(self, tmpdir, newconfig, monkeypatch):
        config = newconfig(["-epy24"], "")
        env = config.envconfigs['py24']
        assert env.basepython == "python2.4"
        assert not env.commands

    def test_defaultenv_partial_override(self, tmpdir, newconfig, monkeypatch):
        inisource = """
            [tox]
            envlist = py24
            [testenv:py24]
            commands= xyz
        """
        config = newconfig([], inisource)
        env = config.envconfigs['py24']
        assert env.basepython == "python2.4"
        assert env.commands == [['xyz']]

class TestIndexServer:
    def test_indexserver(self, tmpdir, newconfig):
        config = newconfig("""
            [tox]
            indexserver =
                name1 = XYZ
                name2 = ABC
        """)
        assert config.indexserver['default'].url == None
        assert config.indexserver['name1'].url == "XYZ"
        assert config.indexserver['name2'].url == "ABC"

    def test_parse_indexserver(self, newconfig):
        inisource = """
            [tox]
            indexserver =
                default = http://pypi.testrun.org
                name1 = whatever
        """
        config = newconfig([], inisource)
        assert config.indexserver['default'].url == "http://pypi.testrun.org"
        assert config.indexserver['name1'].url == "whatever"
        config = newconfig(['-i','qwe'], inisource)
        assert config.indexserver['default'].url == "qwe"
        assert config.indexserver['name1'].url == "whatever"
        config = newconfig(['-i','name1=abc', '-i','qwe2'], inisource)
        assert config.indexserver['default'].url == "qwe2"
        assert config.indexserver['name1'].url == "abc"

        config = newconfig(["-i", "ALL=xzy"], inisource)
        assert len(config.indexserver) == 2
        assert config.indexserver["default"].url == "xzy"
        assert config.indexserver["name1"].url == "xzy"

    def test_multiple_homedir_relative_local_indexservers(self, newconfig):
        inisource = """
            [tox]
            indexserver =
                default = file://{homedir}/.pip/downloads/simple
                local1  = file://{homedir}/.pip/downloads/simple
                local2  = file://{toxinidir}/downloads/simple
                pypi    = http://pypi.python.org/simple
        """
        config = newconfig([], inisource)
        homedir = str(py.path.local._gethomedir())
        assert config.indexserver['default'].url == "file://{h}/.pip/downloads/simple".format(h=homedir)
        assert config.indexserver['local1'].url == config.indexserver['default'].url

class TestParseEnv:

    def test_parse_recreate(self, newconfig):
        inisource = ""
        config = newconfig([], inisource)
        assert not config.envconfigs['python'].recreate
        config = newconfig(['--recreate'], inisource)
        assert config.envconfigs['python'].recreate
        config = newconfig(['-r'], inisource)
        assert config.envconfigs['python'].recreate
        inisource = """
            [testenv:hello]
            recreate = True
        """
        config = newconfig([], inisource)
        assert config.envconfigs['hello'].recreate

class TestCmdInvocation:
    def test_help(self, cmd):
        result = cmd.run("tox", "-h")
        assert not result.ret
        result.stdout.fnmatch_lines([
            "*help*",
        ])

    def test_version(self, cmd):
        result = cmd.run("tox", "--version")
        assert not result.ret
        stdout = result.stdout.str()
        assert tox.__version__ in stdout
        assert "imported from" in stdout

    def test_listenvs(self, cmd, initproj):
        initproj('listenvs', filedefs={
            'tox.ini': '''
            [tox]
            envlist=py26,py27,py33,pypy,docs

            [testenv:notincluded]
            changedir = whatever

            [testenv:docs]
            changedir = docs
            ''',
        })
        result = cmd.run("tox", "-l")
        result.stdout.fnmatch_lines("""
            *py26*
            *py27*
            *py33*
            *pypy*
            *docs*
        """)

    @py.test.mark.xfail("sys.version_info < (2,6)",
        reason="virtualenv3 cannot be imported")
    def test_config_specific_ini(self, tmpdir, cmd):
        ini = tmpdir.ensure("hello.ini")
        result = cmd.run("tox", "-c", ini, "--showconfig")
        assert not result.ret
        result.stdout.fnmatch_lines([
            "*config-file*hello.ini*",
        ])

    def test_no_tox_ini(self, cmd, initproj):
        initproj("noini-0.5", )
        result = cmd.run("tox")
        assert result.ret
        result.stderr.fnmatch_lines([
            "*ERROR*tox.ini*not*found*",
        ])

class TestCommandParser:

    def test_command_parser_for_word(self):
        p = CommandParser('word')
        # import pytest; pytest.set_trace()
        assert list(p.words()) == ['word']

    def test_command_parser_for_posargs(self):
        p = CommandParser('[]')
        assert list(p.words()) == ['[]']

    def test_command_parser_for_multiple_words(self):
        p = CommandParser('w1 w2 w3 ')
        assert list(p.words()) == ['w1', ' ', 'w2', ' ', 'w3']

    def test_command_parser_for_substitution_with_spaces(self):
        p = CommandParser('{sub:something with spaces}')
        assert list(p.words()) == ['{sub:something with spaces}']

    def test_command_parser_with_complex_word_set(self):
        complex_case = 'word [] [literal] {something} {some:other thing} w{ord} w{or}d w{ord} w{o:rd} w{o:r}d {w:or}d w[]ord {posargs:{a key}}'
        p = CommandParser(complex_case)
        parsed = list(p.words())
        expected = [
            'word', ' ', '[]', ' ', '[literal]', ' ', '{something}', ' ', '{some:other thing}',
            ' ', 'w', '{ord}', ' ', 'w', '{or}', 'd', ' ', 'w', '{ord}', ' ', 'w', '{o:rd}', ' ', 'w', '{o:r}', 'd', ' ', '{w:or}', 'd',
            ' ', 'w[]ord', ' ', '{posargs:{a key}}',
            ]

        assert parsed == expected

    def test_command_with_runs_of_whitespace(self):
        cmd = "cmd1 {item1}\n  {item2}"
        p = CommandParser(cmd)
        parsed = list(p.words())
        assert parsed == ['cmd1', ' ', '{item1}', '\n  ', '{item2}']

    def test_command_with_split_line_in_subst_arguments(self):
        cmd = dedent(""" cmd2 {posargs:{item2}
                         other}""")
        p = CommandParser(cmd)
        parsed = list(p.words())
        assert parsed == ['cmd2', ' ', '{posargs:{item2}\n                        other}']

    def test_command_parsing_for_issue_10(self):
        cmd = "nosetests -v -a !deferred --with-doctest []"
        p = CommandParser(cmd)
        parsed = list(p.words())
        assert parsed == ['nosetests', ' ', '-v', ' ', '-a', ' ', '!deferred', ' ', '--with-doctest', ' ', '[]']
