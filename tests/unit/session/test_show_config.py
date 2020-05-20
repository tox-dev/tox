import py
import pytest
from six import PY2, StringIO
from six.moves import configparser


def load_config(args, cmd):
    result = cmd(*args)
    result.assert_success(is_run_test_env=False)
    parser = configparser.ConfigParser()
    output = StringIO(result.out)
    (parser.readfp if PY2 else parser.read_file)(output)
    return parser


def test_showconfig_with_force_dep_version(cmd, initproj):
    initproj(
        "force_dep_version",
        filedefs={
            "tox.ini": """
        [tox]

        [testenv]
        deps=
            dep1==2.3
            dep2
        """,
        },
    )
    parser = load_config(("--showconfig",), cmd)
    assert parser.get("testenv:python", "deps") == "[dep1==2.3, dep2]"

    parser = load_config(("--showconfig", "--force-dep=dep1", "--force-dep=dep2==5.0"), cmd)
    assert parser.get("testenv:python", "deps") == "[dep1, dep2==5.0]"


@pytest.fixture()
def setup_mixed_conf(initproj):
    initproj(
        "force_dep_version",
        filedefs={
            "tox.ini": """
            [tox]
            envlist = py37,py27,pypi,docs

            [testenv:notincluded]
            changedir = whatever

            [testenv:docs]
            changedir = docs
            """,
        },
    )


@pytest.mark.parametrize(
    "args, expected",
    [
        (
            ["--showconfig"],
            [
                "tox",
                "tox:versions",
                "testenv:py37",
                "testenv:py27",
                "testenv:pypi",
                "testenv:docs",
                "testenv:notincluded",
            ],
        ),
        (
            ["--showconfig", "-l"],
            [
                "tox",
                "tox:versions",
                "testenv:py37",
                "testenv:py27",
                "testenv:pypi",
                "testenv:docs",
            ],
        ),
        (["--showconfig", "-e", "py37,py36"], ["testenv:py37", "testenv:py36"]),
    ],
    ids=["all", "default_only", "-e"],
)
def test_showconfig(cmd, setup_mixed_conf, args, expected):
    parser = load_config(args, cmd)
    found_sections = parser.sections()
    assert found_sections == expected


def test_showconfig_interpolation(cmd, initproj):
    initproj(
        "no_interpolation",
        filedefs={
            "tox.ini": """
        [tox]
        envlist = %s
        [testenv:%s]
        commands = python -c "print('works')"
        """,
        },
    )
    load_config(("--showconfig",), cmd)


def test_config_specific_ini(tmpdir, cmd):
    ini = tmpdir.ensure("hello.ini")
    output = load_config(("-c", ini, "--showconfig"), cmd)
    assert output.get("tox", "toxinipath") == ini


def test_override_workdir(cmd, initproj):
    baddir = "badworkdir-123"
    gooddir = "overridden-234"
    initproj(
        "overrideworkdir-0.5",
        filedefs={
            "tox.ini": """
        [tox]
        toxworkdir={}
        """.format(
                baddir,
            ),
        },
    )
    result = cmd("--workdir", gooddir, "--showconfig")
    assert not result.ret
    assert gooddir in result.out
    assert baddir not in result.out
    assert py.path.local(gooddir).check()
    assert not py.path.local(baddir).check()
