from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_conf_in_setup_cfg(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"setup.cfg": "[tox:tox]\nenv_list=\n a\n b"})

    outcome = project.run("l")
    outcome.assert_success()
    assert outcome.out == "default environments:\na -> [no description]\nb -> [no description]\n"


def test_bad_conf_setup_cfg(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"setup.cfg": "[tox]\nenv_list=\n a\n b"})
    filename = str(project.path / "setup.cfg")
    outcome = project.run("l", "-c", filename)
    outcome.assert_failed()
    assert outcome.out == f"ROOT: HandledError| could not recognize config file {filename}\n"
