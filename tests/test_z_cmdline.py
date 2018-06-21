import json
import os
import platform
import re
import subprocess
import sys

import py
import pytest

import tox
from tox._pytestplugin import ReportExpectMock
from tox.config import parseconfig
from tox.exception import MissingDependency, MissingDirectory
from tox.session import Session

pytest_plugins = "pytester"


def test_report_protocol(newconfig):
    config = newconfig(
        [],
        """
            [testenv:mypython]
            deps=xy
    """,
    )

    class Popen:
        def __init__(self, *args, **kwargs):
            pass

        def communicate(self):
            return "", ""

        def wait(self):
            pass

    session = Session(config, popen=Popen, Report=ReportExpectMock)
    report = session.report
    report.expect("using")
    venv = session.getvenv("mypython")
    action = session.newaction(venv, "update")
    venv.update(action)
    report.expect("logpopen")


def test__resolve_pkg(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    spec = distshare.join("pkg123-*")
    with pytest.raises(MissingDirectory):
        mocksession._resolve_pkg(spec)
    distshare.ensure(dir=1)
    with pytest.raises(MissingDependency):
        mocksession._resolve_pkg(spec)
    distshare.ensure("pkg123-1.3.5.zip")
    p = distshare.ensure("pkg123-1.4.5.zip")
    mocksession.report.clear()
    result = mocksession._resolve_pkg(spec)
    assert result == p
    mocksession.report.expect("info", "determin*pkg123*")
    distshare.ensure("pkg123-1.4.7dev.zip")
    mocksession._clearmocks()
    result = mocksession._resolve_pkg(spec)
    mocksession.report.expect("warning", "*1.4.7*")
    assert result == p
    mocksession._clearmocks()
    distshare.ensure("pkg123-1.4.5a1.tar.gz")
    result = mocksession._resolve_pkg(spec)
    assert result == p


def test__resolve_pkg_doubledash(tmpdir, mocksession):
    distshare = tmpdir.join("distshare")
    p = distshare.ensure("pkg-mine-1.3.0.zip")
    res = mocksession._resolve_pkg(distshare.join("pkg-mine*"))
    assert res == p
    distshare.ensure("pkg-mine-1.3.0a1.zip")
    res = mocksession._resolve_pkg(distshare.join("pkg-mine*"))
    assert res == p


class TestSession:
    def test_log_pcall(self, mocksession):
        mocksession.config.logdir.ensure(dir=1)
        assert not mocksession.config.logdir.listdir()
        action = mocksession.newaction(None, "something")
        action.popen(["echo"])
        match = mocksession.report.getnext("logpopen")
        assert match[1].outpath.relto(mocksession.config.logdir)
        assert match[1].shell is False

    def test_summary_status(self, initproj, capfd):
        initproj(
            "logexample123-0.5",
            filedefs={
                "tests": {"test_hello.py": "def test_hello(): pass"},
                "tox.ini": """
            [testenv:hello]
            [testenv:world]
            """,
            },
        )
        config = parseconfig([])
        session = Session(config)
        envs = session.venvlist
        assert len(envs) == 2
        env1, env2 = envs
        env1.status = "FAIL XYZ"
        assert env1.status
        env2.status = 0
        assert not env2.status
        session._summary()
        out, err = capfd.readouterr()
        exp = "{}: FAIL XYZ".format(env1.envconfig.envname)
        assert exp in out
        exp = "{}: commands succeeded".format(env2.envconfig.envname)
        assert exp in out

    def test_getvenv(self, initproj):
        initproj(
            "logexample123-0.5",
            filedefs={
                "tests": {"test_hello.py": "def test_hello(): pass"},
                "tox.ini": """
            [testenv:hello]
            [testenv:world]
            """,
            },
        )
        config = parseconfig([])
        session = Session(config)
        venv1 = session.getvenv("hello")
        venv2 = session.getvenv("hello")
        assert venv1 is venv2
        venv1 = session.getvenv("world")
        venv2 = session.getvenv("world")
        assert venv1 is venv2
        with pytest.raises(LookupError):
            session.getvenv("qwe")


def test_minversion(cmd, initproj):
    initproj(
        "interp123-0.5",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [tox]
            minversion = 6.0
        """,
        },
    )
    result = cmd("-v")
    assert re.match(
        r"ERROR: MinVersionError: tox version is .*," r" required is at least 6.0", result.out
    )
    assert result.ret


def test_notoxini_help_still_works(initproj, cmd):
    initproj("example123-0.5", filedefs={"tests": {"test_hello.py": "def test_hello(): pass"}})
    result = cmd("-h")
    assert result.err == "ERROR: toxini file 'tox.ini' not found\n"
    assert result.out.startswith("usage: ")
    assert any("--help" in l for l in result.outlines), result.outlines
    assert not result.ret


def test_notoxini_help_ini_still_works(initproj, cmd):
    initproj("example123-0.5", filedefs={"tests": {"test_hello.py": "def test_hello(): pass"}})
    result = cmd("--help-ini")
    assert any("setenv" in l for l in result.outlines), result.outlines
    assert not result.ret


def test_envdir_equals_toxini_errors_out(cmd, initproj):
    initproj(
        "interp123-0.7",
        filedefs={
            "tox.ini": """
            [testenv]
            envdir={toxinidir}
        """
        },
    )
    result = cmd()
    assert result.outlines[1] == "ERROR: ConfigError: envdir must not equal toxinidir"
    assert re.match(r"ERROR: venv \'python\' in .* would delete project", result.outlines[0])
    assert result.ret


def test_run_custom_install_command_error(cmd, initproj):
    initproj(
        "interp123-0.5",
        filedefs={
            "tox.ini": """
            [testenv]
            install_command=./tox.ini {opts} {packages}
        """
        },
    )
    result = cmd()
    assert re.match(
        r"ERROR: invocation failed \(errno \d+\), args: .*[/\\]tox\.ini", result.outlines[-1]
    )
    assert result.ret


def test_unknown_interpreter_and_env(cmd, initproj):
    initproj(
        "interp123-0.5",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [testenv:python]
            basepython=xyz_unknown_interpreter
            [testenv]
            changedir=tests
        """,
        },
    )
    result = cmd()
    assert result.ret
    assert any(
        "ERROR: InterpreterNotFound: xyz_unknown_interpreter" == l for l in result.outlines
    ), result.outlines

    result = cmd("-exyz")
    assert result.ret
    assert result.out == "ERROR: unknown environment 'xyz'\n"


