from __future__ import absolute_import, unicode_literals

import json
import os
import shutil
import subprocess
import sys

import py
import pytest
from virtualenv.info import IS_PYPY

if sys.version_info[:2] >= (3, 4):
    from pathlib import Path
else:
    from pathlib2 import Path

from six.moves.urllib.parse import urljoin
from six.moves.urllib.request import pathname2url

from tox.exception import BadRequirement, MissingRequirement


@pytest.fixture(scope="session")
def next_tox_major():
    """a tox version we can guarantee to not be available"""
    return "10.0.0"


@pytest.fixture(scope="session", params=["minversion", "min_version"])
def minversion_option(request):
    """both possible names for the minversion config option"""
    return request.param


def test_provision_min_version_is_requires(newconfig, minversion_option, next_tox_major):
    with pytest.raises(MissingRequirement) as context:
        newconfig(
            [],
            """\
            [tox]
            {} = {}
            """.format(
                minversion_option,
                next_tox_major,
            ),
        )
    config = context.value.config

    deps = [r.name for r in config.envconfigs[config.provision_tox_env].deps]
    assert deps == ["tox >= {}".format(next_tox_major)]
    assert config.run_provision is True
    assert config.toxworkdir
    assert config.toxinipath
    assert config.provision_tox_env == ".tox"
    assert config.ignore_basepython_conflict is False


def test_provision_config_has_minversion_and_requires(
    newconfig, minversion_option, next_tox_major
):
    with pytest.raises(MissingRequirement) as context:
        newconfig(
            [],
            """\
            [tox]
            {} = {}
            requires =
                setuptools > 2
                pip > 3
            """.format(
                minversion_option,
                next_tox_major,
            ),
        )
    config = context.value.config

    assert config.run_provision is True
    assert config.minversion == next_tox_major
    assert config.requires == ["setuptools > 2", "pip > 3"]


def test_provision_config_empty_minversion_and_requires(newconfig, next_tox_major):
    config = newconfig([], "")

    assert config.run_provision is False
    assert config.minversion is None
    assert config.requires == []


def test_provision_tox_change_name(newconfig):
    config = newconfig(
        [],
        """\
        [tox]
        provision_tox_env = magic
        """,
    )
    assert config.provision_tox_env == "magic"


def test_provision_basepython_global_only(newconfig, minversion_option, next_tox_major):
    """we don't want to inherit basepython from global"""
    with pytest.raises(MissingRequirement) as context:
        newconfig(
            [],
            """\
            [tox]
            {} = {}
            [testenv]
            basepython = what
            """.format(
                minversion_option,
                next_tox_major,
            ),
        )
    config = context.value.config
    base_python = config.envconfigs[".tox"].basepython
    assert base_python == sys.executable


def test_provision_basepython_local(newconfig, minversion_option, next_tox_major):
    """however adhere to basepython when explicitly set"""
    with pytest.raises(MissingRequirement) as context:
        newconfig(
            [],
            """\
            [tox]
            {} = {}
            [testenv:.tox]
            basepython = what
            """.format(
                minversion_option,
                next_tox_major,
            ),
        )
    config = context.value.config
    base_python = config.envconfigs[".tox"].basepython
    assert base_python == "what"


def test_provision_bad_requires(newconfig, capsys, monkeypatch):
    with pytest.raises(BadRequirement):
        newconfig(
            [],
            """\
            [tox]
            requires = sad >sds d ok
            """,
        )
    out, err = capsys.readouterr()
    assert "ERROR: failed to parse InvalidRequirement" in out
    assert not err


@pytest.fixture()
def plugin(monkeypatch, tmp_path):
    dest = tmp_path / "a"
    shutil.copytree(str(py.path.local(__file__).dirpath().join("plugin")), str(dest))
    subprocess.check_output([sys.executable, "setup.py", "egg_info"], cwd=str(dest))
    monkeypatch.setenv(str("PYTHONPATH"), str(dest))


def test_provision_cli_args_ignore(cmd, initproj, monkeypatch, plugin):
    import tox.config
    import tox.session

    prev_ensure = tox.config.ParseIni.ensure_requires_satisfied

    @staticmethod
    def ensure_requires_satisfied(config, requires, min_version):
        result = prev_ensure(config, requires, min_version)
        config.run_provision = True
        return result

    monkeypatch.setattr(
        tox.config.ParseIni,
        "ensure_requires_satisfied",
        ensure_requires_satisfied,
    )
    prev_get_venv = tox.session.Session.getvenv

    def getvenv(self, name):
        venv = prev_get_venv(self, name)
        venv.envconfig.envdir = py.path.local(sys.executable).dirpath().dirpath()
        venv.setupenv = lambda: True
        venv.finishvenv = lambda: True
        return venv

    monkeypatch.setattr(tox.session.Session, "getvenv", getvenv)
    initproj("test-0.1", {"tox.ini": "[tox]"})
    result = cmd("-a", "--option", "b")
    result.assert_success(is_run_test_env=False)


def test_provision_cli_args_not_ignored_if_provision_false(cmd, initproj):
    initproj("test-0.1", {"tox.ini": "[tox]"})
    result = cmd("-a", "--option", "b")
    result.assert_fail(is_run_test_env=False)


parametrize_json_path = pytest.mark.parametrize("json_path", [None, "missing.json"])


@parametrize_json_path
def test_provision_does_not_fail_with_no_provision_no_reason(cmd, initproj, json_path):
    p = initproj("test-0.1", {"tox.ini": "[tox]"})
    result = cmd("--no-provision", *([json_path] if json_path else []))
    result.assert_success(is_run_test_env=True)
    assert not (p / "missing.json").exists()


