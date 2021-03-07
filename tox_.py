from tox.config.cli.parser import ToxParser
from tox.plugin.impl import impl


@impl
def tox_add_option(parser: ToxParser) -> None:
    parser.add_argument("--magic", action="store_true", help="provides some magic")
