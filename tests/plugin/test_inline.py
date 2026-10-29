from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tox.config.cli.parser import ToxParser
    from tox.config.sets import ConfigSet
    from tox.pytest import ToxProjectCreator
    from tox.session.state import State


def test_inline_tox_py(tox_project: ToxProjectCreator) -> None:
    def plugin() -> None:  # pragma: no cover # the code is copied to a python file
        import logging  # ruff:ignore[import-outside-top-level]

        from tox.plugin import impl  # ruff:ignore[import-outside-top-level]

        @impl
        def tox_add_option(parser: ToxParser) -> None:
            logging.warning("Add magic")
            parser.add_argument("--magic", action="store_true")

    project = tox_project({"toxfile.py": plugin})
    result = project.run("-h")
    result.assert_success()
    assert "--magic" in result.out


@pytest.mark.parametrize(
    ("files", "conf"),
    [
        pytest.param({}, "tox.toml", id="missing-file"),
        pytest.param({"tox.toml": "deps =\n    mypy\n"}, "tox.toml", id="malformed-file"),
        pytest.param({"pyproject.toml": ""}, "pyproject.toml", id="missing-tox-table"),
        pytest.param({}, "", id="directory-without-config"),
    ],
)
def test_inline_help_invalid_conf_loads_project_plugin(
    tox_project: ToxProjectCreator, tmp_path: Path, files: dict[str, str], conf: str
) -> None:
    def plugin() -> None:  # pragma: no cover - copied to a plugin module
        from tox.plugin import impl  # ruff:ignore[import-outside-top-level]

        @impl
        def tox_add_option(parser: ToxParser) -> None:
            parser.add_argument("--magic", action="store_true")

    project: Final = tox_project({"toxfile.py": plugin, **files})
    cwd: Final[Path] = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "toxfile.py").write_text("raise RuntimeError('plugin loaded from current directory')")

    result: Final = project.run("--help", "-c", str(project.path / conf), from_cwd=cwd)

    assert (result.code, "--magic" in result.out) == (0, True), repr(result)


def test_toxfile_unknown_hook_skipped(tox_project: ToxProjectCreator) -> None:
    def plugin() -> None:  # pragma: no cover
        from tox.plugin import impl  # ruff:ignore[import-outside-top-level]

        @impl
        def tox_nonexistent_hook() -> None: ...

    project = tox_project({"toxfile.py": plugin, "tox.toml": ""})
    result = project.run("l")
    result.assert_success()
    assert "skipping inline plugin" in result.out


def test_toxfile_py_w_ephemeral_envs(tox_project: ToxProjectCreator) -> None:
    """Ensure additional ephemeral tox envs can be plugin-injected."""

    def plugin() -> None:  # pragma: no cover # the code is copied to a python file
        from tox.config.loader.memory import MemoryLoader  # ruff:ignore[import-outside-top-level]
        from tox.plugin import impl  # ruff:ignore[import-outside-top-level]

        env_name = "sentinel-env-name"

        @impl
        def tox_extend_envs() -> tuple[str]:
            return (env_name,)

        @impl
        def tox_add_core_config(core_conf: ConfigSet, state: State) -> None:  # ruff:ignore[unused-function-argument]
            in_memory_config_loader = MemoryLoader(
                base=["sentinel-base"],
                commands_pre=["sentinel-cmd"],
                description="sentinel-description",
            )
            state.conf.memory_seed_loaders[env_name].append(
                in_memory_config_loader,  # src/tox/provision.py:provision()
            )

    project = tox_project({"toxfile.py": plugin})

    tox_list_result = project.run("list", "-qq")
    tox_list_result.assert_success()
    expected_additional_env_txt = "\n\nadditional environments:\nsentinel-env-name -> sentinel-description"
    assert expected_additional_env_txt in tox_list_result.out

    tox_config_result = project.run("config", "-e", "sentinel-env-name", "-qq")
    tox_config_result.assert_success()
    assert "base = sentinel-base" in tox_config_result.out

    tox_run_result = project.run("run", "-e", "sentinel-env-name", "-q")
    tox_run_result.assert_failed()
    underlying_expected_oserror_msg = (
        "[WinError 2] The system cannot find the file specified"
        if sys.platform == "win32"
        else "[Errno 2] No such file or directory: 'sentinel-cmd'"
    )
    expected_cmd_lookup_error_txt = (
        f"sentinel-env-name: Exception running subprocess {underlying_expected_oserror_msg!s}\n"
    )
    assert expected_cmd_lookup_error_txt in tox_run_result.out
