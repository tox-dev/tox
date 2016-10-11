import sys
import os
from textwrap import dedent

import py
import pytest
import tox
import tox.config
from tox.config import (
    SectionReader, is_section_substitution, CommandParser,
    parseconfig, DepOption, get_homedir, getcontextname,
)
from tox.venv import VirtualEnv


class TestVenvConfig:
    def test_config_parsing_minimal(self, tmpdir, newconfig):
        config = newconfig([], """
            [testenv:py1]
        """)
        assert len(config.envconfigs) == 1
        assert config.toxworkdir.realpath() == tmpdir.join(".tox").realpath()
        assert config.envconfigs['py1'].basepython == sys.executable
        assert config.envconfigs['py1'].deps == []
        assert config.envconfigs['py1'].platform == ".*"

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

    def test_envdir_set_manually(self, tmpdir, newconfig):
        config = newconfig([], """
            [testenv:devenv]
            envdir = devenv
        """)
        envconfig = config.envconfigs['devenv']
        assert envconfig.envdir == tmpdir.join('devenv')

    def test_envdir_set_manually_with_substitutions(self, tmpdir, newconfig):
        config = newconfig([], """
            [testenv:devenv]
            envdir = {toxworkdir}/foobar
        """)
        envconfig = config.envconfigs['devenv']
        assert envconfig.envdir == config.toxworkdir.join('foobar')

    def test_force_dep_version(self, initproj):
        """
        Make sure we can override dependencies configured in tox.ini when using the command line
        option --force-dep.
        """
        initproj("example123-0.5", filedefs={
            'tox.ini': '''
            [tox]

            [testenv]
            deps=
                dep1==1.0
                dep2>=2.0
                dep3
                dep4==4.0
            '''
        })
        config = parseconfig(
            ['--force-dep=dep1==1.5', '--force-dep=dep2==2.1',
             '--force-dep=dep3==3.0'])
        assert config.option.force_dep == [
            'dep1==1.5', 'dep2==2.1', 'dep3==3.0']
        assert [str(x) for x in config.envconfigs['python'].deps] == [
            'dep1==1.5', 'dep2==2.1', 'dep3==3.0', 'dep4==4.0',
        ]

    def test_force_dep_with_url(self, initproj):
        initproj("example123-0.5", filedefs={
            'tox.ini': '''
            [tox]

            [testenv]
            deps=
                dep1==1.0
                https://pypi.python.org/xyz/pkg1.tar.gz
            '''
        })
        config = parseconfig(
            ['--force-dep=dep1==1.5'])
        assert config.option.force_dep == [
            'dep1==1.5'
        ]
        assert [str(x) for x in config.envconfigs['python'].deps] == [
            'dep1==1.5', 'https://pypi.python.org/xyz/pkg1.tar.gz'
        ]

    def test_is_same_dep(self):
        """
        Ensure correct parseini._is_same_dep is working with a few samples.
        """
        assert DepOption._is_same_dep('pkg_hello-world3==1.0', 'pkg_hello-world3')
        assert DepOption._is_same_dep('pkg_hello-world3==1.0', 'pkg_hello-world3>=2.0')
        assert DepOption._is_same_dep('pkg_hello-world3==1.0', 'pkg_hello-world3>2.0')
        assert DepOption._is_same_dep('pkg_hello-world3==1.0', 'pkg_hello-world3<2.0')
        assert DepOption._is_same_dep('pkg_hello-world3==1.0', 'pkg_hello-world3<=2.0')
        assert not DepOption._is_same_dep('pkg_hello-world3==1.0', 'otherpkg>=2.0')


