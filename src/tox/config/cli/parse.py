from typing import Dict, List, Tuple

from tox.report import setup_report

from .parser import Handler, Parsed, ToxParser


def get_options(*args) -> Tuple[Parsed, List[str], Dict[str, Handler]]:
    parsed, unknown = ToxParser.base().parse(args)
    guess_verbosity = parsed.verbosity
    setup_report(guess_verbosity)

    tox_parser = ToxParser.core()
    # noinspection PyUnresolvedReferences
    from tox.plugin.manager import MANAGER

    MANAGER.tox_add_option(tox_parser)
    tox_parser.fix_defaults()
    parsed, unknown = tox_parser.parse(args)
    if guess_verbosity != parsed.verbosity:
        setup_report(parsed.verbosity)  # pragma: no cover
    handlers = {k: p for k, (_, p) in tox_parser.handlers.items()}
    return parsed, unknown, handlers
