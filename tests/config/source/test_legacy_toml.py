from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_conf_in_legacy_toml(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"pyproject.toml": '[tool.tox]\nlegacy_tox_ini="""[tox]\nenv_list=\n a\n b\n"""'})

    outcome = project.run("l")
    outcome.assert_success()
    assert outcome.out == "default environments:\na -> [no description]\nb -> [no description]\n"
