from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from tox.config.cli.parser import ToxParser
    from tox.config.sets import ConfigSet
    from tox.pytest import ToxProject, ToxProjectCreator
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
    "args",
    [
        pytest.param(("run", "-c", "{operator}", "-e", "-c=."), id="environment-value"),
        pytest.param(("run", "-e", "--", "-c", "{operator}"), id="positionals"),
        pytest.param(("--colored", "always", "-c", "{operator}", "list"), id="invalid-core-option"),
        pytest.param(("--inline-option", "-c=.", "list"), id="unknown-option-value"),
    ],
)
def test_inline_rejects_unselected_plugin(inline_project: ToxProject, tmp_path: Path, args: tuple[str, ...]) -> None:
    operator: Final = tmp_path / "operator" / "tox.toml"
    operator.parent.mkdir()
    operator.write_text("[env.test]\npackage = 'skip'\n")
    result: Final = inline_project.run(*(arg.format(operator=operator) for arg in args))

    result.assert_failed()
    assert not (inline_project.path / "imported").exists()


def test_inline_selected_plugin_loads(inline_project: ToxProject) -> None:
    inline_project.run("-c", str(inline_project.path / "tox.toml"), "--inline-option", "list").assert_success()

    assert (inline_project.path / "imported").read_text() == "yes"


def test_inline_compact_flags_keep_selected_config(inline_project: ToxProject, tmp_path: Path) -> None:
    operator: Final = tmp_path / "operator" / "tox.toml"
    operator.parent.mkdir()
    operator.write_text("[env.operator]\npackage = 'skip'\n")
    result: Final = inline_project.run("-vr", "-c", str(operator), "list")

    result.assert_success()
    assert "operator" in result.out
    assert not (inline_project.path / "imported").exists()


@pytest.fixture
def inline_project(tox_project: ToxProjectCreator) -> ToxProject:
    return tox_project({
        "tox.toml": "[env.contributor]\npackage = 'skip'\n",
        "toxfile.py": """
            from pathlib import Path

            from tox.config.cli.parser import ToxParser
            from tox.plugin import impl

            Path(__file__).with_name("imported").write_text("yes")

            @impl
            def tox_add_option(parser: ToxParser) -> None:
                parser.add_argument("--inline-option", action="store_true")
        """,
    })


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
