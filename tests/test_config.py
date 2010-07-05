
import tox
import os, sys
import py
from tox._config import IniReader

class TestVenvConfig:
    def test_config_parsing_minimal(self, tmpdir, makeconfig):
        config = makeconfig("""
            [testenv:py1]
        """)
        assert len(config.envconfigs) == 1
        assert config.toxworkdir == tmpdir.join(".tox")
        assert config.envconfigs['py1'].basepython == sys.executable
        assert config.envconfigs['py1'].deps == []

    def test_config_parsing_multienv(self, tmpdir, makeconfig):
        config = makeconfig("""
            [tox]
            toxworkdir = %s
            [testenv:py1]
            basepython=xyz
            deps=hello
            [testenv:py2]
            basepython=hello
            deps=
                world1
                world2
        """ % (tmpdir, ))
        assert config.toxworkdir == tmpdir
        assert len(config.envconfigs) == 2
        assert config.envconfigs['py1'].envdir == tmpdir.join("py1")
        assert config.envconfigs['py1'].basepython == "xyz"
        assert config.envconfigs['py1'].deps == ['hello']
        assert config.envconfigs['py2'].basepython == "hello"
        assert config.envconfigs['py2'].envdir == tmpdir.join("py2")
        assert config.envconfigs['py2'].deps == ['world1', 'world2']

class TestConfigPackage:
    def test_defaults(self, tmpdir, makeconfig):
        config = makeconfig("")
        assert config.setupdir == tmpdir
        assert config.toxworkdir == tmpdir.join(".tox")
        envconfig = config.envconfigs['python']
        assert envconfig.args_are_paths 

    def test_defaults_changed_dir(self, tmpdir, makeconfig):
        tmpdir.mkdir("abc").chdir()
        config = makeconfig("")
        assert config.setupdir == tmpdir
        assert config.toxworkdir == tmpdir.join(".tox")

    def test_project_paths(self, tmpdir, makeconfig):
        config = makeconfig("""
            [tox]
            toxworkdir=%s
        """ % tmpdir)
        assert config.toxworkdir == tmpdir

