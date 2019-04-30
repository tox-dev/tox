import shutil
import subprocess
import sys

import py
import pytest

from tox.exception import BadRequirement, MissingRequirement


@pytest.fixture(scope="session")
def next_tox_major():
    """a tox version we can guarantee to not be available"""
    return "10.0.0"


def test_provision_min_version_is_requires(newconfig, next_tox_major):
    with pytest.raises(MissingRequirement) as context:
        newconfig(
            [],
            """
            [tox]
            minversion = {}
        """.format(
                next_tox_major
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
        """
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
            """
            [tox]
            minversion = {}
            [testenv]
            basepython = what
        """.format(
                next_tox_major
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
            """
            [tox]
            minversion = {}
            [testenv:.tox]
            basepython = what
        """.format(
                next_tox_major
            ),
        )
    config = context.value.config
    base_python = config.envconfigs[".tox"].basepython
    assert base_python == "what"


def test_provision_bad_requires(newconfig, capsys, monkeypatch):
    with pytest.raises(BadRequirement):
        newconfig(
            [],
            """
            [tox]
            requires = sad >sds d ok
        """,
        )
    out, err = capsys.readouterr()
    assert "ERROR: failed to parse RequirementParseError" in out
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
        tox.config.ParseIni, "ensure_requires_satisfied", ensure_requires_satisfied
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
