"""Common functionality shared across multiple type of runs"""
import time
from argparse import Action, ArgumentParser, ArgumentTypeError, Namespace
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

from colorama import Fore

from tox.execute import Outcome
from tox.journal import write_journal
from tox.session.state import State


class SkipMissingInterpreterAction(Action):
    def __call__(
        self,
        parser: ArgumentParser,  # noqa
        args: Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None,
    ) -> None:
        value = "true" if values is None else values
        if value not in ("config", "true", "false"):
            raise ArgumentTypeError(f"value must be 'config', 'true', or 'false' (got {repr(value)})")
        setattr(args, self.dest, value)


def env_run_create_flags(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--result-json",
        dest="result_json",
        metavar="path",
        of_type=Path,
        default=None,
        help="write a json file with detailed information about all commands and results involved",
    )
    parser.add_argument(
        "-s",
        "--skip-missing-interpreters",
        default="config",
        metavar="v",
        nargs="?",
        action=SkipMissingInterpreterAction,
        help="don't fail tests for missing interpreters: {config,true,false} choice",
    )
    parser.add_argument(
        "-r",
        "--recreate",
        dest="recreate",
        help="recreate the tox environments",
        action="store_true",
    )
    parser.add_argument(
        "-n",
        "--notest",
        dest="no_test",
        help="do not run the test commands",
        action="store_true",
    )
    parser.add_argument(
        "-b",
        "--pkg-only",
        "--sdistonly",
        action="store_true",
        help="only perform the packaging activity",
        dest="package_only",
    )
    parser.add_argument(
        "--installpkg",
        help="use specified package for installation into venv, instead of creating an sdist.",
        default=None,
        of_type=Path,
    )
    parser.add_argument(
        "--develop",
        action="store_true",
        help="install package in develop mode",
        dest="develop",
    )
    parser.add_argument(
        "--hashseed",
        metavar="SEED",
        help="set PYTHONHASHSEED to SEED before running commands. Defaults to a random integer in the range "
        "[1, 4294967295] ([1, 1024] on Windows). Passing 'noset' suppresses this behavior.",
        type=str,
        default="noset",
    )
    parser.add_argument(
        "--discover",
        dest="discover",
        nargs="+",
        metavar="path",
        help="for python discovery first try the python executables under these paths",
        default=[],
    )


def run_and_report(state: State, result: Iterator[Tuple[str, Tuple[int, List[Outcome], float]]]) -> int:
    status_codes: Dict[str, Tuple[int, float, List[float]]] = {}
    for name, (code, outcomes, duration) in result:
        status_codes[name] = code, duration, [o.elapsed for o in outcomes]
    write_journal(getattr(state.options, "result_json", None), state.journal)
    return report(state.options.start, status_codes, state.options.is_colored)


def report(start: float, status_dict: Dict[str, Tuple[int, float, List[float]]], is_colored: bool) -> int:
    def _print(color: int, message: str) -> None:
        print(f"{color if is_colored else ''}{message}{Fore.RESET if is_colored else ''}")

    end = time.monotonic()
    all_ok = True
    for name, (status, duration_one, duration_individual) in status_dict.items():
        ok = status == Outcome.OK
        msg = "OK " if ok else f"FAIL code {status}"
        extra = f"+cmd[{','.join(f'{i:.2f}' for i in duration_individual)}]" if len(duration_individual) else ""
        setup = duration_one - sum(duration_individual)
        out = f"  {name}: {msg}({duration_one:.2f}{f'=setup[{setup:.2f}]{extra}' if extra else ''} seconds)"
        _print(Fore.GREEN if ok else Fore.RED, out)
        all_ok = ok and all_ok
    duration = end - start
    if all_ok:
        _print(Fore.GREEN, f"  congratulations :) ({duration:.2f} seconds)")
        return Outcome.OK
    else:
        _print(Fore.RED, f"  evaluation failed :( ({duration:.2f} seconds)")
        return -1