@parametrize_json_path
def test_provision_fails_with_no_provision_next_tox(
    cmd, initproj, minversion_option, next_tox_major, json_path
):
    p = initproj(
        "test-0.1",
        {
            "tox.ini": """\
                             [tox]
                             {} = {}
                             """.format(
                minversion_option,
                next_tox_major,
            )
        },
    )
    result = cmd("--no-provision", *([json_path] if json_path else []))
    result.assert_fail(is_run_test_env=False)
    if json_path:
        missing = json.loads((p / json_path).read_text("utf-8"))
        assert missing["minversion"] == next_tox_major


@parametrize_json_path
def test_provision_fails_with_no_provision_missing_requires(cmd, initproj, json_path):
    p = initproj(
        "test-0.1",
        {
            "tox.ini": """\
                             [tox]
                             requires =
                                 virtualenv > 99999999
                             """
        },
    )
    result = cmd("--no-provision", *([json_path] if json_path else []))
    result.assert_fail(is_run_test_env=False)
    if json_path:
        missing = json.loads((p / json_path).read_text("utf-8"))
        assert missing["requires"] == ["virtualenv > 99999999"]


@parametrize_json_path
def test_provision_does_not_fail_with_satisfied_requires(
    cmd, initproj, minversion_option, json_path
):
    p = initproj(
        "test-0.1",
        {
            "tox.ini": """\
                             [tox]
                             {} = 0
                             requires =
                                 setuptools > 2
                                 pip > 3
                             """.format(
                minversion_option
            )
        },
    )
    result = cmd("--no-provision", *([json_path] if json_path else []))
    result.assert_success(is_run_test_env=True)
    assert not (p / "missing.json").exists()


@parametrize_json_path
def test_provision_fails_with_no_provision_combined(
    cmd, initproj, minversion_option, next_tox_major, json_path
):
    p = initproj(
        "test-0.1",
        {
            "tox.ini": """\
                             [tox]
                             {} = {}
                             requires =
                                 setuptools > 2
                                 pip > 3
                             """.format(
                minversion_option,
                next_tox_major,
            )
        },
    )
    result = cmd("--no-provision", *([json_path] if json_path else []))
    result.assert_fail(is_run_test_env=False)
    if json_path:
        missing = json.loads((p / json_path).read_text("utf-8"))
        assert missing["minversion"] == next_tox_major
        assert missing["requires"] == ["setuptools > 2", "pip > 3"]


@pytest.fixture(scope="session")
def wheel(tmp_path_factory):
    """create a wheel for a project"""
    state = {"at": 0}

    def _wheel(path):
        state["at"] += 1
        dest_path = tmp_path_factory.mktemp("wheel-{}-".format(state["at"]))
        env = os.environ.copy()
        try:
            subprocess.check_output(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    "-w",
                    str(dest_path),
                    "--no-deps",
                    str(path),
                ],
                universal_newlines=True,
                stderr=subprocess.STDOUT,
                env=env,
            )
        except subprocess.CalledProcessError as exception:
            assert not exception.returncode, exception.output

        wheels = list(dest_path.glob("*.whl"))
        assert len(wheels) == 1
        wheel = wheels[0]
        return wheel

    return _wheel


THIS_PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def tox_wheel(wheel):
    return wheel(THIS_PROJECT_ROOT)


@pytest.fixture(scope="session")
def magic_non_canonical_wheel(wheel, tmp_path_factory):
    magic_proj = tmp_path_factory.mktemp("magic")
    (magic_proj / "setup.py").write_text(
        "from setuptools import setup\nsetup(name='com.magic.this-is-fun')",
    )
    return wheel(magic_proj)


@pytest.mark.skipif(IS_PYPY and sys.version_info[0] > 2, reason="fails on pypy3")
def test_provision_non_canonical_dep(
    cmd,
    initproj,
    monkeypatch,
    tox_wheel,
    magic_non_canonical_wheel,
):
    initproj(
        "w-0.1",
        {
            "tox.ini": """\
            [tox]
            envlist = py
            requires =
                com.magic.this-is-fun
                tox == {}
            [testenv:.tox]
            passenv = *
            """.format(
                tox_wheel.name.split("-")[1],
            ),
        },
    )
    find_links = " ".join(
        space_path2url(d) for d in (tox_wheel.parent, magic_non_canonical_wheel.parent)
    )

    monkeypatch.setenv(str("PIP_FIND_LINKS"), str(find_links))

    result = cmd("-a", "-v", "-v")
    result.assert_success(is_run_test_env=False)


def test_provision_requirement_with_environment_marker(cmd, initproj):
    initproj(
        "proj",
        {
            "tox.ini": """\
            [tox]
            requires =
                package-that-does-not-exist;python_version=="1.0"
            """,
        },
    )
    result = cmd("-e", "py", "-vv")
    result.assert_success(is_run_test_env=False)


def space_path2url(path):
    at_path = str(path)
    if " " not in at_path:
        return at_path
    return urljoin("file:", pathname2url(os.path.abspath(at_path)))


def test_provision_does_not_occur_in_devenv(newconfig, minversion_option, next_tox_major):
    """Adding --devenv should not change the directory where provisioning occurs"""
    with pytest.raises(MissingRequirement) as context:
        newconfig(
            ["--devenv", "my_devenv"],
            """\
            [tox]
            {} = {}
            """.format(
                minversion_option,
                next_tox_major,
            ),
        )
    config = context.value.config
    assert config.run_provision is True
    assert config.envconfigs[".tox"].envdir.basename != "my_devenv"
