"""
This module pulls together this package: create and parse CLI arguments for tox.
"""

from typing import Dict, List, Tuple

from tox.report import setup_report

from .parser import Handler, Parsed, ToxParser


def get_options(*args) -> Tuple[Parsed, List[str], Dict[str, Handler]]:
    guess_verbosity = _get_base(args)
    handlers, parsed, unknown = _get_all(args)
    if guess_verbosity != parsed.verbosity:
        setup_report(parsed.verbosity, parsed.is_colored)  # pragma: no cover
    return parsed, unknown, handlers


def _get_base(args):
    """First just load the base options (verbosity+color) to setup the logging framework."""
    tox_parser = ToxParser.base()
    parsed, unknown = tox_parser.parse(args)
    guess_verbosity = parsed.verbosity
    setup_report(guess_verbosity, parsed.is_colored)
    return guess_verbosity


def _get_all(args):
    """Parse all the options."""
    tox_parser = _get_parser()
    parsed, unknown = tox_parser.parse(args)
    handlers = {k: p for k, (_, p) in tox_parser.handlers.items()}
    return handlers, parsed, unknown


def _get_parser():
    tox_parser = ToxParser.core()  # load the core options
    # plus options setup by plugins
    from tox.plugin.manager import MANAGER  # noqa

    MANAGER.tox_add_option(tox_parser)
    tox_parser.fix_defaults()
    return tox_parser


__all__ = ("get_options",)
