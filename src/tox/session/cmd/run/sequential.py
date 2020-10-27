"""
Run tox environments in sequential order.
"""
from datetime import datetime
from typing import Dict, Tuple

from colorama import Fore

from tox.config.cli.parser import ToxParser
from tox.execute.api import Outcome
from tox.plugin.impl import impl
from tox.session.common import env_list_flag
from tox.session.state import State

from .common import env_run_create_flags
from .single import run_one


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("run", ["r"], "run environments", run_sequential)
    env_list_flag(our)
    env_run_create_flags(our)


def run_sequential(state: State) -> int:
    status_codes: Dict[str, Tuple[int, float]] = {}
    for name in state.env_list(everything=False):
        tox_env = state.tox_env(name)
        start_one = datetime.now()
        outcome = run_one(tox_env, state.options.recreate, state.options.no_test)
        duration = (datetime.now() - start_one).total_seconds()
        status_codes[name] = outcome, duration
    return report(state.options.start, status_codes, state.options.is_colored)


def report(start: datetime, status_dict: Dict[str, Tuple[int, float]], is_colored: bool) -> int:
    def _print(color: int, message: str) -> None:
        print(f"{color if is_colored else ''}{message}{Fore.RESET if is_colored else ''}")

    end = datetime.now()
    all_ok = True
    for name, (status, duration_one) in status_dict.items():
        ok = status == Outcome.OK
        msg = "OK " if ok else f"FAIL code {status}"
        _print(Fore.GREEN if ok else Fore.RED, f"  {name}: {msg}({duration_one:.2f}s)")
        all_ok = ok and all_ok
    duration = (end - start).total_seconds()
    if all_ok:
        _print(Fore.GREEN, f"  congratulations :) ({duration:.2f}s)")
        return Outcome.OK
    else:
        _print(Fore.RED, f"  evaluation failed :( ({duration:.2f}s)")
        return -1
