"""Common functionality shared across multiple type of runs"""
import time
from argparse import Action, ArgumentParser, ArgumentTypeError, Namespace
from pathlib import Path
from typing import Any, Iterator, List, Optional, Sequence, Union

from colorama import Fore

from tox.execute import Outcome
from tox.journal import write_journal
from tox.session.cmd.run.single import ToxEnvRunResult
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


def run_and_report(state: State, result: Iterator[ToxEnvRunResult]) -> int:
    # manifest the results
    name_to_run = {r.name: r for r in result}
    runs = [name_to_run[n] for n in list(state.env_list(everything=False))]
    # write the journal
    write_journal(getattr(state.options, "result_json", None), state.journal)
    # report the outcome
    return report(state.options.start, runs, state.options.is_colored)


def report(start: float, runs: List[ToxEnvRunResult], is_colored: bool) -> int:
    def _print(color: int, message: str) -> None:
        print(f"{color if is_colored else ''}{message}{Fore.RESET if is_colored else ''}")

    end = time.monotonic()
    all_ok = True
    for run in runs:
        ok = run.code == Outcome.OK
        msg = ("SKIP" if run.skipped else "OK") if ok else f"FAIL code {run.code}"
        duration_individual = [o.elapsed for o in run.outcomes]
        extra = f"+cmd[{','.join(f'{i:.2f}' for i in duration_individual)}]" if len(duration_individual) else ""
        setup = run.duration - sum(duration_individual)
        out = f"  {run.name}: {msg} ({run.duration:.2f}{f'=setup[{setup:.2f}]{extra}' if extra else ''} seconds)"
        _print((Fore.YELLOW if run.skipped else Fore.GREEN) if ok else Fore.RED, out)
        all_ok = ok and all_ok
    duration = end - start
    if all_ok:
        _print(Fore.GREEN, f"  congratulations :) ({duration:.2f} seconds)")
        return Outcome.OK
    else:
        _print(Fore.RED, f"  evaluation failed :( ({duration:.2f} seconds)")
        return -1
