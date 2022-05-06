"""
Display the version information about tox.
"""
from __future__ import annotations

from pathlib import Path

from tox.config.cli.parser import ToxParser
from tox.plugin import impl
from tox.plugin.manager import MANAGER


@impl
def tox_add_option(parser: ToxParser) -> None:
    import tox
    from tox.version import version

    parser.add_argument(
        "--version",
        action="version",
        version=f"{version} from {Path(tox.__file__).absolute()}.\n{get_registered_plugins()}",
    )


def get_registered_plugins():
    out = ["registered plugins:"]
    plugin_dist_info = MANAGER.manager.list_plugin_distinfo()
    if plugin_dist_info:
        for mod, egg_info in plugin_dist_info:
            source = getattr(mod, "__file__", repr(mod))
            out.append("    {}-{} at {}".format(egg_info.project_name, egg_info.version, source))
    else:
        out.append("None.")
    return "\n".join(out)
