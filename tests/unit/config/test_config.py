import os
import re
import sys
from textwrap import dedent

import py
import pytest
from pluggy import PluginManager

import tox
from tox.config import (
    CommandParser,
    DepOption,
    PosargsOption,
    SectionReader,
    get_homedir,
    get_version_info,
    getcontextname,
    is_section_substitution,
    parseconfig,
)
from tox.config.parallel import ENV_VAR_KEY as PARALLEL_ENV_VAR_KEY


class TestVenvConfig:
    def test_config_parsing_minimal(self, tmpdir, newconfig):
        config = newconfig(
            [],
            """
            [testenv:py1]
        """,
        )
        assert len(config.envconfigs) == 1
        assert config.toxworkdir.realpath() == tmpdir.join(".tox").realpath()
        assert config.envconfigs["py1"].basepython == sys.executable
        assert config.envconfigs["py1"].deps == []
        assert config.envconfigs["py1"].platform == ".*"

    def test_config_parsing_multienv(self, tmpdir, newconfig):
        config = newconfig(
            [],
            """
            [tox]
            toxworkdir = {}
            indexserver =
                xyz = xyz_repo
            [testenv:py1]
            deps=hello
            [testenv:py2]
            deps=
                world1
                :xyz:http://hello/world
        """.format(
                tmpdir
            ),
        )
        assert config.toxworkdir == tmpdir
        assert len(config.envconfigs) == 2
        assert config.envconfigs["py1"].envdir == tmpdir.join("py1")
        dep = config.envconfigs["py1"].deps[0]
        assert dep.name == "hello"
        assert dep.indexserver is None
        assert config.envconfigs["py2"].envdir == tmpdir.join("py2")
        dep1, dep2 = config.envconfigs["py2"].deps
        assert dep1.name == "world1"
        assert dep2.name == "http://hello/world"
        assert dep2.indexserver.name == "xyz"
        assert dep2.indexserver.url == "xyz_repo"

    def test_envdir_set_manually(self, tmpdir, newconfig):
        config = newconfig(
            [],
            """
            [testenv:dev]
            envdir = dev
        """,
        )
        envconfig = config.envconfigs["dev"]
        assert envconfig.envdir == tmpdir.join("dev")

    def test_envdir_set_manually_with_substitutions(self, newconfig):
        config = newconfig(
            [],
            """
            [testenv:dev]
            envdir = {toxworkdir}/foobar
        """,
        )
        envconfig = config.envconfigs["dev"]
        assert envconfig.envdir == config.toxworkdir.join("foobar")

    def test_force_dep_version(self, initproj):
        """
        Make sure we can override dependencies configured in tox.ini when using the command line
        option --force-dep.
        """
        initproj(
            "example123-0.5",
            filedefs={
                "tox.ini": """
            [tox]

            [testenv]
            deps=
                dep1==1.0
                dep2>=2.0
                dep3
                dep4==4.0
            """
            },
        )
        config = parseconfig(
            ["--force-dep=dep1==1.5", "--force-dep=dep2==2.1", "--force-dep=dep3==3.0"]
        )
        assert config.option.force_dep == ["dep1==1.5", "dep2==2.1", "dep3==3.0"]
        expected_deps = ["dep1==1.5", "dep2==2.1", "dep3==3.0", "dep4==4.0"]
        assert expected_deps == [str(x) for x in config.envconfigs["python"].deps]

    def test_force_dep_with_url(self, initproj):
        initproj(
            "example123-0.5",
            filedefs={
                "tox.ini": """
            [tox]

            [testenv]
            deps=
                dep1==1.0
                https://pypi.org/xyz/pkg1.tar.gz
            """
            },
        )
        config = parseconfig(["--force-dep=dep1==1.5"])
        assert config.option.force_dep == ["dep1==1.5"]
        expected_deps = ["dep1==1.5", "https://pypi.org/xyz/pkg1.tar.gz"]
        assert [str(x) for x in config.envconfigs["python"].deps] == expected_deps

    def test_process_deps(self, newconfig):
        config = newconfig(
            [],
            """
            [testenv]
            deps =
                -r requirements.txt
                yapf>=0.25.0,<0.27  # pyup: < 0.27 # disable updates
                --index-url https://pypi.org/simple
                pywin32 >=1.0 ; sys_platform == '#my-magic-platform' # so what now
                -fhttps://pypi.org/packages
                --global-option=foo
                -v dep1
                --help dep2
        """,
        )  # note that those last two are invalid
        expected_deps = [
            "-rrequirements.txt",
            "yapf>=0.25.0,<0.27",
            "--index-url=https://pypi.org/simple",
            "pywin32 >=1.0 ; sys_platform == '#my-magic-platform'",
            "-fhttps://pypi.org/packages",
            "--global-option=foo",
            "-v dep1",
            "--help dep2",
        ]
        assert [str(x) for x in config.envconfigs["python"].deps] == expected_deps

    def test_is_same_dep(self):
        """
        Ensure correct parseini._is_same_dep is working with a few samples.
        """
        assert DepOption._is_same_dep("pkg_hello-world3==1.0", "pkg_hello-world3")
        assert DepOption._is_same_dep("pkg_hello-world3==1.0", "pkg_hello-world3>=2.0")
        assert DepOption._is_same_dep("pkg_hello-world3==1.0", "pkg_hello-world3>2.0")
        assert DepOption._is_same_dep("pkg_hello-world3==1.0", "pkg_hello-world3<2.0")
        assert DepOption._is_same_dep("pkg_hello-world3==1.0", "pkg_hello-world3<=2.0")
        assert not DepOption._is_same_dep("pkg_hello-world3==1.0", "otherpkg>=2.0")


class TestConfigPlatform:
    def test_config_parse_platform(self, newconfig):
        config = newconfig(
            [],
            """
            [testenv:py1]
            platform = linux2
        """,
        )
        assert len(config.envconfigs) == 1
        assert config.envconfigs["py1"].platform == "linux2"

    def test_config_parse_platform_rex(self, newconfig, mocksession, monkeypatch):
        config = newconfig(
            [],
            """
            [testenv:py1]
            platform = a123|b123
        """,
        )
        mocksession.config = config
        assert len(config.envconfigs) == 1
        venv = mocksession.getvenv("py1")
        assert not venv.matching_platform()
        monkeypatch.setattr(sys, "platform", "a123")
        assert venv.matching_platform()
        monkeypatch.setattr(sys, "platform", "b123")
        assert venv.matching_platform()
        monkeypatch.undo()
        assert not venv.matching_platform()

    @pytest.mark.parametrize("plat", ["win", "lin", "osx"])
    def test_config_parse_platform_with_factors(self, newconfig, plat):
        config = newconfig(
            [],
            """
            [tox]
            envlist = py27-{win, lin,osx }
            [testenv]
            platform =
                win: win32
                lin: linux2
        """,
        )
        assert len(config.envconfigs) == 3
        platform = config.envconfigs["py27-" + plat].platform
        expected = {"win": "win32", "lin": "linux2", "osx": ""}.get(plat)
        assert platform == expected


class TestConfigPackage:
    def test_defaults(self, tmpdir, newconfig):
        config = newconfig([], "")
        assert config.setupdir.realpath() == tmpdir.realpath()
        assert config.toxworkdir.realpath() == tmpdir.join(".tox").realpath()
        envconfig = config.envconfigs["python"]
        assert envconfig.args_are_paths
        assert not envconfig.recreate
        assert not envconfig.pip_pre

    def test_defaults_distshare(self, newconfig):
        config = newconfig([], "")
        assert config.distshare == config.homedir.join(".tox", "distshare")

    def test_defaults_changed_dir(self, tmpdir, newconfig):
        with tmpdir.mkdir("abc").as_cwd():
            config = newconfig([], "")
        assert config.setupdir.realpath() == tmpdir.realpath()
        assert config.toxworkdir.realpath() == tmpdir.join(".tox").realpath()

    def test_project_paths(self, tmpdir, newconfig):
        config = newconfig(
            """
            [tox]
            toxworkdir={}
        """.format(
                tmpdir
            )
        )
        assert config.toxworkdir == tmpdir


class TestParseconfig:
    def test_search_parents(self, tmpdir):
        b = tmpdir.mkdir("a").mkdir("b")
        toxinipath = tmpdir.ensure("tox.ini")
        with b.as_cwd():
            config = parseconfig([])
        assert config.toxinipath == toxinipath

    def test_explicit_config_path(self, tmpdir):
        """
        Test explicitly setting config path, both with and without the filename
        """
        path = tmpdir.mkdir("tox_tmp_directory")
        config_file_path = path.ensure("tox.ini")

        config = parseconfig(["-c", str(config_file_path)])
        assert config.toxinipath == config_file_path

        # Passing directory of the config file should also be possible
        # ('tox.ini' filename is assumed)
        config = parseconfig(["-c", str(path)])
        assert config.toxinipath == config_file_path

    @pytest.mark.skipif(sys.platform == "win32", reason="no symlinks on Windows")
    def test_workdir_gets_resolved(self, tmp_path, monkeypatch):
        """
        Test explicitly setting config path, both with and without the filename
        """
        real = tmp_path / "real"
        real.mkdir()
        symlink = tmp_path / "link"
        symlink.symlink_to(real)

        (tmp_path / "tox.ini").touch()
        monkeypatch.chdir(tmp_path)
        config = parseconfig(["--workdir", str(symlink)])
        assert config.toxworkdir == real


