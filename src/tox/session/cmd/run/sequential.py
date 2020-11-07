"""
Run tox environments in sequential order.
"""
import json
from datetime import datetime
from typing import Dict, List, Tuple

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
    status_codes: Dict[str, Tuple[int, float, List[float]]] = {}
    for name in state.env_list(everything=False):
        tox_env = state.tox_env(name)
        start_one = datetime.now()
        code, outcomes = run_one(tox_env, state.options.recreate, state.options.no_test)
        duration = (datetime.now() - start_one).total_seconds()
        status_codes[name] = code, duration, [o.elapsed for o in outcomes]
    result_json = getattr(state.options, "result_json", None)
    if result_json is not None:
        with open(result_json, "wt") as file_handler:
            json.dump(state.journal.content, file_handler, indent=2, ensure_ascii=False)
    return report(state.options.start, status_codes, state.options.is_colored)


def report(start: datetime, status_dict: Dict[str, Tuple[int, float, List[float]]], is_colored: bool) -> int:
    def _print(color: int, message: str) -> None:
        print(f"{color if is_colored else ''}{message}{Fore.RESET if is_colored else ''}")

    end = datetime.now()
    all_ok = True
    for name, (status, duration_one, duration_individual) in status_dict.items():
        ok = status == Outcome.OK
        msg = "OK " if ok else f"FAIL code {status}"
        extra = f"+cmd[{','.join(f'{i:.2f}' for i in duration_individual)}]" if len(duration_individual) else ""
        setup = duration_one - sum(duration_individual)
        out = f"  {name}: {msg}({duration_one:.2f}{f'=setup[{setup:.2f}]{extra}' if extra else ''} seconds)"
        _print(Fore.GREEN if ok else Fore.RED, out)
        all_ok = ok and all_ok
    duration = (end - start).total_seconds()
    if all_ok:
        _print(Fore.GREEN, f"  congratulations :) ({duration:.2f} seconds)")
        return Outcome.OK
    else:
        _print(Fore.RED, f"  evaluation failed :( ({duration:.2f} seconds)")
        return -1
