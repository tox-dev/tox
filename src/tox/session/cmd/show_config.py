from tox.config.cli.parser import ToxParser
from tox.plugin.impl import impl
from tox.session.common import env_list_flag
from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser):
    our = parser.add_command("config", ["c"], "show tox configuration", display_config)
    env_list_flag(our)


def display_config(state: State):
    if not state.options.env_list:
        for key in state.conf.core:
            print("{} = {}".format(key, state.conf.core[key]))
        print(",".join(state.conf.core.unused()))
    for name in state.tox_envs:
        tox_env = state.tox_envs[name]
        print()
        print(f"[{name}]")
        print("type = {}".format(type(tox_env).__name__))
        for key in tox_env.conf:
            print("{} = {}".format(key, tox_env.conf[key]))
        print(",".join(tox_env.conf.unused()))
