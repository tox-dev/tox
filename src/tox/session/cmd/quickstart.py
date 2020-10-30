from tox.config.cli.parser import ToxParser
from tox.plugin.impl import impl
from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    parser.add_command(
        "quickstart",
        ["q"],
        "Command-line script to quickly tox config file for a Python project",
        quickstart,
    )


def quickstart(state: State) -> int:
    print("done quickstart")
    return 0