class TestIniParser:
    def test_getdefault_single(self, tmpdir, makeconfig):
        config = makeconfig("""
            [section]
            key=value
        """)
        reader = IniReader(config._cfg)
        x = reader.getdefault("section", "key")
        assert x == "value"
        assert not reader.getdefault("section", "hello")
        x = reader.getdefault("section", "hello", "world")
        assert x == "world"

    def test_missing_substitution(self, tmpdir, makeconfig):
        config = makeconfig("""
            [mydefault]
            key2={xyz}
        """)
        reader = IniReader(config._cfg, fallbacksections=['mydefault'])
        py.test.raises(tox.exception.ConfigError, 
            'reader.getdefault("mydefault", "key2")')

    def test_getdefault_fallback_sections(self, tmpdir, makeconfig):
        config = makeconfig("""
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

    def test_getdefault_substitution(self, tmpdir, makeconfig):
        config = makeconfig("""
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

    def test_getlist(self, tmpdir, makeconfig):
        config = makeconfig("""
            [section]
            key2=
                item1
                {item2}
        """)
        reader = IniReader(config._cfg)
        reader.addsubstitions(item1="not", item2="grr")
        x = reader.getlist("section", "key2")
        assert x == ['item1', 'grr']

    def test_getdefault_environment_substitution(self, monkeypatch, makeconfig):
        monkeypatch.setenv("KEY1", "hello")
        config = makeconfig("""
            [section]
            key1={env:KEY1}
            key2={env:KEY2}
        """)
        reader = IniReader(config._cfg)
        x = reader.getdefault("section", "key1")
        assert x == "hello"
        py.test.raises(tox.exception.ConfigError, 
            'reader.getdefault("section", "key2")')

    def test_argvlist(self, tmpdir, makeconfig):
        config = makeconfig("""
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

    def test_argvlist_multiline(self, tmpdir, makeconfig):
        config = makeconfig("""
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


    def test_argvlist_positional_substitution(self, tmpdir, makeconfig):
        config = makeconfig("""
            [section]
            key2=
                cmd1 []
                cmd2 [{item2} \
                     other]
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

    def test_getpath(self, tmpdir, makeconfig):
        config = makeconfig("""
            [section]
            path1={HELLO}
        """)
        reader = IniReader(config._cfg)
        reader.addsubstitions(toxinidir=tmpdir, HELLO="mypath")
        x = reader.getpath("section", "path1", tmpdir)
        assert x == tmpdir.join("mypath")

    def test_getbool(self, tmpdir, makeconfig):
        config = makeconfig("""
            [section]
            key1=True
            key2=False
        """)
        reader = IniReader(config._cfg)
        assert reader.getbool("section", "key1") == True
        assert reader.getbool("section", "key2") == False
        py.test.raises(KeyError, 'reader.getbool("section", "key3")')

class TestConfigTestEnv:
    def test_defaults(self, tmpdir, makeconfig):
        config = makeconfig("""
            [testenv]
            commands=
                xyz --abc
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.commands == [["xyz", "--abc"]]
        assert envconfig.changedir == config.setupdir
        assert envconfig.distribute == True

    def test_specific_command_overrides(self, tmpdir, makeconfig):
        config = makeconfig("""
            [testenv]
            commands=xyz
            [testenv:py30]
            commands=abc
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['py30']
        assert envconfig.commands == [["abc"]]

    def test_changedir(self, tmpdir, makeconfig):
        config = makeconfig("""
            [testenv]
            changedir=xyz
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.changedir.basename == "xyz"
        assert envconfig.changedir == config.toxinidir.join("xyz")

    def test_envbindir(self, tmpdir, makeconfig):
        config = makeconfig("""
            [testenv]
            basepython=python 
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.envpython == envconfig.envbindir.join("python")

    def test_envbindir_jython(self, tmpdir, makeconfig):
        config = makeconfig("""
            [testenv]
            basepython=jython 
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.envpython == envconfig.envbindir.join("jython")

    def test_changedir_override(self, tmpdir, makeconfig):
        config = makeconfig("""
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

    def test_simple(tmpdir, makeconfig):
        config = makeconfig("""
            [testenv:py24]
            basepython=python2.4
            [testenv:py25]
            basepython=python2.5
        """)
        assert len(config.envconfigs) == 2
        assert "py24" in config.envconfigs
        assert "py25" in config.envconfigs

    def test_substitution_error(tmpdir, makeconfig):
        py.test.raises(tox.exception.ConfigError, makeconfig, """
            [testenv:py24]
            basepython={xyz}
        """)

    def test_substitution_defaults(tmpdir, makeconfig):
        config = makeconfig("""
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
        """)
        conf = config.envconfigs['py24']
        argv = conf.commands
        assert argv[0][0] == config.toxinidir
        assert argv[1][0] == config.toxworkdir
        assert argv[2][0] == conf.envdir 
        assert argv[3][0] == conf.envbindir
        assert argv[4][0] == conf.envtmpdir
        assert argv[5][0] == conf.envpython
        assert argv[6][0] == os.path.expanduser("~")
        assert argv[7][0] == config.toxdistdir

    def test_substitution_positional(self, newconfig):
        inisource = """
            [testenv:py24]
            commands =
                cmd1 [hello] \
                     world 
        """
        conf = newconfig([], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello", "world"]
        conf = newconfig(['brave', 'new'], inisource).envconfigs['py24']
        argv = conf.commands
        assert argv[0] == ["cmd1", "brave", "new", "world"]

    def test_substitution_hudson_context(self, tmpdir, monkeypatch, makeconfig):
        monkeypatch.setenv("HUDSON_URL", "xyz")
        monkeypatch.setenv("WORKSPACE", tmpdir)
        config = makeconfig("""
            [tox:hudson]
            distshare = {env:WORKSPACE}/hello
            [testenv:py24]
            commands =
                {distshare}
        """)
        conf = config.envconfigs['py24']
        argv = conf.commands
        assert argv[0][0] == config.distshare
        assert config.distshare == tmpdir.join("hello")

    def test_rewrite_posargs(self, tmpdir, newconfig):
        inisource = """
            [testenv:py24]
            args_are_paths = True
            changedir = tests
            commands = cmd1 [hello]
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

class TestParsing:
    def test_skip(self, newconfig):
        config = newconfig([], """
            [tox]
            skip=sdist
        """)
        assert config.skip == ['sdist']
        config = newconfig(["--skip=test"], """
            [tox]
            skip=sdist
        """)
        assert config.skip == ['test']


class TesCmdInvocation:
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

    def test_unkonwn_ini(self, cmd):
        result = cmd.run("tox")
        assert result.ret
        result.stderr.fnmatch_lines([
            "*tox.ini*does not exist*",
        ])

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
            "*ERROR*tox.ini*does not exist*",
        ])

