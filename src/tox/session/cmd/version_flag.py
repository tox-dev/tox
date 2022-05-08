"""
Display the version information about tox.
"""
from __future__ import annotations

from pathlib import Path

import tox
from tox.config.cli.parser import ToxParser
from tox.plugin import impl
from tox.plugin.manager import MANAGER
from tox.version import version


@impl
def tox_add_option(parser: ToxParser) -> None:
    parser.add_argument(
        "--version",
        action="version",
        version=get_version_info(),
    )


def get_version_info() -> str:
    out = [f"{version} from {Path(tox.__file__).absolute()} "]
    plugin_info = MANAGER.manager.list_plugin_distinfo()
    if plugin_info:
        out.append("registered plugins:")
        for mod, egg_info in plugin_info:
            source = getattr(mod, "__file__", repr(mod))
            out.append(f"    {egg_info.project_name}-{egg_info.version} at {source}")
    return "\n".join(out)
