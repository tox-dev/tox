"""
Run tox environments in sequential order.
"""
from typing import Dict

from colorama import Fore

from tox.config.cli.parser import ToxParser
from tox.execute.api import Outcome
from tox.plugin.impl import impl
from tox.session.common import env_list_flag
from tox.session.state import State
from tox.tox_env.runner import RunToxEnv

from .common import env_run_create_flags
from .single import run_one


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("run", ["r"], "run environments", run_sequential)
    env_list_flag(our)
    env_run_create_flags(our)


def run_sequential(state: State) -> int:
    status_codes: Dict[str, int] = {}
    for name in state.env_list:
        tox_env = state.tox_envs[name]
        status_codes[name] = run_one(tox_env, state.options.recreate, state.options.no_test)
    return report(status_codes, state.tox_envs, state.options.is_colored)


def report(status_dict: Dict[str, int], tox_envs: Dict[str, RunToxEnv], is_colored: bool) -> int:  # noqa
    def _print(color: int, msg: str) -> None:
        print(f"{color if is_colored else ''}{msg}{Fore.RESET if is_colored else ''}")

    all_ok = True
    for name, status in status_dict.items():
        ok = status == Outcome.OK
        msg = "OK  " if ok else f"FAIL code {status}"
        _print(Fore.GREEN if ok else Fore.RED, f"  {name}: {msg}")
        all_ok = ok and all_ok
    if all_ok:
        _print(Fore.GREEN, "  congratulations :)")
        return Outcome.OK
    else:
        _print(Fore.RED, "  evaluation failed :(")
        return -1
