from __future__ import absolute_import, unicode_literals

import os
import shutil
import subprocess
import sys

import py
import pytest
from pathlib2 import Path
from six.moves.urllib.parse import urljoin
from six.moves.urllib.request import pathname2url

from tox.exception import BadRequirement, MissingRequirement


@pytest.fixture(scope="session")
def next_tox_major():
    """a tox version we can guarantee to not be available"""
    return "10.0.0"


def test_provision_min_version_is_requires(newconfig, next_tox_major):
    with pytest.raises(MissingRequirement) as context:
        newconfig(
            [],
            """\
            [tox]
            minversion = {}
            """.format(
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


def test_provision_tox_change_name(newconfig):
    config = newconfig(
        [],
        """\
        [tox]
        provision_tox_env = magic
        """,
    )
    assert config.provision_tox_env == "magic"


def test_provision_basepython_global_only(newconfig, next_tox_major):
    """we don't want to inherit basepython from global"""
    with pytest.raises(MissingRequirement) as context:
        newconfig(
            [],
            """\
            [tox]
            minversion = {}
            [testenv]
            basepython = what
            """.format(
                next_tox_major,
            ),
        )
    config = context.value.config
    base_python = config.envconfigs[".tox"].basepython
    assert base_python == sys.executable


def test_provision_basepython_local(newconfig, next_tox_major):
    """however adhere to basepython when explicilty set"""
    with pytest.raises(MissingRequirement) as context:
        newconfig(
            [],
            """\
            [tox]
            minversion = {}
            [testenv:.tox]
            basepython = what
            """.format(
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
        tox.config.ParseIni, "ensure_requires_satisfied", ensure_requires_satisfied,
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


def test_provision_non_canonical_dep(
    cmd, initproj, monkeypatch, tox_wheel, magic_non_canonical_wheel,
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