def test_get_homedir(monkeypatch):
    monkeypatch.setattr(py.path.local, "_gethomedir", classmethod(lambda x: {}[1]))
    assert not get_homedir()
    monkeypatch.setattr(py.path.local, "_gethomedir", classmethod(lambda x: 0 / 0))
    assert not get_homedir()
    monkeypatch.setattr(py.path.local, "_gethomedir", classmethod(lambda x: "123"))
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
        config = newconfig(
            """
            [section]
            key = whatever
            [testenv]
            commands =
                echo {[section]key}
            """
        )
        reader = SectionReader("testenv", config._cfg)
        x = reader.getargvlist("commands")
        assert x == [["echo", "whatever"]]

    def test_command_substitution_from_other_section_multiline(self, newconfig):
        """Ensure referenced multiline commands form from other section injected
        as multiple commands."""
        config = newconfig(
            """
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
            """
        )
        reader = SectionReader("testenv", config._cfg)
        x = reader.getargvlist("commands")
        expected_deps = [
            "cmd1 param11 param12".split(),
            "cmd2 param21 param22".split(),
            "cmd1 param11 param12".split(),
            "cmd2 param21 param22".split(),
            ["echo", "cmd", "1", "2", "3", "4", "cmd", "2"],
        ]
        assert x == expected_deps

    def test_command_substitution_from_other_section_posargs(self, newconfig):
        """Ensure subsitition from other section with posargs succeeds"""
        config = newconfig(
            """
            [section]
            key = thing {posargs} arg2
            [testenv]
            commands =
                {[section]key}
            """
        )
        reader = SectionReader("testenv", config._cfg)
        reader.addsubstitutions([r"argpos"])
        x = reader.getargvlist("commands")
        assert x == [["thing", "argpos", "arg2"]]

    def test_command_section_and_posargs_substitution(self, newconfig):
        """Ensure subsitition from other section with posargs succeeds"""
        config = newconfig(
            """
            [section]
            key = thing arg1
            [testenv]
            commands =
                {[section]key} {posargs} endarg
            """
        )
        reader = SectionReader("testenv", config._cfg)
        reader.addsubstitutions([r"argpos"])
        x = reader.getargvlist("commands")
        assert x == [["thing", "arg1", "argpos", "endarg"]]

    def test_command_env_substitution(self, newconfig):
        """Ensure referenced {env:key:default} values are substituted correctly."""
        config = newconfig(
            """
           [testenv:py27]
           setenv =
             TEST=testvalue
           commands =
             ls {env:TEST}
        """
        )
        envconfig = config.envconfigs["py27"]
        assert envconfig.commands == [["ls", "testvalue"]]
        assert envconfig.setenv["TEST"] == "testvalue"

    def test_command_env_substitution_global(self, newconfig):
        """Ensure referenced {env:key:default} values are substituted correctly."""
        config = newconfig(
            """
            [testenv]
            setenv = FOO = bar
            commands = echo {env:FOO}
        """
        )
        envconfig = config.envconfigs["python"]
        assert envconfig.commands == [["echo", "bar"]]

    def test_regression_issue595(self, newconfig):
        config = newconfig(
            """
            [tox]
            envlist = foo
            [testenv]
            setenv = VAR = x
            [testenv:bar]
            setenv = {[testenv]setenv}
            [testenv:baz]
            setenv =
        """
        )
        assert config.envconfigs["foo"].setenv["VAR"] == "x"
        assert config.envconfigs["bar"].setenv["VAR"] == "x"
        assert "VAR" not in config.envconfigs["baz"].setenv


class TestIniParser:
    def test_getstring_single(self, newconfig):
        config = newconfig(
            """
            [section]
            key=value
        """
        )
        reader = SectionReader("section", config._cfg)
        x = reader.getstring("key")
        assert x == "value"
        assert not reader.getstring("hello")
        x = reader.getstring("hello", "world")
        assert x == "world"

    def test_missing_substitution(self, newconfig):
        config = newconfig(
            """
            [mydefault]
            key2={xyz}
        """
        )
        reader = SectionReader("mydefault", config._cfg, fallbacksections=["mydefault"])
        assert reader is not None
        with pytest.raises(tox.exception.ConfigError):
            reader.getstring("key2")

    def test_getstring_fallback_sections(self, newconfig):
        config = newconfig(
            """
            [mydefault]
            key2=value2
            [section]
            key=value
        """
        )
        reader = SectionReader("section", config._cfg, fallbacksections=["mydefault"])
        x = reader.getstring("key2")
        assert x == "value2"
        x = reader.getstring("key3")
        assert not x
        x = reader.getstring("key3", "world")
        assert x == "world"

    def test_getstring_substitution(self, newconfig):
        config = newconfig(
            """
            [mydefault]
            key2={value2}
            [section]
            key={value}
        """
        )
        reader = SectionReader("section", config._cfg, fallbacksections=["mydefault"])
        reader.addsubstitutions(value="newvalue", value2="newvalue2")
        x = reader.getstring("key2")
        assert x == "newvalue2"
        x = reader.getstring("key3")
        assert not x
        x = reader.getstring("key3", "{value2}")
        assert x == "newvalue2"

    def test_getlist(self, newconfig):
        config = newconfig(
            """
            [section]
            key2=
                item1
                {item2}
        """
        )
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(item1="not", item2="grr")
        x = reader.getlist("key2")
        assert x == ["item1", "grr"]

    def test_getdict(self, newconfig):
        config = newconfig(
            """
            [section]
            key2=
                key1=item1
                key2={item2}
        """
        )
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(item1="not", item2="grr")
        x = reader.getdict("key2")
        assert "key1" in x
        assert "key2" in x
        assert x["key1"] == "item1"
        assert x["key2"] == "grr"

        x = reader.getdict("key3", {1: 2})
        assert x == {1: 2}

    def test_normal_env_sub_works(self, monkeypatch, newconfig):
        monkeypatch.setenv("VAR", "hello")
        config = newconfig("[section]\nkey={env:VAR}")
        assert SectionReader("section", config._cfg).getstring("key") == "hello"

    def test_missing_env_sub_raises_config_error_in_non_testenv(self, newconfig):
        config = newconfig("[section]\nkey={env:VAR}")
        with pytest.raises(tox.exception.ConfigError):
            SectionReader("section", config._cfg).getstring("key")

    def test_missing_env_sub_populates_missing_subs(self, newconfig):
        config = newconfig("[testenv:foo]\ncommands={env:VAR}")
        print(SectionReader("section", config._cfg).getstring("commands"))
        assert config.envconfigs["foo"].missing_subs == ["VAR"]

    def test_getstring_environment_substitution_with_default(self, monkeypatch, newconfig):
        monkeypatch.setenv("KEY1", "hello")
        config = newconfig(
            """
            [section]
            key1={env:KEY1:DEFAULT_VALUE}
            key2={env:KEY2:DEFAULT_VALUE}
            key3={env:KEY3:}
        """
        )
        reader = SectionReader("section", config._cfg)
        x = reader.getstring("key1")
        assert x == "hello"
        x = reader.getstring("key2")
        assert x == "DEFAULT_VALUE"
        x = reader.getstring("key3")
        assert x == ""

    def test_value_matches_section_substitution(self):
        assert is_section_substitution("{[setup]commands}")

    def test_value_doesn_match_section_substitution(self):
        assert is_section_substitution("{[ ]commands}") is None
        assert is_section_substitution("{[setup]}") is None
        assert is_section_substitution("{[setup] commands}") is None

    def test_getstring_other_section_substitution(self, newconfig):
        config = newconfig(
            """
            [section]
            key = rue
            [testenv]
            key = t{[section]key}
            """
        )
        reader = SectionReader("testenv", config._cfg)
        x = reader.getstring("key")
        assert x == "true"

    def test_argvlist(self, newconfig):
        config = newconfig(
            """
            [section]
            key2=
                cmd1 {item1} {item2}
                cmd2 {item2}
        """
        )
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(item1="with space", item2="grr")
        assert reader.getargvlist("key1") == []
        x = reader.getargvlist("key2")
        assert x == [["cmd1", "with", "space", "grr"], ["cmd2", "grr"]]

    def test_argvlist_windows_escaping(self, newconfig):
        config = newconfig(
            """
            [section]
            comm = pytest {posargs}
        """
        )
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions([r"hello\this"])
        argv = reader.getargv("comm")
        assert argv == ["pytest", "hello\\this"]

    def test_argvlist_multiline(self, newconfig):
        config = newconfig(
            """
            [section]
            key2=
                cmd1 {item1} \
                     {item2}
        """
        )
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(item1="with space", item2="grr")
        assert reader.getargvlist("key1") == []
        x = reader.getargvlist("key2")
        assert x == [["cmd1", "with", "space", "grr"]]

    def test_argvlist_quoting_in_command(self, newconfig):
        config = newconfig(
            """
            [section]
            key1=
                cmd1 'part one' \
                     'part two'
        """
        )
        reader = SectionReader("section", config._cfg)
        x = reader.getargvlist("key1")
        assert x == [["cmd1", "part one", "part two"]]

    def test_argvlist_comment_after_command(self, newconfig):
        config = newconfig(
            """
            [section]
            key1=
                cmd1 --flag  # run the flag on the command
        """
        )
        reader = SectionReader("section", config._cfg)
        x = reader.getargvlist("key1")
        assert x == [["cmd1", "--flag"]]

    def test_argvlist_command_contains_hash(self, newconfig):
        config = newconfig(
            """
            [section]
            key1=
                cmd1 --re  "use the # symbol for an arg"
        """
        )
        reader = SectionReader("section", config._cfg)
        x = reader.getargvlist("key1")
        assert x == [["cmd1", "--re", "use the # symbol for an arg"]]

    def test_argvlist_positional_substitution(self, newconfig):
        config = newconfig(
            """
            [section]
            key2=
                cmd1 []
                cmd2 {posargs:{item2} \
                     other}
        """
        )
        reader = SectionReader("section", config._cfg)
        posargs = ["hello", "world"]
        reader.addsubstitutions(posargs, item2="value2")
        assert reader.getargvlist("key1") == []
        argvlist = reader.getargvlist("key2")
        assert argvlist[0] == ["cmd1"] + posargs
        assert argvlist[1] == ["cmd2"] + posargs

        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions([], item2="value2")
        assert reader.getargvlist("key1") == []
        argvlist = reader.getargvlist("key2")
        assert argvlist[0] == ["cmd1"]
        assert argvlist[1] == ["cmd2", "value2", "other"]

    def test_argvlist_quoted_posargs(self, newconfig):
        config = newconfig(
            """
            [section]
            key2=
                cmd1 --foo-args='{posargs}'
                cmd2 -f '{posargs}'
                cmd3 -f {posargs}
        """
        )
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(["foo", "bar"])
        assert reader.getargvlist("key1") == []
        x = reader.getargvlist("key2")
        expected_deps = [
            ["cmd1", "--foo-args=foo bar"],
            ["cmd2", "-f", "foo bar"],
            ["cmd3", "-f", "foo", "bar"],
        ]
        assert x == expected_deps

    def test_argvlist_posargs_with_quotes(self, newconfig):
        config = newconfig(
            """
            [section]
            key2=
                cmd1 -f {posargs}
        """
        )
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(["foo", "'bar", "baz'"])
        assert reader.getargvlist("key1") == []
        x = reader.getargvlist("key2")
        assert x == [["cmd1", "-f", "foo", "bar baz"]]

    def test_positional_arguments_are_only_replaced_when_standing_alone(self, newconfig):
        config = newconfig(
            """
            [section]
            key=
                cmd0 []
                cmd1 -m '[abc]'
                cmd2 -m '\'something\'' []
                cmd3 something[]else
        """
        )
        reader = SectionReader("section", config._cfg)
        posargs = ["hello", "world"]
        reader.addsubstitutions(posargs)

        argvlist = reader.getargvlist("key")
        assert argvlist[0] == ["cmd0"] + posargs
        assert argvlist[1] == ["cmd1", "-m", "[abc]"]
        assert argvlist[2] == ["cmd2", "-m", "something"] + posargs
        assert argvlist[3] == ["cmd3", "something[]else"]

    def test_posargs_are_added_escaped_issue310(self, newconfig):
        config = newconfig(
            """
            [section]
            key= cmd0 {posargs}
        """
        )
        reader = SectionReader("section", config._cfg)
        posargs = ["hello world", "--x==y z", "--format=%(code)s: %(text)s"]
        reader.addsubstitutions(posargs)
        argvlist = reader.getargvlist("key")
        assert argvlist[0] == ["cmd0"] + posargs

    def test_substitution_with_multiple_words(self, newconfig):
        inisource = """
            [section]
            key = pytest -n5 --junitxml={envlogdir}/junit-{envname}.xml []
            """
        config = newconfig(inisource)
        reader = SectionReader("section", config._cfg)
        posargs = ["hello", "world"]
        reader.addsubstitutions(posargs, envlogdir="ENV_LOG_DIR", envname="ENV_NAME")

        expected = ["pytest", "-n5", "--junitxml=ENV_LOG_DIR/junit-ENV_NAME.xml", "hello", "world"]
        assert reader.getargvlist("key")[0] == expected

    def test_getargv(self, newconfig):
        config = newconfig(
            """
            [section]
            key=some command "with quoting"
        """
        )
        reader = SectionReader("section", config._cfg)
        expected = ["some", "command", "with quoting"]
        assert reader.getargv("key") == expected

    def test_getpath(self, tmpdir, newconfig):
        config = newconfig(
            """
            [section]
            path1={HELLO}
        """
        )
        reader = SectionReader("section", config._cfg)
        reader.addsubstitutions(toxinidir=tmpdir, HELLO="mypath")
        x = reader.getpath("path1", tmpdir)
        assert x == tmpdir.join("mypath")

    def test_getbool(self, newconfig):
        config = newconfig(
            """
            [section]
            key1=True
            key2=False
            key1a=true
            key2a=falsE
            key5=yes
        """
        )
        reader = SectionReader("section", config._cfg)
        assert reader.getbool("key1") is True
        assert reader.getbool("key1a") is True
        assert reader.getbool("key2") is False
        assert reader.getbool("key2a") is False
        with pytest.raises(KeyError):
            reader.getbool("key3")
        with pytest.raises(tox.exception.ConfigError) as excinfo:
            reader.getbool("key5")
        msg, = excinfo.value.args
        assert msg == "key5: boolean value 'yes' needs to be 'True' or 'False'"


