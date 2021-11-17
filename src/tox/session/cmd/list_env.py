"""
Print available tox environments.
"""
from __future__ import annotations

from tox.config.cli.parser import ToxParser
from tox.plugin import impl
from tox.session.env_select import register_env_select_flags
from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("list", ["l"], "list environments", list_env)
    our.add_argument("-d", action="store_true", help="list just default envs", dest="list_default_only")
    our.add_argument("--no-desc", action="store_true", help="do not show description", dest="list_no_description")
    register_env_select_flags(our, default=None, group_only=True)


def list_env(state: State) -> int:
    option = state.conf.options
    default = list(state.envs.iter())

    extra = []
    if not option.list_default_only:
        default_entries = set(default)
        for env in state.envs.iter(only_active=False):
            if env not in default_entries:
                extra.append(env)

    if not option.list_no_description and default:
        print("default environments:")
    max_length = max((len(env) for env in (default + extra)), default=0)

    def report_env(name: str) -> None:
        if not option.list_no_description:
            tox_env = state.envs[name]
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
            if default:  # pragma: no branch
                print("")
            print("additional environments:")
        for env in extra:
            report_env(env)
    return 0
