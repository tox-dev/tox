"""This module pulls together this package: create and parse CLI arguments for tox."""

from __future__ import annotations

import locale
import os
from contextlib import redirect_stderr, suppress
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

from tox.config.source import Source, discover_source
from tox.report import HandledError, ToxHandler, setup_report

from .parser import Parsed, ToxParser

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from tox.session.state import State


class Options(NamedTuple):
    parsed: Parsed
    pos_args: Sequence[str] | None
    source: Source
    cmd_handlers: dict[str, Callable[[State], int]]
    log_handler: ToxHandler


def get_options(*args: str) -> Options:
    pos_args: tuple[str, ...] | None = None
    try:  # remove positional arguments passed to parser if specified, they are pulled directly from sys.argv
        pos_arg_at = args.index("--")
    except ValueError:
        pass
    else:
        pos_args = tuple(args[pos_arg_at + 1 :])
        args = args[:pos_arg_at]

    guess_verbosity, log_handler, source = _get_base(args)
    parsed, cmd_handlers = _get_all(args)
    if guess_verbosity != parsed.verbosity:
        log_handler.update_verbosity(parsed.verbosity)
    return Options(parsed, pos_args, source, cmd_handlers, log_handler)


def _get_base(args: Sequence[str]) -> tuple[int, ToxHandler, Source]:
    parsed: Final = Parsed()
    with (
        suppress(SystemExit),
        Path(os.devnull).open("w", encoding=locale.getpreferredencoding(do_setlocale=False)) as file_handler,
        redirect_stderr(file_handler),
    ):
        ToxParser.base().parse_known_args(args, namespace=parsed)
    guess_verbosity: Final = parsed.verbosity
    handler: Final = setup_report(guess_verbosity, parsed.is_colored)
    from tox.plugin.manager import MANAGER, Plugin  # ruff:ignore[import-outside-top-level]

    # Built-in and installed plugins can register option values before tox selects an inline plugin.
    preliminary: Final = Plugin()
    preliminary.load_plugins(None)
    pre_parser: Final = ToxParser.core()
    preliminary.tox_add_option(pre_parser)
    pre_parser.fix_defaults()
    selected: Final = Parsed()
    try:
        with (
            Path(os.devnull).open("w", encoding=locale.getpreferredencoding(do_setlocale=False)) as file_handler,
            redirect_stderr(file_handler),
        ):
            unknown: Final = pre_parser.parse_known_args(
                (arg for arg in args if arg not in {"-h", "--help", "--version"}), namespace=selected
            )[1]
    except SystemExit:
        MANAGER.load_plugins(None)
        return guess_verbosity, handler, _empty_source(None)
    first_unknown: Final = next(
        (at for at, arg in enumerate(args) if arg in unknown and arg.startswith("-")), len(args)
    )
    if any(
        at > first_unknown and (arg in {"-c", "--conf", "--root"} or arg.startswith(("-c=", "--conf=", "--root=")))
        for at, arg in enumerate(args)
    ):
        MANAGER.load_plugins(None)
        return guess_verbosity, handler, _empty_source(None)

    try:
        source = discover_source(selected.config_file, selected.root_dir)
    except HandledError:
        if {"-h", "--help"}.intersection(args):
            source = _empty_source(parsed.config_file)
        else:
            raise

    MANAGER.load_plugins(source.path)

    return guess_verbosity, handler, source


def _empty_source(config_file: Path | None) -> Source:
    from tox.config.source.tox_ini import ToxIni  # ruff:ignore[import-outside-top-level]

    # The placeholder path also selects the directory searched for toxfile.py.
    if config_file is None:
        return ToxIni(Path.cwd() / "tox.ini", content="")
    return ToxIni((config_file if config_file.is_dir() else config_file.parent) / "tox.ini", content="")


def _get_all(args: Sequence[str]) -> tuple[Parsed, dict[str, Callable[[State], int]]]:
    """Parse all the options."""
    tox_parser = _get_parser()
    try:
        import argcomplete  # ruff:ignore[import-outside-top-level]

        argcomplete.autocomplete(tox_parser)
    except ImportError:
        pass
    parsed, unknown = tox_parser.parse_known_args(args)
    parsed.remainder = unknown
    if getattr(parsed, "no_capture", False) and getattr(parsed, "result_json", None):
        tox_parser.error("argument -i/--no-capture: not allowed with argument --result-json")
    handlers = {k: p for k, (_, p) in tox_parser.handlers.items()}
    return parsed, handlers


def _get_parser() -> ToxParser:
    tox_parser = ToxParser.core()  # load the core options
    # plus options setup by plugins
    from tox.plugin.manager import MANAGER  # ruff:ignore[import-outside-top-level]

    MANAGER.tox_add_option(tox_parser)
    tox_parser.fix_defaults()
    return tox_parser


def _get_parser_doc() -> ToxParser:
    # trigger register of tox env types (during normal run we call this later to handle plugins)
    from tox.plugin.manager import MANAGER  # pragma: no cover  # ruff:ignore[import-outside-top-level]

    MANAGER.load_plugins(Path.cwd())

    parser = _get_parser()  # pragma: no cover
    # Remove epilog message from help when formatting website docs
    parser.epilog = None
    return parser


__all__ = (
    "Options",
    "get_options",
)
