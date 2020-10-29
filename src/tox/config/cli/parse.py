"""
This module pulls together this package: create and parse CLI arguments for tox.
"""

from typing import Dict, Optional, Sequence, Tuple, cast

from tox.report import setup_report

from .parser import Handler, Parsed, ToxParser

Handlers = Dict[str, Handler]


def get_options(*args: str) -> Tuple[Parsed, Handlers, Optional[Sequence[str]]]:
    pos_args: Optional[Tuple[str, ...]] = None
    try:  # remove positional arguments passed to parser if specified, they are pulled directly from sys.argv
        pos_arg_at = args.index("--")
        pos_args = tuple(args[pos_arg_at + 1 :])
        args = args[:pos_arg_at]
    except ValueError:
        pass

    guess_verbosity = _get_base(args)
    parsed, handlers = _get_all(args)
    if guess_verbosity != parsed.verbosity:
        setup_report(parsed.verbosity, parsed.is_colored)  # pragma: no cover
    return parsed, handlers, pos_args


def _get_base(args: Sequence[str]) -> int:
    """First just load the base options (verbosity+color) to setup the logging framework."""
    tox_parser = ToxParser.base()
    parsed, _ = tox_parser.parse_known_args(args)
    guess_verbosity = parsed.verbosity
    setup_report(guess_verbosity, parsed.is_colored)
    return guess_verbosity


def _get_all(args: Sequence[str]) -> Tuple[Parsed, Handlers]:
    """Parse all the options."""
    tox_parser = _get_parser()
    parsed = cast(Parsed, tox_parser.parse_args(args))
    handlers = {k: p for k, (_, p) in tox_parser.handlers.items()}
    return parsed, handlers


def _get_parser() -> ToxParser:
    tox_parser = ToxParser.core()  # load the core options
    # plus options setup by plugins
    from tox.plugin.manager import MANAGER  # noqa

    MANAGER.tox_add_option(tox_parser)
    tox_parser.fix_defaults()
    return tox_parser


__all__ = (
    "get_options",
    "Handlers",
)