class TestIniParserPrefix:
    def test_basic_section_access(self, newconfig):
        config = newconfig(
            """
            [p:section]
            key=value
        """
        )
        reader = SectionReader("section", config._cfg, prefix="p")
        x = reader.getstring("key")
        assert x == "value"
        assert not reader.getstring("hello")
        x = reader.getstring("hello", "world")
        assert x == "world"

    def test_fallback_sections(self, newconfig):
        config = newconfig(
            """
            [p:mydefault]
            key2=value2
            [p:section]
            key=value
        """
        )
        reader = SectionReader(
            "section", config._cfg, prefix="p", fallbacksections=["p:mydefault"]
        )
        x = reader.getstring("key2")
        assert x == "value2"
        x = reader.getstring("key3")
        assert not x
        x = reader.getstring("key3", "world")
        assert x == "world"

    def test_value_matches_prefixed_section_substitution(self):
        assert is_section_substitution("{[p:setup]commands}")

    def test_value_doesn_match_prefixed_section_substitution(self):
        assert is_section_substitution("{[p: ]commands}") is None
        assert is_section_substitution("{[p:setup]}") is None
        assert is_section_substitution("{[p:setup] commands}") is None

    def test_other_section_substitution(self, newconfig):
        config = newconfig(
            """
            [p:section]
            key = rue
            [p:testenv]
            key = t{[p:section]key}
            """
        )
        reader = SectionReader("testenv", config._cfg, prefix="p")
        x = reader.getstring("key")
        assert x == "true"


