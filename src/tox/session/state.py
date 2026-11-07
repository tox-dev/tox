from __future__ import annotations

import sys
from itertools import chain, tee
from typing import TYPE_CHECKING

from tox.config.main import Config
from tox.journal import Journal
from tox.plugin import impl
from tox.plugin.manager import MANAGER

from .env_select import EnvSelector

if TYPE_CHECKING:
    from collections.abc import Sequence

    from tox.config.cli.parse import Options
    from tox.config.cli.parser import ToxParser


__all__ = [
    "MANAGER",
    "Config",
    "EnvSelector",
    "Journal",
    "State",
    "impl",
    "tox_add_option",
]


class State:
    """
    Runtime state holder.

    :param options: the parsed command line options and the command handlers
    :param args: the command line arguments tox was started with
    :ivar conf: the configuration of this run
    """

    def __init__(self, options: Options, args: Sequence[str]) -> None:
        (extended_envs,) = tee(chain.from_iterable(MANAGER.tox_extend_envs()), 1)
        self.conf = Config.make(options.parsed, options.pos_args, options.source, extended_envs)
        self.conf.core.add_constant(
            keys=["on_platform"],
            desc="platform we are running on",
            value=sys.platform,
        )
        self._options = options
        self.args = args
        self._journal: Journal = Journal(options.parsed.result_json is not None)
        self._selector: EnvSelector | None = None

    @property
    def envs(self) -> EnvSelector:
        """Access to the tox environments, selected on first access."""
        if self._selector is None:
            self._selector = EnvSelector(self)
        return self._selector


@impl
def tox_add_option(parser: ToxParser) -> None:
    """Add the ``--runner`` option to the command line parser.

    :param parser: the parser to add the option to
    """
    from tox.tox_env.register import REGISTER  # ruff:ignore[import-outside-top-level]  # avoids an import cycle

    parser.add_argument(
        "--runner",
        dest="default_runner",
        help="the tox run engine to use when not explicitly stated in tox env configuration",
        default=REGISTER.default_env_runner,
        choices=list(REGISTER.env_runners),
    )
