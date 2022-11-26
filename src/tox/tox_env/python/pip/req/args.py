from __future__ import annotations

import bisect
import re
from argparse import Action, ArgumentParser, ArgumentTypeError, Namespace
from typing import IO, Any, NoReturn, Sequence


class _OurArgumentParser(ArgumentParser):
    def print_usage(self, file: IO[str] | None = None) -> None:  # noqa: U100
        """ """

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:  # noqa: U100
        message = "" if message is None else message
        msg = message.lstrip(": ").rstrip()
        if msg.startswith("error: "):
            msg = msg[len("error: ") :]
        raise ValueError(msg)


def build_parser() -> ArgumentParser:
    parser = _OurArgumentParser(add_help=False, prog="", allow_abbrev=False)
    _global_options(parser)
    _req_options(parser)
    return parser


def _global_options(parser: ArgumentParser) -> None:
    parser.add_argument("-i", "--index-url", "--pypi-url", dest="index_url", default=None)
    parser.add_argument("--extra-index-url", action=AddUniqueAction)
    parser.add_argument("--no-index", action="store_true", default=False)
    parser.add_argument("-c", "--constraint", action=AddUniqueAction, dest="constraints")
    parser.add_argument("-r", "--requirement", action=AddUniqueAction, dest="requirements")
    parser.add_argument("-e", "--editable", action=AddUniqueAction, dest="editables")
    parser.add_argument("-f", "--find-links", action=AddUniqueAction)
    parser.add_argument("--no-binary", choices=[":all:", ":none:"])  # TODO: colon separated package names
    parser.add_argument("--only-binary", choices=[":all:", ":none:"])  # TODO: colon separated package names
    parser.add_argument("--prefer-binary", action="store_true", default=False)
    parser.add_argument("--require-hashes", action="store_true", default=False)
    parser.add_argument("--pre", action="store_true", default=False)
    parser.add_argument("--trusted-host", action=AddSortedUniqueAction)
    parser.add_argument(
        "--use-feature",
        choices=["2020-resolver", "fast-deps"],
        action=AddSortedUniqueAction,
        dest="features_enabled",
    )


def _req_options(parser: ArgumentParser) -> None:
    parser.add_argument("--install-option", action=AddSortedUniqueAction)
    parser.add_argument("--global-option", action=AddSortedUniqueAction)
    parser.add_argument("--hash", action=AddSortedUniqueAction, type=_validate_hash)


_HASH = re.compile(r"sha(256:[a-f0-9]{64}|384:[a-f0-9]{96}|512:[a-f0-9]{128})")


def _validate_hash(value: str) -> str:
    if not _HASH.fullmatch(value):
        raise ArgumentTypeError(value)
    return value


class AddSortedUniqueAction(Action):
    def __call__(
        self,
        parser: ArgumentParser,  # noqa: U100
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,  # noqa: U100
    ) -> None:
        if getattr(namespace, self.dest, None) is None:
            setattr(namespace, self.dest, [])
        current = getattr(namespace, self.dest)
        if values not in current:
            bisect.insort(current, values)


class AddUniqueAction(Action):
    def __call__(
        self,
        parser: ArgumentParser,  # noqa: U100
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,  # noqa: U100
    ) -> None:
        if getattr(namespace, self.dest, None) is None:
            setattr(namespace, self.dest, [])
        current = getattr(namespace, self.dest)
        if values not in current:
            current.append(values)
