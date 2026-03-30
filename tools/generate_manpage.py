"""Generate the static manpage RST from the CLI parser."""

from __future__ import annotations

from argparse import SUPPRESS, Action, ArgumentParser, _SubParsersAction  # noqa: PLC2701
from pathlib import Path

from tox.config.cli.parse import _get_parser_doc  # noqa: PLC2701


def main() -> None:
    parser = _get_parser_doc()
    rst = generate_manpage_rst(parser)
    output = Path(__file__).parents[1] / "docs" / "man" / "tox.1.rst"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rst, encoding="utf-8")


def generate_manpage_rst(parser: ArgumentParser) -> str:
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
    if parser._subparsers is None:  # noqa: SLF001
        return []
    for action in parser._subparsers._actions:  # noqa: SLF001
        if isinstance(action, _SubParsersAction):
            return [ca.dest for ca in action._choices_actions]  # noqa: SLF001
    return []


def _commands_section(parser: ArgumentParser) -> list[str]:
    lines = ["COMMANDS", "--------", ""]
    if parser._subparsers is None:  # noqa: SLF001
        return lines
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


def _static_sections() -> list[str]:
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


if __name__ == "__main__":
    main()
