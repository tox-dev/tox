
import tox
import sys
import py

class TestVenvConfig:
    def test_config_parsing_minimal(self, tmpdir, makeconfig):
        config = makeconfig("""
            [testenv:py1]
        """)
        assert len(config.envconfigs) == 1
        assert config.toxdir == tmpdir.join(".tox")
        assert config.envconfigs['py1'].python == None
        assert config.envconfigs['py1'].deps == []

    def test_config_parsing_multienv(self, tmpdir, makeconfig):
        config = makeconfig("""
            [global]
            toxdir = %s
            [testenv:py1]
            python=xyz
            deps=hello
            [testenv:py2]
            python=hello
            deps=
                world1
                world2
        """ % (tmpdir, ))
        assert config.toxdir == tmpdir
        assert len(config.envconfigs) == 2
        assert config.envconfigs['py1'].envdir == tmpdir.join("py1")
        assert config.envconfigs['py1'].python == "xyz"
        assert config.envconfigs['py1'].deps == ['hello']
        assert config.envconfigs['py2'].python == "hello"
        assert config.envconfigs['py2'].envdir == tmpdir.join("py2")
        assert config.envconfigs['py2'].deps == ['world1', 'world2']

class TestConfigPackage:
    def test_defaults(self, tmpdir, makeconfig):
        config = makeconfig("")
        assert config.packagedir == tmpdir
        assert config.toxdir == tmpdir.join(".tox")

    def test_defaults_changed_dir(self, tmpdir, makeconfig):
        tmpdir.mkdir("abc").chdir()
        config = makeconfig("")
        assert config.packagedir == tmpdir
        assert config.toxdir == tmpdir.join(".tox")

    def test_project_paths(self, tmpdir, makeconfig):
        config = makeconfig("""
            [global]
            toxdir=%s
        """ % tmpdir)
        assert config.toxdir == tmpdir

class TestConfigTestEnv:
    def test_defaults(self, tmpdir, makeconfig):
        config = makeconfig("""
            [test]
            cmdargs=xyz
                --abc
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.cmdargs == ["xyz", "--abc"]
        assert envconfig.changedir == config.packagedir

    def test_specific_command_overrides(self, tmpdir, makeconfig):
        config = makeconfig("""
            [test]
            cmdargs=xyz
            [testenv:py30]
            cmdargs=abc
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['py30']
        assert envconfig.cmdargs == ["abc"]

    def test_changedir(self, tmpdir, makeconfig):
        config = makeconfig("""
            [test]
            changedir=xyz
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.changedir.basename == "xyz"
        assert envconfig.changedir == config.packagedir.join("xyz")

    def test_changedir_override(self, tmpdir, makeconfig):
        config = makeconfig("""
            [test]
            changedir=xyz
            [testenv:python]
            changedir=abc
            python=python2.6
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.changedir.basename == "abc"
        assert envconfig.changedir == config.packagedir.join("abc")

    def test_getpath(self, tmpdir, makeconfig):
        config = makeconfig("""
            [xyz]
            path=xyz
        """)
        x = config._parser.getpath("xyz", "path", tmpdir)
        assert x == tmpdir.join("xyz")

    def test_simple(tmpdir, makeconfig):
        config = makeconfig("""
            [testenv:py24]
            python=python2.4
            [testenv:py25]
            python=python2.5
        """)
        assert len(config.envconfigs) == 2
        assert "py24" in config.envconfigs
        assert "py25" in config.envconfigs
