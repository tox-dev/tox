"""
This module pulls together this package: create and parse CLI arguments for tox.
"""

from typing import Dict, Optional, Sequence, Tuple, cast

from tox.config.source import Source, discover_source
from tox.report import ToxHandler, setup_report

from .parser import Handler, Parsed, ToxParser

Handlers = Dict[str, Handler]


def get_options(*args: str) -> Tuple[Parsed, Handlers, Optional[Sequence[str]], ToxHandler, Source]:
    pos_args: Optional[Tuple[str, ...]] = None
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
        setup_report(parsed.verbosity, parsed.is_colored)  # pragma: no cover
    return parsed, cmd_handlers, pos_args, log_handler, source


def _get_base(args: Sequence[str]) -> Tuple[int, ToxHandler, Source]:
    """First just load the base options (verbosity+color) to setup the logging framework."""
    tox_parser = ToxParser.base()
    parsed, _ = tox_parser.parse_known_args(args)
    guess_verbosity = parsed.verbosity
    handler = setup_report(guess_verbosity, parsed.is_colored)
    from tox.plugin.manager import MANAGER  # noqa # load the plugin system right after we set up report

    source = discover_source(parsed.config_file, parsed.root_dir)

    MANAGER.load_inline_plugin(source.path)

    return guess_verbosity, handler, source


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


def _get_parser_doc() -> ToxParser:
    # trigger register of tox env types (during normal run we call this later to handle plugins)
    from tox.plugin.manager import MANAGER  # pragma: no cover
    from tox.tox_env.register import REGISTER  # pragma: no cover

    REGISTER._register_tox_env_types(MANAGER)  # pragma: no cover

    return _get_parser()  # pragma: no cover


__all__ = (
    "get_options",
    "Handlers",
)
