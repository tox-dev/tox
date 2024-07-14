from __future__ import annotations

from typing import TYPE_CHECKING

from tox.config.loader.section import Section
from tox.config.sets import ConfigSet
from tox.config.source.toml import ToxToml

# from tox.config.source.toml import PyProjectToml

if TYPE_CHECKING:
    from pathlib import Path

    from tests.conftest import ToxTomlCreator
    from tox.pytest import ToxProjectCreator


def test_conf_in_tox_toml(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": "[tox]\nenv_list=['a', 'b']"})

    outcome = project.run("l")
    outcome.assert_success()
    assert outcome.out == "default environments:\na -> [no description]\nb -> [no description]\n"


def test_source_toml_with_interpolated(tmp_path: Path) -> None:
    loader = ToxToml(tmp_path, content="[tox]\na = '%(c)s'").get_loader(Section(None, "tox"), {})
    assert loader is not None
    loader.load_raw("a", None, None)


def test_source_toml_ignore_non_testenv_sections(tmp_path: Path) -> None:
    loader = ToxToml(tmp_path, content="['mypy-rest_framework.compat.*']")
    res = list(loader.envs({"env_list": []}))  # type: ignore[arg-type]
    assert not res


def test_source_toml_ignore_invalid_factor_filters(tmp_path: Path) -> None:
    loader = ToxToml(tmp_path, content="[a]\nb= 'if c: d'")
    res = list(loader.envs({"env_list": []}))  # type: ignore[arg-type]
    assert not res


def test_source_toml_custom_non_testenv_sections(tox_toml_conf: ToxTomlCreator) -> None:
    """Validate that a plugin can load section with custom prefix overlapping testenv name."""

    class CustomConfigSet(ConfigSet):
        def register_config(self) -> None:
            self.add_config(
                keys=["a"],
                of_type=str,
                default="",
                desc="d",
            )

    config = tox_toml_conf("['testenv:foo']\n['custom:foo']\na = 'b'")
    known_envs = list(config._src.envs(config.core))  # noqa: SLF001
    assert known_envs
    custom_section = config.get_section_config(
        section=Section("custom", "foo"),
        base=[],
        of_type=CustomConfigSet,
        for_env=None,
    )
    assert custom_section["a"] == "b"


# def test_source_pyproject_toml_with_interpolated(tmp_path: Path) -> None:
#     loader = PyProjectToml(tmp_path, content="[tool.tox]\na = '%(c)s'").get_loader(Section(None, "tox"), {})
#     assert loader is not None
#     loader.load_raw("a", None, None)


# def test_source_pyproject_toml_ignore_non_testenv_sections(tmp_path: Path) -> None:
#     loader = PyProjectToml(tmp_path, content="['mypy-rest_framework.compat.*']")
#     res = list(loader.envs({"env_list": []}))  # type: ignore[arg-type]
#     assert not res


# def test_source_pyproject_toml_ignore_invalid_factor_filters(tmp_path: Path) -> None:
#     loader = PyProjectToml(tmp_path, content="[a]\nb= 'if c: d'")
#     res = list(loader.envs({"env_list": []}))  # type: ignore[arg-type]
#     assert not res