def test_unknown_interpreter(cmd, initproj):
    initproj(
        "interp123-0.5",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [testenv:python]
            basepython=xyz_unknown_interpreter
            [testenv]
            changedir=tests
        """,
        },
    )
    result = cmd()
    assert result.ret
    assert any(
        "ERROR: InterpreterNotFound: xyz_unknown_interpreter" == l for l in result.outlines
    ), result.outlines


def test_skip_platform_mismatch(cmd, initproj):
    initproj(
        "interp123-0.5",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [testenv]
            changedir=tests
            platform=x123
        """,
        },
    )
    result = cmd()
    assert not result.ret
    assert any(
        "SKIPPED:  python: platform mismatch" == l for l in result.outlines
    ), result.outlines


def test_skip_unknown_interpreter(cmd, initproj):
    initproj(
        "interp123-0.5",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [testenv:python]
            basepython=xyz_unknown_interpreter
            [testenv]
            changedir=tests
        """,
        },
    )
    result = cmd("--skip-missing-interpreters")
    assert not result.ret
    msg = "SKIPPED:  python: InterpreterNotFound: xyz_unknown_interpreter"
    assert any(msg == l for l in result.outlines), result.outlines


def test_skip_unknown_interpreter_result_json(cmd, initproj, tmpdir):
    report_path = tmpdir.join("toxresult.json")
    initproj(
        "interp123-0.5",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [testenv:python]
            basepython=xyz_unknown_interpreter
            [testenv]
            changedir=tests
        """,
        },
    )
    result = cmd("--skip-missing-interpreters", "--result-json", report_path)
    assert not result.ret
    msg = "SKIPPED:  python: InterpreterNotFound: xyz_unknown_interpreter"
    assert any(msg == l for l in result.outlines), result.outlines
    setup_result_from_json = json.load(report_path)["testenvs"]["python"]["setup"]
    for setup_step in setup_result_from_json:
        assert "InterpreterNotFound" in setup_step["output"]
        assert setup_step["retcode"] == "0"