class TestConfigPlatform:
    def test_config_parse_platform(self, newconfig):
        config = newconfig([], """
            [testenv:py1]
            platform = linux2
        """)
        assert len(config.envconfigs) == 1
        assert config.envconfigs['py1'].platform == "linux2"

    def test_config_parse_platform_rex(self, newconfig, mocksession, monkeypatch):
        config = newconfig([], """
            [testenv:py1]
            platform = a123|b123
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['py1']
        venv = VirtualEnv(envconfig, session=mocksession)
        assert not venv.matching_platform()
        monkeypatch.setattr(sys, "platform", "a123")
        assert venv.matching_platform()
        monkeypatch.setattr(sys, "platform", "b123")
        assert venv.matching_platform()
        monkeypatch.undo()
        assert not venv.matching_platform()

    @pytest.mark.parametrize("plat", ["win", "lin", ])
    def test_config_parse_platform_with_factors(self, newconfig, plat, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        config = newconfig([], """
            [tox]
            envlist = py27-{win,lin,osx}
            [testenv]
            platform =
                win: win32
                lin: linux2
        """)
        assert len(config.envconfigs) == 3
        platform = config.envconfigs['py27-' + plat].platform
        expected = {"win": "win32", "lin": "linux2"}.get(plat)
        assert platform == expected


class TestConfigPackage:
    def test_defaults(self, tmpdir, newconfig):
        config = newconfig([], "")
        assert config.setupdir.realpath() == tmpdir.realpath()
        assert config.toxworkdir.realpath() == tmpdir.join(".tox").realpath()
        envconfig = config.envconfigs['python']
        assert envconfig.args_are_paths
        assert not envconfig.recreate
        assert not envconfig.pip_pre

    def test_defaults_distshare(self, tmpdir, newconfig):
        config = newconfig([], "")
        assert config.distshare == config.homedir.join(".tox", "distshare")

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


def test_get_homedir(monkeypatch):
    monkeypatch.setattr(py.path.local, "_gethomedir",
                        classmethod(lambda x: {}[1]))
    assert not get_homedir()
    monkeypatch.setattr(py.path.local, "_gethomedir",
                        classmethod(lambda x: 0 / 0))
    assert not get_homedir()
    monkeypatch.setattr(py.path.local, "_gethomedir",
                        classmethod(lambda x: "123"))
    assert get_homedir() == "123"


class TestGetcontextname:
    def test_blank(self, monkeypatch):
        monkeypatch.setattr(os, "environ", {})
        assert getcontextname() is None

    def test_jenkins(self, monkeypatch):
        monkeypatch.setattr(os, "environ", {"JENKINS_URL": "xyz"})
        assert getcontextname() == "jenkins"

    def test_hudson_legacy(self, monkeypatch):
        monkeypatch.setattr(os, "environ", {"HUDSON_URL": "xyz"})
        assert getcontextname() == "jenkins"


class TestIniParserAgainstCommandsKey:
    """Test parsing commands with substitutions"""

    def test_command_substitution_from_other_section(self, newconfig):
        config = newconfig("""
            [section]
            key = whatever
            [testenv]
            commands =
                echo {[section]key}
            """)
        reader = SectionReader("testenv", config._cfg)
        x = reader.getargvlist("commands")
        assert x == [["echo", "whatever"]]

    def test_command_substitution_from_other_section_multiline(self, newconfig):
        """Ensure referenced multiline commands form from other section injected
        as multiple commands."""
        config = newconfig("""
            [section]
            commands =
                      cmd1 param11 param12
                      # comment is omitted
                      cmd2 param21 \
                           param22
            [base]
            commands = cmd 1 \
                           2 3 4
                       cmd 2
            [testenv]
            commands =
                {[section]commands}
                {[section]commands}
                # comment is omitted
                echo {[base]commands}
            """)
        reader = SectionReader("testenv", config._cfg)
        x = reader.getargvlist("commands")
        assert x == [
            "cmd1 param11 param12".split(),
            "cmd2 param21 param22".split(),
            "cmd1 param11 param12".split(),
            "cmd2 param21 param22".split(),
            ["echo", "cmd", "1", "2", "3", "4", "cmd", "2"],
        ]

    def test_command_substitution_from_other_section_posargs(self, newconfig):
        """Ensure subsitition from other section with posargs succeeds"""
        config = newconfig("""
            [section]
            key = thing {posargs} arg2
            [testenv]
            commands =
                {[section]key}
            """)
        reader = SectionReader("testenv", config._cfg)
        reader.addsubstitutions([r"argpos"])
        x = reader.getargvlist("commands")
        assert x == [['thing', 'argpos', 'arg2']]

    def test_command_section_and_posargs_substitution(self, newconfig):
        """Ensure subsitition from other section with posargs succeeds"""
        config = newconfig("""
            [section]
            key = thing arg1
            [testenv]
            commands =
                {[section]key} {posargs} endarg
            """)
        reader = SectionReader("testenv", config._cfg)
        reader.addsubstitutions([r"argpos"])
        x = reader.getargvlist("commands")
        assert x == [['thing', 'arg1', 'argpos', 'endarg']]

    def test_command_env_substitution(self, newconfig):
        """Ensure referenced {env:key:default} values are substituted correctly."""
        config = newconfig("""
           [testenv:py27]
           setenv =
             TEST=testvalue
           commands =
             ls {env:TEST}
        """)
        envconfig = config.envconfigs["py27"]
        assert envconfig.commands == [["ls", "testvalue"]]
        assert envconfig.setenv["TEST"] == "testvalue"


class TestIniParser:
    def test_getstring_single(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key=value
        """)
        reader = SectionReader("section", config._cfg)
        x = reader.getstring("key")
        assert x == "value"
        assert not reader.getstring("hello")
        x = reader.getstring("hello", "world")
        assert x == "world"

    def test_missing_substitution(self, tmpdir, newconfig):
        config = newconfig("""
            [mydefault]
            key2={xyz}
        """)
        reader = SectionReader("mydefault", config._cfg, fallbacksections=['mydefault'])
        assert reader is not None
        with py.test.raises(tox.exception.ConfigError):
            reader.getstring("key2")

    def test_getstring_fallback_sections(self, tmpdir, newconfig):
        config = newconfig("""
            [mydefault]
            key2=value2
            [section]
            key=value
        """)
        reader = SectionReader("section", config._cfg, fallbacksections=['mydefault'])
        x = reader.getstring("key2")
        assert x == "value2"
        x = reader.getstring("key3")
        assert not x
        x = reader.getstring("key3", "world")
        assert x == "world"

    def test_getstring_substitution(self, tmpdir, newconfig):
        config = newconfig("""
            [mydefault]
            key2={value2}
            [section]
            key={value}
        """)
        reader = SectionReader("section", config._cfg, fallbacksections=['mydefault'])
        reader.addsubstitutions(value="newvalue", value2="newvalue2")
        x = reader.getstring("key2")
        assert x == "newvalue2"
        x = reader.getstring("key3")
        assert not x
        x = reader.getstring("key3", "{value2}")
        assert x == "newvalue2"

    def test_getlist(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                item1
                {item2}
        """)
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(item1="not", item2="grr")
        x = reader.getlist("key2")
        assert x == ['item1', 'grr']

    def test_getdict(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                key1=item1
                key2={item2}
        """)
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(item1="not", item2="grr")
        x = reader.getdict("key2")
        assert 'key1' in x
        assert 'key2' in x
        assert x['key1'] == 'item1'
        assert x['key2'] == 'grr'

        x = reader.getdict("key3", {1: 2})
        assert x == {1: 2}

    def test_getstring_environment_substitution(self, monkeypatch, newconfig):
        monkeypatch.setenv("KEY1", "hello")
        config = newconfig("""
            [section]
            key1={env:KEY1}
            key2={env:KEY2}
        """)
        reader = SectionReader("section", config._cfg)
        x = reader.getstring("key1")
        assert x == "hello"
        with py.test.raises(tox.exception.ConfigError):
            reader.getstring("key2")

    def test_getstring_environment_substitution_with_default(self, monkeypatch, newconfig):
        monkeypatch.setenv("KEY1", "hello")
        config = newconfig("""
            [section]
            key1={env:KEY1:DEFAULT_VALUE}
            key2={env:KEY2:DEFAULT_VALUE}
            key3={env:KEY3:}
        """)
        reader = SectionReader("section", config._cfg)
        x = reader.getstring("key1")
        assert x == "hello"
        x = reader.getstring("key2")
        assert x == "DEFAULT_VALUE"
        x = reader.getstring("key3")
        assert x == ""

    def test_value_matches_section_substituion(self):
        assert is_section_substitution("{[setup]commands}")

    def test_value_doesn_match_section_substitution(self):
        assert is_section_substitution("{[ ]commands}") is None
        assert is_section_substitution("{[setup]}") is None
        assert is_section_substitution("{[setup] commands}") is None

    def test_getstring_other_section_substitution(self, newconfig):
        config = newconfig("""
            [section]
            key = rue
            [testenv]
            key = t{[section]key}
            """)
        reader = SectionReader("testenv", config._cfg)
        x = reader.getstring("key")
        assert x == "true"

    def test_argvlist(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                cmd1 {item1} {item2}
                cmd2 {item2}
        """)
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(item1="with space", item2="grr")
        # py.test.raises(tox.exception.ConfigError,
        #    "reader.getargvlist('key1')")
        assert reader.getargvlist('key1') == []
        x = reader.getargvlist("key2")
        assert x == [["cmd1", "with", "space", "grr"],
                     ["cmd2", "grr"]]

    def test_argvlist_windows_escaping(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            comm = py.test {posargs}
        """)
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions([r"hello\this"])
        argv = reader.getargv("comm")
        assert argv == ["py.test", "hello\\this"]

    def test_argvlist_multiline(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                cmd1 {item1} \
                     {item2}
        """)
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(item1="with space", item2="grr")
        # py.test.raises(tox.exception.ConfigError,
        #    "reader.getargvlist('key1')")
        assert reader.getargvlist('key1') == []
        x = reader.getargvlist("key2")
        assert x == [["cmd1", "with", "space", "grr"]]

    def test_argvlist_quoting_in_command(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key1=
                cmd1 'part one' \
                     'part two'
        """)
        reader = SectionReader("section", config._cfg)
        x = reader.getargvlist("key1")
        assert x == [["cmd1", "part one", "part two"]]

    def test_argvlist_comment_after_command(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key1=
                cmd1 --flag  # run the flag on the command
        """)
        reader = SectionReader("section", config._cfg)
        x = reader.getargvlist("key1")
        assert x == [["cmd1", "--flag"]]

    def test_argvlist_command_contains_hash(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key1=
                cmd1 --re  "use the # symbol for an arg"
        """)
        reader = SectionReader("section", config._cfg)
        x = reader.getargvlist("key1")
        assert x == [["cmd1", "--re", "use the # symbol for an arg"]]

    def test_argvlist_positional_substitution(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                cmd1 []
                cmd2 {posargs:{item2} \
                     other}
        """)
        reader = SectionReader("section", config._cfg)
        posargs = ['hello', 'world']
        reader.addsubstitutions(posargs, item2="value2")
        # py.test.raises(tox.exception.ConfigError,
        #    "reader.getargvlist('key1')")
        assert reader.getargvlist('key1') == []
        argvlist = reader.getargvlist("key2")
        assert argvlist[0] == ["cmd1"] + posargs
        assert argvlist[1] == ["cmd2"] + posargs

        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions([], item2="value2")
        # py.test.raises(tox.exception.ConfigError,
        #    "reader.getargvlist('key1')")
        assert reader.getargvlist('key1') == []
        argvlist = reader.getargvlist("key2")
        assert argvlist[0] == ["cmd1"]
        assert argvlist[1] == ["cmd2", "value2", "other"]

    def test_argvlist_quoted_posargs(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                cmd1 --foo-args='{posargs}'
                cmd2 -f '{posargs}'
                cmd3 -f {posargs}
        """)
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(["foo", "bar"])
        assert reader.getargvlist('key1') == []
        x = reader.getargvlist("key2")
        assert x == [["cmd1", "--foo-args=foo bar"],
                     ["cmd2", "-f", "foo bar"],
                     ["cmd3", "-f", "foo", "bar"]]

    def test_argvlist_posargs_with_quotes(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key2=
                cmd1 -f {posargs}
        """)
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(["foo", "'bar", "baz'"])
        assert reader.getargvlist('key1') == []
        x = reader.getargvlist("key2")
        assert x == [["cmd1", "-f", "foo", "bar baz"]]

    def test_positional_arguments_are_only_replaced_when_standing_alone(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            key=
                cmd0 []
                cmd1 -m '[abc]'
                cmd2 -m '\'something\'' []
                cmd3 something[]else
        """)
        reader = SectionReader("section", config._cfg)
        posargs = ['hello', 'world']
        reader.addsubstitutions(posargs)

        argvlist = reader.getargvlist('key')
        assert argvlist[0] == ['cmd0'] + posargs
        assert argvlist[1] == ['cmd1', '-m', '[abc]']
        assert argvlist[2] == ['cmd2', '-m', "something"] + posargs
        assert argvlist[3] == ['cmd3', 'something[]else']

    def test_substitution_with_multiple_words(self, newconfig):
        inisource = """
            [section]
            key = py.test -n5 --junitxml={envlogdir}/junit-{envname}.xml []
            """
        config = newconfig(inisource)
        reader = SectionReader("section", config._cfg)
        posargs = ['hello', 'world']
        reader.addsubstitutions(posargs, envlogdir='ENV_LOG_DIR', envname='ENV_NAME')

        expected = [
            'py.test', '-n5', '--junitxml=ENV_LOG_DIR/junit-ENV_NAME.xml', 'hello', 'world'
        ]
        assert reader.getargvlist('key')[0] == expected

    def test_getargv(self, newconfig):
        config = newconfig("""
            [section]
            key=some command "with quoting"
        """)
        reader = SectionReader("section", config._cfg)
        expected = ['some', 'command', 'with quoting']
        assert reader.getargv('key') == expected

    def test_getpath(self, tmpdir, newconfig):
        config = newconfig("""
            [section]
            path1={HELLO}
        """)
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(toxinidir=tmpdir, HELLO="mypath")
        x = reader.getpath("path1", tmpdir)
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
        reader = SectionReader("section", config._cfg)
        assert reader.getbool("key1") is True
        assert reader.getbool("key1a") is True
        assert reader.getbool("key2") is False
        assert reader.getbool("key2a") is False
        py.test.raises(KeyError, 'reader.getbool("key3")')
        py.test.raises(tox.exception.ConfigError, 'reader.getbool("key5")')


