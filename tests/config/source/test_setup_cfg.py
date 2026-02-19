from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_conf_in_setup_cfg(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"setup.cfg": "[tox:tox]\nenv_list=\n a\n b"})

    outcome = project.run("l")
    outcome.assert_success()
    assert outcome.out == "default environments:\na -> [no description]\nb -> [no description]\n"


def test_setup_cfg_without_tox_section(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"setup.cfg": "[tox]\nenv_list=\n a\n b"})
    filename = str(project.path / "setup.cfg")
    outcome = project.run("l", "-c", filename)
    outcome.assert_failed()
    assert outcome.out == f"ROOT: HandledError| could not recognize config file {filename}\n"


def test_setup_cfg_non_tox_section_not_discovered_as_env(tox_project: ToxProjectCreator) -> None:
    cfg = "[tox:tox]\nenv_list = py\n[tox:testenv]\npackage = skip\n[options]\npackages = find:\n"
    project = tox_project({"setup.cfg": cfg})
    outcome = project.run("l")
    outcome.assert_success()
    assert "find" not in outcome.out


def test_setup_cfg_does_not_block_pyproject_toml(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "setup.cfg": "[metadata]\nname = test-pkg\n",
        "pyproject.toml": "[tool.tox]\nenv_list = ['a']\n\n[tool.tox.env_run_base]\npackage = 'skip'\n",
    })
    outcome = project.run("l")
    outcome.assert_success()
    assert "a -> [no description]" in outcome.out


def test_setup_cfg_does_not_block_tox_toml(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "setup.cfg": "[metadata]\nname = test-pkg\n",
        "tox.toml": 'env_list = ["b"]\n\n[env_run_base]\npackage = "skip"\n',
    })
    outcome = project.run("l")
    outcome.assert_success()
    assert "b -> [no description]" in outcome.out


def test_setup_cfg_unicode_characters(tox_project: ToxProjectCreator) -> None:
    """Test that setup.cfg files with unicode characters can be read without UnicodeDecodeError."""
    cfg = """
        [tox:tox]
        env_list=
         a

        [tox:testenv:a]
        description = Test with emoji ❌ and unicode ✨
        package = skip
        """
    project = tox_project({"setup.cfg": dedent(cfg)})
    outcome = project.run("l")
    outcome.assert_success()
    assert "a ->" in outcome.out
