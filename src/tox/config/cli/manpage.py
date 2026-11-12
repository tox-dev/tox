"""Generate the static manpage RST from the CLI parser."""

from __future__ import annotations

from argparse import (
    SUPPRESS,
    Action,
    ArgumentParser,
    _SubParsersAction,  # ruff:ignore[import-private-name]  # simplint: ignore[private-import-path]  # argparse has no public equivalent
)
from typing import TYPE_CHECKING

from ._parser_factory import get_parser_doc

if TYPE_CHECKING:
    from pathlib import Path


def main(output: Path) -> None:
    """Write a manpage for the current CLI parser.

    :param output: the destination file

    """
    rst = _generate_manpage_rst(get_parser_doc())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rst, encoding="utf-8")


def _generate_manpage_rst(parser: ArgumentParser) -> str:
    cmds = " | ".join(f"**{c}**" for c in _get_subcommands(parser))
    lines = [
        ":orphan:",
        "",
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
        "SYNOPSIS",
        "--------",
        "",
        f"**tox** [*options*] [{cmds}] [*command-options*]",
        "",
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
    lines.extend(_commands_section(parser))
    lines.extend(_global_options_section(parser))
    lines.extend(_static_sections())
    result = "\n".join(lines)
    return f"{result}\n"


def _get_subcommands(parser: ArgumentParser) -> list[str]:
    action = _subparser_action(parser)
    return [ca.dest for ca in action._choices_actions] if action else []  # ruff:ignore[private-member-access]  # argparse command order


def _subparser_action(parser: ArgumentParser) -> _SubParsersAction[ArgumentParser] | None:
    if parser._subparsers is None:  # ruff:ignore[private-member-access]  # argparse has no public subparser iterator
        return None
    return next(
        (
            action
            for action in parser._subparsers._actions  # ruff:ignore[private-member-access]  # argparse action group
            if isinstance(action, _SubParsersAction)
        ),
        None,
    )


def _commands_section(parser: ArgumentParser) -> list[str]:
    action = _subparser_action(parser)
    lines = ["COMMANDS", "--------", ""]
    if action is None:
        return lines
    choices = action.choices
    for choice_action in action._choices_actions:  # ruff:ignore[private-member-access]  # argparse command order
        name = choice_action.dest
        subparser = choices[name]
        aliases = [a for a, s in choices.items() if s is subparser and a != name]
        alias_text = f" (*or* {', '.join(f'**{a}**' for a in aliases)})" if aliases else ""
        lines.append(f"**{name}**{alias_text}")
        lines.extend([f"    {choice_action.help}", ""])
    lines.extend(["For command-specific help, use: **tox** *command* **--help**", ""])
    return lines


def _global_options_section(parser: ArgumentParser) -> list[str]:
    seen: set[int] = set()
    subparser_action = _subparser_action(parser)
    lines = ["OPTIONS", "-------", ""]
    for action in parser._actions:  # ruff:ignore[private-member-access]  # internal access
        if id(action) in seen or action.help == SUPPRESS or id(action) == id(subparser_action):
            continue
        seen.add(id(action))
        if not (opts := _format_option(action)):
            continue
        lines.extend([opts, f"    {action.help}", ""])
    return lines


def _format_option(action: Action) -> str:
    opts = ", ".join(f"**{o}**" for o in action.option_strings) if action.option_strings else ""
    if action.metavar:
        opts += f" *{(action.metavar if isinstance(action.metavar, str) else action.metavar[0])}*"
    return opts if action.help else ""


def _static_sections() -> list[str]:  # simplint: ignore[single-caller-helper]  # static sections
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
        "ENVIRONMENT VARIABLES",
        "---------------------",
        "",
        "``TOX_*``",
        "    ``TOX_<option>`` sets a CLI option's default. Use ``TOX_OVERRIDE`` to override configuration values.",
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
        "SEE ALSO",
        "--------",
        "",
        "Full documentation: https://tox.wiki/",
        "",
        r"**pip**\(1), **pytest**\(1), **virtualenv**\(1)",
        "",
        "AUTHOR",
        "------",
        "",
        "tox development team",
        "",
        "https://github.com/tox-dev/tox",
    ]


__all__ = [
    "main",
]
