from __future__ import annotations

import sys
from argparse import SUPPRESS, Action, ArgumentParser, _SubParsersAction  # noqa: PLC2701
from pathlib import Path
from typing import Any

from docutils.core import publish_string
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        if self.target_name == "wheel":
            root = Path(self.root)
            (output := root / "build" / "man").mkdir(parents=True, exist_ok=True)
            (output / "tox.1").write_bytes(
                publish_string(generate_manpage_rst(), writer="manpage", settings_overrides={"report_level": 5})
            )


def generate_manpage_rst() -> str:
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from tox.config.cli.parse import _get_parser_doc  # noqa: PLC0415, PLC2701

    parser = _get_parser_doc()
    lines = [
        "===",
        "tox",
        "===",
        "",
        "---------------------------------------------------",
        "virtualenv-based automation of test activities",
        "---------------------------------------------------",
        "",
        ":Manual section: 1",
        ":Manual group: User Commands",
        "",
    ]
    lines.extend(_synopsis_section(parser))
    lines.extend(_description_section())
    lines.extend(_commands_section(parser))
    lines.extend(_global_options_section(parser))
    lines.extend(_files_section())
    lines.extend(_env_vars_section())
    lines.extend(_see_also_section())
    lines.extend(_author_section())
    return "\n".join(lines) + "\n"


def _synopsis_section(parser: ArgumentParser) -> list[str]:
    cmds = " | ".join(f"**{c}**" for c in _get_subcommands(parser))
    return [
        "SYNOPSIS",
        "--------",
        "",
        f"**tox** [*options*] [{cmds}] [*command-options*]",
        "",
    ]


def _get_subcommands(parser: ArgumentParser) -> list[str]:
    for action in parser._subparsers._actions:  # noqa: SLF001
        if isinstance(action, _SubParsersAction):
            return [ca.dest for ca in action._choices_actions]  # noqa: SLF001
    return []


def _description_section() -> list[str]:
    return [
        "DESCRIPTION",
        "-----------",
        "",
        "tox aims to automate and standardize testing in Python.",
        "It is part of a larger vision of easing the packaging,",
        "testing and release process of Python software.",
        "",
        "tox creates virtual environments for multiple Python versions,",
        "installs project dependencies, and runs tests in each environment.",
        "It supports parallel execution, custom test commands, and extensive configuration.",
        "",
    ]


def _commands_section(parser: ArgumentParser) -> list[str]:
    lines = ["COMMANDS", "--------", ""]
    for action in parser._subparsers._actions:  # noqa: SLF001
        if isinstance(action, _SubParsersAction):
            for choice_action in action._choices_actions:  # noqa: SLF001
                name = choice_action.dest
                subparser = action.choices[name]
                aliases = [a for a, s in action.choices.items() if s is subparser and a != name]
                alias_text = f" (*or* {', '.join(f'**{a}**' for a in aliases)})" if aliases else ""
                lines.append(f"**{name}**{alias_text}")
                lines.extend([f"    {choice_action.help}", ""])
    lines.extend(["For command-specific help, use: **tox** *command* **--help**", ""])
    return lines


def _global_options_section(parser: ArgumentParser) -> list[str]:
    lines = ["OPTIONS", "-------", ""]
    seen: set[int] = set()
    for action in parser._actions:  # noqa: SLF001
        if id(action) in seen or action.help == SUPPRESS or isinstance(action, _SubParsersAction):
            continue
        seen.add(id(action))
        if not (opts := _format_option(action)):
            continue
        lines.extend([opts, f"    {action.help}", ""])
    return lines


def _format_option(action: Action) -> str:
    opts = ", ".join(f"**{o}**" for o in action.option_strings) if action.option_strings else ""
    if action.metavar:
        metavar = action.metavar if isinstance(action.metavar, str) else action.metavar[0]
        opts += f" *{metavar}*"
    return opts if action.help else ""


def _files_section() -> list[str]:
    return [
        "FILES",
        "-----",
        "",
        "**tox.toml**",
        "    Primary configuration file in TOML format (recommended).",
        "",
        "**tox.ini**",
        "    Configuration file in INI format.",
        "",
        "**pyproject.toml**",
        "    Alternative configuration location under the ``[tool.tox]`` section.",
        "",
        "**setup.cfg**",
        "    Legacy configuration location (deprecated).",
        "",
        "The configuration files are searched in the order listed above. The first file found is used.",
        "",
    ]


def _env_vars_section() -> list[str]:
    return [
        "ENVIRONMENT VARIABLES",
        "---------------------",
        "",
        "``TOX_*``",
        "    Any tox configuration setting can be overridden via environment variables with the ``TOX_`` prefix.",
        "",
        "**NO_COLOR**",
        "    When set to any non-empty value, disables colored output.",
        "",
        "**FORCE_COLOR**",
        "    When set to any non-empty value, forces colored output even when stdout is not a terminal.",
        "",
        "**TOX_PARALLEL_NO_SPINNER**",
        "    When set, disables the progress spinner during parallel execution.",
        "",
    ]


def _see_also_section() -> list[str]:
    return [
        "SEE ALSO",
        "--------",
        "",
        "Full documentation: https://tox.wiki/",
        "",
        r"**pip**\(1), **pytest**\(1), **virtualenv**\(1)",
        "",
    ]


def _author_section() -> list[str]:
    return [
        "AUTHOR",
        "------",
        "",
        "tox development team",
        "",
        "https://github.com/tox-dev/tox",
    ]
