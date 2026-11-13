from __future__ import annotations

from typing import TYPE_CHECKING, cast

from tox.config.cli.parser import CORE
from tox.plugin import impl

from .run.common import env_run_create_flags, run_order

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.session.state import State
    from tox.tox_env.runner import RunToxEnv


@impl
def tox_add_option(parser: ToxParser) -> None:
    """Add the ``depends`` sub-command to the command line parser.

    :param parser: the parser to add the sub-command to

    """
    our = parser.add_command(
        "depends",
        ["de"],
        "visualize tox environment dependencies",
        depends,
        inherit=frozenset({CORE}),
    )
    env_run_create_flags(our, mode="depends")


def depends(state: State) -> int:
    """Show the environments and the environments they depend on, in the order they run.

    :param state: the state of the run

    :returns: the exit code

    """
    to_run_list = list(state.envs.iter(only_active=False))
    order, todo = run_order(state, to_run_list)
    print(f"Execution order: {', '.join(order)}")  # ruff:ignore[print]  # terminal output

    deps: dict[str, list[str]] = {k: [o for o in order if o in v] for k, v in todo.items()}
    deps["ALL"] = to_run_list

    def _handle(at: int, env: str) -> None:
        print("   " * at, end="")  # ruff:ignore[print]  # terminal output
        print(env, end="")  # ruff:ignore[print]  # terminal output
        if env != "ALL":
            run_env = cast("RunToxEnv", state.envs[env])
            packager_list: list[str] = []
            try:
                for pkg_env in run_env.package_envs:
                    packager_list.append(  # ruff:ignore[manual-list-comprehension]  # keeps partial results
                        pkg_env.name
                    )
            except Exception as exception:  # ruff:ignore[blind-except]  # failure must not stop run
                packager_list.append(f"... ({exception})")
            if names := " | ".join(packager_list):
                print(f" ~ {names}", end="")  # ruff:ignore[print]  # terminal output
        print()  # ruff:ignore[print]  # terminal output
        at += 1
        for dep in deps[env]:
            _handle(at, dep)

    _handle(0, "ALL")
    return 0
