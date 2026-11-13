"""Customize argparse logic for tox (also contains the base options)."""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from argparse import SUPPRESS, Action, ArgumentDefaultsHelpFormatter, ArgumentError, ArgumentParser, Namespace
from pathlib import Path
from types import GenericAlias, UnionType
from typing import TYPE_CHECKING, Any, Literal, Self, TypeVar, cast, overload
from weakref import WeakKeyDictionary

from colorama import Fore

from tox.plugin import NAME
from tox.util.ci import is_ci
from tox.util.redact import redact_argv
from tox.util.typing_compat import override

from .env_var import get_env_var
from .ini import IniConfig

if TYPE_CHECKING:
    from collections.abc import Callable, Container, Iterable, MutableMapping, Sequence
    from typing import Final

    from packaging.requirements import Requirement

    from tox.config.loader.api import Override
    from tox.session.env_select import CliEnv
    from tox.session.state import State

_N = TypeVar("_N")  # unbounded to match typeshed, argparse accepts any object as namespace

_ACTION_OF_TYPE: Final[MutableMapping[Action, type | UnionType]] = WeakKeyDictionary()
"""The value type an action's option was declared with (actions come from argparse, so no attribute can be added)."""

_ACTION_DEFAULT_SOURCE: Final[MutableMapping[Action, str]] = WeakKeyDictionary()
"""Where an action's default was overridden from (environment variable or user level configuration file)."""