class TestIniParserPrefix:
    def test_basic_section_access(self, tmpdir, newconfig):
        config = newconfig("""
            [p:section]
            key=value
        """)
        reader = SectionReader("section", config._cfg, prefix="p")
        x = reader.getstring("key")
        assert x == "value"
        assert not reader.getstring("hello")
        x = reader.getstring("hello", "world")
        assert x == "world"

    def test_fallback_sections(self, tmpdir, newconfig):
        config = newconfig("""
            [p:mydefault]
            key2=value2
            [p:section]
            key=value
        """)
        reader = SectionReader("section", config._cfg, prefix="p",
                               fallbacksections=['p:mydefault'])
        x = reader.getstring("key2")
        assert x == "value2"
        x = reader.getstring("key3")
        assert not x
        x = reader.getstring("key3", "world")
        assert x == "world"

    def test_value_matches_prefixed_section_substituion(self):
        assert is_section_substitution("{[p:setup]commands}")

    def test_value_doesn_match_prefixed_section_substitution(self):
        assert is_section_substitution("{[p: ]commands}") is None
        assert is_section_substitution("{[p:setup]}") is None
        assert is_section_substitution("{[p:setup] commands}") is None

    def test_other_section_substitution(self, newconfig):
        config = newconfig("""
            [p:section]
            key = rue
            [p:testenv]
            key = t{[p:section]key}
            """)
        reader = SectionReader("testenv", config._cfg, prefix="p")
        x = reader.getstring("key")
        assert x == "true"


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
        assert envconfig.sitepackages is False
        assert envconfig.usedevelop is False
        assert envconfig.ignore_errors is False
        assert envconfig.envlogdir == envconfig.envdir.join("log")
        assert list(envconfig.setenv.definitions.keys()) == ['PYTHONHASHSEED']
        hashseed = envconfig.setenv['PYTHONHASHSEED']
        assert isinstance(hashseed, str)
        # The following line checks that hashseed parses to an integer.
        int_hashseed = int(hashseed)
        # hashseed is random by default, so we can't assert a specific value.
        assert int_hashseed > 0
        assert envconfig.ignore_outcome is False

    def test_sitepackages_switch(self, tmpdir, newconfig):
        config = newconfig(["--sitepackages"], "")
        envconfig = config.envconfigs['python']
        assert envconfig.sitepackages is True

    def test_installpkg_tops_develop(self, newconfig):
        config = newconfig(["--installpkg=abc"], """
            [testenv]
            usedevelop = True
        """)
        assert not config.envconfigs["python"].usedevelop

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

    def test_whitelist_externals(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            whitelist_externals = xyz
            commands=xyz
            [testenv:x]

            [testenv:py]
            whitelist_externals = xyz2
            commands=abc
        """)
        assert len(config.envconfigs) == 2
        envconfig = config.envconfigs['py']
        assert envconfig.commands == [["abc"]]
        assert envconfig.whitelist_externals == ["xyz2"]
        envconfig = config.envconfigs['x']
        assert envconfig.whitelist_externals == ["xyz"]

    def test_changedir(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            changedir=xyz
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.changedir.basename == "xyz"
        assert envconfig.changedir == config.toxinidir.join("xyz")

    def test_ignore_errors(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            ignore_errors=True
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.ignore_errors is True

    def test_envbindir(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            basepython=python
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert envconfig.envpython == envconfig.envbindir.join("python")

    @pytest.mark.parametrize("bp", ["jython", "pypy", "pypy3"])
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

    @pytest.mark.parametrize("plat", ["win32", "linux2"])
    def test_passenv_as_multiline_list(self, tmpdir, newconfig, monkeypatch, plat):
        monkeypatch.setattr(sys, "platform", plat)
        monkeypatch.setenv("A123A", "a")
        monkeypatch.setenv("A123B", "b")
        monkeypatch.setenv("BX23", "0")
        config = newconfig("""
            [testenv]
            passenv =
                      A123*
                      # isolated comment
                      B?23
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        if plat == "win32":
            assert "PATHEXT" in envconfig.passenv
            assert "SYSTEMDRIVE" in envconfig.passenv
            assert "SYSTEMROOT" in envconfig.passenv
            assert "TEMP" in envconfig.passenv
            assert "TMP" in envconfig.passenv
        else:
            assert "TMPDIR" in envconfig.passenv
        assert "PATH" in envconfig.passenv
        assert "PIP_INDEX_URL" in envconfig.passenv
        assert "LANG" in envconfig.passenv
        assert "LD_LIBRARY_PATH" in envconfig.passenv
        assert "A123A" in envconfig.passenv
        assert "A123B" in envconfig.passenv

    @pytest.mark.parametrize("plat", ["win32", "linux2"])
    def test_passenv_as_space_separated_list(self, tmpdir, newconfig, monkeypatch, plat):
        monkeypatch.setattr(sys, "platform", plat)
        monkeypatch.setenv("A123A", "a")
        monkeypatch.setenv("A123B", "b")
        monkeypatch.setenv("BX23", "0")
        config = newconfig("""
            [testenv]
            passenv =
                      # comment
                      A123*  B?23
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        if plat == "win32":
            assert "PATHEXT" in envconfig.passenv
            assert "SYSTEMDRIVE" in envconfig.passenv
            assert "SYSTEMROOT" in envconfig.passenv
            assert "TEMP" in envconfig.passenv
            assert "TMP" in envconfig.passenv
        else:
            assert "TMPDIR" in envconfig.passenv
        assert "PATH" in envconfig.passenv
        assert "PIP_INDEX_URL" in envconfig.passenv
        assert "LANG" in envconfig.passenv
        assert "A123A" in envconfig.passenv
        assert "A123B" in envconfig.passenv

    def test_passenv_with_factor(self, tmpdir, newconfig, monkeypatch):
        monkeypatch.setenv("A123A", "a")
        monkeypatch.setenv("A123B", "b")
        monkeypatch.setenv("A123C", "c")
        monkeypatch.setenv("A123D", "d")
        monkeypatch.setenv("BX23", "0")
        monkeypatch.setenv("CCA43", "3")
        monkeypatch.setenv("CB21", "4")
        config = newconfig("""
            [tox]
            envlist = {x1,x2}
            [testenv]
            passenv =
                x1: A123A CC*
                x1: CB21
                # passed to both environments
                A123C
                x2: A123B A123D
        """)
        assert len(config.envconfigs) == 2

        assert "A123A" in config.envconfigs["x1"].passenv
        assert "A123C" in config.envconfigs["x1"].passenv
        assert "CCA43" in config.envconfigs["x1"].passenv
        assert "CB21" in config.envconfigs["x1"].passenv
        assert "A123B" not in config.envconfigs["x1"].passenv
        assert "A123D" not in config.envconfigs["x1"].passenv
        assert "BX23" not in config.envconfigs["x1"].passenv

        assert "A123B" in config.envconfigs["x2"].passenv
        assert "A123D" in config.envconfigs["x2"].passenv
        assert "A123A" not in config.envconfigs["x2"].passenv
        assert "A123C" in config.envconfigs["x2"].passenv
        assert "CCA43" not in config.envconfigs["x2"].passenv
        assert "CB21" not in config.envconfigs["x2"].passenv
        assert "BX23" not in config.envconfigs["x2"].passenv

    def test_passenv_from_global_env(self, tmpdir, newconfig, monkeypatch):
        monkeypatch.setenv("A1", "a1")
        monkeypatch.setenv("A2", "a2")
        monkeypatch.setenv("TOX_TESTENV_PASSENV", "A1")
        config = newconfig("""
            [testenv]
            passenv = A2
        """)
        env = config.envconfigs["python"]
        assert "A1" in env.passenv
        assert "A2" in env.passenv

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

    def test_install_command_setting(self, newconfig):
        config = newconfig("""
            [testenv]
            install_command=some_install {packages}
        """)
        envconfig = config.envconfigs['python']
        assert envconfig.install_command == [
            'some_install', '{packages}']

    def test_install_command_must_contain_packages(self, newconfig):
        py.test.raises(tox.exception.ConfigError, newconfig, """
            [testenv]
            install_command=pip install
        """)

    def test_install_command_substitutions(self, newconfig):
        config = newconfig("""
            [testenv]
            install_command=some_install --arg={toxinidir}/foo \
                {envname} {opts} {packages}
        """)
        envconfig = config.envconfigs['python']
        assert envconfig.install_command == [
            'some_install', '--arg=%s/foo' % config.toxinidir, 'python',
            '{opts}', '{packages}']

    def test_pip_pre(self, newconfig):
        config = newconfig("""
            [testenv]
            pip_pre=true
        """)
        envconfig = config.envconfigs['python']
        assert envconfig.pip_pre

    def test_pip_pre_cmdline_override(self, newconfig):
        config = newconfig(
            ['--pre'],
            """
            [testenv]
            pip_pre=false
        """)
        envconfig = config.envconfigs['python']
        assert envconfig.pip_pre

    def test_downloadcache(self, newconfig, monkeypatch):
        monkeypatch.delenv("PIP_DOWNLOAD_CACHE", raising=False)
        config = newconfig("""
            [testenv]
            downloadcache=thecache
        """)
        envconfig = config.envconfigs['python']
        assert envconfig.downloadcache.basename == 'thecache'

    def test_downloadcache_env_override(self, newconfig, monkeypatch):
        monkeypatch.setenv("PIP_DOWNLOAD_CACHE", 'fromenv')
        config = newconfig("""
            [testenv]
            downloadcache=somepath
        """)
        envconfig = config.envconfigs['python']
        assert envconfig.downloadcache.basename == "fromenv"

    def test_downloadcache_only_if_in_config(self, newconfig, tmpdir,
                                             monkeypatch):
        monkeypatch.setenv("PIP_DOWNLOAD_CACHE", tmpdir)
        config = newconfig('')
        envconfig = config.envconfigs['python']
        assert not envconfig.downloadcache

    def test_simple(tmpdir, newconfig):
        config = newconfig("""
            [testenv:py26]
            basepython=python2.6
            [testenv:py27]
            basepython=python2.7
        """)
        assert len(config.envconfigs) == 2
        assert "py26" in config.envconfigs
        assert "py27" in config.envconfigs

    def test_substitution_error(tmpdir, newconfig):
        py.test.raises(tox.exception.ConfigError, newconfig, """
            [testenv:py27]
            basepython={xyz}
        """)

    def test_substitution_defaults(tmpdir, newconfig):
        config = newconfig("""
            [testenv:py27]
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
        conf = config.envconfigs['py27']
        argv = conf.commands
        assert argv[0][0] == config.toxinidir
        assert argv[1][0] == config.toxworkdir
        assert argv[2][0] == conf.envdir
        assert argv[3][0] == conf.envbindir
        assert argv[4][0] == conf.envtmpdir
        assert argv[5][0] == conf.envpython
        assert argv[6][0] == str(config.homedir)
        assert argv[7][0] == config.homedir.join(".tox", "distshare")
        assert argv[8][0] == conf.envlogdir

    def test_substitution_notfound_issue246(tmpdir, newconfig):
        config = newconfig("""
            [testenv:py27]
            setenv =
                FOO={envbindir}
                BAR={envsitepackagesdir}
        """)
        conf = config.envconfigs['py27']
        env = conf.setenv
        assert 'FOO' in env
        assert 'BAR' in env

    def test_substitution_positional(self, newconfig):
        inisource = """
            [testenv:py27]
            commands =
                cmd1 [hello] \
                     world
                cmd1 {posargs:hello} \
                     world
        """
        conf = newconfig([], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ["cmd1", "[hello]", "world"]
        assert argv[1] == ["cmd1", "hello", "world"]
        conf = newconfig(['brave', 'new'], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ["cmd1", "[hello]", "world"]
        assert argv[1] == ["cmd1", "brave", "new", "world"]

    def test_substitution_noargs_issue240(self, newconfig):
        inisource = """
            [testenv]
            commands = echo {posargs:foo}
        """
        conf = newconfig([""], inisource).envconfigs['python']
        argv = conf.commands
        assert argv[0] == ["echo"]

    def test_substitution_double(self, newconfig):
        inisource = """
            [params]
            foo = bah
            foo2 = [params]foo

            [testenv:py27]
            commands =
                echo {{[params]foo2}}
        """
        conf = newconfig([], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ['echo', 'bah']

    def test_posargs_backslashed_or_quoted(self, tmpdir, newconfig):
        inisource = """
            [testenv:py27]
            commands =
                echo "\{posargs\}" = {posargs}
                echo "posargs = " "{posargs}"
        """
        conf = newconfig([], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ['echo', '{posargs}', '=']
        assert argv[1] == ['echo', 'posargs = ', ""]

        conf = newconfig(['dog', 'cat'], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ['echo', '{posargs}', '=', 'dog', 'cat']
        assert argv[1] == ['echo', 'posargs = ', 'dog cat']

    def test_rewrite_posargs(self, tmpdir, newconfig):
        inisource = """
            [testenv:py27]
            args_are_paths = True
            changedir = tests
            commands = cmd1 {posargs:hello}
        """
        conf = newconfig([], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello"]

        conf = newconfig(["tests/hello"], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ["cmd1", "tests/hello"]

        tmpdir.ensure("tests", "hello")
        conf = newconfig(["tests/hello"], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello"]

    def test_rewrite_simple_posargs(self, tmpdir, newconfig):
        inisource = """
            [testenv:py27]
            args_are_paths = True
            changedir = tests
            commands = cmd1 {posargs}
        """
        conf = newconfig([], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ["cmd1"]

        conf = newconfig(["tests/hello"], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ["cmd1", "tests/hello"]

        tmpdir.ensure("tests", "hello")
        conf = newconfig(["tests/hello"], inisource).envconfigs['py27']
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello"]

    @pytest.mark.parametrize('envlist, deps', [
        (['py27'], ('pytest', 'pytest-cov')),
        (['py27', 'py34'], ('pytest', 'py{27,34}: pytest-cov')),
    ])
    def test_take_dependencies_from_other_testenv(
        self,
        newconfig,
        envlist,
        deps
    ):
        inisource = """
            [tox]
            envlist = {envlist}
            [testenv]
            deps={deps}
            [testenv:py27]
            deps=
                {{[testenv]deps}}
                fun
        """.format(
            envlist=','.join(envlist),
            deps='\n' + '\n'.join([' ' * 17 + d for d in deps])
        )
        conf = newconfig([], inisource).envconfigs['py27']
        packages = [dep.name for dep in conf.deps]
        assert packages == list(deps) + ['fun']

    def test_take_dependencies_from_other_section(self, newconfig):
        inisource = """
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
        inisource = """
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
        inisource = """
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

    def test_factors(self, newconfig):
        inisource = """
            [tox]
            envlist = a-x,b

            [testenv]
            deps=
                dep-all
                a: dep-a
                b: dep-b
                x: dep-x
        """
        conf = newconfig([], inisource)
        configs = conf.envconfigs
        assert [dep.name for dep in configs['a-x'].deps] == \
            ["dep-all", "dep-a", "dep-x"]
        assert [dep.name for dep in configs['b'].deps] == ["dep-all", "dep-b"]

    def test_factor_ops(self, newconfig):
        inisource = """
            [tox]
            envlist = {a,b}-{x,y}

            [testenv]
            deps=
                a,b: dep-a-or-b
                a-x: dep-a-and-x
                {a,b}-y: dep-ab-and-y
        """
        configs = newconfig([], inisource).envconfigs
        get_deps = lambda env: [dep.name for dep in configs[env].deps]
        assert get_deps("a-x") == ["dep-a-or-b", "dep-a-and-x"]
        assert get_deps("a-y") == ["dep-a-or-b", "dep-ab-and-y"]
        assert get_deps("b-x") == ["dep-a-or-b"]
        assert get_deps("b-y") == ["dep-a-or-b", "dep-ab-and-y"]

    def test_default_factors(self, newconfig):
        inisource = """
            [tox]
            envlist = py{26,27,33,34}-dep

            [testenv]
            deps=
                dep: dep
        """
        conf = newconfig([], inisource)
        configs = conf.envconfigs
        for name, config in configs.items():
            assert config.basepython == 'python%s.%s' % (name[2], name[3])

    @pytest.mark.issue188
    def test_factors_in_boolean(self, newconfig):
        inisource = """
            [tox]
            envlist = py{27,33}

            [testenv]
            recreate =
                py27: True
        """
        configs = newconfig([], inisource).envconfigs
        assert configs["py27"].recreate
        assert not configs["py33"].recreate

    @pytest.mark.issue190
    def test_factors_in_setenv(self, newconfig):
        inisource = """
            [tox]
            envlist = py27,py26

            [testenv]
            setenv =
                py27: X = 1
        """
        configs = newconfig([], inisource).envconfigs
        assert configs["py27"].setenv["X"] == "1"
        assert "X" not in configs["py26"].setenv

    @pytest.mark.issue191
    def test_factor_use_not_checked(self, newconfig):
        inisource = """
            [tox]
            envlist = py27-{a,b}

            [testenv]
            deps = b: test
        """
        configs = newconfig([], inisource).envconfigs
        assert set(configs.keys()) == set(['py27-a', 'py27-b'])

    @pytest.mark.issue198
    def test_factors_groups_touch(self, newconfig):
        inisource = """
            [tox]
            envlist = {a,b}{-x,}

            [testenv]
            deps=
                a,b,x,y: dep
        """
        configs = newconfig([], inisource).envconfigs
        assert set(configs.keys()) == set(['a', 'a-x', 'b', 'b-x'])

    def test_period_in_factor(self, newconfig):
        inisource = """
            [tox]
            envlist = py27-{django1.6,django1.7}

            [testenv]
            deps =
                django1.6: Django==1.6
                django1.7: Django==1.7
        """
        configs = newconfig([], inisource).envconfigs
        assert sorted(configs) == ["py27-django1.6", "py27-django1.7"]
        assert [d.name for d in configs["py27-django1.6"].deps] \
            == ["Django==1.6"]

    def test_ignore_outcome(self, newconfig):
        inisource = """
            [testenv]
            ignore_outcome=True
        """
        config = newconfig([], inisource).envconfigs
        assert config["python"].ignore_outcome is True


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

    def test_substitution_jenkins_default(self, tmpdir,
                                          monkeypatch, newconfig):
        monkeypatch.setenv("HUDSON_URL", "xyz")
        config = newconfig("""
            [testenv:py27]
            commands =
                {distshare}
        """)
        conf = config.envconfigs['py27']
        argv = conf.commands
        expect_path = config.toxworkdir.join("distshare")
        assert argv[0][0] == expect_path

    def test_substitution_jenkins_context(self, tmpdir, monkeypatch, newconfig):
        monkeypatch.setenv("HUDSON_URL", "xyz")
        monkeypatch.setenv("WORKSPACE", tmpdir)
        config = newconfig("""
            [tox:jenkins]
            distshare = {env:WORKSPACE}/hello
            [testenv:py27]
            commands =
                {distshare}
        """)
        conf = config.envconfigs['py27']
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
        # py.test.raises(tox.exception.ConfigError,
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
        envs = "py26,py27,py32,py33,py34,py35,py36,jython,pypy,pypy3"
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
            elif name.startswith("pypy"):
                assert env.basepython == name
            else:
                assert name.startswith("py")
                bp = "python%s.%s" % (name[2], name[3])
                assert env.basepython == bp

    def test_envlist_expansion(self, newconfig):
        inisource = """
            [tox]
            envlist = py{26,27},docs
        """
        config = newconfig([], inisource)
        assert config.envlist == ["py26", "py27", "docs"]

    def test_envlist_cross_product(self, newconfig):
        inisource = """
            [tox]
            envlist = py{26,27}-dep{1,2}
        """
        config = newconfig([], inisource)
        assert config.envlist == \
            ["py26-dep1", "py26-dep2", "py27-dep1", "py27-dep2"]

    def test_envlist_multiline(self, newconfig):
        inisource = """
            [tox]
            envlist =
              py27
              py34
        """
        config = newconfig([], inisource)
        assert config.envlist == \
            ["py27", "py34"]

    def test_minversion(self, tmpdir, newconfig, monkeypatch):
        inisource = """
            [tox]
            minversion = 10.0
        """
        with py.test.raises(tox.exception.MinVersionError):
            newconfig([], inisource)

    def test_skip_missing_interpreters_true(self, tmpdir, newconfig, monkeypatch):
        inisource = """
            [tox]
            skip_missing_interpreters = True
        """
        config = newconfig([], inisource)
        assert config.option.skip_missing_interpreters

    def test_skip_missing_interpreters_false(self, tmpdir, newconfig, monkeypatch):
        inisource = """
            [tox]
            skip_missing_interpreters = False
        """
        config = newconfig([], inisource)
        assert not config.option.skip_missing_interpreters

    def test_defaultenv_commandline(self, tmpdir, newconfig, monkeypatch):
        config = newconfig(["-epy27"], "")
        env = config.envconfigs['py27']
        assert env.basepython == "python2.7"
        assert not env.commands

    def test_defaultenv_partial_override(self, tmpdir, newconfig, monkeypatch):
        inisource = """
            [tox]
            envlist = py27
            [testenv:py27]
            commands= xyz
        """
        config = newconfig([], inisource)
        env = config.envconfigs['py27']
        assert env.basepython == "python2.7"
        assert env.commands == [['xyz']]


class TestHashseedOption:

    def _get_envconfigs(self, newconfig, args=None, tox_ini=None,
                        make_hashseed=None):
        if args is None:
            args = []
        if tox_ini is None:
            tox_ini = """
                [testenv]
            """
        if make_hashseed is None:
            make_hashseed = lambda: '123456789'
        original_make_hashseed = tox.config.make_hashseed
        tox.config.make_hashseed = make_hashseed
        try:
            config = newconfig(args, tox_ini)
        finally:
            tox.config.make_hashseed = original_make_hashseed
        return config.envconfigs

    def _get_envconfig(self, newconfig, args=None, tox_ini=None):
        envconfigs = self._get_envconfigs(newconfig, args=args,
                                          tox_ini=tox_ini)
        return envconfigs["python"]

    def _check_hashseed(self, envconfig, expected):
        assert envconfig.setenv['PYTHONHASHSEED'] == expected

    def _check_testenv(self, newconfig, expected, args=None, tox_ini=None):
        envconfig = self._get_envconfig(newconfig, args=args, tox_ini=tox_ini)
        self._check_hashseed(envconfig, expected)

    def test_default(self, tmpdir, newconfig):
        self._check_testenv(newconfig, '123456789')

    def test_passing_integer(self, tmpdir, newconfig):
        args = ['--hashseed', '1']
        self._check_testenv(newconfig, '1', args=args)

    def test_passing_string(self, tmpdir, newconfig):
        args = ['--hashseed', 'random']
        self._check_testenv(newconfig, 'random', args=args)

    def test_passing_empty_string(self, tmpdir, newconfig):
        args = ['--hashseed', '']
        self._check_testenv(newconfig, '', args=args)

    @pytest.mark.xfail(sys.version_info >= (3, 2),
                       reason="at least Debian python 3.2/3.3 have a bug: "
                              "http://bugs.python.org/issue11884")
    def test_passing_no_argument(self, tmpdir, newconfig):
        """Test that passing no arguments to --hashseed is not allowed."""
        args = ['--hashseed']
        try:
            self._check_testenv(newconfig, '', args=args)
        except SystemExit:
            e = sys.exc_info()[1]
            assert e.code == 2
            return
        assert False  # getting here means we failed the test.

    def test_setenv(self, tmpdir, newconfig):
        """Check that setenv takes precedence."""
        tox_ini = """
            [testenv]
            setenv =
                PYTHONHASHSEED = 2
        """
        self._check_testenv(newconfig, '2', tox_ini=tox_ini)
        args = ['--hashseed', '1']
        self._check_testenv(newconfig, '2', args=args, tox_ini=tox_ini)

    def test_noset(self, tmpdir, newconfig):
        args = ['--hashseed', 'noset']
        envconfig = self._get_envconfig(newconfig, args=args)
        assert not envconfig.setenv.definitions

    def test_noset_with_setenv(self, tmpdir, newconfig):
        tox_ini = """
            [testenv]
            setenv =
                PYTHONHASHSEED = 2
        """
        args = ['--hashseed', 'noset']
        self._check_testenv(newconfig, '2', args=args, tox_ini=tox_ini)

    def test_one_random_hashseed(self, tmpdir, newconfig):
        """Check that different testenvs use the same random seed."""
        tox_ini = """
            [testenv:hash1]
            [testenv:hash2]
        """
        next_seed = [1000]
        # This function is guaranteed to generate a different value each time.

        def make_hashseed():
            next_seed[0] += 1
            return str(next_seed[0])
        # Check that make_hashseed() works.
        assert make_hashseed() == '1001'
        envconfigs = self._get_envconfigs(newconfig, tox_ini=tox_ini,
                                          make_hashseed=make_hashseed)
        self._check_hashseed(envconfigs["hash1"], '1002')
        # Check that hash2's value is not '1003', for example.
        self._check_hashseed(envconfigs["hash2"], '1002')

    def test_setenv_in_one_testenv(self, tmpdir, newconfig):
        """Check using setenv in one of multiple testenvs."""
        tox_ini = """
            [testenv:hash1]
            setenv =
                PYTHONHASHSEED = 2
            [testenv:hash2]
        """
        envconfigs = self._get_envconfigs(newconfig, tox_ini=tox_ini)
        self._check_hashseed(envconfigs["hash1"], '2')
        self._check_hashseed(envconfigs["hash2"], '123456789')


class TestSetenv:
    def test_getdict_lazy(self, tmpdir, newconfig, monkeypatch):
        monkeypatch.setenv("X", "2")
        config = newconfig("""
            [testenv:X]
            key0 =
                key1 = {env:X}
                key2 = {env:Y:1}
        """)
        envconfig = config.envconfigs["X"]
        val = envconfig._reader.getdict_setenv("key0")
        assert val["key1"] == "2"
        assert val["key2"] == "1"

    def test_getdict_lazy_update(self, tmpdir, newconfig, monkeypatch):
        monkeypatch.setenv("X", "2")
        config = newconfig("""
            [testenv:X]
            key0 =
                key1 = {env:X}
                key2 = {env:Y:1}
        """)
        envconfig = config.envconfigs["X"]
        val = envconfig._reader.getdict_setenv("key0")
        d = {}
        d.update(val)
        assert d == {"key1": "2", "key2": "1"}

    def test_setenv_uses_os_environ(self, tmpdir, newconfig, monkeypatch):
        monkeypatch.setenv("X", "1")
        config = newconfig("""
            [testenv:env1]
            setenv =
                X = {env:X}
        """)
        assert config.envconfigs["env1"].setenv["X"] == "1"

    def test_setenv_default_os_environ(self, tmpdir, newconfig, monkeypatch):
        monkeypatch.delenv("X", raising=False)
        config = newconfig("""
            [testenv:env1]
            setenv =
                X = {env:X:2}
        """)
        assert config.envconfigs["env1"].setenv["X"] == "2"

    def test_setenv_uses_other_setenv(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv:env1]
            setenv =
                Y = 5
                X = {env:Y}
        """)
        assert config.envconfigs["env1"].setenv["X"] == "5"

    def test_setenv_recursive_direct(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv:env1]
            setenv =
                X = {env:X:3}
        """)
        assert config.envconfigs["env1"].setenv["X"] == "3"

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

    def test_setenv_with_envdir_and_basepython(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            setenv =
                VAL = {envdir}
            basepython = {env:VAL}
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert 'VAL' in envconfig.setenv
        assert envconfig.setenv['VAL'] == envconfig.envdir
        assert envconfig.basepython == envconfig.envdir

    def test_setenv_ordering_1(self, tmpdir, newconfig):
        config = newconfig("""
            [testenv]
            setenv=
                VAL={envdir}
            commands=echo {env:VAL}
        """)
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs['python']
        assert 'VAL' in envconfig.setenv
        assert envconfig.setenv['VAL'] == envconfig.envdir
        assert str(envconfig.envdir) in envconfig.commands[0]

    def test_setenv_cross_section_subst_issue294(self, monkeypatch, newconfig):
        """test that we can do cross-section substitution with setenv"""
        monkeypatch.delenv('TEST', raising=False)
        config = newconfig("""
            [section]
            x =
              NOT_TEST={env:TEST:defaultvalue}

            [testenv]
            setenv = {[section]x}
        """)
        envconfig = config.envconfigs["python"]
        assert envconfig.setenv["NOT_TEST"] == "defaultvalue"

    def test_setenv_cross_section_subst_twice(self, monkeypatch, newconfig):
        """test that we can do cross-section substitution with setenv"""
        monkeypatch.delenv('TEST', raising=False)
        config = newconfig("""
            [section]
            x = NOT_TEST={env:TEST:defaultvalue}
            [section1]
            y = {[section]x}

            [testenv]
            setenv = {[section1]y}
        """)
        envconfig = config.envconfigs["python"]
        assert envconfig.setenv["NOT_TEST"] == "defaultvalue"

    def test_setenv_cross_section_mixed(self, monkeypatch, newconfig):
        """test that we can do cross-section substitution with setenv"""
        monkeypatch.delenv('TEST', raising=False)
        config = newconfig("""
            [section]
            x = NOT_TEST={env:TEST:defaultvalue}

            [testenv]
            setenv = {[section]x}
                     y = 7
        """)
        envconfig = config.envconfigs["python"]
        assert envconfig.setenv["NOT_TEST"] == "defaultvalue"
        assert envconfig.setenv["y"] == "7"


class TestIndexServer:
    def test_indexserver(self, tmpdir, newconfig):
        config = newconfig("""
            [tox]
            indexserver =
                name1 = XYZ
                name2 = ABC
        """)
        assert config.indexserver['default'].url is None
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
        config = newconfig(['-i', 'qwe'], inisource)
        assert config.indexserver['default'].url == "qwe"
        assert config.indexserver['name1'].url == "whatever"
        config = newconfig(['-i', 'name1=abc', '-i', 'qwe2'], inisource)
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
        expected = "file://%s/.pip/downloads/simple" % config.homedir
        assert config.indexserver['default'].url == expected
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

    def test_override_workdir(self, tmpdir, cmd, initproj):
        baddir = "badworkdir-123"
        gooddir = "overridden-234"
        initproj("overrideworkdir-0.5", filedefs={
            'tox.ini': '''
            [tox]
            toxworkdir=%s
            ''' % baddir,
        })
        result = cmd.run("tox", "--workdir", gooddir, "--showconfig")
        assert not result.ret
        stdout = result.stdout.str()
        assert gooddir in stdout
        assert baddir not in stdout
        assert py.path.local(gooddir).check()
        assert not py.path.local(baddir).check()

    def test_showconfig_with_force_dep_version(self, cmd, initproj):
        initproj('force_dep_version', filedefs={
            'tox.ini': '''
            [tox]

            [testenv]
            deps=
                dep1==2.3
                dep2
            ''',
        })
        result = cmd.run("tox", "--showconfig")
        assert result.ret == 0
        result.stdout.fnmatch_lines([
            r'*deps*dep1==2.3, dep2*',
        ])
        # override dep1 specific version, and force version for dep2
        result = cmd.run("tox", "--showconfig", "--force-dep=dep1",
                         "--force-dep=dep2==5.0")
        assert result.ret == 0
        result.stdout.fnmatch_lines([
            r'*deps*dep1, dep2==5.0*',
        ])


@pytest.mark.parametrize("cmdline,envlist", [
    ("-e py26", ['py26']),
    ("-e py26,py33", ['py26', 'py33']),
    ("-e py26,py26", ['py26', 'py26']),
    ("-e py26,py33 -e py33,py27", ['py26', 'py33', 'py33', 'py27'])
])
def test_env_spec(cmdline, envlist):
    args = cmdline.split()
    config = parseconfig(args)
    assert config.envlist == envlist


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
        complex_case = (
            'word [] [literal] {something} {some:other thing} w{ord} w{or}d w{ord} '
            'w{o:rd} w{o:r}d {w:or}d w[]ord {posargs:{a key}}')
        p = CommandParser(complex_case)
        parsed = list(p.words())
        expected = [
            'word', ' ', '[]', ' ', '[literal]', ' ', '{something}', ' ', '{some:other thing}',
            ' ', 'w', '{ord}', ' ', 'w', '{or}', 'd', ' ', 'w', '{ord}', ' ', 'w', '{o:rd}', ' ',
            'w', '{o:r}', 'd', ' ', '{w:or}', 'd',
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
        assert parsed == [
            'nosetests', ' ', '-v', ' ', '-a', ' ', '!deferred', ' ',
            '--with-doctest', ' ', '[]'
        ]

    @pytest.mark.skipif("sys.platform != 'win32'")
    def test_commands_with_backslash(self, newconfig):
        config = newconfig([r"hello\world"], """
            [testenv:py26]
            commands = some {posargs}
        """)
        envconfig = config.envconfigs["py26"]
        assert envconfig.commands[0] == ["some", r"hello\world"]