def test_unknown_dep(cmd, initproj):
    initproj(
        "dep123-0.7",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [testenv]
            deps=qweqwe123
            changedir=tests
        """,
        },
    )
    result = cmd()
    assert result.ret
    assert result.outlines[-1].startswith("ERROR:   python: could not install deps [qweqwe123];")


def test_venv_special_chars_issue252(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "tox.ini": """
            [tox]
            envlist = special&&1
            [testenv:special&&1]
            changedir=tests
        """,
        },
    )
    result = cmd()
    assert result.ret == 0
    pattern = re.compile("special&&1 installed: .*pkg123==0.7.*")
    assert any(pattern.match(line) for line in result.outlines), result.outlines


def test_unknown_environment(cmd, initproj):
    initproj("env123-0.7", filedefs={"tox.ini": ""})
    result = cmd("-e", "qpwoei")
    assert result.ret
    assert result.out == "ERROR: unknown environment 'qpwoei'\n"


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
    assert result.ret == 0


def test_minimal_setup_py_empty(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "setup.py": """
        """,
            "tox.ini": "",
        },
    )
    result = cmd()
    assert result.ret == 1
    assert result.outlines[-1] == "ERROR: setup.py is empty"


def test_minimal_setup_py_comment_only(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "setup.py": """\n# some comment

        """,
            "tox.ini": "",
        },
    )
    result = cmd()
    assert result.ret == 1
    assert result.outlines[-1] == "ERROR: setup.py is empty"


def test_minimal_setup_py_non_functional(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "setup.py": """
        import sys

        """,
            "tox.ini": "",
        },
    )
    result = cmd()
    assert result.ret == 1
    assert any(re.match(r".*ERROR.*check setup.py.*", l) for l in result.outlines), result.outlines


def test_sdist_fails(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "setup.py": """
            syntax error
        """,
            "tox.ini": "",
        },
    )
    result = cmd()
    assert result.ret
    assert any(
        re.match(r".*FAIL.*could not package project.*", l) for l in result.outlines
    ), result.outlines


def test_no_setup_py_exits(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [testenv]
            commands=python -c "2 + 2"
        """
        },
    )
    os.remove("setup.py")
    result = cmd()
    assert result.ret
    assert any(
        re.match(r".*ERROR.*No setup.py file found.*", l) for l in result.outlines
    ), result.outlines


def test_package_install_fails(cmd, initproj):
    initproj(
        "pkg123-0.7",
        filedefs={
            "tests": {"test_hello.py": "def test_hello(): pass"},
            "setup.py": """
            from setuptools import setup
            setup(
                name='pkg123',
                description='pkg123 project',
                version='0.7',
                license='MIT',
                platforms=['unix', 'win32'],
                packages=['pkg123',],
                install_requires=['qweqwe123'],
                )
            """,
            "tox.ini": "",
        },
    )
    result = cmd()
    assert result.ret
    assert result.outlines[-1].startswith("ERROR:   python: InvocationError for command ")


@pytest.fixture
def example123(initproj):
    yield initproj(
        "example123-0.5",
        filedefs={
            "tests": {
                "test_hello.py": """
                def test_hello(pytestconfig):
                    pass
            """
            },
            "tox.ini": """
            [testenv]
            changedir=tests
            commands= pytest --basetemp={envtmpdir} \
                              --junitxml=junit-{envname}.xml
            deps=pytest
        """,
        },
    )


def test_toxuone_env(cmd, example123):
    result = cmd()
    assert not result.ret
    assert re.match(
        r".*generated\W+xml\W+file.*junit-python\.xml" r".*\W+1\W+passed.*", result.out, re.DOTALL
    )
    result = cmd("-epython")
    assert not result.ret
    assert re.match(
        r".*\W+1\W+passed.*" r"summary.*" r"python:\W+commands\W+succeeded.*",
        result.out,
        re.DOTALL,
    )


def test_different_config_cwd(cmd, example123, monkeypatch):
    # see that things work with a different CWD
    monkeypatch.chdir(example123.dirname)
    result = cmd("-c", "example123/tox.ini")
    assert not result.ret
    assert re.match(
        r".*\W+1\W+passed.*" r"summary.*" r"python:\W+commands\W+succeeded.*",
        result.out,
        re.DOTALL,
    )