class ArgumentParserWithEnvAndConfig(ArgumentParser):  # simplint: ignore[missing-from-all] internal parser base
    """Argument parser which updates its defaults by checking the configuration files and environmental variables.

    :param args: positional arguments passed to :class:`argparse.ArgumentParser`
    :param kwargs: keyword arguments passed to :class:`argparse.ArgumentParser`, ``file_config`` selects the
        configuration the defaults are read from

    :var file_config: the configuration the defaults are read from

    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # sub-parsers also construct an instance of the parser, but they don't get their own file config, but inherit
        self.file_config = kwargs.pop("file_config") if "file_config" in kwargs else IniConfig()
        kwargs["epilog"] = self.file_config.epilog
        super().__init__(*args, **kwargs)

    def fix_defaults(self) -> None:
        """Apply the environment variable and config file defaults to all arguments, sub-parsers included."""
        for action in self._actions:
            self.fix_default(action)

    def fix_default(self, action: Action) -> None:
        """Set the default of an argument from its environment variable or config file value, when one is set.

        :param action: the argument to update

        :raises RuntimeError: when a sub-parser was added without using the tox parser

        """
        if hasattr(action, "default") and hasattr(action, "dest") and action.default != SUPPRESS:
            of_type = self.get_type(action)
            key = action.dest
            outcome = get_env_var(key, of_type=of_type)
            if outcome is None and self.file_config:
                outcome = self.file_config.get(key, of_type=of_type)
            if outcome is not None:
                action.default, default_value = outcome
                if action.default is not None and callable(normalize := getattr(action, "normalize_default", None)):
                    action.default = normalize(action.default)
                _ACTION_DEFAULT_SOURCE[action] = default_value
        if isinstance(action, argparse._SubParsersAction):  # ruff:ignore[private-member-access]  # internal access
            for values in action.choices.values():
                if not isinstance(values, ToxParser):  # pragma: no cover  # setup not built by tests
                    msg = "detected sub-parser added without using our own add command"
                    raise RuntimeError(msg)  # ruff:ignore[type-check-without-type-error]  # documented contract
                values.fix_defaults()

    @staticmethod
    def get_type(action: Action) -> type | UnionType:
        """Get the type the values of an argument are converted to.

        :param action: the argument

        :returns: the type of the argument values, a list type for arguments that accept many values

        :raises TypeError: when the type of the argument cannot be determined

        """
        of_type = _ACTION_OF_TYPE.get(action)
        if of_type is None:
            of_type = _infer_type(action)
        return of_type

    @overload
    def parse_args(self, args: Iterable[str] | None = None, namespace: None = None) -> Namespace: ...

    @overload
    def parse_args(self, args: Iterable[str] | None, namespace: _N) -> _N: ...

    @overload
    def parse_args(self, *, namespace: _N) -> _N: ...

    @override
    def parse_args(
        self,
        args: Iterable[str] | None = None,
        namespace: _N | None = None,
    ) -> _N:
        res, argv = self.parse_known_args(list(args) if args is not None else None, namespace)
        if argv:
            self.error(
                f"unrecognized arguments: {' '.join(redact_argv(argv))}\n"
                "hint: if you tried to pass arguments to a command use -- to separate them from tox ones",
            )
        if getattr(res, "no_capture", False) and getattr(res, "result_json", None):
            self.error("argument -i/--no-capture: not allowed with argument --result-json")
        return cast("_N", res)


class HelpFormatter(ArgumentDefaultsHelpFormatter):
    """A help formatter that provides the default value and the source it comes from.

    :param prog: the program name shown in the usage line
    :param kwargs: keyword arguments passed to :class:`argparse.ArgumentDefaultsHelpFormatter`

    """

    def __init__(self, prog: str, **kwargs: Any) -> None:
        super().__init__(prog, max_help_position=30, width=240, **kwargs)

    @override
    def _get_help_string(self, action: Action) -> str | None:
        text: str = super()._get_help_string(action) or ""
        if (source := _ACTION_DEFAULT_SOURCE.get(action)) is not None:
            default = " (default: %(default)s)"
            if text.endswith(default):  # pragma: no branch  # other outcome untested
                # escape % as the result goes through one more %-formatting pass with the action variables
                text = f"{text[: -len(default)]} (default: %(default)s -> from {source.replace('%', '%%')})"
        return text

    def add_raw_text(self, text: str | None) -> None:
        """Add help text that is printed as is, without wrapping.

        :param text: the text to add, nothing is added when it is suppressed or ``None``

        """

        def keep(content: str) -> str:
            return content

        if text is not SUPPRESS and text is not None:
            self._add_item(keep, [text])


ToxParserT = TypeVar("ToxParserT", bound="ToxParser")
DEFAULT_VERBOSITY: Final[int] = 2
"""Verbosity used when no verbosity flag is given, an index into the log levels."""

CORE: Final[str] = "core"
"""Name of the core option group, which every sub-command inherits."""
ENV: Final[str] = "env"
"""Name of the environment option group, which sub-commands that select environments inherit."""
_INHERIT_ALL: Final[frozenset[str]] = frozenset({CORE, ENV})


class Parsed(Namespace):
    """CLI options.

    The annotations below declare the type each option has once its command registered it; an option belonging to
    another command is absent at runtime, so shared code paths read it via ``getattr`` with a fallback.

    """

    #: the number of ``-v`` flags passed
    verbose: int
    #: the number of ``-q`` flags passed
    quiet: int
    #: ``yes`` when the output is colored, ``no`` otherwise
    colored: Literal["yes", "no"]
    #: the color used for stderr output
    stderr_color: str
    #: seconds after which tox dumps its threads and exits, ``0`` disables it
    exit_and_dump_after: int
    #: the configuration file or folder passed with ``-c``, if any
    config_file: Path | None
    #: the tox working directory, if one was given
    work_dir: Path | None
    #: the project root directory, if one was given
    root_dir: Path | None
    #: the configuration overrides passed with ``--override``
    override: list[Override]
    #: the name of the sub-command to run
    command: str
    #: the arguments passed after ``--``
    remainder: list[str]

    #: the environments selected with ``-e``
    env: CliEnv
    #: the environment labels selected with ``-m``
    labels: list[str]
    #: the environment factors selected with ``-f``
    factors: list[str]
    #: the regular expression of environments to exclude
    skip_env: str
    #: the tox run engine used when an environment does not name one
    default_runner: str

    #: the file the JSON result report is written to, if any
    result_json: Path | None
    #: whether output capture is disabled
    no_capture: bool
    #: the value of ``PYTHONHASHSEED`` for the commands, ``None`` when it is not set
    hash_seed: int | None
    #: the Python executables to try first during discovery
    discover: list[str]
    #: whether the dependencies installed during environment setup are listed
    list_dependencies: bool

    #: whether environments are recreated before use
    recreate: bool
    #: whether the test commands are skipped
    no_test: bool
    #: whether only the package is built
    package_only: bool
    #: the package to install instead of building the project, if any
    install_pkg: Path | None
    #: whether execution stops after the first environment failure
    fail_fast: bool
    #: whether the package is installed in development mode
    develop: bool
    #: whether packaging environments are kept when ``recreate`` is set
    no_recreate_pkg: bool
    #: whether the package installation is skipped
    skip_pkg_install: bool
    #: whether dependency and package installation is skipped
    skip_env_install: bool
    #: whether missing interpreters are skipped, ``config`` defers to the configuration
    skip_missing_interpreters: Literal["config", "true", "false"] | bool  # devenv forces False after parsing
    #: the number of environments run in parallel
    parallel: int
    #: whether the output of parallel environments is shown live
    parallel_live: bool
    #: whether the spinner is disabled in parallel mode
    parallel_no_spinner: bool

    #: whether provisioning is skipped and fails instead, or the path its metadata is written to
    no_provision: bool | str
    #: whether the provisioning environment is kept when ``recreate`` is set
    no_recreate_provision: bool
    #: the directory of the development environment
    devenv_path: Path

    #: the dependency requirements forced into the environments
    force_dep: list[Requirement]
    #: whether the environments can see the system site packages
    site_packages: bool
    #: whether the environments copy files instead of linking them
    always_copy: bool
    #: whether pre-release versions are installed
    pre: bool

    @property
    def verbosity(self) -> int:
        """The reporting verbosity: the ``-v`` count minus the ``-q`` count, never below zero."""
        result: int = max(self.verbose - self.quiet, 0)
        return result

    @property
    def is_colored(self) -> bool:
        """``True`` when the output is colored."""
        return self.colored == "yes"


ArgumentArgs = tuple[tuple[str, ...], type[Any] | UnionType | None, dict[str, Any]]


def _infer_type(action: Action) -> type | UnionType:
    many: Final[bool] = action.nargs in {"+", "*"} or (isinstance(action.nargs, int) and action.nargs >= 1)
    if isinstance(action, argparse._AppendAction):  # ruff:ignore[private-member-access]  # internal access
        if many:
            of_type = cast("type[Any]", GenericAlias(list, (GenericAlias(list, (action.type or str,)),)))
        else:
            of_type = cast("type[Any]", GenericAlias(list, (action.type or str,)))
    # argparse has no public action class
    elif isinstance(action, argparse._StoreAction) and action.choices:  # ruff:ignore[private-member-access]
        of_type = cast("type[Any]", Literal[tuple(action.choices)])  # ty: ignore[invalid-type-form] # pyrefly: ignore[invalid-literal] # choices are only known at runtime and no checker can express a Literal built from them
        if many:
            of_type = cast("type[Any]", GenericAlias(list, (of_type,)))
    elif many:
        of_type = cast("type[Any]", GenericAlias(list, (action.type or str,)))
    elif action.default is not None:
        of_type = type(action.default)
    # argparse has no public action class
    elif isinstance(action, argparse._StoreConstAction) and action.const is not None:  # ruff:ignore[private-member-access]
        of_type = type(action.const)
    else:
        raise TypeError(action)
    return of_type


def _values_for_option(action: Action) -> int | None:
    if action.nargs in {"+", "*"}:
        return None
    return action.nargs if isinstance(action.nargs, int) else 1


def _option_takes_command_as_value(action: Action, index: int, args_list: list[str], commands: Container[str]) -> bool:
    return action.nargs in {"?", "*"} and index + 1 < len(args_list) and args_list[index + 1] in commands


class ToxParser(ArgumentParserWithEnvAndConfig):
    """Argument parser for tox.

    :param args: positional arguments passed to :class:`ArgumentParserWithEnvAndConfig`
    :param root: whether the base options are added, set for the top-level parser
    :param add_cmd: whether a sub-command group is added to take the tox commands
    :param kwargs: keyword arguments passed to :class:`ArgumentParserWithEnvAndConfig`

    :var of_cmd: the command this parser was added for, ``None`` for the top-level parser
    :var inherit: the option groups, ``core`` and ``env``, this parser takes from its parent
    :var handlers: the command and alias names mapped to their sub-parser and handler

    """

    def __init__(self, *args: Any, root: bool = False, add_cmd: bool = False, **kwargs: Any) -> None:
        self.of_cmd: str | None = None
        self.inherit: frozenset[str] = _INHERIT_ALL
        self.handlers: dict[str, tuple[ToxParser, Callable[[State], int]]] = {}
        self._arguments: list[ArgumentArgs] = []
        self._groups: list[
            tuple[
                tuple[str | None, ...],
                dict[
                    str, Any  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
                ],
                list[
                    tuple[
                        dict[
                            str,
                            Any,  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
                        ],
                        list[ArgumentArgs],
                    ]
                ],
            ]
        ] = []
        super().__init__(*args, **kwargs)
        if root is True:
            self._add_base_options()
        if add_cmd is True:
            msg = "tox command to execute (by default legacy)"
            self._cmd: argparse._SubParsersAction[ToxParser] | None = self.add_subparsers(
                title="subcommands", description=msg, dest="command"
            )
            self._cmd.required = False
            self._cmd.default = "legacy"
        else:
            self._cmd = None

    def _add_base_options(self) -> None:
        """Argument options that always make sense."""
        _add_core_arguments(self)
        self.fix_defaults()

    @classmethod
    def base(cls) -> Self:
        """Create a root parser without the help option.

        :returns: the root parser

        """
        return cls(add_help=False, root=True)

    @classmethod
    def core(cls) -> Self:
        """Create the root parser of the tox command, which accepts sub-commands.

        :returns: the root parser

        """
        return cls(
            prog=NAME,
            formatter_class=HelpFormatter,
            add_cmd=True,
            root=True,
            description="create and set up environments to run command(s) in them",
        )

    def add_command(
        self,
        cmd: str,
        aliases: Sequence[str],
        help_msg: str,
        handler: Callable[[State], int],
        *,
        inherit: frozenset[str] = _INHERIT_ALL,
    ) -> ArgumentParser:
        """Register a sub-command with its own parser and handler.

        :param cmd: the name of the sub-command
        :param aliases: other names the sub-command can be invoked with
        :param help_msg: the help text of the sub-command
        :param handler: the function that runs the sub-command
        :param inherit: the option groups the sub-command inherits from the root parser

        :returns: the parser of the sub-command

        :raises RuntimeError: when this parser does not accept sub-commands

        """
        if self._cmd is None:
            msg = "no sub-command group allowed"
            raise RuntimeError(msg)
        sub_parser: ToxParser = self._cmd.add_parser(
            cmd,
            help=help_msg,
            aliases=aliases,
            formatter_class=HelpFormatter,
            file_config=self.file_config,
        )
        sub_parser.of_cmd = cmd
        sub_parser.inherit = inherit
        content = sub_parser, handler
        self.handlers[cmd] = content
        for alias in aliases:
            self.handlers[alias] = content
        defaults: dict[
            str, Any  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
        ] = {}
        self._copy_arguments(sub_parser, defaults)
        self._copy_groups(sub_parser, defaults)
        self._add_env_arguments(sub_parser, defaults)
        if defaults:
            sub_parser.set_defaults(**defaults)
        return sub_parser

    def _copy_arguments(
        self,
        sub_parser: ToxParser,
        defaults: dict[
            str, Any  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
        ],
    ) -> None:
        for args, of_type, kwargs in self._arguments:
            if CORE in sub_parser.inherit:
                sub_parser.add_argument(*args, of_type=of_type, **kwargs)
            else:
                defaults[self._dest_from(args, kwargs)] = kwargs.get("default")

    @staticmethod
    def _dest_from(
        args: tuple[str, ...],
        kwargs: dict[
            str, Any  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
        ],
    ) -> str:
        if dest := cast("str | None", kwargs.get("dest")):
            return dest
        args_list = list(args)
        args_list.sort(key=len, reverse=True)
        for arg in args_list:
            if arg.startswith("--"):
                return arg.lstrip("-").replace("-", "_")
        return args[0].lstrip("-").replace("-", "_")

    def _copy_groups(
        self,
        sub_parser: ToxParser,
        defaults: dict[
            str, Any  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
        ],
    ) -> None:
        for args, kwargs, excl in self._groups:
            if CORE in sub_parser.inherit:
                group = sub_parser.add_argument_group(*args, **kwargs)
                for e_kwargs, arguments in excl:
                    excl_group = group.add_mutually_exclusive_group(**e_kwargs)
                    for a_args, _, a_kwargs in arguments:
                        excl_group.add_argument(*a_args, **a_kwargs)
            else:
                for _, arguments in excl:
                    for a_args, _, a_kwargs in arguments:
                        defaults[self._dest_from(a_args, a_kwargs)] = a_kwargs.get("default")

    def _add_env_arguments(  # ruff:ignore[no-self-use]  # override keeps self
        self,
        sub_parser: ToxParser,
        defaults: dict[
            str, Any  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
        ],
    ) -> None:
        # Python treats an empty PYTHONHASHSEED as unset
        if (hashseed := os.environ.get("PYTHONHASHSEED", "")) not in {"", "random"}:
            hashseed_default = int(hashseed)
        else:
            # hash seed needs no cryptographic randomness
            hashseed_default = random.randint(1, 1024 if sys.platform == "win32" else 4294967295)  # ruff:ignore[suspicious-non-cryptographic-random-usage]

        if ENV not in sub_parser.inherit:
            defaults.update(
                result_json=None,
                hash_seed=hashseed_default,
                discover=[],
                list_dependencies=is_ci(),
            )
            return

        sub_parser.add_argument(
            "--result-json",
            dest="result_json",
            metavar="path",
            of_type=Path,
            default=None,
            help="write a JSON file with detailed information about all commands and results involved",
        )
        if sub_parser.of_cmd != "exec":
            sub_parser.add_argument(
                "-i",
                "--no-capture",
                dest="no_capture",
                action="store_true",
                default=False,
                help="disable output capture (mutually exclusive with --result-json and parallel mode)",
            )
        else:
            defaults["no_capture"] = False

        class SeedAction(Action):
            @override
            def __call__(
                self,
                parser: ArgumentParser,
                namespace: Namespace,
                values: str | Sequence[Any] | None,
                option_string: str | None = None,
            ) -> None:
                if values == "notset":
                    result = None
                else:
                    try:
                        result = int(cast("str", values))
                        if result <= 0:
                            msg = "must be greater than zero"
                            raise ValueError(msg)  # ruff:ignore[raise-within-try]  # maps error in try
                    except ValueError as exc:
                        raise ArgumentError(self, str(exc)) from exc
                setattr(namespace, self.dest, result)

        sub_parser.add_argument(
            "--hashseed",
            metavar="SEED",
            help="set PYTHONHASHSEED to SEED before running commands. Defaults to a random integer in the range "
            "[1, 4294967295] ([1, 1024] on Windows). Passing 'notset' suppresses this behavior.",
            action=SeedAction,
            of_type=int | None,
            default=hashseed_default,
            dest="hash_seed",
        )
        sub_parser.add_argument(
            "--discover",
            dest="discover",
            nargs="+",
            metavar="path",
            of_type=list[str],
            help="for Python discovery first try these Python executables",
            default=[],
        )
        list_deps = sub_parser.add_mutually_exclusive_group()
        list_deps.add_argument(
            "--list-dependencies",
            action="store_true",
            default=is_ci(),
            help="list the dependencies installed during environment setup",
        )
        list_deps.add_argument(
            "--no-list-dependencies",
            action="store_false",
            dest="list_dependencies",
            help="never list the dependencies installed during environment setup",
        )

    @override
    def add_argument_group(
        self,
        *args: Any,  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
        **kwargs: Any,  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
    ) -> argparse._ArgumentGroup:
        if self.of_cmd is not None or args in {("positional arguments",), ("optional arguments",)}:
            return super().add_argument_group(*args, **kwargs)
        excl: list[
            tuple[
                dict[
                    str, Any  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
                ],
                list[ArgumentArgs],
            ]
        ] = []
        group = _RecordingArgumentGroup(self, *args, excl=excl, **kwargs)
        self._action_groups.append(group)  # the same bookkeeping argparse add_argument_group performs
        self._groups.append((args, kwargs, excl))
        return group

    @override
    def add_argument(
        self,
        *args: str,
        of_type: type[Any]  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
        | UnionType
        | None = None,
        **kwargs: Any,  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
    ) -> Action:
        result = super().add_argument(*args, **kwargs)
        if self.of_cmd is None and result.dest != "help":
            self._arguments.append((args, of_type, kwargs))
            if hasattr(self, "_cmd") and self._cmd is not None and hasattr(self._cmd, "choices"):
                for parser in {id(v): v for v in self._cmd.choices.values()}.values():
                    if CORE in parser.inherit:
                        parser.add_argument(*args, of_type=of_type, **kwargs)
                    else:
                        parser.set_defaults(**{result.dest: result.default})
        if of_type is not None:
            _ACTION_OF_TYPE[result] = of_type
        return result

    @overload
    def parse_known_args(
        self, args: Iterable[str] | None = None, namespace: None = None
    ) -> tuple[Parsed, list[str]]: ...

    @overload
    def parse_known_args(self, args: Iterable[str] | None, namespace: _N) -> tuple[_N, list[str]]: ...

    @overload
    def parse_known_args(self, *, namespace: _N) -> tuple[_N, list[str]]: ...

    @override
    def parse_known_args(
        self,
        args: Iterable[str] | None = None,
        namespace: _N | None = None,
    ) -> tuple[_N, list[str]]:
        args_list: list[str] = list(args) if args is not None else sys.argv[1:]
        if (command_index := self._find_command(args_list)) is not None:
            args_list = [args_list[command_index], *args_list[:command_index], *args_list[command_index + 1 :]]
        elif tuple(args_list) not in {("--help",), ("-h",)} and (
            self._cmd is not None and "legacy" in self._cmd.choices
        ):
            # on help no mangling needed, and we also want to insert once we have legacy to insert
            args_list = ["legacy", *args_list]
        result = Parsed() if namespace is None else namespace
        _, remainder = super().parse_known_args(args_list, namespace=result)
        return cast("tuple[_N, list[str]]", (result, remainder))

    def _find_command(self, args_list: list[str]) -> int | None:
        if self._cmd is None or not args_list:
            return None
        # Legacy options live on its subparser, so include them when searching for the command.
        option_actions: Final[dict[str, Action]] = {
            name: action
            for parser in (self, self._cmd.choices.get("legacy"))
            if parser is not None
            for name, action in (
                parser._option_string_actions.items()  # ruff:ignore[private-member-access]  # no public lookup
            )
        }
        remaining_values: int | None = 0
        for index, arg in enumerate(args_list):
            if self._parse_optional(arg) is not None:  # argparse accepts negative numbers as values
                remaining_values = 0
            if remaining_values is None or remaining_values > 0:
                if remaining_values is not None:
                    remaining_values -= 1
            elif (action := option_actions.get(arg)) is not None and action.nargs != 0:
                if _option_takes_command_as_value(action, index, args_list, self._cmd.choices):
                    continue
                remaining_values = _values_for_option(action)
            elif arg in self._cmd.choices:
                return index
        return None


class _RecordingArgumentGroup(argparse._ArgumentGroup):  # ruff:ignore[private-member-access]  # internal access
    # Argument group that records its exclusive sub-groups so they replay onto later added sub-parsers.
    def __init__(
        self, container: ToxParser, *args: Any, excl: list[tuple[dict[str, Any], list[ArgumentArgs]]], **kwargs: Any
    ) -> None:
        super().__init__(container, *args, **kwargs)
        self._excl = excl

    @override
    def add_mutually_exclusive_group(
        self,
        **kwargs: Any,  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
    ) -> _RecordingMutuallyExclusiveGroup:
        arguments: list[ArgumentArgs] = []
        self._excl.append((kwargs, arguments))
        group = _RecordingMutuallyExclusiveGroup(self, recorded=arguments, **kwargs)
        self._mutually_exclusive_groups.append(group)  # the same bookkeeping argparse performs
        return group


class _RecordingMutuallyExclusiveGroup(  # internal access
    argparse._MutuallyExclusiveGroup  # ruff:ignore[private-member-access]  # internal access
):
    # Exclusive group that records added arguments so they replay onto later added sub-parsers.
    def __init__(self, container: _RecordingArgumentGroup, *, recorded: list[ArgumentArgs], **kwargs: Any) -> None:
        super().__init__(container, **kwargs)
        self._recorded = recorded

    @override
    def add_argument(
        self,
        *args: str,
        of_type: type[Any]  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
        | UnionType
        | None = None,
        **kwargs: Any,  # simplint: ignore[imprecise-annotation]  # argparse option values of any type
    ) -> Action:
        action = super().add_argument(*args, **kwargs)
        self._recorded.append((args, of_type, kwargs))
        return action


def _add_core_arguments(parser: ArgumentParser) -> None:
    _add_color_flags(parser)
    _add_verbosity_flags(parser)
    parser.add_argument(
        "--exit-and-dump-after",
        dest="exit_and_dump_after",
        metavar="seconds",
        default=0,
        type=int,
        help="dump tox threads after n seconds and exit the app - useful to debug when tox hangs, 0 means disabled",
    )
    parser.add_argument(
        "-c",
        "--conf",
        dest="config_file",
        metavar="file",
        default=None,
        type=Path,
        of_type=Path | None,
        help="configuration file/folder for tox (if not specified will discover one)",
    )
    parser.add_argument(
        "--workdir",
        dest="work_dir",
        metavar="dir",
        default=None,
        type=Path,
        of_type=Path | None,
        help="tox working directory (if not specified will be the folder of the config file)",
    )
    parser.add_argument(
        "--root",
        dest="root_dir",
        metavar="dir",
        default=None,
        type=Path,
        of_type=Path | None,
        help="project root directory (if not specified will be the folder of the config file)",
    )


def _add_color_flags(parser: ArgumentParser) -> None:
    if os.environ.get("NO_COLOR", ""):
        color = "no"
    elif os.environ.get("FORCE_COLOR", ""):
        color = "yes"
    elif (tty_compat := os.environ.get("TTY_COMPATIBLE", "")) in {"0", "1"}:
        color = "yes" if tty_compat == "1" else "no"
    elif os.environ.get("TERM", "") == "dumb":
        color = "no"
    else:
        color = "yes" if sys.stdout.isatty() else "no"

    parser.add_argument(
        "--colored",
        default=color,
        choices=["yes", "no"],
        help="should output be enriched with colors, default is yes unless TERM=dumb or NO_COLOR is defined.",
    )
    parser.add_argument(
        "--stderr-color",
        default="RED",
        choices=[*Fore.__dict__.keys()],
        help="color for stderr output, use RESET for terminal defaults.",
    )


def _add_verbosity_flags(parser: ArgumentParser) -> None:
    from tox.report import LEVELS  # ruff:ignore[import-outside-top-level]  # avoids an import cycle

    level_map = "|".join(f"{c}={logging.getLevelName(level)}" for c, level in sorted(LEVELS.items()))
    verbosity_group = parser.add_argument_group("verbosity")
    verbosity_group.description = (
        f"every -v increases, every -q decreases verbosity level, "
        f"default {logging.getLevelName(LEVELS[DEFAULT_VERBOSITY])}, map {level_map}"
    )
    verbosity = verbosity_group.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verbose",
        help="increase verbosity",
        default=DEFAULT_VERBOSITY,
    )
    verbosity.add_argument("-q", "--quiet", action="count", dest="quiet", help="decrease verbosity", default=0)


__all__ = [
    "CORE",
    "DEFAULT_VERBOSITY",
    "ENV",
    "HelpFormatter",
    "Parsed",
    "ToxParser",
]
