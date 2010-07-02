
import tox
import sys
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
            [global]
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

    def test_defaults_changed_dir(self, tmpdir, makeconfig):
        tmpdir.mkdir("abc").chdir()
        config = makeconfig("")
        assert config.setupdir == tmpdir
        assert config.toxworkdir == tmpdir.join(".tox")

    def test_project_paths(self, tmpdir, makeconfig):
        config = makeconfig("""
            [global]
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

    def test_getpath(self, tmpdir, makeconfig):
        config = makeconfig("""
            [section]
            path1={HELLO}
        """)
        reader = IniReader(config._cfg)
        reader.addsubstitions(HELLO="mypath")
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
            [test]
            argv=xyz
                --abc
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.argv == ["xyz", "--abc"]
        assert envconfig.changedir == config.setupdir
        assert envconfig.distribute == False

    def test_specific_command_overrides(self, tmpdir, makeconfig):
        config = makeconfig("""
            [test]
            argv=xyz
            [testenv:py30]
            argv=abc
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['py30']
        assert envconfig.argv == ["abc"]

    def test_changedir(self, tmpdir, makeconfig):
        config = makeconfig("""
            [test]
            changedir=xyz
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.changedir.basename == "xyz"
        assert envconfig.changedir == config.toxinidir.join("xyz")

    def test_changedir_override(self, tmpdir, makeconfig):
        config = makeconfig("""
            [test]
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
            argv=
                {toxinidir}
                {toxworkdir}
                {envdir}
                {envbindir}
                {envtmpdir}
                {envpython}
        """)
        conf = config.envconfigs['py24']
        argv = conf.argv 
        assert argv[0] == config.toxinidir 
        assert argv[1] == config.toxworkdir 
        assert argv[2] == conf.envdir 
        assert argv[3] == conf.envbindir
        assert argv[4] == conf.envtmpdir
        assert argv[5] == conf.envpython
