"""Build the CLI parser for execution and generated documentation."""

from __future__ import annotations

from pathlib import Path

from .parser import ToxParser


def get_parser_doc() -> ToxParser:
    from tox.plugin.manager import MANAGER  # ruff:ignore[import-outside-top-level]  # import cycle

    MANAGER.load_plugins(Path.cwd())
    parser = get_parser()
    parser.epilog = None
    return parser


def get_parser() -> ToxParser:
    parser = ToxParser.core()
    from tox.plugin.manager import MANAGER  # ruff:ignore[import-outside-top-level]  # avoids an import cycle

    MANAGER.tox_add_option(parser)
    parser.fix_defaults()
    return parser


__all__ = [
    "get_parser",
    "get_parser_doc",
]
