from typing import Dict, List

from tox.config.cli.parser import ToxParser
from tox.plugin.impl import impl
from tox.session.cmd.run.common import run_order
from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    parser.add_command(
        "depends",
        ["de"],
        "visualize tox environment dependencies",
        depends,
    )


def depends(state: State) -> int:
    to_run_list = list(state.env_list(everything=True))
    order, todo = run_order(state, to_run_list)
    print(f"Execution order: {', '.join(order)}")

    deps: Dict[str, List[str]] = {k: [o for o in order if o in v] for k, v in todo.items()}
    deps["ALL"] = to_run_list

    def _handle(at: int, env: str) -> None:
        if env not in order and env != "ALL":  # skipped envs
            return
        print("   " * at, end="")
        print(env, end="")
        if env != "ALL":
            names = " | ".join(e.conf.name for e in state.tox_env(env).package_envs())
            if names:
                print(f" ~ {names}", end="")
        print("")
        at += 1
        for dep in deps[env]:
            _handle(at, dep)

    _handle(0, "ALL")
    return 0