class TestConfigTestEnv:
    def test_commentchars_issue33(self, newconfig):
        config = newconfig(
            """
            [testenv] # hello
            deps = http://abc#123
            commands=
                python -c "x ; y"
        """
        )
        envconfig = config.envconfigs["python"]
        assert envconfig.deps[0].name == "http://abc#123"
        assert envconfig.commands[0] == ["python", "-c", "x ; y"]

    def test_defaults(self, newconfig):
        config = newconfig(
            """
            [testenv]
            commands=
                xyz --abc
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        assert envconfig.commands == [["xyz", "--abc"]]
        assert envconfig.changedir == config.setupdir
        assert envconfig.sitepackages is False
        assert envconfig.usedevelop is False
        assert envconfig.ignore_errors is False
        assert envconfig.envlogdir == envconfig.envdir.join("log")
        assert set(envconfig.setenv.definitions.keys()) == {
            "PYTHONHASHSEED",
            "TOX_ENV_NAME",
            "TOX_ENV_DIR",
        }
        hashseed = envconfig.setenv["PYTHONHASHSEED"]
        assert isinstance(hashseed, str)
        # The following line checks that hashseed parses to an integer.
        int_hashseed = int(hashseed)
        # hashseed is random by default, so we can't assert a specific value.
        assert int_hashseed > 0
        assert envconfig.ignore_outcome is False

    def test_sitepackages_switch(self, newconfig):
        config = newconfig(["--sitepackages"], "")
        envconfig = config.envconfigs["python"]
        assert envconfig.sitepackages is True

    def test_installpkg_tops_develop(self, newconfig):
        config = newconfig(
            ["--installpkg=abc"],
            """
            [testenv]
            usedevelop = True
        """,
        )
        assert not config.envconfigs["python"].usedevelop

    def test_specific_command_overrides(self, newconfig):
        config = newconfig(
            """
            [testenv]
            commands=xyz
            [testenv:py]
            commands=abc
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["py"]
        assert envconfig.commands == [["abc"]]

    def test_whitelist_externals(self, newconfig):
        config = newconfig(
            """
            [testenv]
            whitelist_externals = xyz
            commands=xyz
            [testenv:x]

            [testenv:py]
            whitelist_externals = xyz2
            commands=abc
        """
        )
        assert len(config.envconfigs) == 2
        envconfig = config.envconfigs["py"]
        assert envconfig.commands == [["abc"]]
        assert envconfig.whitelist_externals == ["xyz2"]
        envconfig = config.envconfigs["x"]
        assert envconfig.whitelist_externals == ["xyz"]

    def test_changedir(self, newconfig):
        config = newconfig(
            """
            [testenv]
            changedir=xyz
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        assert envconfig.changedir.basename == "xyz"
        assert envconfig.changedir == config.toxinidir.join("xyz")

    def test_ignore_errors(self, newconfig):
        config = newconfig(
            """
            [testenv]
            ignore_errors=True
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        assert envconfig.ignore_errors is True

    def test_envbindir(self, newconfig):
        config = newconfig(
            """
            [testenv]
            basepython=python
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        assert envconfig.envpython == envconfig.envbindir.join("python")

    @pytest.mark.parametrize("bp", ["jython", "pypy", "pypy3"])
    def test_envbindir_jython(self, newconfig, bp):
        config = newconfig(
            """
            [testenv]
            basepython={}
        """.format(
                bp
            )
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        # on win32 and linux virtualenv uses "bin" for pypy/jython
        assert envconfig.envbindir.basename == "bin"
        if bp == "jython":
            assert envconfig.envpython == envconfig.envbindir.join(bp)

    @pytest.mark.parametrize("plat", ["win32", "linux2"])
    def test_passenv_as_multiline_list(self, newconfig, monkeypatch, plat):
        monkeypatch.setattr(tox.INFO, "IS_WIN", plat == "win32")
        monkeypatch.setenv("A123A", "a")
        monkeypatch.setenv("A123B", "b")
        monkeypatch.setenv("BX23", "0")
        config = newconfig(
            """
            [testenv]
            passenv =
                      A123*
                      # isolated comment
                      B?23
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        if plat == "win32":
            assert "PATHEXT" in envconfig.passenv
            assert "SYSTEMDRIVE" in envconfig.passenv
            assert "SYSTEMROOT" in envconfig.passenv
            assert "COMSPEC" in envconfig.passenv
            assert "TEMP" in envconfig.passenv
            assert "TMP" in envconfig.passenv
            assert "NUMBER_OF_PROCESSORS" in envconfig.passenv
            assert "PROCESSOR_ARCHITECTURE" in envconfig.passenv
            assert "USERPROFILE" in envconfig.passenv
            assert "MSYSTEM" in envconfig.passenv
        else:
            assert "TMPDIR" in envconfig.passenv
        assert "PATH" in envconfig.passenv
        assert "PIP_INDEX_URL" in envconfig.passenv
        assert "LANG" in envconfig.passenv
        assert "LANGUAGE" in envconfig.passenv
        assert "LD_LIBRARY_PATH" in envconfig.passenv
        assert PARALLEL_ENV_VAR_KEY in envconfig.passenv
        assert "A123A" in envconfig.passenv
        assert "A123B" in envconfig.passenv

    @pytest.mark.parametrize("plat", ["win32", "linux2"])
    def test_passenv_as_space_separated_list(self, newconfig, monkeypatch, plat):
        monkeypatch.setattr(tox.INFO, "IS_WIN", plat == "win32")
        monkeypatch.setenv("A123A", "a")
        monkeypatch.setenv("A123B", "b")
        monkeypatch.setenv("BX23", "0")
        config = newconfig(
            """
            [testenv]
            passenv =
                      # comment
                      A123*  B?23
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
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
        assert "LANGUAGE" in envconfig.passenv
        assert "A123A" in envconfig.passenv
        assert "A123B" in envconfig.passenv

    def test_passenv_with_factor(self, newconfig, monkeypatch):
        monkeypatch.setenv("A123A", "a")
        monkeypatch.setenv("A123B", "b")
        monkeypatch.setenv("A123C", "c")
        monkeypatch.setenv("A123D", "d")
        monkeypatch.setenv("BX23", "0")
        monkeypatch.setenv("CCA43", "3")
        monkeypatch.setenv("CB21", "4")
        config = newconfig(
            """
            [tox]
            envlist = {x1,x2}
            [testenv]
            passenv =
                x1: A123A CC*
                x1: CB21
                # passed to both environments
                A123C
                x2: A123B A123D
        """
        )
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

    def test_passenv_from_global_env(self, newconfig, monkeypatch):
        monkeypatch.setenv("A1", "a1")
        monkeypatch.setenv("A2", "a2")
        monkeypatch.setenv("TOX_TESTENV_PASSENV", "A1")
        config = newconfig(
            """
            [testenv]
            passenv = A2
        """
        )
        env = config.envconfigs["python"]
        assert "A1" in env.passenv
        assert "A2" in env.passenv

    def test_passenv_glob_from_global_env(self, newconfig, monkeypatch):
        monkeypatch.setenv("A1", "a1")
        monkeypatch.setenv("A2", "a2")
        monkeypatch.setenv("TOX_TESTENV_PASSENV", "A*")
        config = newconfig(
            """
            [testenv]
        """
        )
        env = config.envconfigs["python"]
        assert "A1" in env.passenv
        assert "A2" in env.passenv

    def test_changedir_override(self, newconfig):
        config = newconfig(
            """
            [testenv]
            changedir=xyz
            [testenv:python]
            changedir=abc
            basepython=python3.6
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        assert envconfig.changedir.basename == "abc"
        assert envconfig.changedir == config.setupdir.join("abc")

    def test_install_command_setting(self, newconfig):
        config = newconfig(
            """
            [testenv]
            install_command=some_install {packages}
        """
        )
        envconfig = config.envconfigs["python"]
        assert envconfig.install_command == ["some_install", "{packages}"]

    def test_install_command_must_contain_packages(self, newconfig):
        with pytest.raises(tox.exception.ConfigError):
            newconfig("[testenv]\ninstall_command=pip install")

    def test_install_command_substitutions(self, newconfig):
        config = newconfig(
            """
            [testenv]
            install_command=some_install --arg={toxinidir}/foo \
                {envname} {opts} {packages}
        """
        )
        envconfig = config.envconfigs["python"]
        expected_deps = [
            "some_install",
            "--arg={}/foo".format(config.toxinidir),
            "python",
            "{opts}",
            "{packages}",
        ]
        assert envconfig.install_command == expected_deps

    def test_pip_pre(self, newconfig):
        config = newconfig(
            """
            [testenv]
            pip_pre=true
        """
        )
        envconfig = config.envconfigs["python"]
        assert envconfig.pip_pre

    def test_pip_pre_cmdline_override(self, newconfig):
        config = newconfig(
            ["--pre"],
            """
            [testenv]
            pip_pre=false
        """,
        )
        envconfig = config.envconfigs["python"]
        assert envconfig.pip_pre

    def test_simple(self, newconfig):
        config = newconfig(
            """
            [testenv:py36]
            basepython=python3.6
            [testenv:py27]
            basepython=python2.7
        """
        )
        assert len(config.envconfigs) == 2
        assert "py36" in config.envconfigs
        assert "py27" in config.envconfigs

    def test_substitution_error(self, newconfig):
        with pytest.raises(tox.exception.ConfigError):
            newconfig("[testenv:py27]\nbasepython={xyz}")

    def test_substitution_defaults(self, newconfig):
        config = newconfig(
            """
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
        """
        )
        conf = config.envconfigs["py27"]
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

    def test_substitution_notfound_issue246(self, newconfig):
        config = newconfig(
            """
            [testenv:py27]
            setenv =
                FOO={envbindir}
                BAR={envsitepackagesdir}
        """
        )
        conf = config.envconfigs["py27"]
        env = conf.setenv
        assert "FOO" in env
        assert "BAR" in env

    def test_substitution_notfound_issue515(self, newconfig):
        config = newconfig(
            """
            [tox]
            envlist = standard-greeting

            [testenv:standard-greeting]
            commands =
                python -c 'print("Hello, world!")'

            [testenv:custom-greeting]
            passenv =
                NAME
            commands =
                python -c 'print("Hello, {env:NAME}!")'
        """
        )
        conf = config.envconfigs["standard-greeting"]
        assert conf.commands == [["python", "-c", 'print("Hello, world!")']]

    def test_substitution_nested_env_defaults(self, newconfig, monkeypatch):
        monkeypatch.setenv("IGNORE_STATIC_DEFAULT", "env")
        monkeypatch.setenv("IGNORE_DYNAMIC_DEFAULT", "env")
        config = newconfig(
            """
            [testenv:py27]
            passenv =
                IGNORE_STATIC_DEFAULT
                USE_STATIC_DEFAULT
                IGNORE_DYNAMIC_DEFAULT
                USE_DYNAMIC_DEFAULT
            setenv =
                OTHER_VAR=other
                IGNORE_STATIC_DEFAULT={env:IGNORE_STATIC_DEFAULT:default}
                USE_STATIC_DEFAULT={env:USE_STATIC_DEFAULT:default}
                IGNORE_DYNAMIC_DEFAULT={env:IGNORE_DYNAMIC_DEFAULT:{env:OTHER_VAR}+default}
                USE_DYNAMIC_DEFAULT={env:USE_DYNAMIC_DEFAULT:{env:OTHER_VAR}+default}
                IGNORE_OTHER_DEFAULT={env:OTHER_VAR:{env:OTHER_VAR}+default}
                USE_OTHER_DEFAULT={env:NON_EXISTENT_VAR:{env:OTHER_VAR}+default}
        """
        )
        conf = config.envconfigs["py27"]
        env = conf.setenv
        assert env["IGNORE_STATIC_DEFAULT"] == "env"
        assert env["USE_STATIC_DEFAULT"] == "default"
        assert env["IGNORE_OTHER_DEFAULT"] == "other"
        assert env["USE_OTHER_DEFAULT"] == "other+default"
        assert env["IGNORE_DYNAMIC_DEFAULT"] == "env"
        assert env["USE_DYNAMIC_DEFAULT"] == "other+default"

    def test_substitution_positional(self, newconfig):
        inisource = """
            [testenv:py27]
            commands =
                cmd1 [hello] \
                     world
                cmd1 {posargs:hello} \
                     world
        """
        conf = newconfig([], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["cmd1", "[hello]", "world"]
        assert argv[1] == ["cmd1", "hello", "world"]
        conf = newconfig(["brave", "new"], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["cmd1", "[hello]", "world"]
        assert argv[1] == ["cmd1", "brave", "new", "world"]

    def test_substitution_noargs_issue240(self, newconfig):
        inisource = """
            [testenv]
            commands = echo {posargs:foo}
        """
        conf = newconfig([""], inisource).envconfigs["python"]
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
        conf = newconfig([], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["echo", "bah"]

    def test_posargs_backslashed_or_quoted(self, newconfig):
        inisource = r"""
            [testenv:py27]
            commands =
                echo "\{posargs\}" = {posargs}
                echo "posargs = " "{posargs}"
        """
        conf = newconfig([], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["echo", "{posargs}", "="]
        assert argv[1] == ["echo", "posargs = ", ""]

        conf = newconfig(["dog", "cat"], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["echo", "{posargs}", "=", "dog", "cat"]
        assert argv[1] == ["echo", "posargs = ", "dog cat"]

    def test_rewrite_posargs(self, tmpdir, newconfig):
        inisource = """
            [testenv:py27]
            args_are_paths = True
            changedir = tests
            commands = cmd1 {posargs:hello}
        """
        conf = newconfig([], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello"]

        conf = newconfig(["tests/hello"], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["cmd1", "tests/hello"]

        tmpdir.ensure("tests", "hello")
        conf = newconfig(["tests/hello"], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello"]

    def test_rewrite_simple_posargs(self, tmpdir, newconfig):
        inisource = """
            [testenv:py27]
            args_are_paths = True
            changedir = tests
            commands = cmd1 {posargs}
        """
        conf = newconfig([], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["cmd1"]

        conf = newconfig(["tests/hello"], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["cmd1", "tests/hello"]

        tmpdir.ensure("tests", "hello")
        conf = newconfig(["tests/hello"], inisource).envconfigs["py27"]
        argv = conf.commands
        assert argv[0] == ["cmd1", "hello"]

    @pytest.mark.parametrize(
        "envlist, deps",
        [
            (["py27"], ("pytest", "pytest-cov")),
            (["py27", "py34"], ("pytest", "py{27,34}: pytest-cov")),
        ],
    )
    def test_take_dependencies_from_other_testenv(self, newconfig, envlist, deps):
        inisource = """
            [tox]
            envlist = {envlist}
            [testenv]
            deps={deps}
            [testenv:py27]
            deps=
                {{[testenv]deps}}
                fun
                frob{{env:ENV_VAR:>1.0,<2.0}}
        """.format(
            envlist=",".join(envlist), deps="\n" + "\n".join([" " * 17 + d for d in deps])
        )
        conf = newconfig([], inisource).envconfigs["py27"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["pytest", "pytest-cov", "fun", "frob>1.0,<2.0"]

    # https://github.com/tox-dev/tox/issues/706
    @pytest.mark.parametrize("envlist", [["py27", "coverage", "other"]])
    def test_regression_test_issue_706(self, newconfig, envlist):
        inisource = """
            [tox]
            envlist = {envlist}
            [testenv]
            deps=
              flake8
              coverage: coverage
            [testenv:py27]
            deps=
                {{[testenv]deps}}
                fun
        """.format(
            envlist=",".join(envlist)
        )
        conf = newconfig([], inisource).envconfigs["coverage"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["flake8", "coverage"]

        conf = newconfig([], inisource).envconfigs["other"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["flake8"]

        conf = newconfig([], inisource).envconfigs["py27"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["flake8", "fun"]

    def test_factor_expansion(self, newconfig):
        inisource = """
            [tox]
            envlist = {py27, py37}-cover
            [testenv]
            deps=
              {py27}: foo
              {py37}: bar
        """
        conf = newconfig([], inisource).envconfigs["py27-cover"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["foo"]

        conf = newconfig([], inisource).envconfigs["py37-cover"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["bar"]

    # Regression test https://github.com/tox-dev/tox/issues/899
    def test_factors_support_curly_braces(self, newconfig):
        inisource = """
            [tox]
            envlist =
                style
                sdist
                bdist_wheel
                {py27,py34,py35,py36,pypy,pypy3}-cover
                {py27,py34,py35,py36,pypy,pypy3}-nocov

            [testenv]
            deps =
                cover: coverage
                cover: codecov
                {py27}: unittest2
                {py27}: mysql-python
                {py27,py36}: mmtf-python
                {py27,py35}: reportlab
                {py27,py34,py35,py36}: psycopg2-binary
                {py27,py34,py35,py35}: mysql-connector-python-rf
                {py27,py35,pypy}: rdflib
                {pypy,pypy3}: numpy==1.12.1
                {py27,py34,py36}: numpy
                {py36}: scipy
                {py27}: networkx
                {py36}: matplotlib
        """
        conf = newconfig([], inisource).envconfigs["style"]
        packages = [dep.name for dep in conf.deps]
        assert packages == []

        conf = newconfig([], inisource).envconfigs["py27-cover"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [
            "coverage",
            "codecov",
            "unittest2",
            "mysql-python",
            "mmtf-python",
            "reportlab",
            "psycopg2-binary",
            "mysql-connector-python-rf",
            "rdflib",
            "numpy",
            "networkx",
        ]

        conf = newconfig([], inisource).envconfigs["py34-cover"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [
            "coverage",
            "codecov",
            "psycopg2-binary",
            "mysql-connector-python-rf",
            "numpy",
        ]

        conf = newconfig([], inisource).envconfigs["py35-cover"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [
            "coverage",
            "codecov",
            "reportlab",
            "psycopg2-binary",
            "mysql-connector-python-rf",
            "rdflib",
        ]

        conf = newconfig([], inisource).envconfigs["py36-cover"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [
            "coverage",
            "codecov",
            "mmtf-python",
            "psycopg2-binary",
            "numpy",
            "scipy",
            "matplotlib",
        ]

        conf = newconfig([], inisource).envconfigs["pypy-cover"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["coverage", "codecov", "rdflib", "numpy==1.12.1"]

        conf = newconfig([], inisource).envconfigs["pypy3-cover"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["coverage", "codecov", "numpy==1.12.1"]

        conf = newconfig([], inisource).envconfigs["py27-nocov"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [
            "unittest2",
            "mysql-python",
            "mmtf-python",
            "reportlab",
            "psycopg2-binary",
            "mysql-connector-python-rf",
            "rdflib",
            "numpy",
            "networkx",
        ]

        conf = newconfig([], inisource).envconfigs["py34-nocov"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["psycopg2-binary", "mysql-connector-python-rf", "numpy"]

        conf = newconfig([], inisource).envconfigs["py35-nocov"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["reportlab", "psycopg2-binary", "mysql-connector-python-rf", "rdflib"]

        conf = newconfig([], inisource).envconfigs["py36-nocov"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["mmtf-python", "psycopg2-binary", "numpy", "scipy", "matplotlib"]

        conf = newconfig([], inisource).envconfigs["pypy-nocov"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["rdflib", "numpy==1.12.1"]

        conf = newconfig([], inisource).envconfigs["pypy3-cover"]
        packages = [dep.name for dep in conf.deps]
        assert packages == ["coverage", "codecov", "numpy==1.12.1"]

    # Regression test https://github.com/tox-dev/tox/issues/906
    def test_do_not_substitute_more_than_needed(self, newconfig):
        inisource = """
            [tox]
            envlist =
                django_master-py{36,35}
                django20-py{36,35,34,py3}
                django111-py{36,35,34,27,py}
                django18-py{35,34,27,py}
                lint
                docs

            [testenv]
            deps =
                .[test]
                django18: {[django]1.8.x}
                django111: {[django]1.11.x}
                django20: {[django]2.0.x}
                django_master: {[django]master}

            [django]
            1.8.x  =
                   Django>=1.8.0,<1.9.0
                   django-reversion==1.10.0
                   djangorestframework>=3.3.3,<3.7.0
            1.11.x  =
                   Django>=1.11.0,<2.0.0
                   django-reversion>=2.0.8
                   djangorestframework>=3.6.2
            2.0.x  =
                   Django>=2.0,<2.1
                   django-reversion>=2.0.8
                   djangorestframework>=3.7.3
            master =
                   https://github.com/django/django/tarball/master
                   django-reversion>=2.0.8
                   djangorestframework>=3.6.2
        """
        conf = newconfig([], inisource).envconfigs["django_master-py36"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [
            ".[test]",
            "https://github.com/django/django/tarball/master",
            "django-reversion>=2.0.8",
            "djangorestframework>=3.6.2",
        ]

        conf = newconfig([], inisource).envconfigs["django20-pypy3"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [
            ".[test]",
            "Django>=2.0,<2.1",
            "django-reversion>=2.0.8",
            "djangorestframework>=3.7.3",
        ]

        conf = newconfig([], inisource).envconfigs["django111-py34"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [
            ".[test]",
            "Django>=1.11.0,<2.0.0",
            "django-reversion>=2.0.8",
            "djangorestframework>=3.6.2",
        ]

        conf = newconfig([], inisource).envconfigs["django18-py27"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [
            ".[test]",
            "Django>=1.8.0,<1.9.0",
            "django-reversion==1.10.0",
            "djangorestframework>=3.3.3,<3.7.0",
        ]

        conf = newconfig([], inisource).envconfigs["lint"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [".[test]"]

        conf = newconfig([], inisource).envconfigs["docs"]
        packages = [dep.name for dep in conf.deps]
        assert packages == [".[test]"]

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
        env = conf.envconfigs["python"]
        packages = [dep.name for dep in env.deps]
        assert packages == ["pytest", "pytest-cov", "mock", "fun"]

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
        env = conf.envconfigs["python"]
        packages = [dep.name for dep in env.deps]
        assert packages == ["pytest", "pytest-cov", "mock", "fun"]

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
        with pytest.raises(tox.exception.ConfigError):
            newconfig([], inisource)

    def test_single_value_from_other_secton(self, newconfig, tmpdir):
        inisource = """
            [common]
            changedir = testing
            [testenv]
            changedir = {[common]changedir}
        """
        conf = newconfig([], inisource).envconfigs["python"]
        assert conf.changedir.basename == "testing"
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
                !a: dep-!a
                !b: dep-!b
                !x: dep-!x
        """
        conf = newconfig([], inisource)
        configs = conf.envconfigs
        expected = ["dep-all", "dep-a", "dep-x", "dep-!b"]
        assert [dep.name for dep in configs["a-x"].deps] == expected
        expected = ["dep-all", "dep-b", "dep-!a", "dep-!x"]
        assert [dep.name for dep in configs["b"].deps] == expected
        expected = ["dep-all", "dep-a", "dep-x", "dep-!b"]
        assert [dep.name for dep in configs["a-x"].deps] == expected
        expected = ["dep-all", "dep-b", "dep-!a", "dep-!x"]
        assert [dep.name for dep in configs["b"].deps] == expected

    def test_factor_ops(self, newconfig):
        inisource = """
            [tox]
            envlist = {a,b}-{x,y}

            [testenv]
            deps=
                a,b: dep-a-or-b
                a-x: dep-a-and-x
                {a,b}-y: dep-ab-and-y
                a-!x: dep-a-and-!x
                a,!x: dep-a-or-!x
                !a-!x: dep-!a-and-!x
                !a,!x: dep-!a-or-!x
                !a-!b: dep-!a-and-!b
                !a-!b-!x-!y: dep-!a-and-!b-and-!x-and-!y
        """
        configs = newconfig([], inisource).envconfigs

        def get_deps(env):
            return [dep.name for dep in configs[env].deps]

        assert get_deps("a-x") == ["dep-a-or-b", "dep-a-and-x", "dep-a-or-!x"]
        expected = ["dep-a-or-b", "dep-ab-and-y", "dep-a-and-!x", "dep-a-or-!x", "dep-!a-or-!x"]
        assert get_deps("a-y") == expected
        assert get_deps("b-x") == ["dep-a-or-b", "dep-!a-or-!x"]
        expected = ["dep-a-or-b", "dep-ab-and-y", "dep-a-or-!x", "dep-!a-and-!x", "dep-!a-or-!x"]
        assert get_deps("b-y") == expected

    def test_envconfigs_based_on_factors(self, newconfig):
        inisource = """
            [testenv]
            some-setting=
                a: something
                b,c: something
                d-e: something
                !f: something
                !g,!h: something
                !i-!j: something

            [unknown-section]
            some-setting=
                eggs: something
        """
        config = newconfig(["-e spam"], inisource)
        assert not config.envconfigs
        assert config.envlist == ["spam"]
        config = newconfig(["-e eggs"], inisource)
        assert not config.envconfigs
        assert config.envlist == ["eggs"]
        config = newconfig(["-e py3-spam"], inisource)
        assert not config.envconfigs
        assert config.envlist == ["py3-spam"]
        for x in "abcdefghij":
            env = "py3-{}".format(x)
            config = newconfig(["-e {}".format(env)], inisource)
            assert sorted(config.envconfigs) == [env]
            assert config.envlist == [env]

    def test_default_factors(self, newconfig):
        inisource = """
            [tox]
            envlist = py{27,34,36}-dep

            [testenv]
            deps=
                dep: dep
        """
        conf = newconfig([], inisource)
        configs = conf.envconfigs
        for name, config in configs.items():
            assert config.basepython == "python{}.{}".format(name[2], name[3])

    def test_default_factors_conflict(self, newconfig, capsys):
        with pytest.warns(UserWarning, match=r"conflicting basepython .*"):
            config = newconfig(
                """
                [testenv]
                basepython=python3
                [testenv:py27]
                commands = python --version
            """
            )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["py27"]
        assert envconfig.basepython == "python3"

    def test_default_factors_conflict_lying_name(
        self, newconfig, capsys, tmpdir, recwarn, monkeypatch
    ):
        # we first need to create a lying Python here, let's mock out here
        from tox.interpreters import Interpreters

        def get_executable(self, envconfig):
            return sys.executable

        monkeypatch.setattr(Interpreters, "get_executable", get_executable)

        major, minor = sys.version_info[0:2]
        config = newconfig(
            """
            [testenv:py{0}{1}]
            basepython=python{0}.{2}
            commands = python --version
        """.format(
                major, minor, minor - 1
            )
        )
        env_config = config.envconfigs["py{}{}".format(major, minor)]
        assert env_config.basepython == "python{}.{}".format(major, minor - 1)
        assert not recwarn.list, "\n".join(repr(i.message) for i in recwarn.list)

    def test_default_single_digit_factors(self, newconfig, monkeypatch):
        from tox.interpreters import Interpreters

        def get_executable(self, envconfig):
            return sys.executable

        monkeypatch.setattr(Interpreters, "get_executable", get_executable)

        major, minor = sys.version_info[0:2]

        with pytest.warns(None) as lying:
            config = newconfig(
                """
                [testenv:py{0}]
                basepython=python{0}.{1}
                commands = python --version
                """.format(
                    major, minor - 1
                )
            )

        env_config = config.envconfigs["py{}".format(major)]
        assert env_config.basepython == "python{}.{}".format(major, minor - 1)
        assert len(lying) == 0, "\n".join(repr(r.message) for r in lying)

        with pytest.warns(None) as truthful:
            config = newconfig(
                """
                [testenv:py{0}]
                basepython=python{0}.{1}
                commands = python --version
                """.format(
                    major, minor
                )
            )

        env_config = config.envconfigs["py{}".format(major)]
        assert env_config.basepython == "python{}.{}".format(major, minor)
        assert len(truthful) == 0, "\n".join(repr(r.message) for r in truthful)

    def test_default_factors_conflict_ignore(self, newconfig, capsys):
        with pytest.warns(None) as record:
            config = newconfig(
                """
                [tox]
                ignore_basepython_conflict=True
                [testenv]
                basepython=python3
                [testenv:py27]
                commands = python --version
            """
            )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["py27"]
        assert envconfig.basepython == "python2.7"
        assert len(record) == 0, "\n".join(repr(r.message) for r in record)

    @pytest.mark.issue188
    def test_factors_in_boolean(self, newconfig):
        inisource = """
            [tox]
            envlist = py{27,36}

            [testenv]
            recreate =
                py27: True
        """
        configs = newconfig([], inisource).envconfigs
        assert configs["py27"].recreate
        assert not configs["py36"].recreate

    @pytest.mark.issue190
    def test_factors_in_setenv(self, newconfig):
        inisource = """
            [tox]
            envlist = py27,py36

            [testenv]
            setenv =
                py27: X = 1
        """
        configs = newconfig([], inisource).envconfigs
        assert configs["py27"].setenv["X"] == "1"
        assert "X" not in configs["py36"].setenv

    @pytest.mark.issue191
    def test_factor_use_not_checked(self, newconfig):
        inisource = """
            [tox]
            envlist = py27-{a,b}

            [testenv]
            deps = b: test
        """
        configs = newconfig([], inisource).envconfigs
        assert set(configs.keys()) == {"py27-a", "py27-b"}

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
        assert set(configs.keys()) == {"a", "a-x", "b", "b-x"}

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
        assert [d.name for d in configs["py27-django1.6"].deps] == ["Django==1.6"]

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
        assert config.option.verbose_level == 0
        config = newconfig(["-v"], "")
        assert config.option.verbose_level == 1
        config = newconfig(["-vv"], "")
        assert config.option.verbose_level == 2

    @pytest.mark.parametrize("args, expected", [([], 0), (["-q"], 1), (["-qq"], 2), (["-qqq"], 3)])
    def test_quiet(self, args, expected, newconfig):
        config = newconfig(args, "")
        assert config.option.quiet_level == expected

    def test_substitution_jenkins_default(self, monkeypatch, newconfig):
        monkeypatch.setenv("HUDSON_URL", "xyz")
        config = newconfig(
            """
            [testenv:py27]
            commands =
                {distshare}
        """
        )
        conf = config.envconfigs["py27"]
        argv = conf.commands
        expect_path = config.toxworkdir.join("distshare")
        assert argv[0][0] == expect_path

    def test_substitution_jenkins_context(self, tmpdir, monkeypatch, newconfig):
        monkeypatch.setenv("HUDSON_URL", "xyz")
        monkeypatch.setenv("WORKSPACE", str(tmpdir))
        config = newconfig(
            """
            [tox:jenkins]
            distshare = {env:WORKSPACE}/hello
            [testenv:py27]
            commands =
                {distshare}
        """
        )
        conf = config.envconfigs["py27"]
        argv = conf.commands
        assert argv[0][0] == config.distshare
        assert config.distshare == tmpdir.join("hello")

    def test_sdist_specification(self, newconfig):
        config = newconfig(
            """
            [tox]
            sdistsrc = {distshare}/xyz.zip
        """
        )
        assert config.sdistsrc == config.distshare.join("xyz.zip")
        config = newconfig([], "")
        assert not config.sdistsrc

    def test_env_selection_with_section_name(self, newconfig, monkeypatch):
        inisource = """
            [tox]
            envlist = py36
            [testenv:py36]
            basepython=python3.6
            [testenv:py35]
            basepython=python3.5
            [testenv:py27]
            basepython=python2.7
        """
        config = newconfig([], inisource)
        assert config.envlist == ["py36"]
        config = newconfig(["-epy35"], inisource)
        assert config.envlist == ["py35"]
        monkeypatch.setenv("TOXENV", "py35,py36")
        config = newconfig([], inisource)
        assert config.envlist == ["py35", "py36"]
        monkeypatch.setenv("TOXENV", "ALL")
        config = newconfig([], inisource)
        assert config.envlist == ["py36", "py35", "py27"]
        config = newconfig(["-eALL"], inisource)
        assert config.envlist == ["py36", "py35", "py27"]
        config = newconfig(["-espam"], inisource)
        assert config.envlist == ["spam"]

    def test_env_selection_expanded_envlist(self, newconfig, monkeypatch):
        inisource = """
            [tox]
            envlist = py{36,35,27}
            [testenv:py36]
            basepython=python3.6
        """
        config = newconfig([], inisource)
        assert config.envlist == ["py36", "py35", "py27"]
        config = newconfig(["-eALL"], inisource)
        assert config.envlist == ["py36", "py35", "py27"]

    def test_py_venv(self, newconfig):
        config = newconfig(["-epy"], "")
        env = config.envconfigs["py"]
        assert str(env.basepython) == sys.executable

    def test_no_implicit_venv_from_cli_with_envlist(self, newconfig):
        # See issue 1160.
        inisource = """
            [tox]
            envlist = stated-factors
        """
        config = newconfig(["-etypo-factor"], inisource)
        assert "typo-factor" not in config.envconfigs

    def test_correct_basepython_chosen_from_default_factors(self, newconfig):
        envlist = list(tox.PYTHON.DEFAULT_FACTORS.keys())
        config = newconfig([], "[tox]\nenvlist={}".format(", ".join(envlist)))
        assert config.envlist == envlist
        for name in config.envlist:
            basepython = config.envconfigs[name].basepython
            if name == "jython":
                assert basepython == "jython"
            elif name in ("pypy2", "pypy3"):
                assert basepython == "pypy" + name[-1]
            elif name in ("py2", "py3"):
                assert basepython == "python" + name[-1]
            elif name == "pypy":
                assert basepython == name
            elif name == "py":
                assert "python" in basepython or "pypy" in basepython
            elif "pypy" in name:
                assert basepython == "pypy{}.{}".format(name[-2], name[-1])
            else:
                assert name.startswith("py")
                assert basepython == "python{}.{}".format(name[2], name[3])

    def test_envlist_expansion(self, newconfig):
        inisource = """
            [tox]
            envlist = py{36,27},docs
        """
        config = newconfig([], inisource)
        assert config.envlist == ["py36", "py27", "docs"]

    def test_envlist_cross_product(self, newconfig):
        inisource = """
            [tox]
            envlist = py{36,27}-dep{1,2}
        """
        config = newconfig([], inisource)
        envs = ["py36-dep1", "py36-dep2", "py27-dep1", "py27-dep2"]
        assert config.envlist == envs

    def test_envlist_multiline(self, newconfig):
        inisource = """
            [tox]
            envlist =
              py27
              py34
        """
        config = newconfig([], inisource)
        assert config.envlist == ["py27", "py34"]

    def test_skip_missing_interpreters_true(self, newconfig):
        ini_source = """
            [tox]
            skip_missing_interpreters = True
        """
        config = newconfig([], ini_source)
        assert config.option.skip_missing_interpreters == "true"

    def test_skip_missing_interpreters_false(self, newconfig):
        ini_source = """
            [tox]
            skip_missing_interpreters = False
        """
        config = newconfig([], ini_source)
        assert config.option.skip_missing_interpreters == "false"

    def test_skip_missing_interpreters_cli_no_arg(self, newconfig):
        ini_source = """
            [tox]
            skip_missing_interpreters = False
        """
        config = newconfig(["--skip-missing-interpreters"], ini_source)
        assert config.option.skip_missing_interpreters == "true"

    def test_skip_missing_interpreters_cli_not_specified(self, newconfig):
        config = newconfig([], "")
        assert config.option.skip_missing_interpreters == "false"

    def test_skip_missing_interpreters_cli_overrides_true(self, newconfig):
        ini_source = """
                    [tox]
                    skip_missing_interpreters = False
                """
        config = newconfig(["--skip-missing-interpreters", "true"], ini_source)
        assert config.option.skip_missing_interpreters == "true"

    def test_skip_missing_interpreters_cli_overrides_false(self, newconfig):
        ini_source = """
                    [tox]
                    skip_missing_interpreters = True
                """
        config = newconfig(["--skip-missing-interpreters", "false"], ini_source)
        assert config.option.skip_missing_interpreters == "false"

    def test_defaultenv_commandline(self, newconfig):
        config = newconfig(["-epy27"], "")
        env = config.envconfigs["py27"]
        assert env.basepython == "python2.7"
        assert not env.commands

    def test_defaultenv_partial_override(self, newconfig):
        inisource = """
            [tox]
            envlist = py27
            [testenv:py27]
            commands= xyz
        """
        config = newconfig([], inisource)
        env = config.envconfigs["py27"]
        assert env.basepython == "python2.7"
        assert env.commands == [["xyz"]]


class TestHashseedOption:
    def _get_envconfigs(self, newconfig, args=None, tox_ini=None, make_hashseed=None):
        if args is None:
            args = []
        if tox_ini is None:
            tox_ini = """
                [testenv]
            """
        if make_hashseed is None:

            def make_hashseed():
                return "123456789"

        original_make_hashseed = tox.config.make_hashseed
        tox.config.make_hashseed = make_hashseed
        try:
            config = newconfig(args, tox_ini)
        finally:
            tox.config.make_hashseed = original_make_hashseed
        return config.envconfigs

    def _get_envconfig(self, newconfig, args=None, tox_ini=None):
        envconfigs = self._get_envconfigs(newconfig, args=args, tox_ini=tox_ini)
        return envconfigs["python"]

    def _check_hashseed(self, envconfig, expected):
        assert envconfig.setenv["PYTHONHASHSEED"] == expected

    def _check_testenv(self, newconfig, expected, args=None, tox_ini=None):
        envconfig = self._get_envconfig(newconfig, args=args, tox_ini=tox_ini)
        self._check_hashseed(envconfig, expected)

    def test_default(self, newconfig):
        self._check_testenv(newconfig, "123456789")

    def test_passing_integer(self, newconfig):
        args = ["--hashseed", "1"]
        self._check_testenv(newconfig, "1", args=args)

    def test_passing_string(self, newconfig):
        args = ["--hashseed", "random"]
        self._check_testenv(newconfig, "random", args=args)

    def test_passing_empty_string(self, newconfig):
        args = ["--hashseed", ""]
        self._check_testenv(newconfig, "", args=args)

    def test_passing_no_argument(self, newconfig):
        """Test that passing no arguments to --hashseed is not allowed."""
        args = ["--hashseed"]
        try:
            self._check_testenv(newconfig, "", args=args)
        except SystemExit as exception:
            assert exception.code == 2
            return
        assert False  # getting here means we failed the test.

    def test_setenv(self, newconfig):
        """Check that setenv takes precedence."""
        tox_ini = """
            [testenv]
            setenv =
                PYTHONHASHSEED = 2
        """
        self._check_testenv(newconfig, "2", tox_ini=tox_ini)
        args = ["--hashseed", "1"]
        self._check_testenv(newconfig, "2", args=args, tox_ini=tox_ini)

    def test_noset(self, newconfig):
        args = ["--hashseed", "noset"]
        envconfig = self._get_envconfig(newconfig, args=args)
        assert set(envconfig.setenv.definitions.keys()) == {"TOX_ENV_DIR", "TOX_ENV_NAME"}

    def test_noset_with_setenv(self, newconfig):
        tox_ini = """
            [testenv]
            setenv =
                PYTHONHASHSEED = 2
        """
        args = ["--hashseed", "noset"]
        self._check_testenv(newconfig, "2", args=args, tox_ini=tox_ini)

    def test_one_random_hashseed(self, newconfig):
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
        assert make_hashseed() == "1001"
        envconfigs = self._get_envconfigs(newconfig, tox_ini=tox_ini, make_hashseed=make_hashseed)
        self._check_hashseed(envconfigs["hash1"], "1002")
        # Check that hash2's value is not '1003', for example.
        self._check_hashseed(envconfigs["hash2"], "1002")

    def test_setenv_in_one_testenv(self, newconfig):
        """Check using setenv in one of multiple testenvs."""
        tox_ini = """
            [testenv:hash1]
            setenv =
                PYTHONHASHSEED = 2
            [testenv:hash2]
        """
        envconfigs = self._get_envconfigs(newconfig, tox_ini=tox_ini)
        self._check_hashseed(envconfigs["hash1"], "2")
        self._check_hashseed(envconfigs["hash2"], "123456789")


class TestSetenv:
    def test_getdict_lazy(self, newconfig, monkeypatch):
        monkeypatch.setenv("X", "2")
        config = newconfig(
            """
            [testenv:X]
            key0 =
                key1 = {env:X}
                key2 = {env:Y:1}
        """
        )
        envconfig = config.envconfigs["X"]
        val = envconfig._reader.getdict_setenv("key0")
        assert val["key1"] == "2"
        assert val["key2"] == "1"

    def test_getdict_lazy_update(self, newconfig, monkeypatch):
        monkeypatch.setenv("X", "2")
        config = newconfig(
            """
            [testenv:X]
            key0 =
                key1 = {env:X}
                key2 = {env:Y:1}
        """
        )
        envconfig = config.envconfigs["X"]
        val = envconfig._reader.getdict_setenv("key0")
        d = {}
        d.update(val)
        assert d == {"key1": "2", "key2": "1"}

    def test_setenv_uses_os_environ(self, newconfig, monkeypatch):
        monkeypatch.setenv("X", "1")
        config = newconfig(
            """
            [testenv:env1]
            setenv =
                X = {env:X}
        """
        )
        assert config.envconfigs["env1"].setenv["X"] == "1"

    def test_setenv_default_os_environ(self, newconfig, monkeypatch):
        monkeypatch.delenv("X", raising=False)
        config = newconfig(
            """
            [testenv:env1]
            setenv =
                X = {env:X:2}
        """
        )
        assert config.envconfigs["env1"].setenv["X"] == "2"

    def test_setenv_uses_other_setenv(self, newconfig):
        config = newconfig(
            """
            [testenv:env1]
            setenv =
                Y = 5
                X = {env:Y}
        """
        )
        assert config.envconfigs["env1"].setenv["X"] == "5"

    def test_setenv_recursive_direct(self, newconfig):
        config = newconfig(
            """
            [testenv:env1]
            setenv =
                X = {env:X:3}
        """
        )
        assert config.envconfigs["env1"].setenv["X"] == "3"

    def test_setenv_overrides(self, newconfig):
        config = newconfig(
            """
            [testenv]
            setenv =
                PYTHONPATH = something
                ANOTHER_VAL=else
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        assert "PYTHONPATH" in envconfig.setenv
        assert "ANOTHER_VAL" in envconfig.setenv
        assert envconfig.setenv["PYTHONPATH"] == "something"
        assert envconfig.setenv["ANOTHER_VAL"] == "else"

    def test_setenv_with_envdir_and_basepython(self, newconfig):
        config = newconfig(
            """
            [testenv]
            setenv =
                VAL = {envdir}
            basepython = {env:VAL}
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        assert "VAL" in envconfig.setenv
        assert envconfig.setenv["VAL"] == envconfig.envdir
        assert envconfig.basepython == envconfig.envdir

    def test_setenv_ordering_1(self, newconfig):
        config = newconfig(
            """
            [testenv]
            setenv=
                VAL={envdir}
            commands=echo {env:VAL}
        """
        )
        assert len(config.envconfigs) == 1
        envconfig = config.envconfigs["python"]
        assert "VAL" in envconfig.setenv
        assert envconfig.setenv["VAL"] == envconfig.envdir
        assert str(envconfig.envdir) in envconfig.commands[0]

    def test_setenv_cross_section_subst_issue294(self, monkeypatch, newconfig):
        """test that we can do cross-section substitution with setenv"""
        monkeypatch.delenv("TEST", raising=False)
        config = newconfig(
            """
            [section]
            x =
              NOT_TEST={env:TEST:defaultvalue}

            [testenv]
            setenv = {[section]x}
        """
        )
        envconfig = config.envconfigs["python"]
        assert envconfig.setenv["NOT_TEST"] == "defaultvalue"

    def test_setenv_cross_section_subst_twice(self, monkeypatch, newconfig):
        """test that we can do cross-section substitution with setenv"""
        monkeypatch.delenv("TEST", raising=False)
        config = newconfig(
            """
            [section]
            x = NOT_TEST={env:TEST:defaultvalue}
            [section1]
            y = {[section]x}

            [testenv]
            setenv = {[section1]y}
        """
        )
        envconfig = config.envconfigs["python"]
        assert envconfig.setenv["NOT_TEST"] == "defaultvalue"

    def test_setenv_cross_section_mixed(self, monkeypatch, newconfig):
        """test that we can do cross-section substitution with setenv"""
        monkeypatch.delenv("TEST", raising=False)
        config = newconfig(
            """
            [section]
            x = NOT_TEST={env:TEST:defaultvalue}

            [testenv]
            setenv = {[section]x}
                     y = 7
        """
        )
        envconfig = config.envconfigs["python"]
        assert envconfig.setenv["NOT_TEST"] == "defaultvalue"
        assert envconfig.setenv["y"] == "7"


class TestIndexServer:
    def test_indexserver(self, newconfig):
        config = newconfig(
            """
            [tox]
            indexserver =
                name1 = XYZ
                name2 = ABC
        """
        )
        assert config.indexserver["default"].url is None
        assert config.indexserver["name1"].url == "XYZ"
        assert config.indexserver["name2"].url == "ABC"

    def test_parse_indexserver(self, newconfig):
        inisource = """
            [tox]
            indexserver =
                default = https://pypi.somewhere.org
                name1 = whatever
        """
        config = newconfig([], inisource)
        assert config.indexserver["default"].url == "https://pypi.somewhere.org"
        assert config.indexserver["name1"].url == "whatever"
        config = newconfig(["-i", "qwe"], inisource)
        assert config.indexserver["default"].url == "qwe"
        assert config.indexserver["name1"].url == "whatever"
        config = newconfig(["-i", "name1=abc", "-i", "qwe2"], inisource)
        assert config.indexserver["default"].url == "qwe2"
        assert config.indexserver["name1"].url == "abc"

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
                pypi    = https://pypi.org/simple
        """
        config = newconfig([], inisource)
        expected = "file://{}/.pip/downloads/simple".format(config.homedir)
        assert config.indexserver["default"].url == expected
        assert config.indexserver["local1"].url == config.indexserver["default"].url


class TestConfigConstSubstitutions:
    @pytest.mark.parametrize("pathsep", [":", ";"])
    def test_replace_pathsep_unix(self, monkeypatch, newconfig, pathsep):
        monkeypatch.setattr("os.pathsep", pathsep)
        config = newconfig(
            """
        [testenv]
        setenv =
            PATH = dira{:}dirb{:}dirc
        """
        )
        envconfig = config.envconfigs["python"]
        assert envconfig.setenv["PATH"] == pathsep.join(["dira", "dirb", "dirc"])

    def test_pathsep_regex(self):
        """Sanity check for regex behavior for empty colon."""
        regex = tox.config.Replacer.RE_ITEM_REF
        match = next(regex.finditer("{:}"))
        mdict = match.groupdict()
        assert mdict["sub_type"] is None
        assert mdict["substitution_value"] == ""
        assert mdict["default_value"] == ""


class TestParseEnv:
    def test_parse_recreate(self, newconfig):
        inisource = ""
        config = newconfig([], inisource)
        assert not config.envconfigs["python"].recreate
        config = newconfig(["--recreate"], inisource)
        assert config.envconfigs["python"].recreate
        config = newconfig(["-r"], inisource)
        assert config.envconfigs["python"].recreate
        inisource = """
            [testenv:hello]
            recreate = True
        """
        config = newconfig([], inisource)
        assert config.envconfigs["hello"].recreate


class TestCmdInvocation:
    def test_help(self, cmd, initproj):
        initproj("help", filedefs={"tox.ini": ""})
        result = cmd("-h")
        assert not result.ret
        assert re.match(r"usage:.*help.*", result.out, re.DOTALL)

    def test_version_simple(self, cmd, initproj):
        initproj("help", filedefs={"tox.ini": ""})
        result = cmd("--version")
        assert not result.ret
        assert "{} imported from".format(tox.__version__) in result.out

    def test_version_no_plugins(self):
        pm = PluginManager("fakeprject")
        version_info = get_version_info(pm)
        assert "imported from" in version_info
        assert "registered plugins:" not in version_info

    def test_version_with_normal_plugin(self, monkeypatch):
        def fake_normal_plugin_distinfo():
            class MockModule:
                __file__ = "some-file"

            class MockEggInfo:
                project_name = "some-project"
                version = "1.0"

            return [(MockModule, MockEggInfo)]

        pm = PluginManager("fakeproject")
        monkeypatch.setattr(pm, "list_plugin_distinfo", fake_normal_plugin_distinfo)
        version_info = get_version_info(pm)
        assert "registered plugins:" in version_info
        assert "some-file" in version_info
        assert "some-project" in version_info
        assert "1.0" in version_info

    def test_version_with_fileless_module(self, monkeypatch):
        def fake_no_file_plugin_distinfo():
            class MockModule:
                def __repr__(self):
                    return "some-repr"

            class MockEggInfo:
                project_name = "some-project"
                version = "1.0"

            return [(MockModule(), MockEggInfo)]

        pm = PluginManager("fakeproject")
        monkeypatch.setattr(pm, "list_plugin_distinfo", fake_no_file_plugin_distinfo)
        version_info = get_version_info(pm)
        assert "registered plugins:" in version_info
        assert "some-project" in version_info
        assert "some-repr" in version_info
        assert "1.0" in version_info

    def test_config_specific_ini(self, tmpdir, cmd):
        ini = tmpdir.ensure("hello.ini")
        result = cmd("-c", ini, "--showconfig")
        assert not result.ret
        assert result.outlines[1] == "config-file: {}".format(ini)

    def test_no_tox_ini(self, cmd, initproj):
        initproj("noini-0.5")
        result = cmd()
        result.assert_fail()
        msg = "ERROR: tox config file (either pyproject.toml, tox.ini, setup.cfg) not found\n"
        assert result.err == msg
        assert not result.out

    def test_override_workdir(self, cmd, initproj):
        baddir = "badworkdir-123"
        gooddir = "overridden-234"
        initproj(
            "overrideworkdir-0.5",
            filedefs={
                "tox.ini": """
            [tox]
            toxworkdir={}
            """.format(
                    baddir
                )
            },
        )
        result = cmd("--workdir", gooddir, "--showconfig")
        assert not result.ret
        assert gooddir in result.out
        assert baddir not in result.out
        assert py.path.local(gooddir).check()
        assert not py.path.local(baddir).check()

    def test_showconfig_with_force_dep_version(self, cmd, initproj):
        initproj(
            "force_dep_version",
            filedefs={
                "tox.ini": """
            [tox]

            [testenv]
            deps=
                dep1==2.3
                dep2
            """
            },
        )
        result = cmd("--showconfig")
        result.assert_success(is_run_test_env=False)
        assert any(re.match(r".*deps.*dep1==2.3, dep2.*", l) for l in result.outlines)
        # override dep1 specific version, and force version for dep2
        result = cmd("--showconfig", "--force-dep=dep1", "--force-dep=dep2==5.0")
        result.assert_success(is_run_test_env=False)
        assert any(re.match(r".*deps.*dep1, dep2==5.0.*", l) for l in result.outlines)


@pytest.mark.parametrize(
    "cli_args,run_envlist",
    [
        ("-e py36", ["py36"]),
        ("-e py36,py34", ["py36", "py34"]),
        ("-e py36,py36", ["py36", "py36"]),
        ("-e py36,py34 -e py34,py27", ["py36", "py34", "py34", "py27"]),
    ],
)
def test_env_spec(initproj, cli_args, run_envlist):
    initproj(
        "env_spec",
        filedefs={
            "tox.ini": """
                [tox]
                envlist =

                [testenv]
                commands = python -c ""
                """
        },
    )
    args = cli_args.split()
    config = parseconfig(args)
    assert config.envlist == run_envlist


class TestCommandParser:
    def test_command_parser_for_word(self):
        p = CommandParser("word")
        assert list(p.words()) == ["word"]

    def test_command_parser_for_posargs(self):
        p = CommandParser("[]")
        assert list(p.words()) == ["[]"]

    def test_command_parser_for_multiple_words(self):
        p = CommandParser("w1 w2 w3 ")
        assert list(p.words()) == ["w1", " ", "w2", " ", "w3"]

    def test_command_parser_for_substitution_with_spaces(self):
        p = CommandParser("{sub:something with spaces}")
        assert list(p.words()) == ["{sub:something with spaces}"]

    def test_command_parser_with_complex_word_set(self):
        complex_case = (
            "word [] [literal] {something} {some:other thing} w{ord} w{or}d w{ord} "
            "w{o:rd} w{o:r}d {w:or}d w[]ord {posargs:{a key}}"
        )
        p = CommandParser(complex_case)
        parsed = list(p.words())
        expected = [
            "word",
            " ",
            "[]",
            " ",
            "[literal]",
            " ",
            "{something}",
            " ",
            "{some:other thing}",
            " ",
            "w",
            "{ord}",
            " ",
            "w",
            "{or}",
            "d",
            " ",
            "w",
            "{ord}",
            " ",
            "w",
            "{o:rd}",
            " ",
            "w",
            "{o:r}",
            "d",
            " ",
            "{w:or}",
            "d",
            " ",
            "w[]ord",
            " ",
            "{posargs:{a key}}",
        ]

        assert parsed == expected

    def test_command_with_runs_of_whitespace(self):
        cmd = "cmd1 {item1}\n  {item2}"
        p = CommandParser(cmd)
        parsed = list(p.words())
        assert parsed == ["cmd1", " ", "{item1}", "\n  ", "{item2}"]

    def test_command_with_split_line_in_subst_arguments(self):
        cmd = dedent(
            """ cmd2 {posargs:{item2}
                         other}"""
        )
        p = CommandParser(cmd)
        parsed = list(p.words())
        expected = ["cmd2", " ", "{posargs:{item2}\n                        other}"]
        assert parsed == expected

    def test_command_parsing_for_issue_10(self):
        cmd = "nosetests -v -a !deferred --with-doctest []"
        p = CommandParser(cmd)
        parsed = list(p.words())
        expected = [
            "nosetests",
            " ",
            "-v",
            " ",
            "-a",
            " ",
            "!deferred",
            " ",
            "--with-doctest",
            " ",
            "[]",
        ]
        assert parsed == expected

    # @mark_dont_run_on_windows
    def test_commands_with_backslash(self, newconfig):
        config = newconfig(
            [r"hello\world"],
            """
            [testenv:py36]
            commands = some {posargs}
        """,
        )
        envconfig = config.envconfigs["py36"]
        assert envconfig.commands[0] == ["some", r"hello\world"]


def test_isolated_build_env_cannot_be_in_envlist(newconfig, capsys):
    inisource = """
            [tox]
            envlist = py36,package
            isolated_build = True
            isolated_build_env = package
        """
    with pytest.raises(
        tox.exception.ConfigError, match="isolated_build_env package cannot be part of envlist"
    ):
        newconfig([], inisource)

    out, err = capsys.readouterr()
    assert not err
    assert not out


def test_isolated_build_overrides(newconfig, capsys):
    inisource = """
            [tox]
            isolated_build = True

            [testenv]
            deps = something crazy here

            [testenv:.package]
            deps =
        """
    config = newconfig([], inisource)
    deps = config.envconfigs.get(".package").deps
    assert deps == []


@pytest.mark.parametrize(
    "key, set_value, default", [("deps", "crazy", []), ("sitepackages", "True", False)]
)
def test_isolated_build_ignores(newconfig, capsys, key, set_value, default):
    config = newconfig(
        [],
        """
            [tox]
            isolated_build = True

            [testenv]
            {} = {}
        """.format(
            key, set_value
        ),
    )
    package_env = config.envconfigs.get(".package")
    value = getattr(package_env, key)
    assert value == default


def test_config_via_pyproject_legacy(initproj):
    initproj(
        "config_via_pyproject_legacy-0.5",
        filedefs={
            "pyproject.toml": '''
                [tool.tox]
                legacy_tox_ini = """
                [tox]
                envlist = py27
                """
        '''
        },
    )
    config = parseconfig([])
    assert config.envlist == ["py27"]


def test_config_bad_pyproject_specified(initproj, capsys):
    base = initproj("config_via_pyproject_legacy-0.5", filedefs={"pyproject.toml": ""})
    with pytest.raises(SystemExit):
        parseconfig(["-c", str(base.join("pyproject.toml"))])

    out, err = capsys.readouterr()
    msg = "ERROR: tox config file (either pyproject.toml, tox.ini, setup.cfg) not found\n"
    assert err == msg
    assert "ERROR:" not in out


@pytest.mark.skipif(sys.platform == "win32", reason="no named pipes on Windows")
def test_config_bad_config_type_specified(monkeypatch, tmpdir, capsys):
    monkeypatch.chdir(tmpdir)
    name = tmpdir.join("named_pipe")
    os.mkfifo(str(name))
    with pytest.raises(SystemExit):
        parseconfig(["-c", str(name)])

    out, err = capsys.readouterr()
    notes = (
        "ERROR: {} is neither file or directory".format(name),
        "ERROR: tox config file (either pyproject.toml, tox.ini, setup.cfg) not found",
    )
    msg = "\n".join(notes) + "\n"
    assert err == msg
    assert "ERROR:" not in out


def test_interactive_na(newconfig, monkeypatch):
    monkeypatch.setattr(tox.config, "is_interactive", lambda: False)
    config = newconfig(
        """
        [testenv:py]
        setenv = A = {tty:X:Y}
        """
    )
    assert config.envconfigs["py"].setenv["A"] == "Y"


def test_interactive_available(newconfig, monkeypatch):
    monkeypatch.setattr(tox.config, "is_interactive", lambda: True)
    config = newconfig(
        """
        [testenv:py]
        setenv = A = {tty:X:Y}
        """
    )
    assert config.envconfigs["py"].setenv["A"] == "X"


def test_interactive():
    tox.config.is_interactive()


def test_config_current_py(newconfig, current_tox_py, cmd, tmpdir, monkeypatch):
    monkeypatch.chdir(tmpdir)
    config = newconfig(
        """
        [tox]
        envlist = {0}
        skipsdist = True

        [testenv:{0}]
        commands = python -c "print('all')"
        """.format(
            current_tox_py
        )
    )
    assert config.envconfigs[current_tox_py]
    result = cmd()
    result.assert_success()


def test_posargs_relative_changedir(newconfig, tmpdir):
    dir1 = tmpdir.join("dir1").ensure()
    tmpdir.join("dir2").ensure()
    with tmpdir.as_cwd():
        config = newconfig(
            """\
            [tox]
            [testenv]
            changedir = dir2
            commands =
                echo {posargs}
            """
        )
        config.option.args = ["dir1", dir1.strpath, "dir3"]
        testenv = config.envconfigs["python"]
        PosargsOption().postprocess(testenv, config.option.args)

        assert testenv._reader.posargs == [
            # should have relative-ized
            os.path.join("..", "dir1"),
            # should have stayed the same,
            dir1.strpath,
            "dir3",
        ]


def test_config_no_version_data_in__name(newconfig, capsys):
    newconfig(
        """
        [tox]
        envlist = py, pypy, jython
        [testenv]
        basepython = python
        """
    )
    out, err = capsys.readouterr()
    assert not out
    assert not err
