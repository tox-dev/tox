"""
Show materialized configuration of tox environments.
"""

from textwrap import indent

from tox.config.cli.parser import ToxParser
from tox.config.loader.stringify import stringify
from tox.config.sets import ConfigSet
from tox.plugin.impl import impl
from tox.session.common import env_list_flag
from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("config", ["c"], "show tox configuration", display_config)
    our.add_argument("-d", action="store_true", help="list just default envs", dest="list_default_only")
    env_list_flag(our)


def display_config(state: State) -> int:
    first = True
    if not state.options.env:
        print("[tox]")
        print_conf(state.conf.core)
        first = False
    for name in state.env_list(everything=False):
        tox_env = state.tox_env(name)
        if not first:
            print()
        first = False
        print(f"[testenv:{name}]")
        print(f"type = {type(tox_env).__name__}")
        print_conf(tox_env.conf)
    return 0


def print_conf(conf: ConfigSet) -> None:
    for key in conf:
        value = conf[key]
        as_str, multi_line = stringify(value)
        if multi_line and "\n" not in as_str:
            multi_line = False
        if multi_line and as_str.strip():
            print(f"{key} =\n{indent(as_str, prefix='  ')}")
        else:
            print(f"{key} ={' ' if as_str else ''}{as_str}")
    unused = conf.unused()
    if unused:
        print(f"# !!! unused: {', '.join(unused)}")
