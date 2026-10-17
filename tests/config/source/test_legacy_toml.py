from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_conf_in_legacy_toml(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"pyproject.toml": '[tool.tox]\nlegacy_tox_ini="""[tox]\nenv_list=\n a\n b\n"""'})

    outcome = project.run("l")
    outcome.assert_success()
    assert outcome.out == "default environments:\na -> [no description]\nb -> [no description]\n"


def test_conf_in_legacy_toml_with_utf8_bom_in_embedded_ini(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"pyproject.toml": '[tool.tox]\nlegacy_tox_ini="\\ufeff[tox]\\nenv_list=\\n a\\n b\\n"'})

    outcome = project.run("l")
    outcome.assert_success()
    assert outcome.out == "default environments:\na -> [no description]\nb -> [no description]\n"


def test_conf_in_legacy_toml_with_utf8_bom(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"pyproject.toml": '[tool.tox]\nlegacy_tox_ini="""[tox]\nenv_list=\n a\n b\n"""'})
    pyproject = project.path / "pyproject.toml"
    pyproject.write_bytes(b"\xef\xbb\xbf" + pyproject.read_bytes())

    outcome = project.run("l")
    outcome.assert_success()
    assert outcome.out == "default environments:\na -> [no description]\nb -> [no description]\n"
