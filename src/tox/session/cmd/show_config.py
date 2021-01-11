"""
Show materialized configuration of tox environments.
"""

from textwrap import indent
from typing import Iterable, List

from tox.config.cli.parser import ToxParser
from tox.config.loader.stringify import stringify
from tox.config.sets import ConfigSet
from tox.plugin.impl import impl
from tox.session.common import env_list_flag
from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("config", ["c"], "show tox configuration", show_config)
    our.add_argument("-d", action="store_true", help="list just default envs", dest="list_default_only")
    our.add_argument(
        "-k", nargs="+", help="list just configuration keys specified", dest="list_keys_only", default=[], metavar="key"
    )
    our.add_argument(
        "--core", action="store_true", help="show core options too when selecting an env with -e", dest="show_core"
    )
    env_list_flag(our)


def show_config(state: State) -> int:
    show_core = state.options.env.all or state.options.show_core
    keys: List[str] = state.options.list_keys_only
    # environments may define core configuration flags, so we must exhaust first the environments to tell the core part
    envs = list(state.env_list(everything=False))
    for at, name in enumerate(envs):
        tox_env = state.tox_env(name)
        print(f"[testenv:{name}]")
        if not keys:
            print(f"type = {type(tox_env).__name__}")
        print_conf(tox_env.conf, keys)
        if show_core or at + 1 != len(envs):
            print("")
    # no print core
    if show_core:
        print("[tox]")
        print_conf(state.conf.core, keys)
    return 0


def print_conf(conf: ConfigSet, keys: Iterable[str]) -> None:
    for key in keys if keys else conf:
        if key not in conf:
            continue
        try:
            value = conf[key]
        except Exception as exception:  # because e.g. the interpreter cannot be found
            as_str, multi_line = f"# Exception: {exception!r}", False
        else:
            as_str, multi_line = stringify(value)
        if multi_line and "\n" not in as_str:
            multi_line = False
        if multi_line and as_str.strip():
            print(f"{key} =\n{indent(as_str, prefix='  ')}")
        else:
            print(f"{key} ={' ' if as_str else ''}{as_str}")
    unused = conf.unused()
    if unused and not keys:
        print(f"# !!! unused: {', '.join(unused)}")