def test_json(cmd, example123):
    # see that tests can also fail and retcode is correct
    testfile = py.path.local("tests").join("test_hello.py")
    assert testfile.check()
    testfile.write("def test_fail(): assert 0")
    jsonpath = example123.join("res.json")
    result = cmd("--result-json", jsonpath)
    assert result.ret == 1
    data = json.load(jsonpath.open("r"))
    verify_json_report_format(data)
    assert re.match(
        r".*\W+1\W+failed.*" r"summary.*" r"python:\W+commands\W+failed.*", result.out, re.DOTALL
    )


def test_developz(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
    """
        },
    )
    result = cmd("-vv", "--develop")
    assert not result.ret
    assert "sdist-make" not in result.out


def test_usedevelop(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
            [testenv]
            usedevelop=True
    """
        },
    )
    result = cmd("-vv")
    assert not result.ret
    assert "sdist-make" not in result.out


def test_usedevelop_mixed(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
            [testenv:devenv]
            usedevelop=True
            [testenv:nondev]
            usedevelop=False
    """
        },
    )

    # running only 'devenv' should not do sdist
    result = cmd("-vv", "-e", "devenv")
    assert not result.ret
    assert "sdist-make" not in result.out

    # running all envs should do sdist
    result = cmd("-vv")
    assert not result.ret
    assert "sdist-make" in result.out


@pytest.mark.parametrize("src_root", [".", "src"])
def test_test_usedevelop(cmd, initproj, src_root, monkeypatch):
    base = initproj(
        "example123-0.5",
        src_root=src_root,
        filedefs={
            "tests": {
                "test_hello.py": """
                def test_hello(pytestconfig):
                    pass
            """
            },
            "tox.ini": """
            [testenv]
            usedevelop=True
            changedir=tests
            commands=
                pytest --basetemp={envtmpdir} --junitxml=junit-{envname}.xml []
            deps=pytest
        """,
        },
    )
    result = cmd("-v")
    assert not result.ret
    assert re.match(
        r".*generated\W+xml\W+file.*junit-python\.xml" r".*\W+1\W+passed.*", result.out, re.DOTALL
    )
    assert "sdist-make" not in result.out
    result = cmd("-epython")
    assert not result.ret
    assert "develop-inst-noop" in result.out
    assert re.match(
        r".*\W+1\W+passed.*" r"summary.*" r"python:\W+commands\W+succeeded.*",
        result.out,
        re.DOTALL,
    )

    # see that things work with a different CWD
    monkeypatch.chdir(base.dirname)
    result = cmd("-c", "example123/tox.ini")
    assert not result.ret
    assert "develop-inst-noop" in result.out
    assert re.match(
        r".*\W+1\W+passed.*" r"summary.*" r"python:\W+commands\W+succeeded.*",
        result.out,
        re.DOTALL,
    )
    monkeypatch.chdir(base)

    # see that tests can also fail and retcode is correct
    testfile = py.path.local("tests").join("test_hello.py")
    assert testfile.check()
    testfile.write("def test_fail(): assert 0")
    result = cmd()
    assert result.ret
    assert "develop-inst-noop" in result.out
    assert re.match(
        r".*\W+1\W+failed.*" r"summary.*" r"python:\W+commands\W+failed.*", result.out, re.DOTALL
    )

    # test develop is called if setup.py changes
    setup_py = py.path.local("setup.py")
    setup_py.write(setup_py.read() + " ")
    result = cmd()
    assert result.ret
    assert "develop-inst-nodeps" in result.out


def _alwayscopy_not_supported():
    # This is due to virtualenv bugs with alwayscopy in some platforms
    # see: https://github.com/pypa/virtualenv/issues/565
    if hasattr(platform, "linux_distribution"):
        _dist = platform.linux_distribution(full_distribution_name=False)
        (name, version, arch) = _dist
        if any((name == "centos" and version[0] == "7", name == "SuSE" and arch == "x86_64")):
            return True
    return False


@pytest.mark.skipif(_alwayscopy_not_supported(), reason="Platform doesnt support alwayscopy")
def test_alwayscopy(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
            [testenv]
            commands={envpython} --version
            alwayscopy=True
    """
        },
    )
    result = cmd("-vv")
    assert not result.ret
    assert "virtualenv --always-copy" in result.out


