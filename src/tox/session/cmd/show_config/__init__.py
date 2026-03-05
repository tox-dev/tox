"""Show materialized configuration of tox environments."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal, get_args

from tox.plugin import impl
from tox.session.cmd.run.common import env_run_create_flags
from tox.session.env_select import CliEnv, register_env_select_flags

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.session.state import State

ConfigFormat = Literal["ini", "json", "toml"]


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("config", ["c"], "show tox configuration", show_config)
    our.add_argument(
        "-k",
        nargs="+",
        help="list just configuration keys specified",
        dest="list_keys_only",
        default=[],
        metavar="key",
    )
    our.add_argument(
        "--core",
        action="store_true",
        help="show core options (by default is hidden unless -e ALL is passed)",
        dest="show_core",
    )
    our.add_argument(
        "--format",
        choices=get_args(ConfigFormat),
        default="ini",
        help="output format (default: %(default)s)",
        dest="config_format",
    )
    our.add_argument(
        "-o",
        "--output-file",
        of_type=Path,
        default=None,
        help="write output to file instead of stdout",
        dest="output_file",
    )
    register_env_select_flags(our, default=CliEnv())
    env_run_create_flags(our, mode="config")


def show_config(state: State) -> int:
    from .ini import show_config_ini  # noqa: PLC0415
    from .json_format import show_config_json  # noqa: PLC0415
    from .toml_format import show_config_toml  # noqa: PLC0415

    fmt: ConfigFormat = state.conf.options.config_format
    if fmt == "json":
        return show_config_json(state)
    if fmt == "toml":
        return show_config_toml(state)
    return show_config_ini(state)
