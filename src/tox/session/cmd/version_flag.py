"""
Display the version information about tox.
"""
from pathlib import Path

from tox.config.cli.parser import ToxParser
from tox.plugin.impl import impl


@impl
def tox_add_option(parser: ToxParser) -> None:
    import tox
    from tox.version import __version__

    parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__} from {Path(tox.__file__).absolute()}",
    )
