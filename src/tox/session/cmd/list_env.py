"""
Print available tox environments.
"""
from __future__ import annotations

from tox.config.cli.parser import ToxParser
from tox.plugin import impl
from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("list", ["l"], "list environments", list_env)
    our.add_argument("-d", action="store_true", help="list just default envs", dest="list_default_only")
    our.add_argument("--no-desc", action="store_true", help="do not show description", dest="list_no_description")


def list_env(state: State) -> int:
    core = state.conf.core
    option = state.options

    default = core["env_list"]  # this should be something not affected by env-vars :-|

    extra = [] if option.list_default_only else [e for e in state.all_run_envs(with_skip=True) if e not in default]

    if not option.list_no_description and default:
        print("default environments:")
    max_length = max((len(env) for env in (default.envs + extra)), default=0)

    def report_env(name: str) -> None:
        if not option.list_no_description:
            tox_env = state.tox_env(name)
            text = tox_env.conf["description"]
            if not text.strip():
                text = "[no description]"
            text = text.replace("\n", " ")
            msg = f"{env.ljust(max_length)} -> {text}".strip()
        else:
            msg = env
        print(msg)

    for env in default:
        report_env(env)

    if not option.list_default_only and extra:
        if not option.list_no_description:
            if default:
                print("")
            print("additional environments:")
        for env in extra:
            report_env(env)
    return 0
