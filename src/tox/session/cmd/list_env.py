"""
Print available tox environments.
"""
from tox.config.cli.parser import ToxParser
from tox.plugin.impl import impl
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
    ignore = {core["provision_tox_env"]}.union(default)

    extra = [] if option.list_default_only else [e for e in state.env_list(everything=True) if e not in ignore]

    if not option.list_no_description and default:
        print("default environments:")
    max_length = max(len(env) for env in (default.envs + extra))

    def report_env(name: str) -> None:
        if not option.list_no_description:
            text = state.tox_env(name).conf["description"]
            if not text.strip():
                text = "[no description]"
            text = text.replace("\n", " ")
            msg = f"{e.ljust(max_length)} -> {text}".strip()
        else:
            msg = e
        print(msg)

    for e in default:
        report_env(e)
    if not option.list_default_only and extra:
        if not option.list_no_description:
            if default:
                print("")
            print("additional environments:")
        for e in extra:
            report_env(e)
    return 0
