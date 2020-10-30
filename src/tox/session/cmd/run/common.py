"""Common functionality shared across multiple type of runs"""
from argparse import Action, ArgumentParser, ArgumentTypeError, Namespace
from pathlib import Path
from typing import Any, Optional, Sequence, Union


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
            raise ArgumentTypeError("value must be config, true or false")
        setattr(args, self.dest, value)


def env_run_create_flags(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--result-json",
        dest="resultjson",
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