def test_alwayscopy_default(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
            [testenv]
            commands={envpython} --version
    """
        },
    )
    result = cmd("-vv")
    assert not result.ret
    assert "virtualenv --always-copy" not in result.out


def test_empty_activity_ignored(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
            [testenv]
            list_dependencies_command=echo
            commands={envpython} --version
    """
        },
    )
    result = cmd()
    assert not result.ret
    assert "installed:" not in result.out


def test_empty_activity_shown_verbose(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
            [testenv]
            list_dependencies_command=echo
            commands={envpython} --version
    """
        },
    )
    result = cmd("-v")
    assert not result.ret
    assert "installed:" in result.out


def test_test_piphelp(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
            # content of: tox.ini
            [testenv]
            commands=pip -h
    """
        },
    )
    result = cmd()
    assert not result.ret


def test_notest(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
        # content of: tox.ini
        [testenv:py26]
        basepython=python
    """
        },
    )
    result = cmd("-v", "--notest")
    assert not result.ret
    assert re.match(r".*summary.*" r"py26\W+skipped\W+tests.*", result.out, re.DOTALL)
    result = cmd("-v", "--notest", "-epy26")
    assert not result.ret
    assert re.match(r".*py26\W+reusing.*", result.out, re.DOTALL)


def test_PYC(initproj, cmd, monkeypatch):
    initproj("example123", filedefs={"tox.ini": ""})
    monkeypatch.setenv("PYTHONDOWNWRITEBYTECODE", 1)
    result = cmd("-v", "--notest")
    assert not result.ret
    assert "create" in result.out


def test_env_VIRTUALENV_PYTHON(initproj, cmd, monkeypatch):
    initproj("example123", filedefs={"tox.ini": ""})
    monkeypatch.setenv("VIRTUALENV_PYTHON", "/FOO")
    result = cmd("-v", "--notest")
    assert not result.ret, result.outlines
    assert "create" in result.out


def test_sdistonly(initproj, cmd):
    initproj(
        "example123",
        filedefs={
            "tox.ini": """
    """
        },
    )
    result = cmd("-v", "--sdistonly")
    assert not result.ret
    assert re.match(r".*sdist-make.*setup.py.*", result.out, re.DOTALL)
    assert "-mvirtualenv" not in result.out


def test_separate_sdist_no_sdistfile(cmd, initproj, tmpdir):
    distshare = tmpdir.join("distshare")
    initproj(
        ("pkg123-foo", "0.7"),
        filedefs={
            "tox.ini": """
            [tox]
            distshare={}
        """.format(
                distshare
            )
        },
    )
    result = cmd("--sdistonly")
    assert not result.ret
    distshare_files = distshare.listdir()
    assert len(distshare_files) == 1
    sdistfile = distshare_files[0]
    assert "pkg123-foo-0.7.zip" in str(sdistfile)


def test_separate_sdist(cmd, initproj, tmpdir):
    distshare = tmpdir.join("distshare")
    initproj(
        "pkg123-0.7",
        filedefs={
            "tox.ini": """
            [tox]
            distshare={}
            sdistsrc={{distshare}}/pkg123-0.7.zip
        """.format(
                distshare
            )
        },
    )
    result = cmd("--sdistonly")
    assert not result.ret
    sdistfiles = distshare.listdir()
    assert len(sdistfiles) == 1
    sdistfile = sdistfiles[0]
    result = cmd("-v", "--notest")
    assert not result.ret
    assert "python inst: {}".format(sdistfile) in result.out


def test_envsitepackagesdir(cmd, initproj):
    initproj(
        "pkg512-0.0.5",
        filedefs={
            "tox.ini": """
        [testenv]
        commands=
            python -c "print(r'X:{envsitepackagesdir}')"
    """
        },
    )
    result = cmd()
    assert result.ret == 0
    assert re.match(r".*\nX:.*tox.*site-packages.*", result.out, re.DOTALL)


def test_envsitepackagesdir_skip_missing_issue280(cmd, initproj):
    initproj(
        "pkg513-0.0.5",
        filedefs={
            "tox.ini": """
        [testenv]
        basepython=/usr/bin/qwelkjqwle
        commands=
            {envsitepackagesdir}
    """
        },
    )
    result = cmd("--skip-missing-interpreters")
    assert result.ret == 0
    assert re.match(r".*SKIPPED:.*qwelkj.*", result.out, re.DOTALL)


@pytest.mark.parametrize("verbosity", ["", "-v", "-vv"])
def test_verbosity(cmd, initproj, verbosity):
    initproj(
        "pkgX-0.0.5",
        filedefs={
            "tox.ini": """
        [testenv]
    """
        },
    )
    result = cmd(verbosity)
    assert result.ret == 0

    needle = "Successfully installed pkgX-0.0.5"
    if verbosity == "-vv":
        assert any(needle in line for line in result.outlines), result.outlines
    else:
        assert all(needle not in line for line in result.outlines), result.outlines


def verify_json_report_format(data, testenvs=True):
    assert data["reportversion"] == "1"
    assert data["toxversion"] == tox.__version__
    if testenvs:
        for envname, envdata in data["testenvs"].items():
            for commandtype in ("setup", "test"):
                if commandtype not in envdata:
                    continue
                for command in envdata[commandtype]:
                    assert command["output"]
                    assert command["retcode"]
            if envname != "GLOB":
                assert isinstance(envdata["installed_packages"], list)
                pyinfo = envdata["python"]
                assert isinstance(pyinfo["version_info"], list)
                assert pyinfo["version"]
                assert pyinfo["executable"]


def test_envtmpdir(initproj, cmd):
    initproj(
        "foo",
        filedefs={
            # This file first checks that envtmpdir is existent and empty. Then it
            # creates an empty file in that directory.  The tox command is run
            # twice below, so this is to test whether the directory is cleared
            # before the second run.
            "check_empty_envtmpdir.py": """if True:
            import os
            from sys import argv
            envtmpdir = argv[1]
            assert os.path.exists(envtmpdir)
            assert os.listdir(envtmpdir) == []
            open(os.path.join(envtmpdir, 'test'), 'w').close()
        """,
            "tox.ini": """
            [testenv]
            commands=python check_empty_envtmpdir.py {envtmpdir}
        """,
        },
    )

    result = cmd()
    assert not result.ret

    result = cmd()
    assert not result.ret


def test_missing_env_fails(initproj, cmd):
    initproj("foo", filedefs={"tox.ini": "[testenv:foo]\ncommands={env:VAR}"})
    result = cmd()
    assert result.ret == 1
    assert result.out.endswith(
        "foo: unresolvable substitution(s): 'VAR'."
        " Environment variables are missing or defined recursively.\n"
    )


def test_tox_console_script():
    result = subprocess.check_call(["tox", "--help"])
    assert result == 0


def test_tox_quickstart_script():
    result = subprocess.check_call(["tox-quickstart", "--help"])
    assert result == 0


def test_tox_cmdline_no_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["caller_script", "--help"])
    with pytest.raises(SystemExit):
        tox.cmdline()


def test_tox_cmdline_args():
    with pytest.raises(SystemExit):
        tox.cmdline(["caller_script", "--help"])


@pytest.mark.parametrize("exit_code", [0, 6])
def test_exit_code(initproj, cmd, exit_code, mocker):
    """ Check for correct InvocationError, with exit code,
        except for zero exit code """
    import tox.exception

    mocker.spy(tox.exception, "exit_code_str")
    tox_ini_content = "[testenv:foo]\ncommands=python -c 'import sys; sys.exit({:d})'".format(
        exit_code
    )
    initproj("foo", filedefs={"tox.ini": tox_ini_content})
    cmd()
    if exit_code:
        # need mocker.spy above
        assert tox.exception.exit_code_str.call_count == 1
        (args, kwargs) = tox.exception.exit_code_str.call_args
        assert kwargs == {}
        (call_error_name, call_command, call_exit_code) = args
        assert call_error_name == "InvocationError"
        # quotes are removed in result.out
        # do not include "python" as it is changed to python.EXE by appveyor
        expected_command_arg = " -c import sys; sys.exit({:d})".format(exit_code)
        assert expected_command_arg in call_command
        assert call_exit_code == exit_code
    else:
        # need mocker.spy above
        assert tox.exception.exit_code_str.call_count == 0
