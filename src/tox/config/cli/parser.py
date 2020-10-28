"""
Customize argparse logic for tox (also contains the base options).
"""

import argparse
import logging
import os
import sys
from argparse import SUPPRESS, Action, ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace, _SubParsersAction
from itertools import chain
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, TypeVar, cast

from tox.config.source.ini.convert import StrConvert
from tox.plugin import NAME
from tox.session.state import State

from .env_var import get_env_var
from .ini import IniConfig

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # noqa


class ArgumentParserWithEnvAndConfig(ArgumentParser):
    """
    Argument parser which updates its defaults by checking the configuration files and environmental variables.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.file_config = IniConfig()
        kwargs["epilog"] = self.file_config.epilog
        super().__init__(*args, **kwargs)

    def fix_defaults(self) -> None:
        for action in self._actions:
            self.fix_default(action)

    def fix_default(self, action: Action) -> None:
        if hasattr(action, "default") and hasattr(action, "dest") and action.default != SUPPRESS:
            of_type = self.get_type(action)
            key = action.dest
            outcome = get_env_var(key, of_type=of_type)
            if outcome is None and self.file_config:
                outcome = self.file_config.get(key, of_type=of_type)
            if outcome is not None:
                action.default, default_value = outcome
                action.default_source = default_value  # type: ignore[attr-defined]
        if isinstance(action, argparse._SubParsersAction):  # noqa
            for values in action.choices.values():  # noqa
                if isinstance(values, ToxParser):
                    values.fix_defaults()

    @staticmethod
    def get_type(action: Action) -> Type[Any]:
        of_type: Optional[Type[Any]] = getattr(action, "of_type", None)
        if of_type is None:
            if isinstance(action, argparse._AppendAction):  # noqa
                of_type = List[action.type]  # type: ignore[name-defined]
            elif isinstance(action, argparse._StoreAction) and action.choices:  # noqa
                loc = locals()
                loc["Literal"] = Literal
                as_literal = f"Literal[{', '.join(repr(i) for i in action.choices)}]"
                of_type = eval(as_literal, globals(), loc)
            elif action.default is not None:
                of_type = type(action.default)
            elif isinstance(action, argparse._StoreConstAction) and action.const is not None:  # noqa
                of_type = type(action.const)
            else:  # pragma: no cover
                raise TypeError(action)  # pragma: no cover
        return of_type


class HelpFormatter(ArgumentDefaultsHelpFormatter):
    """
    A help formatter that provides the default value and the source it comes from.
    """

    def __init__(self, prog: str) -> None:
        super().__init__(prog, max_help_position=42, width=240)

    def _get_help_string(self, action: Action) -> Optional[str]:

        text = super()._get_help_string(action)  # noqa
        if text is not None:
            if hasattr(action, "default_source"):
                default = " (default: %(default)s)"
                if text.endswith(default):
                    text = f"{text[: -len(default)]} (default: %(default)s -> from %(default_source)s)"
        return text


Handler = Callable[[State], Optional[int]]


ToxParserT = TypeVar("ToxParserT", bound="ToxParser")
DEFAULT_VERBOSITY = 2


class Parsed(Namespace):
    @property
    def verbosity(self) -> int:
        result: int = max(self.verbose - self.quiet, 0)
        return result

    @property
    def is_colored(self) -> bool:
        return cast(bool, self.colored == "yes")


class ToxParser(ArgumentParserWithEnvAndConfig):
    """Argument parser for tox."""

    def __init__(self, *args: Any, root: bool = False, add_cmd: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if root is True:
            self._add_base_options()
        self.handlers: Dict[str, Tuple[Any, Handler]] = {}
        if add_cmd is True:
            self._cmd: Optional[_SubParsersAction] = self.add_subparsers(
                title="command", help="tox command to execute", dest="command"
            )
            self._cmd.required = False
            self._cmd.default = "run"

        else:
            self._cmd = None

    def add_command(self, cmd: str, aliases: Sequence[str], help_msg: str, handler: Handler) -> "ArgumentParser":
        if self._cmd is None:
            raise RuntimeError("no sub-command group allowed")
        sub_parser = self._cmd.add_parser(cmd, help=help_msg, aliases=aliases, formatter_class=HelpFormatter)
        content = sub_parser, handler
        self.handlers[cmd] = content
        for alias in aliases:
            self.handlers[alias] = content
        return cast(ToxParser, sub_parser)

    def add_argument(self, *args: str, of_type: Optional[Type[Any]] = None, **kwargs: Any) -> Action:
        result = super().add_argument(*args, **kwargs)
        if of_type is not None:
            result.of_type = of_type  # type: ignore[attr-defined]
        return result

    @classmethod
    def base(cls: Type[ToxParserT]) -> ToxParserT:
        return cls(add_help=False, root=True)

    @classmethod
    def core(cls: Type[ToxParserT]) -> ToxParserT:
        return cls(prog=NAME, formatter_class=HelpFormatter, add_cmd=True, root=True)

    def _add_base_options(self) -> None:
        """Argument options that always make sense."""
        from tox.report import LEVELS

        level_map = "|".join("{} - {}".format(c, logging.getLevelName(l)) for c, l in sorted(list(LEVELS.items())))
        verbosity_group = self.add_argument_group(
            f"verbosity=verbose-quiet, default {logging.getLevelName(LEVELS[3])}, map {level_map}",
        )
        verbosity = verbosity_group.add_mutually_exclusive_group()
        verbosity.add_argument(
            "-v", "--verbose", action="count", dest="verbose", help="increase verbosity", default=DEFAULT_VERBOSITY
        )
        verbosity.add_argument("-q", "--quiet", action="count", dest="quiet", help="decrease verbosity", default=0)

        converter = StrConvert()
        if converter.to_bool(os.environ.get("NO_COLOR", "")):
            color = "no"
        elif converter.to_bool(os.environ.get("FORCE_COLOR", "")):
            color = "yes"
        else:
            color = "yes" if sys.stdout.isatty() else "no"

        verbosity_group.add_argument(
            "--colored",
            default=color,
            choices=["yes", "no"],
            help="should output be enriched with colors",
        )
        self.fix_defaults()

    def parse_known_args(  # type: ignore[override]
        self, args: Optional[Sequence[str]], namespace: Optional[Parsed] = None
    ) -> Tuple[Parsed, List[str]]:
        result = Parsed() if namespace is None else namespace
        args = self._inject_default_cmd([] if args is None else args)
        _, args = super(ToxParser, self).parse_known_args(args, namespace=result)
        return result, args

    def _inject_default_cmd(self, args: Sequence[str]) -> Sequence[str]:
        # if the users specifies no command we imply he wants run, however for this to work we need to inject it onto
        # the argument parsers left side
        if self._cmd is None:  # no commands yet so must be all global, nothing to fix
            return args
        _global = {
            k: v
            for k, v in chain.from_iterable(
                ((j, isinstance(i, (argparse._StoreAction, argparse._AppendAction))) for j in i.option_strings)  # noqa
                for i in self._actions
                if hasattr(i, "option_strings")
            )
        }
        _global_single = {i[1:] for i in _global if len(i) == 2 and i.startswith("-")}
        cmd_at = next((j for j, i in enumerate(args) if i in self._cmd.choices), None)
        global_args: List[str] = []
        command_args: List[str] = []
        reorganize_to = cmd_at if cmd_at is not None else len(args)
        at = 0
        while at < reorganize_to:
            arg = args[at]
            needs_extra = False
            is_global = False
            if arg in _global:
                needs_extra = _global[arg]
                is_global = True
            elif arg.startswith("-") and not (set(arg[1:]) - _global_single):
                is_global = True
            (global_args if is_global else command_args).append(arg)
            at += 1
            if needs_extra:
                global_args.append(args[at])
                at += 1
        new_args = global_args
        new_args.append(self._cmd.default if cmd_at is None else args[cmd_at])
        new_args.extend(command_args)
        new_args.extend(args[reorganize_to + 1 :])
        return new_args


__all__ = (
    "DEFAULT_VERBOSITY",
    "Parsed",
    "ToxParser",
)
